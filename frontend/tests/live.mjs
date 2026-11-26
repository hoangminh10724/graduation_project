import assert from "node:assert/strict";
import { access } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const site = new URL(process.env.WORDSPEAK_TEST_URL || "http://localhost:3000");
const email = process.env.WORDSPEAK_LIVE_EMAIL;
const password = process.env.WORDSPEAK_LIVE_PASSWORD;
const microphone = process.env.WORDSPEAK_LIVE_AUDIO
  ? resolve(process.env.WORDSPEAK_LIVE_AUDIO)
  : fileURLToPath(new URL("../public/audio/dictionary/she.wav", import.meta.url));
const timeout = 90000;

if (!email || !password) {
  throw new Error("Cần WORDSPEAK_LIVE_EMAIL và WORDSPEAK_LIVE_PASSWORD của tài khoản kiểm thử.");
}

await access(microphone);
const browser = await chromium.launch({
  executablePath: process.env.WORDSPEAK_CHROMIUM || undefined,
  headless: true,
  args: [
    "--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream",
    `--use-file-for-fake-audio-capture=${microphone}`,
  ],
});

function url(pathname) {
  return new URL(pathname, site).href;
}

try {
  const context = await browser.newContext({ permissions: ["microphone"] });
  const page = await context.newPage();
  const turns = [];
  const errors = [];
  page.setDefaultTimeout(15000);
  page.setDefaultNavigationTimeout(timeout);
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("websocket", (socket) => {
    if (!new URL(socket.url()).pathname.endsWith("/ws/audio")) return;
    const events = [];
    turns.push(events);
    socket.on("framereceived", ({ payload }) => {
      if (typeof payload !== "string") return;
      try {
        events.push(JSON.parse(payload));
      } catch {
        errors.push("WebSocket trả thông điệp không hợp lệ.");
      }
    });
  });

  async function record(start, stop, milliseconds) {
    await page.getByRole("button", { name: start, exact: true }).click();
    await page.getByText("Đang ghi âm", { exact: true }).waitFor();
    await page.waitForFunction(() => Number(document.querySelector("meter")?.value) > 0);
    await page.waitForTimeout(milliseconds);
    await page.getByRole("button", { name: stop, exact: true }).click();
  }

  async function check(name, run) {
    try {
      await run();
      console.log(`PASS · ${name}`);
    } catch (error) {
      const reason = error instanceof Error ? error.message.split("\n")[0] : "Lỗi không xác định";
      const last = turns.at(-1)?.findLast((event) => event.type === "error");
      console.error(
        `FAIL · ${name}: ${reason.replaceAll(password, "[đã ẩn]")}${last ? ` [${last.code}]` : ""}`,
      );
      process.exitCode = 1;
    }
  }

  await page.goto(url("/dang-nhap"));
  await page.getByRole("textbox", { name: "Email" }).fill(email);
  await page.locator("input[name=password]").fill(password);
  await page.locator("form").getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await page.waitForURL(url("/"));
  console.log("PASS · đăng nhập qua API cấu hình trong frontend");

  await check("chấm âm vị qua dịch vụ thật", async () => {
    await page.goto(url("/luyen-ngu-am?am=%CA%83"));
    await record("Ghi âm", "Dừng ghi âm", 1700);
    await page.getByRole("button", { name: "Kiểm tra", exact: true }).click();
    const result = page.getByRole("heading", { name: "Kết quả kiểm tra", exact: true });
    const unsupported = page.getByText(/Dịch vụ chưa trả dữ liệu âm vị đã chấm/);
    await result.or(unsupported).first().waitFor({ timeout });
    assert.ok(await result.isVisible(), "Dịch vụ chưa trả dữ liệu âm vị thật.");
    const final = turns.at(-1)?.find((event) => event.type === "final");
    assert.ok(
      final?.assessment?.words?.some((word) =>
        word.phonemes?.some(
          (phoneme) =>
            phoneme.ipa === "ʃ" &&
            Number.isFinite(phoneme.score) &&
            phoneme.score >= 0 &&
            phoneme.score <= 100,
        ),
      ),
      "Không có điểm hợp lệ cho âm /ʃ/ trong sự kiện final.",
    );
  });

  await check("Talk nhận dạng trên máy chủ và lưu lượt nói", async () => {
    await page.goto(url("/tu-dien"));
    await page.getByRole("searchbox").fill("she");
    await page.getByRole("button", { name: "Chi tiết: she", exact: true }).click();
    const mark = page.getByRole("button", { name: "Đánh dấu đã học", exact: true });
    await mark
      .or(page.getByRole("button", { name: "Đã học", exact: true }))
      .first()
      .waitFor();
    if (await mark.isVisible()) await mark.click();

    await page.goto(url("/talk"));
    await page.getByRole("button", { name: "she", exact: true }).click();
    const created = page.waitForResponse(
      (response) =>
        response.url().endsWith("/sessions") && response.request().method() === "POST" && response.ok(),
    );
    await page.getByRole("button", { name: "Bắt đầu luyện nói", exact: true }).click();
    const { id } = await (await created).json();
    await record("Bấm để ghi âm", "Dừng và gửi", 2400);
    const replyButton = page.getByRole("button", { name: "Nghe lại gia sư", exact: true });
    const serviceError = page.getByText(
      /Dịch vụ nhận dạng tiếng nói chưa khả dụng|Gia sư AI chưa phản hồi được/,
    );
    await replyButton.or(serviceError).first().waitFor({ timeout });
    assert.ok(await replyButton.isVisible(), "Chưa có phản hồi giọng nói từ gia sư.");

    const events = turns.at(-1) || [];
    const transcript = events.find((event) => event.type === "transcript")?.text;
    const reply = events.find((event) => event.type === "done")?.text;
    assert.ok(transcript?.trim() && reply?.trim(), "WebSocket thiếu transcript hoặc phản hồi cuối.");

    await page.goto(url("/lich-su"));
    const row = page.locator(".list-item").filter({ hasText: `Phiên ${id} ·` });
    await row.getByRole("button", { name: "Mở", exact: true }).click();
    await page.getByRole("button", { name: `Nghe gia sư: ${reply}`, exact: true }).waitFor();
  });

  assert.deepEqual(errors, [], "Trình duyệt ghi nhận lỗi.");
} catch (error) {
  const reason = error instanceof Error ? error.message.split("\n")[0] : "Lỗi không xác định";
  console.error(reason.replaceAll(password, "[đã ẩn]"));
  process.exitCode = 1;
} finally {
  await browser.close();
}
