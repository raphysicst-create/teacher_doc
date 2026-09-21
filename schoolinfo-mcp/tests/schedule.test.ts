// 학사일정과 학교 식별: 외부 API 키 없이 실제 응답 형태를 mock한다.
import { afterEach, beforeEach, mock, test } from "node:test";
import assert from "node:assert/strict";
import { fetchSchedule, findNeisSchool, formatSchedule } from "../src/neis.js";
import { schoolCache } from "../src/lib/cache.js";

const originalKey = process.env.NEIS_API_KEY;
beforeEach(() => {
  process.env.NEIS_API_KEY = "offline-test-key";
  schoolCache.clear();
});
afterEach(() => {
  mock.restoreAll();
  schoolCache.clear();
  if (originalKey === undefined) delete process.env.NEIS_API_KEY;
  else process.env.NEIS_API_KEY = originalKey;
});

function respond(body: unknown) {
  return mock.method(globalThis, "fetch", async () => Response.json(body));
}
function serviceRows(service: string, rows: unknown[]) {
  return { [service]: [{ head: [{ list_total_count: rows.length }, { RESULT: { CODE: "INFO-000" } }] }, { row: rows }] };
}
const school = {
  SCHUL_NM: "한빛중학교", LCTN_SC_NM: "서울특별시", ORG_RDNMA: "서울특별시 강남구 학교로 1",
  ATPT_OFCDC_SC_CODE: "B10", SD_SCHUL_CODE: "7010001",
};

test("학교명과 지역이 일치하는 학교코드를 반환한다", async () => {
  respond(serviceRows("schoolInfo", [school, { ...school, LCTN_SC_NM: "부산광역시", SD_SCHUL_CODE: "other" }]));
  assert.deepEqual(await findNeisSchool("한빛중학교", "서울특별시", "강남구"), {
    atptCode: "B10", schoolCode: "7010001", name: "한빛중학교", sido: "서울특별시",
  });
});

test("부분 일치 학교명이나 잘못된 시군구를 임의 선택하지 않는다", async () => {
  respond(serviceRows("schoolInfo", [school]));
  assert.equal(await findNeisSchool("한빛", "서울특별시", "강남구"), null);
  assert.equal(await findNeisSchool("한빛중학교", "서울특별시", "강북구"), null);
  assert.equal(await findNeisSchool("한빛중학교", "부산광역시", "강남구"), null);
});

test("지역 미지정 또는 동명이교가 남으면 실패한다", async () => {
  respond(serviceRows("schoolInfo", [school, { ...school, SD_SCHUL_CODE: "7010002" }]));
  await assert.rejects(findNeisSchool("한빛중학교", "서울특별시"), /시군구/);
  await assert.rejects(findNeisSchool("한빛중학교", "서울특별시", "강남구"), /여러 곳/);
});

test("학사일정 조회 기간을 전달하고 중복·범위 밖·잘못된 날짜를 제거한다", async () => {
  const fetchMock = respond(serviceRows("SchoolSchedule", [
    { AA_YMD: "20260305", EVENT_NM: "현장체험학습", EVENT_CNTNT: "1학년" },
    { AA_YMD: "20260302", EVENT_NM: "입학식" },
    { AA_YMD: "20260305", EVENT_NM: "현장체험학습", EVENT_CNTNT: "1학년" },
    { AA_YMD: "20260307", EVENT_NM: "토요휴업일" },
    { AA_YMD: "20260230", EVENT_NM: "없는 날짜" },
    { AA_YMD: "20270401", EVENT_NM: "범위 밖" },
  ]));
  assert.deepEqual(await fetchSchedule("B10", "7010001", "20260301", "20270228"), [
    { date: "20260302", name: "입학식", content: undefined },
    { date: "20260305", name: "현장체험학습", content: "1학년" },
  ]);
  const url = new URL(String(fetchMock.mock.calls[0].arguments[0]));
  assert.equal(url.pathname, "/hub/SchoolSchedule");
  assert.equal(url.searchParams.get("AA_FROM_YMD"), "20260301");
  assert.equal(url.searchParams.get("AA_TO_YMD"), "20270228");
});

test("NEIS 무자료 INFO-200은 빈 결과를 반환한다", async () => {
  respond({ RESULT: { CODE: "INFO-200", MESSAGE: "해당하는 데이터가 없습니다." } });
  assert.deepEqual(await fetchSchedule("B10", "7010001", "20260301", "20270228"), []);
  assert.equal(await findNeisSchool("한빛중학교", "서울특별시", "강남구"), null);
});

test("HTTP 200인 인증 오류와 알 수 없는 응답은 무자료로 위장하지 않는다", async () => {
  const fetchMock = respond({ RESULT: { CODE: "ERROR-290", MESSAGE: "인증키 오류" } });
  await assert.rejects(fetchSchedule("B10", "7010001", "20260301", "20270228"), /NEIS ERROR-290/);
  fetchMock.mock.mockImplementation(async () => Response.json({ changed_schema: [] }));
  await assert.rejects(fetchSchedule("B10", "7010001", "20260301", "20270228"), /응답 형식/);
});

test("필수 키 누락과 잘못된 조회 기간은 API 요청 전에 실패한다", async () => {
  const fetchMock = respond({});
  delete process.env.NEIS_API_KEY;
  await assert.rejects(fetchSchedule("B10", "7010001", "20260301", "20270228"), /NEIS_API_KEY/);
  await assert.rejects(fetchSchedule("B10", "7010001", "20260230", "20270301"), /조회 기간/);
  await assert.rejects(fetchSchedule("B10", "7010001", "20260302", "20260301"), /조회 기간/);
  assert.equal(fetchMock.mock.callCount(), 0);
});

test("학사일정 표시에는 달력연도와 행사 내용이 포함된다", () => {
  const markdown = formatSchedule("한빛중학교", 2026, [
    { date: "20270205", name: "졸업식", content: "3학년" },
    { date: "20260302", name: "입학식" },
  ]);
  assert.match(markdown, /2026학년도/);
  assert.match(markdown, /2026년 3월/);
  assert.match(markdown, /2027년 2월/);
  assert.match(markdown, /졸업식 — 3학년/);
  assert.doesNotMatch(markdown, /D-day|D-DAY|D-\d|급식|시간표/);
});
