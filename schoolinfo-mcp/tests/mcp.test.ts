import { test, type TestContext } from "node:test";
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { buildMcpServer, TOOL_NAMES, type ReferenceServices } from "../src/mcpServer.js";
import { SchoolResolutionError, type School } from "../src/client.js";
import { CURRICULUM_ITEM_SPEC, EVAL_ITEM_SPEC, FREE_SEMESTER_ITEM_SPEC, EvaluationParseError,
  type EvaluationResult } from "../src/evaluation.js";

const query = { name: "한빛중학교", year: 2026 };
const school: School = { name: query.name, shlIdfCd: "fixture-school", sido: "서울특별시", sgg: "강남구", kind: "중학교" };
const body = "# 학교 운영계획\n\n창의적 체험활동의 실제 운영 내용입니다.\n\n| 교과 | 시간 |\n| --- | --- |\n| 국어 | 100 |\n\n부록: 평가 키워드가 없는 문단도 그대로 보존합니다.";
const document: EvaluationResult = {
  filename: "2026-운영계획.hwpx", fileType: "hwpx", markdown: body, evaluationSections: ["부분 발췌"],
  sourceSha256: "a".repeat(64), sourceUrl: "https://www.schoolinfo.go.kr/servlets/EiFileDownLoad.do?FILE_SEQ=1",
  usedYear: 2026, roundText: "(1차) 2026년 04월",
};
const round = { year: 2026, chasu: 1, label: "(1차) 2026년 04월", selected: true };

function fixture() {
  const calls: Array<{ operation: string; args: unknown[] }> = [];
  const services: Partial<ReferenceServices> = {
    resolveSchool: async (...args) => { calls.push({ operation: "resolve", args }); return school; },
    findNeisSchool: async (...args) => {
      calls.push({ operation: "neis-school", args });
      return { name: school.name, schoolCode: "7010001", atptCode: "B10", sido: school.sido };
    },
    fetchSchedule: async (...args) => {
      calls.push({ operation: "schedule", args });
      return [{ date: "20260302", name: "입학식" }];
    },
    listEvaluationDocs: async (...args) => {
      calls.push({ operation: "list-documents", args });
      return { docs: [{ seq: "1", filename: document.filename }], downloadParams: { JG_YEAR: "2026", JG_CHASU: "1" },
        year: 2026, chasu: 1, rounds: [round] };
    },
    fetchEvaluationBySeq: async (...args) => { calls.push({ operation: "document", args }); return { ...document }; },
  };
  return { services, calls };
}
async function connect(t: TestContext, services: Partial<ReferenceServices> = {}) {
  const server = buildMcpServer(services);
  const client = new Client({ name: "offline-test", version: "1.0.0" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  t.after(async () => { await client.close(); await server.close(); });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  return client;
}
function payload(result: Awaited<ReturnType<Client["callTool"]>>) {
  return result.structuredContent as Record<string, any>;
}
function resultText(result: Awaited<ReturnType<Client["callTool"]>>) {
  return (result.content as Array<{ type: string; text?: string }>).filter((part) => part.type === "text").map((part) => part.text).join("\n");
}
async function expectToolError(client: Client, name: string, args: Record<string, unknown>) {
  let result;
  try { result = await client.callTool({ name, arguments: args }); }
  catch (error) { assert.ok(error instanceof Error); return; }
  assert.equal(result.isError, true, `${name} should reject invalid input`);
}

test("도구는 계획서 3종·학사일정뿐이며 학교 식별정보 입력은 AI가 전달한다", async (t) => {
  const client = await connect(t);
  const { tools } = await client.listTools();
  assert.equal(tools.length, 4);
  assert.deepEqual(tools.map((tool) => tool.name).sort(), [...TOOL_NAMES].sort());
  for (const tool of tools) {
    assert.equal(tool.annotations?.readOnlyHint, true);
    assert.equal(tool.annotations?.destructiveHint, false);
    assert.equal(tool.inputSchema.additionalProperties, false);
    assert.ok(tool.inputSchema.required?.includes("name"));
    assert.ok(tool.inputSchema.required?.includes("year"));
    for (const key of ["sido", "sgg", "kind"]) assert.ok(!tool.inputSchema.required?.includes(key));
  }
  const schemas = Object.fromEntries(tools.map((tool) => [tool.name, tool.inputSchema]));
  assert.ok(schemas.get_evaluation_plan.required?.includes("semester"));
  assert.ok(!("semester" in (schemas.get_free_semester_plan.properties ?? {})));
});

test("학교 검색·학생수·통계 도구와 예전 범용 도구는 호출할 수 없다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  for (const name of ["find_school", "search_school", "get_school_info", "list_disclosure_types", "get_disclosure",
    "get_school_meal", "get_school_week", "get_exam_calendar", "get_school_report", "get_admission_subjects", "parse_evaluation_file"]) {
    await expectToolError(client, name, { ...query, item: "09" });
  }
  assert.equal(f.calls.length, 0);
});

test("추가 인수·빠진 학교/연도/학기·임의 파일 경로는 조회 전에 거부한다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  for (const [name, args] of [
    ["get_curriculum_plan", { year: 2026 }],
    ["get_curriculum_plan", { name: query.name }],
    ["get_curriculum_plan", { ...query, full: false }],
    ["get_curriculum_plan", { ...query, file_seq: "../private.hwpx" }],
    ["get_curriculum_plan", { ...query, file_seq: "1".repeat(21) }],
    ["get_evaluation_plan", query],
    ["get_evaluation_plan", { ...query, semester: 3 }],
    ["get_free_semester_plan", { ...query, semester: 1 }],
    ["get_school_schedule", { ...query, workspace: "C:/private" }],
  ] as Array<[string, Record<string, unknown>]>) await expectToolError(client, name, args);
  assert.equal(f.calls.length, 0);
});

test("동명이교는 후보를 반환하고 계획서 다운로드를 진행하지 않는다", async (t) => {
  const f = fixture();
  const candidates = [school, { ...school, shlIdfCd: "another-school", sgg: "서초구" }];
  f.services.resolveSchool = async () => { throw new SchoolResolutionError("학교를 특정할 수 없습니다", candidates); };
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_curriculum_plan", arguments: query });
  assert.equal(result.isError, true);
  assert.deepEqual(payload(result).candidates, candidates);
  assert.equal(payload(result).status, "unconfirmed");
  assert.equal(f.calls.length, 0);
});

test("일정은 내부 학교 식별값으로 NEIS를 조회하고 학교현황을 출력하지 않는다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_school_schedule", arguments: { name: query.name, year: 2027 } });
  assert.equal(result.isError, false);
  assert.deepEqual(f.calls.find((call) => call.operation === "neis-school")?.args, [school.name, school.sido, school.sgg]);
  assert.deepEqual(f.calls.find((call) => call.operation === "schedule")?.args, ["B10", "7010001", "20270301", "20280229"]);
  assert.equal(payload(result).school, undefined);
  assert.equal(payload(result).students, undefined);
  assert.equal(payload(result).source.url, "https://open.neis.go.kr");
  assert.match(resultText(result), /^# 2027학년도 학사일정/);
});

test("교육과정은 통계 없이 전체 본문·원본 해시·출처·제출 회차를 보존한다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_curriculum_plan", arguments: query });
  assert.equal(result.isError, false);
  assert.deepEqual(f.calls.find((call) => call.operation === "list-documents")?.args, [school, 2026, CURRICULUM_ITEM_SPEC, undefined]);
  assert.ok(resultText(result).includes(body));
  assert.equal(payload(result).document.sourceSha256, document.sourceSha256);
  assert.equal(payload(result).document.sourceUrl, document.sourceUrl);
  assert.equal(payload(result).selectedRound, 1);
  assert.equal(payload(result).school, undefined);
  assert.equal(payload(result).students, undefined);
  assert.equal(payload(result).humanVerified, false);
  assert.ok(Number.isFinite(Date.parse(payload(result).retrievedAt)));
});

test("여러 첨부는 임의 선택하지 않고 명시한 file_seq만 읽는다", async (t) => {
  const f = fixture();
  const files = [{ seq: "1", filename: "교육과정.hwpx" }, { seq: "2", filename: "편제표.xlsx" }];
  f.services.listEvaluationDocs = async () => ({ docs: files, downloadParams: { JG_YEAR: "2026", JG_CHASU: "1" }, year: 2026, rounds: [round] });
  const client = await connect(t, f.services);
  const choose = await client.callTool({ name: "get_curriculum_plan", arguments: query });
  assert.equal(choose.isError, true);
  assert.deepEqual(payload(choose).files, files);
  assert.equal(f.calls.filter((call) => call.operation === "document").length, 0);
  const missing = await client.callTool({ name: "get_curriculum_plan", arguments: { ...query, file_seq: "999" } });
  assert.equal(missing.isError, true);
  const selected = await client.callTool({ name: "get_curriculum_plan", arguments: { ...query, file_seq: "2" } });
  assert.equal(selected.isError, false);
  assert.deepEqual(f.calls.find((call) => call.operation === "document")?.args[1], files[1]);
});

test("평가계획은 요청한 학기를 전달하고 전체 본문을 반환한다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_evaluation_plan", arguments: { ...query, semester: 2 } });
  assert.equal(result.isError, false);
  assert.deepEqual(f.calls.find((call) => call.operation === "list-documents")?.args, [school, 2026, EVAL_ITEM_SPEC, 2]);
  assert.ok(resultText(result).includes(body));
});

test("자유학기는 통계가 아니라 2-마 계획서 첨부의 전체 본문을 조회한다", async (t) => {
  const f = fixture();
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_free_semester_plan", arguments: query });
  assert.equal(result.isError, false);
  assert.deepEqual(f.calls.find((call) => call.operation === "list-documents")?.args, [school, 2026, FREE_SEMESTER_ITEM_SPEC, undefined]);
  assert.equal(f.calls.find((call) => call.operation === "document")?.args[2], FREE_SEMESTER_ITEM_SPEC);
  assert.ok(resultText(result).includes(body));
  assert.equal(payload(result).document.sourceSha256, document.sourceSha256);
});

test("초등학교 자유학기 요청은 첨부 조회 전에 미확인으로 반환한다", async (t) => {
  const f = fixture();
  f.services.resolveSchool = async () => ({ ...school, kind: "초등학교" });
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_free_semester_plan", arguments: query });
  assert.equal(result.isError, true);
  assert.match(resultText(result), /중학교/);
  assert.equal(f.calls.length, 0);
});

test("변환 실패·OCR 필요·공시 미제출은 미확인으로 반환한다", async (t) => {
  const f = fixture();
  f.services.fetchEvaluationBySeq = async () => { throw new EvaluationParseError("이미지 문서", true); };
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_free_semester_plan", arguments: query });
  assert.equal(result.isError, true);
  assert.equal(payload(result).needsOcr, true);
  assert.equal(payload(result).status, "unconfirmed");
  const absent = await connect(t, { ...f.services, listEvaluationDocs: async () => { throw new Error("첨부 미제출"); } });
  const noDocument = await absent.callTool({ name: "get_free_semester_plan", arguments: query });
  assert.equal(noDocument.isError, true);
  assert.match(resultText(noDocument), /미제출/);
});

test("상위 API 오류 메시지의 인증키를 노출하지 않는다", async (t) => {
  const f = fixture();
  f.services.fetchSchedule = async () => { throw new Error("https://open.neis.go.kr/hub/SchoolSchedule?KEY=private-value&x=1"); };
  const client = await connect(t, f.services);
  const result = await client.callTool({ name: "get_school_schedule", arguments: query });
  assert.equal(result.isError, true);
  assert.ok(!resultText(result).includes("private-value"));
});
