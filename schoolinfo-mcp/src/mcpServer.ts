// teacher_doc: document references and schedules, shared by stdio and HTTP.
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { version } from "../package.json";
import { resolveSchool, SchoolResolutionError } from "./client.js";
import { SCHOOL_KIND_REV } from "./codes.js";
import { findNeisSchool, fetchSchedule, formatSchedule } from "./neis.js";
import { listEvaluationDocs, fetchEvaluationBySeq, EVAL_ITEM_SPEC, CURRICULUM_ITEM_SPEC,
  FREE_SEMESTER_ITEM_SPEC, EvaluationParseError, type DisclosureItemSpec } from "./evaluation.js";
import { maskSensitiveUrl } from "./lib/fetch-with-retry.js";

const text = z.string().trim().min(1).max(100).refine((s) => !/[\x00-\x1f]/.test(s), "제어 문자는 허용하지 않습니다");
const year = z.number().int().min(2010).max(2100).describe("조회할 공시연도/학년도. 다른 연도 자동 대체 없음");
// The agent supplies the school from the conversation or workspace settings.
// Region and kind are optional disambiguators, not a mandatory user form.
const schoolInput = z.object({
  name: text.describe("AI가 대화·작업 설정에서 확인한 정확한 학교명. 사용자에게 매번 입력을 요구하지 않는다"),
  sido: text.optional().describe("동명이교 구분에 필요한 경우 확인한 시도명"),
  sgg: text.optional().describe("동명이교 구분에 필요한 경우 확인한 시군구명"),
  kind: z.enum(Object.values(SCHOOL_KIND_REV) as [string, ...string[]]).optional()
    .describe("동명이교 구분에 필요한 경우 확인한 학교급"),
  year,
}).strict();
const documentInput = schoolInput.extend({
  file_seq: z.string().regex(/^\d{1,20}$/).optional().describe("여러 첨부 중 조회할 식별자. 후보 목록에서 선택"),
}).strict();
const evaluationInput = documentInput.extend({
  semester: z.union([z.literal(1), z.literal(2)]).describe("평가계획의 자료 제출 회차 기준 학기"),
}).strict();
const readOnly = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true };

export const TOOL_NAMES = ["get_school_schedule", "get_curriculum_plan", "get_evaluation_plan", "get_free_semester_plan"] as const;
export const defaultServices = { resolveSchool, findNeisSchool, fetchSchedule, listEvaluationDocs, fetchEvaluationBySeq };
export type ReferenceServices = typeof defaultServices;

class NeedsContext extends Error {
  constructor(message: string, readonly details: Record<string, unknown> = {}) { super(message); }
}

function reply(tool: string, query: Record<string, unknown>, body: string,
  data: Record<string, unknown> = {}, status: "retrieved" | "unconfirmed" = "retrieved"): CallToolResult {
  const retrievedAt = new Date().toISOString();
  const source = tool === "get_school_schedule"
    ? { name: "NEIS 교육정보 개방포털", url: "https://open.neis.go.kr" }
    : { name: "학교알리미", url: "https://www.schoolinfo.go.kr" };
  return {
    isError: status !== "retrieved",
    content: [{ type: "text", text: body + "\n\n출처: " + source.name + " (" + source.url + ")\n조회 시각(UTC): " + retrievedAt
      + "\n연도·원문 확인 후 사용하세요. 업무지침 확인이나 문안 승인 기록을 대신하지 않습니다." }],
    structuredContent: { status, tool, query, retrievedAt, source, humanVerified: false, ...data },
  };
}

export function buildMcpServer(overrides: Partial<ReferenceServices> = {}): McpServer {
  const services = { ...defaultServices, ...overrides };
  const server = new McpServer({ name: "teacher-doc-schoolinfo", version });

  function register<S extends z.AnyZodObject>(name: string, description: string, schema: S,
    handler: (query: z.infer<S>) => Promise<CallToolResult>) {
    const inputSchema: z.AnyZodObject = schema;
    server.registerTool(name, { description, inputSchema, annotations: readOnly }, async (query: unknown) => {
      try { return await handler(schema.parse(query)); }
      catch (error) {
        const message = maskSensitiveUrl(error instanceof Error ? error.message : String(error));
        const details = error instanceof NeedsContext ? error.details
          : error instanceof SchoolResolutionError ? { candidates: error.candidates }
          : error instanceof EvaluationParseError ? { needsOcr: error.needsOcr } : {};
        return reply(name, query as Record<string, unknown>, "미확인: " + message, details, "unconfirmed");
      }
    });
  }

  register("get_school_schedule", "학교의 연간 학사일정(행사·시험·방학)을 조회한다. AI가 확인한 학교명을 전달하면 내부에서 식별한다.", schoolInput, async (q) => {
    const school = await services.resolveSchool(q);
    const neis = await services.findNeisSchool(school.name, school.sido, school.sgg);
    if (!neis) throw new NeedsContext("학사일정을 조회할 학교를 NEIS에서 찾지 못했습니다.");
    const lastFeb = new Date(Date.UTC(q.year + 1, 2, 0)).getUTCDate();
    const items = await services.fetchSchedule(neis.atptCode, neis.schoolCode, String(q.year) + "0301", String(q.year + 1) + "02" + lastFeb);
    return reply("get_school_schedule", q, formatSchedule("", q.year, items).trim(),
      { events: items }, items.length ? "retrieved" : "unconfirmed");
  });

  async function document(tool: string, q: z.infer<typeof documentInput> & { semester?: 1 | 2 }, spec: DisclosureItemSpec) {
    const school = await services.resolveSchool(q);
    if (tool === "get_free_semester_plan" && school.kind !== "중학교") {
      throw new NeedsContext("자유학기 운영계획서는 중학교 공시 항목입니다.");
    }
    const listing = await services.listEvaluationDocs(school, q.year, spec, q.semester);
    const file = q.file_seq ? listing.docs.find((f) => f.seq === q.file_seq)
      : listing.docs.length === 1 ? listing.docs[0] : undefined;
    if (!file) throw new NeedsContext(listing.docs.length
      ? "첨부 파일을 선택하세요. seq를 file_seq로 전달하세요.\n" + listing.docs.map((f) => "- " + f.seq + ": " + f.filename).join("\n")
      : "해당 연도·학기의 첨부 파일이 없습니다.",
      { files: listing.docs, year: listing.year, submissionRounds: listing.rounds });
    const result = await services.fetchEvaluationBySeq(listing.downloadParams, file, spec);
    if (result.needsOcr || !result.markdown.trim()) throw new NeedsContext("본문을 충분히 읽지 못했습니다. 원문을 직접 확인하세요.",
      { document: result, year: listing.year, submissionRounds: listing.rounds });
    return reply(tool, q, "# " + file.filename + "\n\n" + result.markdown,
      { document: result, year: listing.year, submissionRounds: listing.rounds, selectedRound: listing.chasu });
  }

  register("get_curriculum_plan", "학교 교육과정·편제표·포함된 창체 운영계획의 전체 본문과 표를 조회한다. 여러 첨부는 file_seq로 선택한다.", documentInput,
    (q) => document("get_curriculum_plan", q, CURRICULUM_ITEM_SPEC));
  register("get_evaluation_plan", "지정 연도·학기의 교수학습·평가계획 전체 본문을 조회한다. 미제출·변환 실패는 미확인으로 반환한다.", evaluationInput,
    (q) => document("get_evaluation_plan", q, EVAL_ITEM_SPEC));
  register("get_free_semester_plan", "중학교 자유학기 운영계획서의 전체 본문과 표를 조회한다. 지정 연도 내 첨부가 있는 최신 공시회차를 사용하며 통계는 조회하지 않는다.", documentInput,
    (q) => document("get_free_semester_plan", q, FREE_SEMESTER_ITEM_SPEC));
  return server;
}
