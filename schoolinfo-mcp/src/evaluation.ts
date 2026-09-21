// 학교 교육과정, 교수·학습·평가계획, 자유학기 운영계획의 첨부 문서 조회.
//
// 이 자료는 학교알리미 OpenAPI 정형 데이터에 없고 문서 첨부파일로 공시된다.
// 하지만 학교별 공시정보 웹의 내부 요청을 그대로 재현하면 **순수 HTTP fetch로**
// 자동 다운로드가 가능하다 (브라우저 자동화 불필요). 흐름:
//
//   1) 공개 학교명 검색 → SHL_IDF_CD (학교고유식별코드)
//   2) POST /ei/pp/Pneipp_b43_s0p.do, b14 또는 b74 → 첨부파일 목록 (EUC-KR HTML)
//   3) GET /servlets/EiFileDownLoad.do?...&FILE_SEQ=n → 선택한 원본 문서
//   4) kordoc parse → 전체 마크다운 + 원본 출처·해시

import { parse } from "kordoc";
import { createHash } from "node:crypto";
import iconv from "iconv-lite";
import type { School } from "./client.js";
import { fetchWithRetry } from "./lib/fetch-with-retry.js";

const BASE = "https://www.schoolinfo.go.kr";
const DISCLOSURE_PORTAL = `${BASE}/ei/ss/pneiss_a03_s0.do`;

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36";

/** 외부 요청 타임아웃 (ms) — 학교알리미 지연 시 무한 대기 방지 */
const FETCH_TIMEOUT = 20_000;
/** 다운로드/파싱 허용 최대 크기 (50MB) — 메모리/DoS 방어 */
const MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024;
/** 숫자·문자 40자 미만인 추출물은 빈/이미지 문서일 수 있어 확인을 요구한다. */
const MIN_USEFUL_TEXT = 40;

/** 타임아웃 + 재시도 fetch (학교알리미 평가계획 조회/다운로드용) */
async function fetchT(url: string, init: RequestInit = {}, timeout = FETCH_TIMEOUT): Promise<Response> {
  return fetchWithRetry(url, init, { timeout, label: "학교알리미" });
}

/**
 * 공시항목별 첨부파일 다운로드 명세.
 * 다운로드 메커니즘(POST b페이지 → 첨부목록 → EiFileDownLoad.do → kordoc)은 동일하고
 * **항목 코드/엔드포인트만** 항목마다 다르다 (코드는 학교알리미 공시항목 분류 — 전국·전학교급 공통).
 */
export interface DisclosureItemSpec {
  /** 항목 조회 POST 엔드포인트 (/ei/pp/ 하위). 엔드포인트 번호 = GS_HANGMOK_CD */
  endpoint: string;
  /** 공시항목 고정 코드 (POST body + 다운로드 파라미터 폴백) */
  codes: {
    GS_HANGMOK_CD: string; GS_HANGMOK_NO: string; GS_HANGMOK_NM: string;
    GS_BURYU_CD: string; JG_BURYU_CD: string; JG_HANGMOK_CD: string; JG_GUBUN: string;
  };
  /** 목록 표시 순서 (낮을수록 우선). 파일을 자동 선택하지 않는다. */
  score: (filename: string) => number;
  /** 변환 마크다운에서 뽑아낼 관심 섹션 키워드 */
  sectionKeywords: string[];
  /** 학년도 계획서는 같은 연도의 제출 회차를 최신순으로 확인해 첨부가 있는 회차를 사용한다. */
  latestAvailableInYear?: boolean;
}

const EVAL_SECTION_KEYWORDS = ["수행평가", "평가기준", "평가요소", "평가방법", "평가영역", "반영비율", "평가시기", "성취기준", "지필", "정기시험"];
const CURRICULUM_SECTION_KEYWORDS = ["편제", "이수단위", "이수 단위", "단위 배당", "학점 배당", "시간 배당", "교과(군)", "창의적 체험활동", "학년군", "기준 단위"];

/** 4-가. 교과별(학년별) 교수·학습 및 평가 운영 계획 (= 수행평가 주제·평가기준) */
export const EVAL_ITEM_SPEC: DisclosureItemSpec = {
  endpoint: "Pneipp_b43_s0p.do",
  codes: {
    GS_HANGMOK_CD: "43", GS_HANGMOK_NO: "4-가",
    GS_HANGMOK_NM: "교과별(학년별) 교수ㆍ학습 및 평가계획에 관한 사항",
    GS_BURYU_CD: "JG110", JG_BURYU_CD: "JG040", JG_HANGMOK_CD: "14", JG_GUBUN: "1",
  },
  score: evalScore,
  sectionKeywords: EVAL_SECTION_KEYWORDS,
};

/** 2-가. 학교교육과정 편성·운영 및 평가에 관한 사항 (= 교육과정 편제표) */
export const CURRICULUM_ITEM_SPEC: DisclosureItemSpec = {
  endpoint: "Pneipp_b14_s0p.do",
  codes: {
    GS_HANGMOK_CD: "14", GS_HANGMOK_NO: "2-가",
    GS_HANGMOK_NM: "학교교육과정 편성ㆍ운영 및 평가에 관한 사항",
    GS_BURYU_CD: "JG100", JG_BURYU_CD: "JG020", JG_HANGMOK_CD: "05", JG_GUBUN: "1",
  },
  score: curriculumScore,
  sectionKeywords: CURRICULUM_SECTION_KEYWORDS,
};

/**
 * 2-마. 자유학기제 운영에 관한 사항 중 운영계획서 첨부.
 * 공식 공시포털(/ei/ss/pneiss_a03_s0.do)의 항목 명세와 b74의
 * "② 자유학기(자유학년) 운영 계획서" 다운로드 폼으로 확인했다.
 * OpenAPI apiType=04의 운영시수 통계와 별개로 원본 문서를 내려받는다.
 */
export const FREE_SEMESTER_ITEM_SPEC: DisclosureItemSpec = {
  endpoint: "Pneipp_b74_s0p.do",
  codes: {
    GS_HANGMOK_CD: "74", GS_HANGMOK_NO: "2-마",
    GS_HANGMOK_NM: "자유학기제 운영에 관한 사항",
    GS_BURYU_CD: "JG100", JG_BURYU_CD: "JG020", JG_HANGMOK_CD: "04", JG_GUBUN: "1",
  },
  score: () => 0,
  sectionKeywords: ["자유학기", "자유학년", "운영계획", "운영 계획", "주제선택", "진로탐색"],
  latestAvailableInYear: true,
};

export interface EvaluationFile {
  seq: string; // FILE_SEQ
  filename: string;
  sizeKB?: number;
}

/**
 * 학교알리미 "자료제출일" 드롭다운(#select_trans_dt)의 한 항목 — 실제 제출 회차.
 * value="{JG_YEAR}{JG_CHASU}" 형태(예: "20253" = 2025년 3차)를 그대로 분해한 것.
 * 관찰상 1차=4월(1학기), 3차=9월(2학기) 패턴이나, 학교/연도별 예외 가능성을 감안해
 * "그 해 최소 chasu=1학기, 최대 chasu=2학기"로 일반화해 판단한다 (하드코딩 1/3 지양).
 */
export interface SubmissionRound {
  year: number;
  chasu: number;
  label: string; // 예: "(3차) 2025년 09월"
  selected: boolean;
}

/** #select_trans_dt 드롭다운에서 제출 회차 목록을 파싱한다 */
function parseSubmissionRounds(html: string): SubmissionRound[] {
  const sel = html.match(/<select[^>]*id="select_trans_dt"[^>]*>([\s\S]*?)<\/select>/i);
  if (!sel) return [];
  const rounds: SubmissionRound[] = [];
  const re = /<option\s+value="(\d{4})(\d+)"\s*(selected)?\s*>\s*([^<]*)<\/option>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(sel[1]))) {
    rounds.push({ year: Number(m[1]), chasu: Number(m[2]), label: m[4].trim(), selected: !!m[3] });
  }
  return rounds;
}

/** 선택한 공시항목의 첨부파일 목록과 다운로드 파라미터 조회 */
async function fetchEvaluationFiles(
  shlIdfCd: string,
  schoolName: string,
  year: number,
  spec: DisclosureItemSpec = EVAL_ITEM_SPEC,
  chasu?: number
): Promise<{ files: EvaluationFile[]; downloadParams: Record<string, string>; rounds: SubmissionRound[] }> {
  if (!shlIdfCd) throw new Error("학교고유식별코드(SHL_IDF_CD)가 없습니다.");
  validateYear(year);
  const body = new URLSearchParams({
    ...spec.codes,
    HG_NM: schoolName,
    SHL_IDF_CD: shlIdfCd,
    GS_TYPE: "Y",
    JG_YEAR: String(year),
    SORT: "BR",
    CHOSEN_JG_YEAR: String(year),
    PRE_JG_YEAR: String(year),
    LOAD_TYPE: "single",
  });
  // 회차 미지정 시 서버 기본 선택을 받아 실제 회차를 확인한다.
  if (chasu != null) body.set("JG_CHASU", String(chasu));

  const res = await fetchT(`${BASE}/ei/pp/${spec.endpoint}`, {
    method: "POST",
    headers: {
      "User-Agent": UA,
      "X-Requested-With": "XMLHttpRequest",
      "Content-Type": "application/x-www-form-urlencoded",
      Referer: `${BASE}/ei/ss/Pneiss_b01_s0.do`,
    },
    body,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} — 평가계획 항목 조회 실패`);
  const listBuf = Buffer.from(await res.arrayBuffer());
  if (listBuf.byteLength > MAX_DOWNLOAD_BYTES) throw new Error("평가계획 목록 응답이 너무 큽니다.");
  const html = iconv.decode(listBuf, "euc-kr");

  // 첨부파일 목록: getEiFile43('N') + 파일명.확장자(NN KB)
  const files = parseFileList(html);
  // 다운로드 폼 파라미터 (eiFileDownForm hidden)
  const downloadParams = parseDownloadParams(html, shlIdfCd, year, spec);
  // 자료제출일(회차) 드롭다운 — 몇 차까지 제출됐는지, 어느 회차가 1/2학기인지 판단용
  const rounds = parseSubmissionRounds(html);
  // 응답이 요청 연도/회차를 무시했다면 다른 자료로 대체하지 않는다.
  const selected = rounds.find((round) => round.selected);
  if (Number(downloadParams.JG_YEAR) !== year || (selected && selected.year !== year)) {
    throw new Error(`${year}년도 자료가 응답에 없습니다. 다른 연도 자료로 대체하지 않습니다.`);
  }
  // 폼 회차가 생략되면 검증한 선택 회차만 사용한다. 근거 없이 1차로 가정하지 않는다.
  if (downloadParams.JG_CHASU == null && selected) {
    downloadParams.JG_CHASU = String(selected.chasu);
  }
  const actualChasu = Number(downloadParams.JG_CHASU);
  if (!Number.isSafeInteger(actualChasu) || actualChasu < 1) {
    throw new Error(`${year}년도 자료의 제출 회차를 확인할 수 없습니다.`);
  }
  if (selected && selected.chasu !== actualChasu) {
    throw new Error(`${year}년도 자료의 선택 회차와 다운로드 회차가 일치하지 않습니다.`);
  }
  if (chasu != null && actualChasu !== chasu) {
    throw new Error(`${year}년 ${chasu}차 자료를 확인할 수 없습니다. 다른 회차 자료로 대체하지 않습니다.`);
  }

  return { files, downloadParams, rounds };
}

function parseFileList(html: string): EvaluationFile[] {
  const files: EvaluationFile[] = [];
  const seen = new Set<string>();
  // <a ... onclick="getEiFile43('5')...">파일명.hwpx(89 KB)</a>
  // 파일명에 괄호가 있을 수 있으므로 앵커(>)와 종료(<) 사이 전체를 잡고, 크기 표기는 선택적.
  // 핸들러명은 항목마다 다르다(4-가=getEiFile43, 2-가=getEiFile14)므로 getEiFile\d*로 일반화.
  // onclick 따옴표(작은/큰), 인자 공백·따옴표 유무를 모두 허용 (HTML 변형 견고화).
  const re =
    /onclick=["'][^"']*getEiFile\d*\(\s*['"]?(\d+)['"]?\s*\)[^"']*["'][^>]*>\s*([^<]*?\.(?:hwpx|hwp|pdf|docx|xlsx))\s*(?:\(\s*([\d.,]+)\s*([KM]B)\s*\))?/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (seen.has(m[1])) continue;
    seen.add(m[1]);
    files.push({ seq: m[1], filename: m[2].trim(), sizeKB: toKB(m[3], m[4]) });
  }
  // 폴백: 순서 기반 매칭 (onclick과 파일명이 분리된 비표준 구조)
  if (files.length === 0) {
    const seqs = [...html.matchAll(/getEiFile\d*\(\s*['"]?(\d+)['"]?\s*\)/g)].map((x) => x[1]);
    const names = [...html.matchAll(/([^>\s][^<>]*?\.(?:hwpx|hwp|pdf|docx|xlsx))\s*(?:\(\s*([\d.,]+)\s*([KM]B)\s*\))?/gi)];
    // 개수가 일치할 때만 신뢰 (어긋나면 seq↔파일명 뒤바뀜 위험)
    if (seqs.length === names.length) {
      seqs.forEach((seq, i) => {
        files.push({ seq, filename: names[i][1].trim(), sizeKB: toKB(names[i][2], names[i][3]) });
      });
    } else {
      // 최후 폴백: 파일명 없이 seq만 (다운로드 후 Content-Disposition으로 파일명 확보)
      seqs.forEach((seq) => { if (!seen.has(seq)) { seen.add(seq); files.push({ seq, filename: `첨부파일_${seq}` }); } });
    }
  }
  return files;
}

/** "89", "1,234"(KB) / "1.2"(MB) → KB 숫자 */
function toKB(num?: string, unit?: string): number | undefined {
  if (!num) return undefined;
  const n = parseFloat(num.replace(/,/g, ""));
  if (!isFinite(n)) return undefined;
  return /MB/i.test(unit ?? "") ? Math.round(n * 1024) : n;
}

function parseDownloadParams(
  html: string,
  shlIdfCd: string,
  year: number,
  spec: DisclosureItemSpec
): Record<string, string> {
  const params: Record<string, string> = {};
  const formIdx = html.indexOf("eiFileDownForm");
  // 폼 전체를 </form>까지 잡는다 (고정 1200B 슬라이스는 hidden이 많으면 뒤쪽 필수값을 잘랐음).
  let seg = html;
  if (formIdx >= 0) {
    const end = html.indexOf("</form>", formIdx);
    seg = html.slice(formIdx, end >= 0 ? end : formIdx + 4096);
  }
  const re = /name="([A-Za-z_][A-Za-z0-9_]*)"[^>]*?value="([^"]*)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(seg))) {
    // 값은 코드/연도 등 단순 토큰만 신뢰 (외부 HTML에서 추출 → 방어적 형식 검증)
    if (!(m[1] in params) && /^[\w.\-]*$/.test(m[2])) params[m[1]] = m[2];
  }
  // 필수값 보강
  params.SHL_IDF_CD ??= shlIdfCd;
  params.JG_BURYU_CD ??= spec.codes.JG_BURYU_CD;
  params.JG_HANGMOK_CD ??= spec.codes.JG_HANGMOK_CD;
  params.JG_GUBUN ??= spec.codes.JG_GUBUN;
  params.JG_YEAR ??= String(year);
  params.PRE_JG_YEAR ??= String(year);
  return params;
}

/** 특정 첨부파일 다운로드 (GET EiFileDownLoad) */
export async function downloadEvaluationFile(
  downloadParams: Record<string, string>,
  seq: string,
  spec: DisclosureItemSpec = EVAL_ITEM_SPEC
): Promise<{ buffer: ArrayBuffer; filename: string; sourceUrl: string }> {
  if (!/^\d+$/.test(seq)) throw new Error("잘못된 파일 식별자입니다.");
  const qs = new URLSearchParams({ ...downloadParams, FILE_SEQ: seq });
  const sourceUrl = `${BASE}/servlets/EiFileDownLoad.do?${qs}`;
  const res = await fetchT(sourceUrl, {
    headers: { "User-Agent": UA, Referer: `${BASE}/ei/pp/${spec.endpoint}` },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} — 파일 다운로드 실패`);
  // 크기 상한 — Content-Length 선검사 + 실제 바이트 재확인
  const declared = Number(res.headers.get("content-length") ?? "0");
  if (declared > MAX_DOWNLOAD_BYTES) throw new Error("파일이 너무 큽니다 (50MB 초과).");
  const buffer = await res.arrayBuffer();
  if (buffer.byteLength > MAX_DOWNLOAD_BYTES) throw new Error("파일이 너무 큽니다 (50MB 초과).");
  // Content-Disposition에서 파일명 (RFC URL-encoded)
  let filename = `evaluation_${seq}`;
  const cd = res.headers.get("content-disposition") ?? "";
  const fm = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/i);
  if (fm) {
    try {
      filename = decodeURIComponent(fm[1].trim());
    } catch {
      filename = fm[1].trim();
    }
  }
  return { buffer, filename, sourceUrl };
}

export interface EvaluationResult {
  filename: string;
  fileType: string;
  markdown: string;
  evaluationSections: string[];
  /** 다운로드한 원본 바이트의 SHA-256 (변환 본문 해시가 아님) */
  sourceSha256: string;
  /** 실제 원본 다운로드 요청 URL */
  sourceUrl: string;
  usedYear: number;
  roundText: string;
  /** 본문 추출이 빈약(이미지 PDF 추정)해 OCR/수동확인이 필요할 때 true */
  needsOcr?: boolean;
}

/** 파싱 실패를 빈 정상문서로 숨기지 않는다. needsOcr는 자동 OCR을 수행했다는 뜻이 아니다. */
export class EvaluationParseError extends Error {
  readonly needsOcr: boolean;

  constructor(message: string, needsOcr = false) {
    super(message);
    this.name = "EvaluationParseError";
    this.needsOcr = needsOcr;
  }
}

function validateYear(year: number): void {
  if (!Number.isInteger(year) || year < 2000 || year > 2100) {
    throw new Error("공시연도는 2000~2100 사이의 정수로 지정해야 합니다.");
  }
}

/**
 * 같은 해에 제출된 회차들 중 학기를 판단한다.
 * 관찰된 패턴(1차=4월=1학기, 3차=9월=2학기)을 하드코딩하지 않고,
 * 그 해의 최소 chasu를 1학기, 최대 chasu를 2학기로 취급한다 — 회차 번호 자체가
 * 학교/연도마다 다를 수 있어(정정 회차 등) 상대적 순서로 판단하는 편이 안전하다.
 */
function roundForSemester(rounds: SubmissionRound[], year: number, semester: 1 | 2): SubmissionRound | undefined {
  const ofYear = rounds.filter((r) => r.year === year).sort((a, b) => a.chasu - b.chasu);
  if (!ofYear.length) return undefined;
  if (semester === 1) return ofYear[0];
  // 2학기: 그 해에 회차가 2개 이상 있어야 함(1개뿐이면 아직 2학기 자료가 없다는 뜻)
  return ofYear.length > 1 ? ofYear[ofYear.length - 1] : undefined;
}

/**
 * 평가계획 첨부파일 목록을 수행평가 관련성 순으로 정렬해 반환한다 (다운로드/파싱 전).
 * 과목별로 쪼개진 학교(과목별 PDF 여러 개)는 목록을 먼저 보여주고 선택하게 하기 위함.
 *
 * @param semester 1(1학기) | 2(2학기) 지정 시, 그 학기에 해당하는 제출 회차를 찾아 재조회한다.
 *   해당 학기 자료가 아직 없으면(예: 연중 2학기 미제출) 명시적으로 에러를 던진다 — 엉뚱한
 *   학기 자료를 조용히 대신 반환하지 않는다.
 */
export async function listEvaluationDocs(
  school: School,
  year: number,
  spec: DisclosureItemSpec = EVAL_ITEM_SPEC,
  semester?: 1 | 2
): Promise<{ docs: EvaluationFile[]; downloadParams: Record<string, string>; year: number; chasu?: number; rounds: SubmissionRound[] }> {
  validateYear(year);
  if (semester != null && semester !== 1 && semester !== 2) throw new Error("학기는 1 또는 2로 지정해야 합니다.");
  let { files, downloadParams, rounds } = await fetchEvaluationFiles(school.shlIdfCd, school.name, year, spec);
  let chasu: number | undefined;
  if (semester != null) {
    const target = roundForSemester(rounds, year, semester);
    if (!target) {
      const available = rounds.filter((r) => r.year === year).map((r) => r.label).join(", ") || "없음";
      throw new Error(`${year}년 ${semester}학기 자료가 아직 제출되지 않았습니다. (${year}년 제출 회차: ${available})`);
    }
    chasu = target.chasu;
    if (!target.selected) {
      ({ files, downloadParams, rounds } = await fetchEvaluationFiles(school.shlIdfCd, school.name, year, spec, chasu));
    }
  }
  if (semester == null && spec.latestAvailableInYear) {
    const initial = { files, downloadParams, rounds };
    const initialChasu = Number(downloadParams.JG_CHASU);
    // 기본 선택이 오래된 회차일 수 있으므로 같은 연도를 최신순으로 확인한다.
    // 최초 응답은 해당 회차에서 재사용해 같은 목록을 중복 요청하지 않는다.
    const candidates = [...new Set([initialChasu,
      ...rounds.filter((round) => round.year === year).map((round) => round.chasu)])]
      .sort((a, b) => b - a);
    for (const candidate of candidates) {
      ({ files, downloadParams, rounds } = candidate === initialChasu ? initial
        : await fetchEvaluationFiles(school.shlIdfCd, school.name, year, spec, candidate));
      chasu = candidate;
      if (files.length) break;
    }
  }
  if (!files.length) {
    throw new Error(`${year}년도 첨부파일을 찾지 못했습니다. (${DISCLOSURE_PORTAL} 직접 확인)`);
  }
  // 모든 첨부를 보존하고 순서만 정돈한다. 다른 파일로 자동 대체하지 않는다.
  const docs = [...files].sort((a, b) => spec.score(a.filename) - spec.score(b.filename));
  return { docs, downloadParams, year, chasu, rounds };
}

/** 특정 첨부파일을 다운로드 + kordoc 파싱 */
export async function fetchEvaluationBySeq(
  downloadParams: Record<string, string>,
  file: EvaluationFile,
  spec: DisclosureItemSpec = EVAL_ITEM_SPEC
): Promise<EvaluationResult> {
  const { buffer, filename, sourceUrl } = await downloadEvaluationFile(downloadParams, file.seq, spec);
  // filePath를 넘기지 않는다: 다운로드 파일명은 디스크에 없는 가짜 경로라
  // kordoc의 배포용 HWP COM 폴백이 존재하지 않는 파일을 열려 시도할 수 있음.
  // 포맷은 매직바이트로 자동 감지되므로 ArrayBuffer만으로 충분.
  const parsed = await parseEvaluationDocument(buffer);
  return {
    filename: filename || file.filename,
    fileType: parsed.fileType,
    markdown: parsed.markdown,
    evaluationSections: extractEvaluationSections(parsed.markdown, spec.sectionKeywords),
    sourceSha256: createHash("sha256").update(Buffer.from(buffer)).digest("hex"),
    sourceUrl,
    usedYear: Number(downloadParams.JG_YEAR),
    roundText: `${downloadParams.JG_YEAR}년 ${downloadParams.JG_CHASU}차`,
  };
}

/** 파일명 기반 수행평가 관련성 점수 (낮을수록 우선) */
function evalScore(filename: string): number {
  if (/교수.?학습|평가\s*계획|평가\s*운영/.test(filename)) return 0;
  if (/학업성적관리/.test(filename)) return 2;
  return 1;
}

/**
 * 파일명 기반 교육과정 편제표 관련성 점수 (낮을수록 우선).
 * 2-가 항목엔 '편제표 본문'과 '연간학사일정'이 함께 올라오는 경우가 많아,
 * 학사일정류를 후순위로 밀고 교육과정/교육계획 문서를 우선 선택한다.
 * 공백 변형("교육 계획" vs "교육계획서")을 흡수하려 공백을 제거하고 매칭.
 */
function curriculumScore(filename: string): number {
  const n = filename.replace(/\s/g, "");
  if (/연간학사일정|학사일정/.test(n)) return 3; // 학사 캘린더 — 편제표 아님
  if (/(학교)?교육과정|교육계획/.test(n)) return 0; // 편제표 본문
  return 1;
}

/** 내려받은 원본 바이트를 kordoc으로 파싱. 로컬 파일 경로는 받지 않는다. */
export async function parseEvaluationDocument(
  input: ArrayBuffer | Buffer
): Promise<{ fileType: string; markdown: string; evaluationSections: string[] }> {
  const buf = input instanceof ArrayBuffer ? input : toArrayBuffer(input);
  const result = await parse(buf);
  if (!result.success) throw new EvaluationParseError("문서 파싱 실패: 원문을 직접 확인하세요.");
  const markdown = result.markdown ?? "";
  const text = markdown.replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/<[^>]+>/g, " ").replace(/&(?:#\d+|#x[\da-f]+|\w+);/gi, " ");
  if ((text.match(/[\p{L}\p{N}]/gu) ?? []).length < MIN_USEFUL_TEXT) {
    throw new EvaluationParseError("본문 추출이 빈약합니다. 이미지 문서는 OCR 또는 원문 확인이 필요합니다.", true);
  }
  return {
    fileType: result.fileType ?? "unknown",
    markdown,
    evaluationSections: extractEvaluationSections(markdown),
  };
}

/** 마크다운에서 수행평가/평가 관련 구간 추출 */
export function extractEvaluationSections(markdown: string, keywords: string[] = EVAL_SECTION_KEYWORDS): string[] {
  const blocks = markdown.split(/\n\s*\n/);
  const hits: string[] = [];
  for (const block of blocks) {
    if (keywords.some((k) => block.includes(k))) hits.push(block.trim());
  }
  return hits;
}

function toArrayBuffer(b: Buffer): ArrayBuffer {
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
}
