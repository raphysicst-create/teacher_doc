import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { buildMcpServer } from "./mcpServer.js";
const server = buildMcpServer();
server.connect(new StdioServerTransport()).catch((error) => {
  console.error("teacher-doc-schoolinfo 시작 실패:", error.message);
  process.exitCode = 1;
});
