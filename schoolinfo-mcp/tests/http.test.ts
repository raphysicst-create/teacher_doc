import { test, type TestContext } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { createHttpServer, type HttpOptions } from "../src/server.js";
import { TOOL_NAMES } from "../src/mcpServer.js";

async function listen(t: TestContext, options: HttpOptions = {}) {
  const server = createHttpServer(options);
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  t.after(async () => {
    server.closeAllConnections();
    await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  });
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}
const headers = { "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
const request = (method: string, params?: Record<string, unknown>) => JSON.stringify({ jsonrpc: "2.0", id: 1, method, ...(params ? { params } : {}) });

test("HTTP 공개 경로는 health와 mcp뿐이며 기존 웹/API는 404다", async (t) => {
  const base = await listen(t);
  const health = await fetch(base + "/health");
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { ok: true, service: "teacher-doc-schoolinfo" });
  for (const path of ["/", "/api/search", "/api/evaluation", "/api/meal", "/school", "/health/other"]) {
    const response = await fetch(base + path);
    assert.equal(response.status, 404, path);
    assert.match(response.headers.get("content-type") ?? "", /application\/json/);
  }
});

test("HTTP MCP도 동일한 도구 4개만 제공하며 학교를 내부에서 식별한다", async (t) => {
  const calls: string[] = [];
  const base = await listen(t, { services: { resolveSchool: async ({ name }) => {
    calls.push(name);
    await new Promise((resolve) => setTimeout(resolve, 25));
    return { name: "한빛중학교", shlIdfCd: "A01", sido: "서울특별시", sgg: "강남구", kind: "중학교" };
  }, findNeisSchool: async () => ({ name: "한빛중학교", schoolCode: "S01", atptCode: "B10", sido: "서울특별시" }),
    fetchSchedule: async () => [{ date: "20260302", name: "입학식" }] } });
  const initialization = await fetch(base + "/mcp", { method: "POST", headers,
    body: request("initialize", { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "http-test", version: "1" } }) });
  assert.equal(initialization.status, 200);
  assert.equal((await initialization.json()).result.serverInfo.name, "teacher-doc-schoolinfo");
  const listing = await fetch(base + "/mcp", { method: "POST", headers, body: request("tools/list") });
  assert.equal(listing.status, 200);
  const list = await listing.json();
  assert.deepEqual(list.result.tools.map((tool: { name: string }) => tool.name).sort(), [...TOOL_NAMES].sort());
  const lookup = await fetch(base + "/mcp", { method: "POST", headers,
    body: request("tools/call", { name: "get_school_schedule", arguments: { name: "한빛중학교", year: 2026 } }) });
  assert.equal(lookup.status, 200);
  const result = (await lookup.json()).result;
  assert.equal(result.isError, false);
  assert.deepEqual(result.structuredContent.events, [{ date: "20260302", name: "입학식" }]);
  assert.equal(result.structuredContent.school, undefined);
  assert.deepEqual(calls, ["한빛중학교"]);
  const removed = await fetch(base + "/mcp", { method: "POST", headers,
    body: request("tools/call", { name: "get_school_meal", arguments: {} }) });
  const rejected = await removed.json();
  assert.ok(rejected.error || rejected.result?.isError);
});

test("허용하지 않은 Origin은 토큰 유무와 관계없이 403이다", async (t) => {
  const base = await listen(t, { token: "offline-token", allowedOrigins: ["https://allowed.invalid"] });
  const response = await fetch(base + "/mcp", { method: "POST",
    headers: { ...headers, Origin: "https://unexpected.invalid", Authorization: "Bearer offline-token" }, body: request("tools/list") });
  assert.equal(response.status, 403);
  assert.equal(response.headers.get("access-control-allow-origin"), null);
  assert.deepEqual(await response.json(), { error: "Origin not allowed" });
});

test("토큰 설정 시 누락·잘못된 토큰은 401이고 올바른 토큰은 허용된다", async (t) => {
  const base = await listen(t, { token: "offline-token" });
  for (const authorization of [undefined, "Bearer wrong-token", "offline-token"]) {
    const response = await fetch(base + "/mcp", { method: "POST",
      headers: { ...headers, ...(authorization ? { Authorization: authorization } : {}) }, body: request("tools/list") });
    assert.equal(response.status, 401);
    assert.deepEqual(await response.json(), { error: "Unauthorized" });
  }
  const accepted = await fetch(base + "/mcp", { method: "POST", headers: { ...headers, Authorization: "Bearer offline-token" }, body: request("tools/list") });
  assert.equal(accepted.status, 200);
  assert.equal((await accepted.json()).result.tools.length, 4);
});

test("허용 Origin의 preflight와 실제 응답에는 CORS 헤더가 포함된다", async (t) => {
  const base = await listen(t, { token: "offline-token", allowedOrigins: ["https://allowed.invalid"] });
  const preflight = await fetch(base + "/mcp", { method: "OPTIONS", headers: { Origin: "https://allowed.invalid" } });
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get("access-control-allow-origin"), "https://allowed.invalid");
  assert.match(preflight.headers.get("access-control-allow-methods") ?? "", /POST/);
  const response = await fetch(base + "/mcp", { method: "POST", headers: {
    ...headers, Origin: "https://allowed.invalid", Authorization: "Bearer offline-token",
  }, body: request("tools/list") });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("access-control-allow-origin"), "https://allowed.invalid");
});

test("stateless MCP의 GET은 405 JSON 오류를 반환한다", async (t) => {
  const base = await listen(t);
  const response = await fetch(base + "/mcp");
  assert.equal(response.status, 405);
  assert.equal(response.headers.get("allow"), "POST, OPTIONS");
  assert.match(response.headers.get("content-type") ?? "", /application\/json/);
  assert.match((await response.json()).error, /POST only/);
});

test("깨진 JSON과 과도한 요청 본문은 MCP 처리 전에 거부된다", async (t) => {
  const base = await listen(t);
  const invalid = await fetch(base + "/mcp", { method: "POST", headers, body: "{" });
  assert.equal(invalid.status, 400);
  assert.equal((await invalid.json()).error.code, -32700);
  const large = await fetch(base + "/mcp", { method: "POST", headers, body: JSON.stringify({ data: "x".repeat(65 * 1024) }) });
  assert.equal(large.status, 413);
  assert.deepEqual(await large.json(), { error: "Request too large" });
});
