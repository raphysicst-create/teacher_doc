import { test, type TestContext } from "node:test";
import assert from "node:assert/strict";
import { resolveSchool, searchSchoolsByName, SchoolResolutionError } from "../src/client.js";

const rawSchool = {
  SHL_NM: "한빛중학교", SHL_IDF_CD: "school-1", SHL_CD: "unused-code",
  USER_DFN_CODE_VALUE_01: "서울특별시", USER_DFN_CODE_VALUE_02: "강남구", SCHUL_KIND: "03",
  FULL_ADDR: "보여주지 않는 주소", FOND_SC_NM: "공립", TOTAL_STUDENTS: 500,
};

function respond(t: TestContext, rows: unknown) {
  return t.mock.method(globalThis, "fetch", async () => Response.json(rows));
}

test("공개 학교 식별은 API 키 없이 SEARCH_WORD만 보내고 최소 필드만 반환한다", async (t) => {
  const fetchMock = respond(t, [rawSchool]);
  const schools = await searchSchoolsByName("한빛중학교");
  assert.deepEqual(schools, [{ name: "한빛중학교", shlIdfCd: "school-1", sido: "서울특별시", sgg: "강남구", kind: "중학교" }]);
  const call = fetchMock.mock.calls[0];
  assert.equal(String(call.arguments[0]), "https://www.schoolinfo.go.kr/ei/ss/pneiss_a04_s0/getSchoolList.do");
  assert.equal(call.arguments[1]?.method, "POST");
  assert.deepEqual([...new URLSearchParams(String(call.arguments[1]?.body))], [["SEARCH_WORD", "한빛중학교"]]);
  assert.equal(fetchMock.mock.callCount(), 1);
  assert.doesNotMatch(JSON.stringify(schools), /TOTAL_STUDENTS|학생|주소|schoolCode|foundation/);
});

test("학교명만으로 전국에서 정확히 일치하는 한 학교를 식별한다", async (t) => {
  respond(t, [rawSchool, { ...rawSchool, SHL_NM: "한빛여자중학교", SHL_IDF_CD: "school-2" }]);
  const school = await resolveSchool({ name: "한빛중학교" });
  assert.equal(school.shlIdfCd, "school-1");
  assert.equal(school.name, "한빛중학교");
});

test("학교명의 공백은 정규화하되 부분일치 학교를 자동 선택하지 않는다", async (t) => {
  respond(t, [rawSchool]);
  assert.equal((await resolveSchool({ name: " 한빛 중학교 " })).shlIdfCd, "school-1");
  await assert.rejects(resolveSchool({ name: "한빛" }), (error: unknown) => {
    assert.ok(error instanceof SchoolResolutionError);
    assert.match(error.message, /정확히 일치/);
    assert.equal(error.candidates[0].name, "한빛중학교");
    return true;
  });
});

test("동명이교는 첫 결과 대신 식별에 필요한 후보를 오류로 반환한다", async (t) => {
  respond(t, [rawSchool, { ...rawSchool, SHL_IDF_CD: "school-2", USER_DFN_CODE_VALUE_02: "강북구" }]);
  await assert.rejects(resolveSchool({ name: "한빛중학교" }), (error: unknown) => {
    assert.ok(error instanceof SchoolResolutionError);
    assert.equal(error.candidates.length, 2);
    assert.deepEqual(error.candidates.map((school) => school.sgg), ["강남구", "강북구"]);
    return true;
  });
});

test("AI가 전달한 선택 지역·학교급으로 동명이교를 구분한다", async (t) => {
  respond(t, [rawSchool,
    { ...rawSchool, SHL_IDF_CD: "school-2", USER_DFN_CODE_VALUE_02: "강북구" },
    { ...rawSchool, SHL_IDF_CD: "school-3", USER_DFN_CODE_VALUE_01: "부산광역시", USER_DFN_CODE_VALUE_02: "강남구" },
    { ...rawSchool, SHL_IDF_CD: "school-4", SCHUL_KIND: "07" },
  ]);
  const selected = await resolveSchool({ name: "한빛중학교", sido: "서울", sgg: "강남구", kind: "중학교" });
  assert.equal(selected.shlIdfCd, "school-1");
  await assert.rejects(resolveSchool({ name: "한빛중학교", sido: "서울", sgg: "서초구" }), (error: unknown) => {
    assert.ok(error instanceof SchoolResolutionError);
    assert.match(error.message, /함께 일치하지/);
    assert.equal(error.candidates.length, 4);
    return true;
  });
});

test("후보가 30개를 넘어도 잘라내어 동명이교를 숨기지 않는다", async (t) => {
  respond(t, Array.from({ length: 31 }, (_, i) => ({ ...rawSchool, SHL_IDF_CD: `school-${i}` })));
  await assert.rejects(resolveSchool({ name: "한빛중학교" }), (error: unknown) => {
    assert.ok(error instanceof SchoolResolutionError);
    assert.equal(error.candidates.length, 31);
    return true;
  });
});

test("동일 학교 식별코드의 중복 행은 동명이교로 판단하지 않는다", async (t) => {
  respond(t, [rawSchool, { ...rawSchool }]);
  assert.equal((await resolveSchool({ name: "한빛중학교" })).shlIdfCd, "school-1");
});

test("검색 결과 없음과 누락된 학교 식별코드는 자동 선택으로 보완하지 않는다", async (t) => {
  const fetchMock = respond(t, []);
  await assert.rejects(resolveSchool({ name: "한빛중학교" }), (error: unknown) => {
    assert.ok(error instanceof SchoolResolutionError);
    assert.deepEqual(error.candidates, []);
    return true;
  });
  fetchMock.mock.mockImplementation(async () => Response.json([{ ...rawSchool, SHL_IDF_CD: "" }, null]));
  await assert.rejects(resolveSchool({ name: "한빛중학교" }), SchoolResolutionError);
});

test("세종의 생략된 시군구와 숫자 학교급 코드를 정규화한다", async (t) => {
  respond(t, [{ ...rawSchool, USER_DFN_CODE_VALUE_01: "세종", USER_DFN_CODE_VALUE_02: "", SCHUL_KIND: 3 }]);
  const school = await resolveSchool({ name: "한빛중학교" });
  assert.equal(school.sido, "세종특별자치시");
  assert.equal(school.sgg, "세종특별자치시");
  assert.equal(school.kind, "중학교");
});

test("잘못된 학교명·구분자는 네트워크 요청 전에 거부한다", async (t) => {
  const fetchMock = respond(t, []);
  await assert.rejects(resolveSchool({ name: "" }), /학교명/);
  await assert.rejects(resolveSchool({ name: "한빛\n중학교" }), /학교명/);
  await assert.rejects(resolveSchool({ name: "한".repeat(101) }), /학교명/);
  await assert.rejects(resolveSchool({ name: "한빛중학교", sgg: " " }), /구분자/);
  assert.equal(fetchMock.mock.callCount(), 0);
});

test("공개 검색 응답 오류와 크기 초과는 정상 무자료로 처리하지 않는다", async (t) => {
  const fetchMock = t.mock.method(globalThis, "fetch", async () => new Response("not-json"));
  await assert.rejects(searchSchoolsByName("한빛중학교"), /해석할 수 없/);
  fetchMock.mock.mockImplementation(async () => Response.json({ changed: [] }));
  await assert.rejects(searchSchoolsByName("한빛중학교"), /응답 형식/);
  fetchMock.mock.mockImplementation(async () => new Response("[]", { headers: { "Content-Length": "4000001" } }));
  await assert.rejects(searchSchoolsByName("한빛중학교"), /너무 큽니다/);
  fetchMock.mock.mockImplementation(async () => new Response("denied", { status: 403 }));
  await assert.rejects(searchSchoolsByName("한빛중학교"), /HTTP 403/);
});
