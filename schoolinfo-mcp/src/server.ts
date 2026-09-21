// Optional HTTP entry point for a later remote deployment. No website or REST API.
import http from "node:http";
import { timingSafeEqual } from "node:crypto";
import { pathToFileURL } from "node:url";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { buildMcpServer, type ReferenceServices } from "./mcpServer.js";

export interface HttpOptions {
  token?: string;
  allowedOrigins?: string[];
  services?: Partial<ReferenceServices>;
}
function equalToken(value: string, expected: string) {
  const a = Buffer.from(value), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
export function createHttpServer(options: HttpOptions = {}) {
  let active = 0;
  return http.createServer(async (req, res) => {
    const pathname = (req.url ?? "/").split("?")[0];
    const json = (code: number, body: unknown) => {
      res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(body));
    };
    if (pathname === "/health" && req.method === "GET") return json(200, { ok: true, service: "teacher-doc-schoolinfo" });
    if (pathname !== "/mcp") return json(404, { error: "Not found" });
    const origin = req.headers.origin;
    if (origin && !options.allowedOrigins?.includes(origin)) return json(403, { error: "Origin not allowed" });
    if (origin) {
      res.setHeader("Access-Control-Allow-Origin", origin);
      res.setHeader("Vary", "Origin");
      res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, MCP-Protocol-Version");
    }
    if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
    if (options.token && !equalToken(req.headers.authorization ?? "", "Bearer " + options.token)) return json(401, { error: "Unauthorized" });
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST, OPTIONS");
      return json(405, { error: "This stateless endpoint accepts POST only" });
    }
    if (active >= 4) return json(503, { error: "Server busy" });
    active++;
    const mcp = buildMcpServer(options.services);
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    // SDK request dispatch may return before an asynchronous tool completes.
    // Keep its transport alive until the actual response finishes or disconnects.
    res.once("close", () => {
      active--;
      void mcp.close().catch(() => {});
      void transport.close().catch(() => {});
    });
    try {
      const chunks: Buffer[] = [];
      let bytes = 0;
      for await (const chunk of req) {
        bytes += chunk.length;
        if (bytes > 64 * 1024) { json(413, { error: "Request too large" }); return; }
        chunks.push(Buffer.from(chunk));
      }
      let message;
      try { message = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
      catch { return json(400, { jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }); }
      await mcp.connect(transport);
      await transport.handleRequest(req, res, message);
    } catch {
      if (!res.headersSent) json(500, { error: "MCP request failed" });
      else res.end();
    }
  });
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const host = process.env.HOST ?? "127.0.0.1";
  const token = process.env.SCHOOLINFO_MCP_TOKEN;
  if (!["127.0.0.1", "::1", "localhost"].includes(host) && !token) throw new Error("외부 주소로 실행할 때는 SCHOOLINFO_MCP_TOKEN이 필요합니다.");
  const server = createHttpServer({ token,
    allowedOrigins: (process.env.SCHOOLINFO_MCP_ALLOWED_ORIGINS ?? "").split(",").map((s) => s.trim()).filter(Boolean) });
  server.requestTimeout = 60_000;
  server.listen(Number(process.env.PORT ?? 8080), host, () => console.error("teacher-doc-schoolinfo: http://" + host + ":" + (process.env.PORT ?? 8080) + "/mcp"));
}
