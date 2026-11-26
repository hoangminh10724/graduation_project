import { access, cp } from "node:fs/promises";

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
