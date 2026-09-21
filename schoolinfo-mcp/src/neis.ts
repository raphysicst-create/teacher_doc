// NEIS 학교 식별과 학사일정 조회. 급식·시간표·주간 브리핑은 제공하지 않는다.
// NEIS_API_KEY는 실행 환경에서 받으며 결과나 로그에 포함하지 않는다.

import { fetchWithRetry } from "./lib/fetch-with-retry.js";
import { schoolCache } from "./lib/cache.js";

const SCHOOL_TTL = 30 * 24 * 60 * 60 * 1000;
const SCHEDULE_TTL = 12 * 60 * 60 * 1000;
const NEIS_BASE = "https://open.neis.go.kr/hub";
const FETCH_TIMEOUT = 15_000;

export function hasNeisKey(): boolean {
  return !!process.env.NEIS_API_KEY;
}

async function neisGet(path: string, params: Record<string, string>): Promise<any> {
  const key = process.env.NEIS_API_KEY;
  if (!key) throw new Error("NEIS_API_KEY가 설정되지 않았습니다.");
  const qs = new URLSearchParams({ KEY: key, Type: "json", pIndex: "1", pSize: "1000", ...params });
  const res = await fetchWithRetry(`${NEIS_BASE}/${path}?${qs}`, {}, { timeout: FETCH_TIMEOUT, label: "NEIS" });
  if (!res.ok) throw new Error(`NEIS HTTP ${res.status}`);
  return await res.json();
}

/** HTTP 200으로 반환되는 인증 오류를 '자료 없음'으로 처리하지 않는다. */
function neisRows(json: any, service: string): any[] {
  const node = json?.[service];
  const head = Array.isArray(node) ? node.find((part: any) => Array.isArray(part?.head))?.head : undefined;
  const code = json?.RESULT?.CODE ?? head?.find((part: any) => part?.RESULT)?.RESULT?.CODE;
  if (code === "INFO-200") return [];
  if (code && code !== "INFO-000") throw new Error(`NEIS ${code}`);
  const rows = Array.isArray(node) ? node.find((part: any) => Array.isArray(part?.row))?.row : undefined;
  if (!Array.isArray(rows)) throw new Error(`NEIS ${service} 응답 형식을 확인할 수 없습니다.`);
  return rows;
}

export interface NeisSchool {
  atptCode: string;
  schoolCode: string;
  name: string;
  sido: string;
}

/** 정식 학교명과 시도·시군구가 모두 맞는 한 학교만 선택한다. */
export async function findNeisSchool(name: string, sidoName?: string, sgg?: string): Promise<NeisSchool | null> {
  if (!name.trim() || !sidoName?.trim() || !sgg?.trim()) {
    throw new Error("학교명·시도·시군구를 모두 지정하세요.");
  }
  const cacheKey = `neis:school:${name}:${sidoName}:${sgg}`;
  const cached = schoolCache.get<NeisSchool>(cacheKey);
  if (cached) return cached;
  const json = await neisGet("schoolInfo", { SCHUL_NM: name });
  const norm = (value: unknown) => String(value ?? "").replace(/\s/g, "");
  const province = norm(sidoName);
  const district = norm(sgg);
  const candidates = neisRows(json, "schoolInfo").filter((row: any) => {
    const location = norm(row.LCTN_SC_NM);
    return norm(row.SCHUL_NM) === norm(name)
      && location.length > 0
      && (location === province || location.startsWith(province) || province.startsWith(location))
      && norm(row.ORG_RDNMA).includes(district);
  });
  if (!candidates.length) return null;
  // 같은 학교가 중복된 응답은 합치되 서로 다른 학교코드는 임의 선택하지 않는다.
  const unique = new Map<string, any>();
  for (const row of candidates) {
    if (!row.ATPT_OFCDC_SC_CODE || !row.SD_SCHUL_CODE) {
      throw new Error("NEIS 학교 식별코드가 누락되었습니다.");
    }
    unique.set(`${row.ATPT_OFCDC_SC_CODE}:${row.SD_SCHUL_CODE}`, row);
  }
  if (unique.size !== 1) throw new Error("같은 지역에 같은 이름의 학교가 여러 곳입니다. 학교 식별정보를 확인하세요.");
  const hit = unique.values().next().value;
  const result: NeisSchool = {
    atptCode: String(hit.ATPT_OFCDC_SC_CODE),
    schoolCode: String(hit.SD_SCHUL_CODE),
    name: String(hit.SCHUL_NM),
    sido: String(hit.LCTN_SC_NM),
  };
  schoolCache.set(cacheKey, result, SCHOOL_TTL);
  return result;
}

export interface ScheduleItem {
  date: string; // YYYYMMDD
  name: string;
  content?: string;
}

function isCalendarDate(value: string): boolean {
  if (!/^\d{8}$/.test(value)) return false;
  const date = new Date(Date.UTC(+value.slice(0, 4), +value.slice(4, 6) - 1, +value.slice(6, 8)));
  return date.toISOString().slice(0, 10).replace(/-/g, "") === value;
}

/** 명시한 기간의 학사일정. 무자료와 API 실패를 구분한다. */
export async function fetchSchedule(
  atptCode: string,
  schoolCode: string,
  fromYmd: string,
  toYmd: string
): Promise<ScheduleItem[]> {
  if (!atptCode.trim() || !schoolCode.trim()) throw new Error("NEIS 학교 식별코드가 필요합니다.");
  if (!isCalendarDate(fromYmd) || !isCalendarDate(toYmd) || fromYmd > toYmd) {
    throw new Error("학사일정 조회 기간은 실제 날짜 YYYYMMDD의 오름차순이어야 합니다.");
  }
  const cacheKey = `neis:sched:${atptCode}:${schoolCode}:${fromYmd}:${toYmd}`;
  const cached = schoolCache.get<ScheduleItem[]>(cacheKey);
  if (cached) return cached;
  const json = await neisGet("SchoolSchedule", {
    ATPT_OFCDC_SC_CODE: atptCode,
    SD_SCHUL_CODE: schoolCode,
    AA_FROM_YMD: fromYmd,
    AA_TO_YMD: toYmd,
  });
  const seen = new Set<string>();
  const items: ScheduleItem[] = [];
  for (const row of neisRows(json, "SchoolSchedule")) {
    const name = String(row.EVENT_NM ?? "").trim();
    const date = String(row.AA_YMD ?? "").trim();
    if (!name || !isCalendarDate(date) || date < fromYmd || date > toYmd) continue;
    if (name === "토요휴업일") continue;
    const key = `${date}|${name}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const content = String(row.EVENT_CNTNT ?? "").trim();
    items.push({ date, name, content: content || undefined });
  }
  items.sort((a, b) => a.date.localeCompare(b.date));
  schoolCache.set(cacheKey, items, SCHEDULE_TTL);
  return items;
}

/** 월별 일정에 실제 연도를 표시해 학년도와 달력연도를 구분한다. */
export function formatSchedule(school: string, year: number | undefined, items: ScheduleItem[]): string {
  const title = [school, year ? `${year}학년도` : "", "학사일정"].filter(Boolean).join(" ");
  if (!items.length) return `# ${title}\n\n해당 조회 기간에 공개된 학사일정이 없습니다.`;
  const parts = [`# ${title}`, ""];
  let month = "";
  for (const item of [...items].sort((a, b) => a.date.localeCompare(b.date))) {
    const nextMonth = item.date.slice(0, 6);
    if (nextMonth !== month) {
      month = nextMonth;
      parts.push(`## ${month.slice(0, 4)}년 ${Number(month.slice(4, 6))}월`, "");
    }
    parts.push(`- ${Number(item.date.slice(6, 8))}일 ${item.name}${item.content ? ` — ${item.content}` : ""}`);
  }
  return parts.join("\n");
}
