import { defineConfig } from "tsup";
export default defineConfig({
  entry: ["src/mcp.ts", "src/server.ts"],
  format: ["esm"], target: "node22", clean: true, sourcemap: false,
});
