import { access, cp } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

if (process.platform === "win32") {
  const cli = fileURLToPath(new URL("../node_modules/next/dist/bin/next", import.meta.url));
  const child = spawn(process.execPath, [cli, "start", "-H", process.env.HOSTNAME || "127.0.0.1"], {
    stdio: "inherit",
  });
  process.on("exit", () => child.kill());
  child.on("exit", (code) => process.exit(code ?? 1));
  await new Promise(() => {});
}

const standalone = new URL("../.next/standalone/", import.meta.url);
const server = new URL("server.js", standalone);

try {
  await access(server);
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
  console.error("Chưa có bản build production. Hãy chạy npm run build trước.");
  process.exit(1);
}

await Promise.all([
  cp(new URL("../.next/static/", import.meta.url), new URL(".next/static/", standalone), {
    recursive: true,
  }),
  cp(new URL("../public/", import.meta.url), new URL("public/", standalone), { recursive: true }),
]);

await import(server.href);
