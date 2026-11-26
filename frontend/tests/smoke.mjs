import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdtemp, rmdir, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.WORDSPEAK_PLAYWRIGHT_PACKAGE || "playwright");
const site = process.env.WORDSPEAK_TEST_URL || "http://localhost:3000";
const apiBase = process.env.WORDSPEAK_TEST_API || "http://localhost:8000";
const routes = [
  "/",
  "/dang-nhap",
  "/dang-ky",
  "/ho-so",
  "/luyen-ngu-am",
  "/ipa",
  "/luyen-ngu-dieu",
  "/tu-dien",
  "/tu-da-luu",
  "/talk",
  "/tien-do",
  "/lich-su",
  "/cai-dat",
];
const areas = [390, 768, 1280, 1440];
const directory = await mkdtemp(join(tmpdir(), "wordspeak-smoke-"));
const microphone = join(directory, "mic.wav");

function audioFixture() {
  const rate = 48000;
  const frames = rate * 2;
  const buffer = Buffer.alloc(44 + frames * 2);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(buffer.length - 8, 4);
  buffer.write("WAVEfmt ", 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(rate, 24);
  buffer.writeUInt32LE(rate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(frames * 2, 40);
  for (let index = 0; index < frames; index++) {
    buffer.writeInt16LE(Math.trunc(7800 * Math.sin((2 * Math.PI * 255 * index) / rate)), 44 + index * 2);
  }
  return buffer;
}

async function checkArticulationMotion(page, region) {
  const diagrams = region.locator(".art-gap");
  assert.equal(await diagrams.count(), 2);
  const resting = await diagrams.evaluateAll((items) => items.map((item) => item.getAttribute("ry")));
  await region.getByRole("button", { name: "Xem mô phỏng hai âm" }).click();
  await page.waitForFunction(
    ({ section, resting }) => {
      const diagrams = [...document.querySelectorAll("section")]
        .find((item) => item.getAttribute("aria-label") === section)
        ?.querySelectorAll(".art-gap");
      return (
        diagrams?.length === 2 &&
        [...diagrams].every((item, index) => item.getAttribute("ry") !== resting[index])
      );
    },
    { section: await region.getAttribute("aria-label"), resting },
  );
  await region.getByRole("button", { name: "Dừng mô phỏng hai âm" }).click();
  assert.deepEqual(
    await diagrams.evaluateAll((items) => items.map((item) => item.getAttribute("ry"))),
    resting,
  );
}

await writeFile(microphone, audioFixture());
let browser;
try {
  browser = await chromium.launch({
    executablePath: process.env.WORDSPEAK_CHROMIUM || undefined,
    headless: true,
    args: [
      "--use-fake-device-for-media-stream",
      "--use-fake-ui-for-media-stream",
      `--use-file-for-fake-audio-capture=${microphone}`,
    ],
  });
  const context = await browser.newContext({ permissions: ["microphone"] });
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.wordspeakSpoken = [];
    Object.defineProperty(window, "speechSynthesis", {
      value: {
        getVoices: () => [],
        cancel: () => {},
        speak(utterance) {
          window.wordspeakSpoken.push({ text: utterance.text, language: utterance.lang });
          queueMicrotask(() => utterance.onend?.(new Event("end")));
        },
      },
    });
  });
  page.setDefaultNavigationTimeout(90000);
  const errors = [];
  const audio = [];
  let holdPractice;
  const heldPractice = new Promise((resolve) => {
    holdPractice = resolve;
  });
  const fixtures = [];
  page.on("pageerror", (error) => errors.push(error.message));

  const session = {
    id: 1,
    topic: "Voice practice: use these learned words naturally: she",
    cefr_level: "A2",
  };
  const token = [
    "e30",
    Buffer.from(JSON.stringify({ sub: "1", exp: Math.floor(Date.now() / 1000) + 1800 })).toString(
      "base64url",
    ),
    "test",
  ].join(".");
  const headers = {
    "Access-Control-Allow-Origin": new URL(site).origin,
    "Access-Control-Allow-Headers": "authorization,content-type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  };
  await page.route(
    (url) => url.origin === new URL(apiBase).origin,
    (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (request.method() === "OPTIONS") return route.fulfill({ headers, status: 204 });
      if (path.startsWith("/auth/"))
        return route.fulfill({ headers, json: { access_token: token, token_type: "bearer" } });
      if (path === "/sessions" && request.method() === "POST") {
        fixtures.push(request.postDataJSON());
        return route.fulfill({ headers, json: session, status: 201 });
      }
      if (path === "/sessions")
        return route.fulfill({ headers, json: { items: [session], next_cursor: null } });
      if (path === "/sessions/1/turns")
        return route.fulfill({
          headers,
          json: {
            items: [{ id: 1, text: "She is my friend.", reply: "Where did you meet her?" }],
            next_cursor: null,
          },
        });
      if (path === "/progress")
        return route.fulfill({ headers, json: { attempts: 1, streak_days: 1, daily: [] } });
      return route.fulfill({ headers, status: 404, json: { detail: "Missing test fixture" } });
    },
  );
  await page.routeWebSocket(/\/ws\/audio$/, (socket) => {
    const chunks = [];
    function send(event) {
      socket.send(JSON.stringify(event));
    }
    socket.onMessage((message) => {
      if (typeof message !== "string") {
        chunks.push(message);
        send({ type: "partial", received_bytes: chunks.reduce((sum, chunk) => sum + chunk.length, 0) });
        return;
      }
      const end = JSON.parse(message);
      if (end.type === "auth") return send({ type: "authenticated" });
      assert.ok(end.request_id);
      const bytes = Buffer.concat(chunks);
      audio.push({ end, bytes });
      send({ type: "transcript", text: end.text || "She is my friend." });
      if (!end.session_id) {
        const practiceTurn = audio.filter(({ end }) => !end.session_id).length;
        if (practiceTurn === 2) {
          socket.close({ code: 1011, reason: "fixture disconnect after pronunciation submission" });
          return;
        }
        if (practiceTurn === 3) {
          holdPractice();
          return;
        }
      }
      if (end.session_id) {
        const turn = audio.filter(({ end }) => end.session_id).length;
        if (turn === 3) {
          socket.close({ code: 1011, reason: "fixture disconnect after submission" });
          return;
        }
        send({ type: "token", text: "Where did you meet her?" });
        send({ type: "done", text: "Where did you meet her?" });
        if (turn === 2) {
          send({ type: "error", code: "assessment_unavailable" });
          return;
        }
      }
      send({
        type: "final",
        text: "she",
        assessment: {
          sentence_score: 73,
          words: [{ word: "she", score: 73, phonemes: [{ ipa: "ʃ", score: 64, start: 0, end: 0.3 }] }],
          hints: ["Hãy lùi lưỡi nhẹ hơn."],
          errors: [{ ipa: "ʃ", actual: "s", type: "substitution" }],
        },
      });
      send({ type: "coaching", hints: ["Hãy lùi lưỡi nhẹ hơn."], errors: [] });
    });
  });

  for (const route of ["/", "/tu-dien", "/talk"]) {
    await page.goto(site + route);
    await page.waitForURL("**/dang-nhap");
    await page.getByRole("heading", { name: "Đăng nhập", exact: true }).waitFor();
    assert.equal(await page.locator(".sidebar").count(), 0);
  }
  await page.locator("form").getByRole("button", { name: "Đăng nhập" }).click();
  await page.getByText("Nhập địa chỉ email hợp lệ.").waitFor();
  await page.getByRole("textbox", { name: "Email" }).fill("dev3@example.com");
  await page.locator("input[name=password]").fill("valid-test-password");
  await page.getByRole("button", { name: "Hiện mật khẩu" }).click();
  assert.equal(await page.locator("input[name=password]").getAttribute("type"), "text");
  await page.locator("form").getByRole("button", { name: "Đăng nhập" }).click();
  await page.waitForURL(new URL("/", site).href);
  await page.getByRole("heading", { name: /Nói tiếng Anh/ }).waitFor();

  for (const width of areas) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of routes) {
      await page.goto(site + route, { waitUntil: "domcontentloaded" });
      await page.locator("h1").waitFor();
      assert.equal(new URL(page.url()).pathname, route);
      if (route === "/luyen-ngu-am")
        await page.getByRole("heading", { name: "Bài luyện của bạn" }).waitFor();
      assert.equal(await page.locator("h1").count(), 1, route);
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        true,
        `${route} overflows at ${width} px`,
      );
      assert.equal(await page.getByRole("button", { name: "Kịch bản demo" }).count(), 0);
      assert.equal(await page.locator("input[type=file]").count(), 0);
    }
    console.log(`${width} px · ${routes.length} màn không tràn ngang`);
  }
  const sideNav = page.getByRole("navigation", { name: "Điều hướng chính" });
  assert.deepEqual(await sideNav.locator(".nav-group").first().getByRole("link").allTextContents(), [
    "Luyện ngữ âm",
    "Luyện ngữ điệu",
    "Hội thoại AI",
  ]);
  await sideNav.locator(".nav-group").nth(1).getByRole("link", { name: "Bản đồ IPA" }).waitFor();

  await page.setViewportSize({ width: 390, height: 900 });
  const comparison = await context.newPage();
  await comparison.addInitScript((token) => {
    sessionStorage.setItem("wordspeak-session", JSON.stringify({ email: "dev3@example.com", token }));
    window.SpeechRecognition = class {
      start() {}
      stop() {
        this.onresult?.({ results: [{ isFinal: true, 0: { transcript: "See." } }] });
        this.onend?.();
      }
      abort() {
        this.onend?.();
      }
    };
  }, token);
  await comparison.routeWebSocket(/\/ws\/audio$/, (socket) => {
    socket.onMessage((message) => {
      if (typeof message !== "string") return;
      if (JSON.parse(message).type === "auth")
        return socket.send(JSON.stringify({ type: "authenticated" }));
      socket.send(
        JSON.stringify({
          type: "final",
          text: "See.",
          assessment: { sentence_score: 0, words: [] },
        }),
      );
    });
  });
  await comparison.goto(site + "/luyen-ngu-am?am=%CA%83");
  await comparison
    .getByRole("checkbox", { name: "Đối chiếu từ bằng nhận dạng của trình duyệt" })
    .check();
  await comparison.getByRole("button", { name: "Ghi âm", exact: true }).click();
  await comparison.getByText("Đang ghi âm", { exact: true }).waitFor();
  await comparison.waitForTimeout(450);
  await comparison.getByRole("button", { name: "Dừng ghi âm", exact: true }).click();
  await comparison.getByRole("button", { name: "Kiểm tra", exact: true }).click();
  const browserResult = comparison.getByRole("region", { name: "Đối chiếu từ đã nhận dạng" });
  await browserResult.getByText("See.", { exact: true }).waitFor();
  await browserResult.getByRole("heading", { name: "Âm trong từ được nhận dạng" }).waitFor();
  await browserResult.getByRole("heading", { name: "Âm cần đọc" }).waitFor();
  assert.equal(await browserResult.getByText(/GOP|\/100/).count(), 0);
  await checkArticulationMotion(comparison, browserResult);
  await comparison.emulateMedia({ reducedMotion: "reduce" });
  await browserResult.getByRole("button", { name: "Xem mô phỏng hai âm", disabled: true }).waitFor();
  await comparison.close();

  await page.goto(site + "/ho-so");
  await page.getByRole("textbox", { name: "Tên hiển thị" }).fill("Dev 3");
  await page.getByRole("button", { name: "Lưu hồ sơ" }).click();
  await page.getByText("Đã lưu hồ sơ trên thiết bị này.").waitFor();
  await page.getByRole("button", { name: "Bật giao diện tối" }).click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");

  await page.goto(site + "/ipa");
  assert.equal(await page.locator(".sound-card").count(), 44);
  await page.getByRole("button", { name: "Có bài luyện" }).click();
  assert.equal(await page.locator(".sound-card").count(), 12);
  await page.getByRole("searchbox").fill("she");
  await page.getByRole("link", { name: "Luyện âm" }).click();
  await page.getByRole("heading", { name: "Cách đặt môi và lưỡi" }).waitFor();
  async function runPracticeCheck() {
    await page.getByRole("button", { name: "Ghi âm", exact: true }).click();
    await page.getByText("Đang ghi âm", { exact: true }).waitFor();
    await page.waitForFunction(() => Number(document.querySelector("meter")?.value) > 0);
    await page.waitForTimeout(350);
    await page.getByRole("button", { name: "Dừng ghi âm", exact: true }).click();
    await page.getByRole("button", { name: "Kiểm tra", exact: true }).click();
  }
  await runPracticeCheck();
  await page.getByText("Hãy lùi lưỡi nhẹ hơn.").waitFor();
  await checkArticulationMotion(page, page.getByRole("region", { name: "Kết quả chấm ngữ âm" }));
  assert.equal(audio[0].end.text, "she");
  assert.equal(audio[0].end.media_type, "audio/wav");
  assert.equal(audio[0].bytes.toString("ascii", 0, 4), "RIFF");
  assert.equal(audio[0].bytes.readUInt16LE(22), 1);
  assert.equal(audio[0].bytes.readUInt32LE(24), 16000);
  await page.getByRole("button", { name: "Đã nhận kết quả", disabled: true }).waitFor();

  await runPracticeCheck();
  await page.getByText(/Máy chủ có thể đã lưu lượt này/).waitFor();
  const uncertain = page.getByRole("button", { name: "Chưa xác nhận kết quả", disabled: true });
  await uncertain.waitFor();
  assert.equal(audio.filter(({ end }) => !end.session_id).length, 2);
  assert.equal(await page.getByLabel("Nghe lại bản thu", { exact: true }).count(), 1);

  await runPracticeCheck();
  await Promise.race([
    heldPractice,
    page.waitForTimeout(10000).then(() => {
      throw new Error("Bản thu kiểm thử chưa được gửi.");
    }),
  ]);
  await page.getByRole("button", { name: "Dừng chờ kết quả", exact: true }).click();
  await page.getByText(/Đã dừng chờ kết quả/).waitFor();
  await uncertain.waitFor();
  assert.equal(audio.filter(({ end }) => !end.session_id).length, 3);

  await page.goto(site + "/luyen-ngu-dieu");
  await page.getByRole("button", { name: "Lên và xuống giọng" }).click();
  await page.getByRole("button", { name: "Nghe mẫu", exact: true }).click();
  await page.locator(".pitch-segment.active").waitFor();
  await page.getByRole("button", { name: "Really.", exact: true }).click();
  await page.getByRole("button", { name: "Nghe mẫu", exact: true }).click();
  await page.locator(".pitch-segment.active").waitFor();
  await page.getByRole("button", { name: "Dừng mẫu", exact: true }).click();
  await page.getByRole("button", { name: "Ghi âm", exact: true }).click();
  await page.getByText("Đang ghi âm", { exact: true }).waitFor();
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: "Dừng ghi âm", exact: true }).click();
  await page.getByRole("button", { name: "Nghe lại bản thu", exact: true }).click();
  await page.getByRole("button", { name: "Tạm dừng bản thu", exact: true }).waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll("audio")].some(
      (audio) => audio.currentSrc.startsWith("blob:") && !audio.paused && audio.currentTime > 0,
    ),
  );

  await page.goto(site + "/tu-dien");
  await page.getByRole("region", { name: "Con người và hoạt động" }).waitFor();
  assert.equal(await page.locator(".word-group").count(), 4);
  assert.equal(await page.locator(".word-tile").count(), 20);
  const firstRow = page.locator(".word-group").first().locator(".word-tile");
  assert.equal((await firstRow.nth(0).boundingBox()).y, (await firstRow.nth(1).boundingBox()).y);
  await page.getByRole("searchbox").fill("she");
  await page.getByRole("button", { name: "Chi tiết: she", exact: true }).click();
  await page.getByRole("dialog", { name: "she", exact: true }).waitFor();
  await page.getByRole("heading", { name: "she", exact: true }).waitFor();
  const wordSample = page.waitForResponse(
    (response) => response.url().endsWith("/audio/dictionary/she.wav") && response.ok(),
  );
  await page.getByRole("button", { name: "Nghe mẫu: she", exact: true }).click();
  await wordSample;
  await page.getByRole("button", { name: "Dừng mẫu", exact: true }).waitFor();
  const exampleSample = page.waitForResponse(
    (response) => response.url().endsWith("/audio/dictionary/she-example.wav") && response.ok(),
  );
  await page.getByRole("button", { name: /Nghe câu ví dụ: She listens/ }).click();
  await exampleSample;
  await page.getByRole("button", { name: "Nghe mẫu: she", exact: true }).waitFor();
  await page.getByRole("button", { name: "Dừng mẫu", exact: true }).click();
  await page.getByRole("button", { name: /Nghe câu ví dụ: She listens/ }).waitFor();
  await page.getByRole("button", { name: "Lưu từ", exact: true }).first().click();
  await page.getByText("Đánh giá", { exact: true }).first().click();
  await page.getByRole("button", { name: "4 trên 5" }).click();
  await page.getByText("Đánh giá · 4/5", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page.goto(site + "/tu-da-luu");
  await page.getByRole("button", { name: "Chi tiết: she", exact: true }).waitFor();

  await page.goto(site + "/talk");
  await page.getByRole("button", { name: "she", exact: true }).click();
  await page.getByRole("button", { name: "Bắt đầu luyện nói" }).click();
  await page.getByRole("button", { name: "Bấm để ghi âm" }).click();
  await page.getByText("Đang ghi âm", { exact: true }).waitFor();
  await page.waitForTimeout(750);
  await page.getByRole("button", { name: "Dừng và gửi" }).click();
  await page.getByRole("button", { name: "Nghe lại gia sư" }).waitFor();
  const firstTalk = audio.find(({ end }) => end.session_id);
  assert.equal(firstTalk.end.session_id, 1);
  assert.equal(firstTalk.end.text, undefined);
  assert.match(fixtures[0].topic, /she/);
  assert.equal(await page.getByRole("textbox").count(), 0);
  assert.equal(await page.getByText("Hãy lùi lưỡi nhẹ hơn.", { exact: true }).count(), 0);
  await page.getByRole("button", { name: "Nghe gợi ý phát âm", exact: true }).click();
  assert.deepEqual(await page.evaluate(() => window.wordspeakSpoken.at(-1)), {
    text: "Hãy lùi lưỡi nhẹ hơn.",
    language: "vi-VN",
  });
  await page.getByRole("button", { name: "Bấm để ghi âm" }).click();
  await page.getByText("Đang ghi âm", { exact: true }).waitFor();
  await page.waitForTimeout(750);
  await page.getByRole("button", { name: "Dừng và gửi" }).click();
  await page.getByText("Dịch vụ chấm ngữ âm chưa khả dụng.", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Nghe lại gia sư", exact: true }).click();
  assert.equal(await page.getByRole("button", { name: "Nghe gợi ý phát âm", exact: true }).count(), 0);
  assert.equal(
    await page.getByRole("button", { name: /Dùng nhận dạng trình duyệt cho lần tiếp theo/ }).count(),
    0,
  );
  assert.equal(
    await page.evaluate(() => window.wordspeakSpoken.at(-1)?.text),
    "Where did you meet her?",
  );

  async function recordTalkTurn() {
    await page.getByRole("button", { name: "Bấm để ghi âm" }).click();
    await page.getByText("Đang ghi âm", { exact: true }).waitFor();
    await page.waitForTimeout(750);
    await page.getByRole("button", { name: "Dừng và gửi" }).click();
  }
  await recordTalkTurn();
  await page.getByRole("link", { name: "Kiểm tra Lịch sử trước khi nói lại" }).waitFor();
  assert.equal(await page.getByRole("button", { name: "Gửi lại bản thu" }).count(), 0);
  assert.equal(audio.filter(({ end }) => end.session_id).length, 3);

  await page.evaluate(() => {
    const RoutedSocket = window.WebSocket;
    window.wordspeakUnsentAttempts = 0;
    window.WebSocket = class extends RoutedSocket {
      constructor(...args) {
        super(...args);
        if (window.wordspeakUnsentAttempts < 2) {
          window.wordspeakUnsentAttempts++;
          this.close();
        }
      }
    };
  });
  await recordTalkTurn();
  const retry = page.getByRole("button", { name: "Gửi lại bản thu" });
  await retry.waitFor();
  assert.equal(await page.evaluate(() => window.wordspeakUnsentAttempts), 2);
  assert.equal(audio.filter(({ end }) => end.session_id).length, 3);
  await retry.click();
  await page.getByRole("button", { name: "Nghe lại gia sư" }).waitFor();
  assert.equal(audio.filter(({ end }) => end.session_id).length, 4);

  await page.goto(site + "/lich-su");
  await page.getByRole("button", { name: "Mở", exact: true }).click();
  await page.getByRole("button", { name: /Nghe gia sư:/ }).waitFor();
  await page.goto(site + "/tien-do");
  await page.getByText("1 lượt máy chủ đã ghi nhận", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Menu hồ sơ" }).click();
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await page.waitForURL("**/dang-nhap");
  assert.deepEqual(errors, []);
  console.log(
    "PASS · tài khoản, chủ đề, audio WAV 16 kHz, ngữ điệu, từ điển, Talk giọng nói, lịch sử và tiến độ.",
  );
} finally {
  await browser?.close();
  await unlink(microphone);
  await rmdir(directory);
}
