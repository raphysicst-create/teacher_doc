// 자료 조회 도구 안에서만 사용하는 공개 학교 식별. API 키·현황 조회는 사용하지 않는다.
import { normalizeSido, SCHOOL_KIND_REV } from "./codes.js";
import { fetchWithRetry } from "./lib/fetch-with-retry.js";

const NAME_SEARCH_URL = "https://www.schoolinfo.go.kr/ei/ss/pneiss_a04_s0/getSchoolList.do";
const NAME_SEARCH_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";
const MAX_RESPONSE_BYTES = 4_000_000;

/** 첨부 조회와 NEIS 학교 식별에 필요한 최소 정보. */
export interface School {
  name: string;
  shlIdfCd: string;
  sido: string;
  sgg: string;
  kind: string;
}

/** AI가 확인한 학교명. 지역·학교급은 동명이교를 구분할 때만 전달한다. */
export interface SchoolSelector {
  name: string;
  sido?: string;
  sgg?: string;
  kind?: string;
}

export class SchoolResolutionError extends Error {
  constructor(message: string, readonly candidates: School[] = []) {
    super(message);
    this.name = "SchoolResolutionError";
  }
}

function searchName(value: string): string {
  if (typeof value !== "string") throw new Error("확인한 학교명을 전달하세요.");
  const name = value.trim();
  if (name.length < 2 || name.length > 100 || /[\x00-\x1f]/.test(name)) {
    throw new Error("학교명은 제어 문자가 없는 2~100자 문자열이어야 합니다.");
  }
  return name;
}

/** 인증키 없는 학교알리미 공개 검색. 후보를 잘라 동명이교를 숨기지 않는다. */
export async function searchSchoolsByName(word: string): Promise<School[]> {
  const name = searchName(word);
  const res = await fetchWithRetry(NAME_SEARCH_URL, {
    method: "POST",
    headers: {
      "User-Agent": NAME_SEARCH_UA,
      "X-Requested-With": "XMLHttpRequest",
      "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
      Referer: "https://www.schoolinfo.go.kr/ei/ss/pneiss_a03_s0.do",
    },
    body: new URLSearchParams({ SEARCH_WORD: name }),
  }, { timeout: 15_000, label: "학교알리미" });
  if (!res.ok) throw new Error(`HTTP ${res.status} — 학교명 검색 실패`);
  const declared = Number(res.headers.get("content-length") ?? "0");
  if (declared > MAX_RESPONSE_BYTES) throw new Error("학교명 검색 응답이 너무 큽니다.");
  const buffer = Buffer.from(await res.arrayBuffer());
  if (buffer.byteLength > MAX_RESPONSE_BYTES) throw new Error("학교명 검색 응답이 너무 큽니다.");
  let rows: unknown;
  try { rows = JSON.parse(buffer.toString("utf-8")); }
  catch { throw new Error("학교 검색 응답을 해석할 수 없습니다."); }
  if (!Array.isArray(rows)) throw new Error("학교 검색 응답 형식이 바뀌었습니다.");
  return rows.filter((row) => row && typeof row === "object" && row.SHL_NM && row.SHL_IDF_CD).map((row) => {
    const name = String(row.SHL_NM).trim();
    const sido = normalizeSido(String(row.USER_DFN_CODE_VALUE_01 ?? row.LCTN_NM ?? ""));
    const sgg = String(row.USER_DFN_CODE_VALUE_02 ?? "").trim() || (sido === "세종특별자치시" ? sido : "");
    const code = String(row.SCHUL_KIND ?? row.SHL_CRSE_SC_CD ?? "").padStart(2, "0");
    const kind = SCHOOL_KIND_REV[code] ?? Object.values(SCHOOL_KIND_REV).find((suffix) => name.endsWith(suffix)) ?? "";
    return { name, shlIdfCd: String(row.SHL_IDF_CD).trim(), sido, sgg, kind };
  }).filter((school) => school.name && school.shlIdfCd);
}

/** 정확히 일치하는 한 학교만 선택한다. 동명이교나 잘못된 구분자는 후보와 함께 미확인 처리한다. */
export async function resolveSchool(selector: SchoolSelector): Promise<School> {
  const name = searchName(selector.name);
  const normalize = (value: string) => value.trim().replace(/\s/g, "");
  for (const key of ["sido", "sgg", "kind"] as const) {
    const value = selector[key];
    if (value !== undefined && (typeof value !== "string" || !value.trim() || value.length > 100 || /[\x00-\x1f]/.test(value))) {
      throw new Error(`학교 구분자 ${key}를 확인하세요.`);
    }
  }
  const found = await searchSchoolsByName(name);
  const exact = found.filter((school) => normalize(school.name) === normalize(name));
  const matching = exact.filter((school) =>
    (selector.sido === undefined || normalize(normalizeSido(school.sido)) === normalize(normalizeSido(selector.sido)))
    && (selector.sgg === undefined || normalize(school.sgg) === normalize(selector.sgg))
    && (selector.kind === undefined || normalize(school.kind) === normalize(selector.kind))
  );
  const unique = [...new Map(matching.map((school) => [school.shlIdfCd, school])).values()];
  if (unique.length === 1) return unique[0];
  if (unique.length > 1) {
    throw new SchoolResolutionError("같은 이름의 학교가 여러 곳입니다. 대화나 작업 자료에서 확인한 지역·학교급으로 구분하세요.", unique);
  }
  throw new SchoolResolutionError(
    exact.length ? "확인한 학교명과 지역·학교급이 함께 일치하지 않습니다. 후보와 작업 자료를 대조하세요."
      : "정확히 일치하는 학교명이 없습니다. 대화나 작업 자료의 학교명을 확인하세요.",
    exact.length ? exact : found
  );
}
