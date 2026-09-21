// 공문용 전체 문서 조회: 연도·학기·파일 선택 및 원본 추적을 검증한다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import iconv from "iconv-lite";
import type { School } from "../src/client.js";
import {
  CURRICULUM_ITEM_SPEC, downloadEvaluationFile,
  EVAL_ITEM_SPEC, FREE_SEMESTER_ITEM_SPEC, EvaluationParseError, extractEvaluationSections,
  fetchEvaluationBySeq, listEvaluationDocs, parseEvaluationDocument,
} from "../src/evaluation.js";

const school = { shlIdfCd: "TEST001", name: "테스트중학교" } as School;

function listing({ year = 2026, chasu = 1, files = ["교육과정.docx"], rounds = [1], handler = 43,
  priorYear = 0, formChasu = chasu as number | null, selected = true } = {}): Response {
  const html = `<select id="select_trans_dt">${rounds.map((round) =>
    `<option value="${year}${round}" ${selected && round === chasu ? "selected" : ""}>(${round}차) ${year}년</option>`).join("")}
    ${priorYear ? `<option value="${priorYear}3">(3차) ${priorYear}년</option>` : ""}</select>
    <form id="eiFileDownForm"><input name="JG_YEAR" value="${year}">${formChasu == null ? "" : `<input name="JG_CHASU" value="${formChasu}">`}</form>
    ${files.map((name, i) => `<a onclick="getEiFile${handler}('${i + 1}')">${name}(1 KB)</a>`).join("")}`;
  return new Response(new Uint8Array(iconv.encode(html, "euc-kr")), { status: 200 });
}

// Minimal stored ZIP fixture: exercise the real DOCX parser without another dependency.
function zip(files: Record<string, string>): Buffer {
  const local: Buffer[] = [], central: Buffer[] = [];
  let offset = 0;
  function crc32(data: Buffer): number {
    let crc = 0xffffffff;
    for (const byte of data) {
      crc ^= byte;
      for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
  }
  for (const [path, contents] of Object.entries(files)) {
    const name = Buffer.from(path), data = Buffer.from(contents), crc = crc32(data);
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50, 0); header.writeUInt16LE(20, 4);
    header.writeUInt32LE(crc, 14); header.writeUInt32LE(data.length, 18);
    header.writeUInt32LE(data.length, 22); header.writeUInt16LE(name.length, 26);
    local.push(header, name, data);
    const entry = Buffer.alloc(46);
    entry.writeUInt32LE(0x02014b50, 0); entry.writeUInt16LE(20, 4); entry.writeUInt16LE(20, 6);
    entry.writeUInt32LE(crc, 16); entry.writeUInt32LE(data.length, 20); entry.writeUInt32LE(data.length, 24);
    entry.writeUInt16LE(name.length, 28); entry.writeUInt32LE(offset, 42);
    central.push(entry, name);
    offset += header.length + name.length + data.length;
  }
  const directory = Buffer.concat(central), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(Object.keys(files).length, 8); end.writeUInt16LE(Object.keys(files).length, 10);
  end.writeUInt32LE(directory.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, directory, end]);
}

function docx(body: string): Buffer {
  return zip({
    "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
    "_rels/.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    "word/document.xml": `<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>${body}<w:sectPr/></w:body></w:document>`,
  });
}

function freeSemesterWorkbook(): Buffer {
  const sheet = (text: string) => `<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>${text}</t></is></c></row></sheetData></worksheet>`;
  return zip({
    "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
    "_rels/.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
    "xl/workbook.xml": '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="자유학기 활동" sheetId="1" r:id="rId1"/><sheet name="예산 계획서" sheetId="2" r:id="rId2"/></sheets></workbook>',
    "xl/_rels/workbook.xml.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>',
    "xl/worksheets/sheet1.xml": sheet("2026학년도 자유학기 운영 계획서. 주제선택과 진로탐색 활동의 프로그램별 운영 일정을 본 문서에서 확인한다."),
    "xl/worksheets/sheet2.xml": sheet("마지막 예산 계획서의 산출근거까지 전체 문서 변환 결과에 보존한다."),
  });
}

const paragraph = (text: string) => `<w:p><w:r><w:t>${text}</w:t></w:r></w:p>`;
const fullDocument = () => docx(
  paragraph("2026학년도 테스트중학교 교육과정 운영 계획. 학교 구성원이 합의한 연간 교육활동 및 창의적 체험활동 운영계획을 다음과 같이 정한다.") +
  `<w:tbl><w:tr><w:tc>${paragraph("일자")}</w:tc><w:tc>${paragraph("활동")}</w:tc></w:tr><w:tr><w:tc>${paragraph("3월 2일")}</w:tc><w:tc>${paragraph("입학식 및 학교생활 안내")}</w:tc></w:tr></w:tbl>` +
  paragraph("이 문단은 평가 키워드가 없는 문서의 마지막 안내사항이며 전체 조회 결과에 그대로 남아 있어야 합니다.")
);

test("지정한 연도의 첨부가 없으면 이전 연도로 재조회하지 않는다", async (t) => {
  const calls: string[] = [];
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    calls.push(String(init?.body));
    return listing({ files: [] });
  });
  await assert.rejects(listEvaluationDocs(school, 2026), /2026년도 첨부파일을 찾지 못/);
  assert.equal(calls.length, 1);
  assert.equal(new URLSearchParams(calls[0]).get("JG_YEAR"), "2026");
});

test("연도 생략·잘못된 학기는 네트워크 호출 전에 거부한다", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => { throw new Error("unexpected fetch"); });
  await assert.rejects(listEvaluationDocs(school, undefined as unknown as number), /공시연도/);
  await assert.rejects(listEvaluationDocs(school, 2026, EVAL_ITEM_SPEC, 3 as 1), /학기는/);
  assert.equal(fetch.mock.callCount(), 0);
});

test("서버가 다른 연도 자료를 반환해도 요청 연도로 표시하지 않는다", async (t) => {
  t.mock.method(globalThis, "fetch", async () => listing({ year: 2025 }));
  await assert.rejects(listEvaluationDocs(school, 2026), /다른 연도 자료로 대체하지/);
});

test("미제출 2학기를 1학기 자료로 대체하지 않는다", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => listing({ rounds: [1] }));
  await assert.rejects(listEvaluationDocs(school, 2026, EVAL_ITEM_SPEC, 2), /2학기 자료가 아직 제출되지/);
  assert.equal(fetch.mock.callCount(), 1);
});

test("선택한 제출 회차를 재조회하고 실제 회차를 다운로드에 유지한다", async (t) => {
  const calls: URLSearchParams[] = [];
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    const params = new URLSearchParams(String(init?.body));
    calls.push(params);
    return listing({ chasu: params.has("JG_CHASU") ? 1 : 3, rounds: [1, 3] });
  });
  const result = await listEvaluationDocs(school, 2026, EVAL_ITEM_SPEC, 1);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].get("JG_CHASU"), "1");
  assert.equal(result.downloadParams.JG_CHASU, "1");
  assert.equal(result.chasu, 1);
});

test("서버가 요청 회차를 무시하면 다운로드하지 않는다", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => listing({ chasu: 3, rounds: [1, 3] }));
  await assert.rejects(listEvaluationDocs(school, 2026, EVAL_ITEM_SPEC, 1), /다른 회차 자료로 대체하지/);
  assert.equal(fetch.mock.callCount(), 2);
});

test("첨부 목록 조회는 모든 파일을 보존하고 파일을 다운로드하지 않는다", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => listing({ files: ["교육과정.docx", "편제표.xlsx"] }));
  const listed = await listEvaluationDocs(school, 2026, CURRICULUM_ITEM_SPEC);
  assert.deepEqual(listed.docs.map((file) => file.filename), ["교육과정.docx", "편제표.xlsx"]);
  assert.deepEqual(listed.docs.map((file) => file.seq), ["1", "2"]);
  assert.equal(fetch.mock.callCount(), 1, "목록 요청뿐이며 파일 다운로드가 없어야 한다");
});

test("전체 DOCX 본문과 표를 보존하며 원본 bytes 해시와 URL을 반환한다", async (t) => {
  const bytes = fullDocument();
  let requested = "";
  t.mock.method(globalThis, "fetch", async (url) => {
    requested = String(url);
    return new Response(new Uint8Array(bytes), { headers: { "Content-Disposition": "attachment; filename=curriculum.docx" } });
  });
  const result = await fetchEvaluationBySeq({ SHL_IDF_CD: "TEST001", JG_YEAR: "2026", JG_CHASU: "1" }, { seq: "7", filename: "교육과정.docx" }, CURRICULUM_ITEM_SPEC);
  assert.match(result.markdown, /입학식 및 학교생활 안내/);
  assert.match(result.markdown, /문서의 마지막 안내사항/);
  assert.match(result.markdown, /3월 2일/);
  assert.equal(result.sourceSha256, createHash("sha256").update(bytes).digest("hex"));
  assert.equal(result.sourceUrl, requested);
  assert.equal(new URL(requested).searchParams.get("FILE_SEQ"), "7");
  assert.equal(result.usedYear, 2026);
  assert.equal(result.roundText, "2026년 1차");
});

test("본문이 사실상 빈 문서는 needsOcr 오류로 반환한다", async () => {
  await assert.rejects(parseEvaluationDocument(docx(paragraph("1"))), (error: unknown) => {
    assert.ok(error instanceof EvaluationParseError);
    assert.equal(error.needsOcr, true);
    return true;
  });
});

test("손상된 파일을 빈 정상 문서로 반환하지 않는다", async () => {
  await assert.rejects(parseEvaluationDocument(Buffer.from("not a supported document")));
});

test("원문 다운로드는 잘못된 식별자 및 과대 파일을 거부한다", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch", async () => new Response("", { headers: { "Content-Length": String(51 * 1024 * 1024) } }));
  await assert.rejects(downloadEvaluationFile({}, "../1"), /잘못된 파일 식별자/);
  assert.equal(fetch.mock.callCount(), 0);
  await assert.rejects(downloadEvaluationFile({}, "1"), /50MB 초과/);
});

test("참고 구간 추출은 GFM 표와 HTML 표를 재구성하지 않는다", () => {
  const table = "| 교과 | 평가방법 |\n| --- | --- |\n| 국어 | 수행평가 |";
  const html = "<table><tr><td>창의적 체험활동</td><td>20시간</td></tr></table>";
  assert.deepEqual(extractEvaluationSections(`일반 안내\n\n${table}`), [table]);
  assert.deepEqual(extractEvaluationSections(html, CURRICULUM_ITEM_SPEC.sectionKeywords), [html]);
});

test("자유학기 계획서는 b74 첨부 원문을 내려받아 XLSX 마지막 시트까지 변환한다", async (t) => {
  const bytes = freeSemesterWorkbook();
  const requests: { url: string; body: string }[] = [];
  t.mock.method(globalThis, "fetch", async (url, init) => {
    requests.push({ url: String(url), body: String(init?.body ?? "") });
    if (String(url).endsWith("/ei/pp/Pneipp_b74_s0p.do")) {
      const response = listing({ files: ["자유학기 운영 계획서.xlsx"], handler: 74 });
      const html = iconv.decode(Buffer.from(await response.arrayBuffer()), "euc-kr")
        + "<table><tr><td>STATISTICS_ONLY_NOT_DOCUMENT</td></tr></table>";
      return new Response(new Uint8Array(iconv.encode(html, "euc-kr")));
    }
    assert.match(String(url), /\/servlets\/EiFileDownLoad\.do\?/);
    return new Response(new Uint8Array(bytes), { headers: { "Content-Disposition": "attachment; filename=free-plan.xlsx" } });
  });
  const listed = await listEvaluationDocs(school, 2026, FREE_SEMESTER_ITEM_SPEC);
  const result = await fetchEvaluationBySeq(listed.downloadParams, listed.docs[0], FREE_SEMESTER_ITEM_SPEC);
  const posted = new URLSearchParams(requests[0].body);
  assert.equal(posted.get("GS_HANGMOK_CD"), "74");
  assert.equal(posted.get("GS_HANGMOK_NO"), "2-마");
  assert.equal(posted.get("JG_HANGMOK_CD"), "04");
  assert.equal(posted.get("JG_BURYU_CD"), "JG020");
  assert.equal(listed.chasu, 1);
  assert.equal(result.fileType, "xlsx");
  assert.match(result.markdown, /주제선택과 진로탐색/);
  assert.match(result.markdown, /마지막 예산 계획서의 산출근거/);
  assert.doesNotMatch(result.markdown, /STATISTICS_ONLY_NOT_DOCUMENT/);
  assert.equal(result.sourceSha256, createHash("sha256").update(bytes).digest("hex"));
  assert.equal(requests.length, 2);
  assert.ok(requests.every(({ url }) => !url.includes("openApi.do")));
});

test("자유학기 최신 회차가 무첨부면 같은 학년도에서 첨부가 있는 가장 최근 회차를 선택한다", async (t) => {
  const requests: URLSearchParams[] = [];
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    const params = new URLSearchParams(String(init?.body));
    requests.push(params);
    const chasu = params.has("JG_CHASU") ? Number(params.get("JG_CHASU")) : 3;
    return listing({ year: 2025, chasu, rounds: [1, 3], priorYear: 2024,
      files: chasu === 1 ? ["2025학년도 자유학기 운영 계획.hwp"] : [], handler: 74 });
  });
  const result = await listEvaluationDocs(school, 2025, FREE_SEMESTER_ITEM_SPEC);
  assert.equal(requests.length, 2);
  assert.deepEqual(requests.map((params) => params.get("JG_YEAR")), ["2025", "2025"]);
  assert.equal(requests[1].get("JG_CHASU"), "1");
  assert.equal(result.year, 2025);
  assert.equal(result.chasu, 1);
  assert.equal(result.downloadParams.JG_CHASU, "1");
  assert.equal(result.rounds.find((round) => round.selected)?.chasu, 1);
  assert.equal(result.docs[0].filename, "2025학년도 자유학기 운영 계획.hwp");
});

test("자유학기 첨부가 모든 회차에 없어도 다른 학년도로 넘어가지 않는다", async (t) => {
  const requests: URLSearchParams[] = [];
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    const params = new URLSearchParams(String(init?.body));
    requests.push(params);
    return listing({ year: 2025, chasu: Number(params.get("JG_CHASU") ?? "3"),
      rounds: [1, 3], priorYear: 2024, files: [], handler: 74 });
  });
  await assert.rejects(listEvaluationDocs(school, 2025, FREE_SEMESTER_ITEM_SPEC), /2025년도 첨부파일을 찾지 못/);
  assert.equal(requests.length, 2);
  assert.ok(requests.every((params) => params.get("JG_YEAR") === "2025"));
});

test("최초 응답의 폼 회차 누락은 선택 회차로 보완하고 불일치·모두 누락은 거부한다", async (t) => {
  let formChasu: number | null = null;
  let selected = true;
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    listing({ chasu: 3, rounds: [1, 3], handler: 74, formChasu, selected }));

  const result = await listEvaluationDocs(school, 2026, FREE_SEMESTER_ITEM_SPEC);
  assert.equal(result.chasu, 3);
  assert.equal(result.downloadParams.JG_CHASU, "3");
  assert.equal(result.rounds.find((round) => round.selected)?.chasu, 3);
  assert.equal(fetch.mock.callCount(), 1);

  formChasu = 1;
  await assert.rejects(listEvaluationDocs(school, 2026, FREE_SEMESTER_ITEM_SPEC), /선택 회차와 다운로드 회차가 일치하지/);
  assert.equal(fetch.mock.callCount(), 2);

  formChasu = null;
  selected = false;
  await assert.rejects(listEvaluationDocs(school, 2026, FREE_SEMESTER_ITEM_SPEC), /제출 회차를 확인할 수 없습니다/);
  assert.equal(fetch.mock.callCount(), 3);
});

test("자유학기는 기본 선택이 1차여도 3차 첨부를 우선하며 최초 응답을 중복 조회하지 않는다", async (t) => {
  const requests: URLSearchParams[] = [];
  let latestHasFiles = true;
  t.mock.method(globalThis, "fetch", async (_url, init) => {
    const params = new URLSearchParams(String(init?.body));
    requests.push(params);
    const chasu = Number(params.get("JG_CHASU") ?? "1");
    return listing({ chasu, rounds: [1, 3], handler: 74,
      files: chasu === 3 && !latestHasFiles ? [] : [`${chasu}차 자유학기 계획.hwp`] });
  });

  for (const hasFiles of [true, false]) {
    latestHasFiles = hasFiles;
    requests.length = 0;
    const result = await listEvaluationDocs(school, 2026, FREE_SEMESTER_ITEM_SPEC);
    const expectedChasu = hasFiles ? 3 : 1;
    assert.equal(result.chasu, expectedChasu);
    assert.equal(result.downloadParams.JG_CHASU, String(expectedChasu));
    assert.equal(result.rounds.find((round) => round.selected)?.chasu, expectedChasu);
    assert.equal(result.docs[0].filename, `${expectedChasu}차 자유학기 계획.hwp`);
    assert.deepEqual(requests.map((params) => params.get("JG_CHASU")), [null, "3"]);
  }
});
