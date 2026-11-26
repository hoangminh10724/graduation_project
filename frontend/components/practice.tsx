"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AudioConnectionError, sendAudio, type Assessment } from "@/lib/api";
import { sounds, targets, type Sound } from "@/lib/content";
import { useRecorder } from "@/lib/recorder";
import { hasRecognition, startRecognition, type RecognitionHandle } from "@/lib/recognition";
import { SpeakButton, RecorderDisplay, RecordButton } from "./audio-controls";
import { Action, Button, Notice, Panel, Title } from "./ui";
import { useApp } from "./provider";

export function Ipa() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const { study } = useApp();
  const query = search.trim().toLowerCase();
  const matching = sounds.filter((sound) => {
    const inGroup =
      filter === "all" ||
      (filter === "difficult" && sound.difficult) ||
      (filter === "practice" && sound.supported) ||
      filter === sound.group;
    return inGroup && (!query || `${sound.ipa} ${sound.word}`.toLowerCase().includes(query));
  });
  return (
    <>
      <Title title="Bản đồ IPA">
        Nghe từ ví dụ và chọn âm bạn muốn tập. Có bài luyện riêng cho{" "}
        {sounds.filter((item) => item.supported).length} âm.
      </Title>
      <div className="stack">
        <Panel className="stack">
          <label className="field">
            Tìm âm hoặc từ
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Ví dụ: ʃ, she"
            />
          </label>
          <div className="row" aria-label="Lọc âm" role="group">
            {[
              ["all", "Tất cả"],
              ["practice", "Có bài luyện"],
              ["difficult", "Âm hay nhầm"],
              ...Array.from(new Set(sounds.map((sound) => sound.group))).map((group) => [group, group]),
            ].map(([value, label]) => (
              <Button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>
                {label}
              </Button>
            ))}
          </div>
        </Panel>
        {matching.length === 0 && <Notice>Không tìm thấy âm hoặc từ phù hợp.</Notice>}
        {Array.from(new Set(matching.map((sound) => sound.group))).map((group) => (
          <section className="stack" key={group}>
            <h2>{group}</h2>
            <div className="sound-grid">
              {matching
                .filter((sound) => group === sound.group)
                .map((sound) => (
                  <article className="panel sound-card" key={sound.ipa}>
                    <div className="row spread">
                      <span className="ipa-mark">/{sound.ipa}/</span>
                      {study.some((item) => item.word === sound.word) && (
                        <span className="badge mint">Đã luyện</span>
                      )}
                    </div>
                    <h3 lang="en">{sound.word}</h3>
                    <small>{sound.guide}</small>
                    <div>
                      <SpeakButton text={sound.word} />
                    </div>
                    {sound.supported ? (
                      <Action href={`/luyen-ngu-am?am=${encodeURIComponent(sound.ipa)}`}>
                        Luyện âm
                      </Action>
                    ) : (
                      <small className="badge dim">Nghe tham khảo</small>
                    )}
                  </article>
                ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}

function useArticulationPhase(playing: boolean) {
  const [release, setRelease] = useState(false);
  useEffect(() => {
    if (!playing) {
      setRelease(false);
      return;
    }
    const timer = window.setInterval(() => setRelease((value) => !value), 800);
    return () => window.clearInterval(timer);
  }, [playing]);
  return playing && release;
}

function Articulation({
  sound,
  title,
  target = false,
  release = false,
}: {
  sound: Sound;
  title: string;
  target?: boolean;
  release?: boolean;
}) {
  const [, , , lip, jaw, tongue] = sound.hint ?? ["", "", "", 0.6, 0.45, 0.4];
  const x = 18 + lip * 28;
  const y = Math.max(1, 2 + jaw * 15 + (release ? 4 : 0));
  const center = 35 + tongue * 54;
  const contact = 32 + jaw * 12 + (release ? 6 : 0);
  return (
    <article className={`reference stack ${target ? "target" : ""}`}>
      <div className="row spread">
        <h3>{title}</h3>
        <span className="ipa-mark">/{sound.ipa}/</span>
      </div>
      <div className="grid reference-icons">
        <figure>
          <svg viewBox="0 0 120 80" role="img" aria-label={`Môi nhìn thẳng của âm ${sound.ipa}`}>
            <path
              className="art-mouth"
              d={`M ${60 - x} 40 Q 41 ${20 - y} 60 29 Q 79 ${20 - y} ${60 + x} 40 Q 79 ${54 + y} 60 ${52 + y} Q 41 ${54 + y} ${60 - x} 40Z`}
            />
            <ellipse className="art-gap" cx="60" cy="41" rx={x * 0.74} ry={y} />
          </svg>
          <figcaption>Môi · nhìn thẳng</figcaption>
        </figure>
        <figure>
          <svg viewBox="0 0 120 80" role="img" aria-label={`Lưỡi và hàm nhìn ngang của âm ${sound.ipa}`}>
            <path
              className="art-outline"
              d="M16 32Q30 17 51 21Q80 11 101 27L106 62Q74 74 35 64L17 51L25 44L15 39Z"
            />
            <path
              className="art-tongue"
              d={`M24 ${47 + y / 3} Q ${center} ${contact} 95 51L97 62 Q52 69 24 ${47 + y / 3}Z`}
            />
            <circle className="art-position" cx={center} cy={contact + 4} r="3" />
          </svg>
          <figcaption>Lưỡi · nhìn ngang</figcaption>
        </figure>
      </div>
      <p>{sound.guide}</p>
      <SpeakButton text={sound.word} />
    </article>
  );
}

function ArticulationComparison({
  heard,
  target,
  heardTitle,
  reducedMotion,
}: {
  heard: Sound;
  target: Sound;
  heardTitle: string;
  reducedMotion: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const active = playing && !reducedMotion;
  const release = useArticulationPhase(active);
  return (
    <div className="stack">
      <div className="grid two">
        <Articulation sound={heard} title={heardTitle} release={release} />
        <Articulation sound={target} title="Âm cần đọc" target release={release} />
      </div>
      <div className="row">
        <Button
          icon="play"
          aria-pressed={active}
          disabled={reducedMotion}
          onClick={() => setPlaying(!active)}
        >
          {active ? "Dừng mô phỏng hai âm" : "Xem mô phỏng hai âm"}
        </Button>
      </div>
    </div>
  );
}

function Feedback({
  assessment,
  sound,
  reducedMotion,
}: {
  assessment: Assessment;
  sound: Sound;
  reducedMotion: boolean;
}) {
  const phones = assessment.words.flatMap((word) =>
    word.phonemes.map((phone) => ({ ...phone, word: word.word })),
  );
  if (!phones.length)
    return (
      <Notice tone="warn">
        Dịch vụ chưa trả dữ liệu âm vị đã chấm. Hãy nghe lại và đối chiếu với hình hướng dẫn.
      </Notice>
    );
  const reported = assessment.errors?.find((item) => item.ipa === sound.ipa)?.actual;
  const actual = typeof reported === "string" ? reported.trim().replace(/^\/|\/$/g, "") : "";
  const phone = phones.find((item) => item.ipa === sound.ipa);
  const heard =
    actual && actual !== sound.ipa && sounds.find((item) => item.ipa === actual && item.hint);
  return (
    <section className="stack" aria-label="Kết quả chấm ngữ âm">
      <h3>Kết quả kiểm tra</h3>
      <div className="row">
        <span className="badge">Bài luyện · {assessment.sentence_score}/100</span>
        {assessment.words.map((word, index) => (
          <span className="badge dim" key={index}>
            {word.word} · {word.score}/100
          </span>
        ))}
      </div>
      <div className="feedback">
        <strong>Âm nhận được</strong>
        <p>
          {actual
            ? `Dịch vụ ghi /${actual}/ ở vị trí /${sound.ipa}/.`
            : "Dịch vụ chưa cung cấp nhãn âm thay thế."}
        </p>
      </div>
      <div className="feedback">
        <strong>So với âm mục tiêu</strong>
        <p>
          {phone
            ? `/${phone.ipa}/ · GOP ${phone.score}/100 trong từ ${phone.word}.`
            : "Chưa có điểm riêng cho âm đang chọn."}
        </p>
      </div>
      <div className="feedback">
        <strong>Thử điều chỉnh</strong>
        <p>{assessment.hints?.[0] ?? sound.guide}</p>
      </div>
      {heard && (
        <ArticulationComparison
          heard={heard}
          target={sound}
          heardTitle="Âm dịch vụ nhận được"
          reducedMotion={reducedMotion}
        />
      )}
      {actual && actual !== sound.ipa && !heard && (
        <small>
          Chưa có sơ đồ cho âm dịch vụ nhận được. Bạn vẫn có thể xem sơ đồ âm mục tiêu ở trên.
        </small>
      )}
      <details>
        <summary>Chi tiết âm vị</summary>
        <div className="row">
          {phones.map((item, index) => (
            <span
              className={`badge ${item.score >= 75 ? "mint" : item.score < 50 ? "score-low" : "score-mid"}`}
              key={index}
            >
              /{item.ipa}/ · {item.score} · {item.score >= 75 ? "Cao" : item.score < 50 ? "Thấp" : "Vừa"}
            </span>
          ))}
        </div>
      </details>
    </section>
  );
}

const contrasts: Record<string, string> = {
  seat: "sit",
  sit: "seat",
  bed: "bad",
  bad: "bed",
  she: "see",
  see: "she",
  pen: "ten",
};

function normalizedWords(text: string) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function BrowserFeedback({
  heard,
  phrase,
  sound,
  reducedMotion,
}: {
  heard: string;
  phrase: string;
  sound: Sound;
  reducedMotion: boolean;
}) {
  const word = normalizedWords(heard);
  const matches = word === normalizedWords(phrase);
  const contrast =
    phrase === sound.word && word === contrasts[sound.word]
      ? sounds.find((item) => item.word === word && item.hint)
      : undefined;
  return (
    <section className="stack" aria-label="Đối chiếu từ đã nhận dạng">
      <h3>Trình duyệt nghe được gì?</h3>
      <p>
        Trình duyệt nhận dạng <strong lang="en">{heard}</strong>.
      </p>
      {matches ? (
        <p>Từ nhận dạng trùng với bài luyện. Nghe lại bản thu nếu bạn muốn kiểm tra cách phát âm.</p>
      ) : contrast ? (
        <>
          <p>Hai từ này khác nhau ở một âm. Hãy thử đối chiếu sơ đồ rồi đọc lại từ mục tiêu.</p>
          <ArticulationComparison
            heard={contrast}
            target={sound}
            heardTitle="Âm trong từ được nhận dạng"
            reducedMotion={reducedMotion}
          />
        </>
      ) : (
        <p>Từ nhận dạng khác bài luyện. Hãy nghe lại hoặc thử ghi âm thêm một lần.</p>
      )}
      <small>
        Kết quả này chỉ phản ánh từ mà trình duyệt nhận dạng được. Điểm âm vị cần dịch vụ chấm riêng.
      </small>
    </section>
  );
}

export function Practice() {
  const params = useSearchParams();
  const { account, log, motion, logout } = useApp();
  const [ipa, setIpa] = useState(params.get("am") || "ʃ");
  const [context, setContext] = useState(false);
  const [showMotion, setShowMotion] = useState(false);
  const [systemMotion, setSystemMotion] = useState(false);
  const reducedMotion = motion || systemMotion;
  const previewPlaying = showMotion && !reducedMotion;
  const release = useArticulationPhase(previewPlaying);
  const [selfCompare, setSelfCompare] = useState(true);
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<"received" | "unknown">();
  const [assessment, setAssessment] = useState<Assessment>();
  const [marked, setMarked] = useState(false);
  const [error, setError] = useState("");
  const [browserSupported, setBrowserSupported] = useState(false);
  const [browserEnabled, setBrowserEnabled] = useState(false);
  const [browserResult, setBrowserResult] = useState<{ heard?: string; error?: string }>({});
  const [recognizing, setRecognizing] = useState(false);
  const [showBrowserResult, setShowBrowserResult] = useState(false);
  const activeCheck = useRef<{ controller: AbortController; dispatched: boolean; received: boolean }>();
  const recognizer = useRef<RecognitionHandle>();
  const feedback = useRef<HTMLDivElement>(null);
  const recorder = useRecorder({ maxSeconds: 4 });
  const { clip, status } = recorder;
  const sound = targets.find((item) => item.ipa === ipa) ?? targets[0];
  const compare = sounds.find((item) => item.ipa === sound.hint?.[2]);
  const phrase = context ? (sound.hint?.[1] ?? sound.word) : sound.word;
  const busy = recorder.status !== "idle" || checking;
  useEffect(() => {
    setBrowserSupported(hasRecognition());
    return () => {
      activeCheck.current?.controller.abort();
      recognizer.current?.cancel();
    };
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    function sync() {
      setSystemMotion(media.matches);
    }
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);
  useEffect(() => {
    setAssessment(undefined);
    setCheckResult(undefined);
    setError("");
    setMarked(false);
  }, [clip]);
  useEffect(() => {
    if (status !== "recording") return;
    setBrowserResult({});
    setShowBrowserResult(false);
    if (!browserEnabled) return;
    try {
      recognizer.current = startRecognition();
    } catch (error) {
      setBrowserResult({ error: error instanceof Error ? error.message : "Không mở được nhận dạng." });
    }
  }, [status, browserEnabled]);
  useEffect(() => {
    if (status !== "idle") return;
    const handle = recognizer.current;
    recognizer.current = undefined;
    if (!clip || !handle) {
      handle?.cancel();
      return;
    }
    let current = true;
    setRecognizing(true);
    void handle
      .finish()
      .then(
        (heard) => {
          if (current) setBrowserResult({ heard });
        },
        (error: unknown) => {
          if (current)
            setBrowserResult({
              error: error instanceof Error ? error.message : "Không nhận dạng được bản thu.",
            });
        },
      )
      .finally(() => {
        if (current) setRecognizing(false);
      });
    return () => {
      current = false;
      handle.cancel();
      setRecognizing(false);
    };
  }, [clip, status]);

  async function check() {
    if (!clip || recognizing || activeCheck.current || checkResult) return;
    setShowBrowserResult(browserEnabled);
    if (!account) {
      if (browserEnabled) feedback.current?.focus();
      else setError("Đăng nhập để gửi bản thu đến dịch vụ chấm ngữ âm.");
      return;
    }
    const request = new AbortController();
    const attempt = { controller: request, dispatched: false, received: false };
    activeCheck.current = attempt;
    setChecking(true);
    setError("");
    setAssessment(undefined);
    try {
      await sendAudio({
        blob: clip.blob,
        token: account.token,
        text: phrase,
        signal: request.signal,
        onDispatch() {
          attempt.dispatched = true;
        },
        onEvent(event) {
          if (event.type === "final" && !attempt.received) {
            attempt.received = true;
            setAssessment(event.assessment);
            setCheckResult("received");
            log(`Luyện /${sound.ipa}/ · ${sound.word}`, "speech", sound.word);
            feedback.current?.focus();
          }
          if (event.type === "error" && event.code === "unauthorized") logout();
        },
      });
    } catch (error) {
      if (!request.signal.aborted) {
        if (error instanceof AudioConnectionError && error.delivery === "unknown")
          setCheckResult("unknown");
        setError(error instanceof Error ? error.message : "Không kiểm tra được bản thu.");
      }
    } finally {
      if (activeCheck.current === attempt) activeCheck.current = undefined;
      if (!request.signal.aborted) setChecking(false);
    }
  }

  function cancelCheck() {
    const attempt = activeCheck.current;
    if (!attempt || attempt.received) return;
    activeCheck.current = undefined;
    attempt.controller.abort();
    setChecking(false);
    if (attempt.dispatched) {
      setCheckResult("unknown");
      setError("Đã dừng chờ kết quả. Máy chủ có thể đã lưu lượt này.");
    }
  }

  return (
    <>
      <div className="grid practice-grid practice-phonetics practice-workspace">
        <Panel className="stack">
          <h2>Bài luyện của bạn</h2>
          <div className="grid two">
            <label className="field">
              Âm mục tiêu
              <select
                value={sound.ipa}
                disabled={busy}
                onChange={(event) => {
                  recorder.clear();
                  setIpa(event.target.value);
                }}
              >
                {targets.map((item) => (
                  <option key={item.ipa} value={item.ipa}>
                    /{item.ipa}/
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Từ luyện
              <select
                value={sound.ipa}
                disabled={busy}
                onChange={(event) => {
                  recorder.clear();
                  setIpa(event.target.value);
                }}
              >
                {targets.map((item) => (
                  <option key={item.ipa} value={item.ipa}>
                    {item.word}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="row" role="group" aria-label="Dạng bài luyện">
            <Button
              disabled={busy}
              aria-pressed={!context}
              onClick={() => {
                setContext(false);
                recorder.clear();
              }}
            >
              Một từ
            </Button>
            <Button
              disabled={busy}
              aria-pressed={context}
              onClick={() => {
                setContext(true);
                recorder.clear();
              }}
            >
              Cụm từ
            </Button>
          </div>
          <div className="word-target">
            <span className="badge">/{sound.ipa}/</span>
            <strong lang="en">{phrase}</strong>
            <p>{sound.guide}</p>
          </div>
          {browserSupported && (
            <div className="stack">
              <label className="row">
                <input
                  type="checkbox"
                  checked={browserEnabled}
                  disabled={busy || Boolean(clip)}
                  onChange={(event) => setBrowserEnabled(event.target.checked)}
                />
                Đối chiếu từ bằng nhận dạng của trình duyệt
              </label>
              {browserEnabled && (
                <small>
                  Trình duyệt có thể gửi tiếng nói đến dịch vụ nhận dạng của nhà cung cấp trình duyệt.
                </small>
              )}
            </div>
          )}
          <div className="recorder stack">
            <RecordButton recorder={recorder} disabled={checking} />
            <strong>
              {recorder.status === "recording" || recorder.status === "permission"
                ? "Dừng ghi âm"
                : "Ghi âm"}
            </strong>
          </div>
          <RecorderDisplay recorder={recorder} />
          {recorder.clip && (
            <div className="stack">
              <audio controls src={recorder.clip.url} aria-label="Nghe lại bản thu" className="audio" />
              <div className="row">
                <Button
                  tone="primary"
                  icon="check"
                  disabled={context || checking || recognizing || Boolean(checkResult)}
                  onClick={() => void check()}
                >
                  {checking
                    ? "Đang kiểm tra…"
                    : recognizing
                      ? "Đang nhận dạng từ…"
                      : checkResult === "received"
                        ? "Đã nhận kết quả"
                        : checkResult === "unknown"
                          ? "Chưa xác nhận kết quả"
                          : context
                            ? "Chấm GOP ở chế độ từ đơn"
                            : "Kiểm tra"}
                </Button>
                <Button disabled={checking} onClick={recorder.clear}>
                  Thử lại
                </Button>
                {!account && (
                  <Button
                    disabled={marked}
                    onClick={() => {
                      setMarked(true);
                      log(`Tự luyện /${sound.ipa}/ · ${sound.word}`, "speech", sound.word);
                    }}
                  >
                    {marked ? "Đã đánh dấu tự luyện" : "Đánh dấu đã tự luyện"}
                  </Button>
                )}
              </div>
              {checking && checkResult !== "received" && (
                <Button onClick={cancelCheck}>Dừng chờ kết quả</Button>
              )}
            </div>
          )}
          {error && (
            <Notice tone="error">
              {error}
              {checkResult === "unknown" && (
                <p>Chọn Thử lại để ghi bản mới. Bạn vẫn có thể nghe lại bản thu này.</p>
              )}
              {!account && (
                <div className="row">
                  <Action href="/dang-nhap">Đăng nhập</Action>
                </div>
              )}
            </Notice>
          )}
        </Panel>
        <Panel className="stack">
          <div ref={feedback} className="stack feedback-summary" tabIndex={-1}>
            <h2>Cách đặt môi và lưỡi</h2>
            <p>
              Quan sát vị trí, thử động tác im lặng, sau đó phát âm. Hình là sơ đồ minh họa cho bài
              luyện.
            </p>
            <div className="grid two">
              {selfCompare && compare && (
                <Articulation sound={compare} title="Âm dễ nhầm" release={release} />
              )}
              <Articulation sound={sound} title="Âm cần đọc" target release={release} />
            </div>
            <div className="row">
              <Button
                aria-pressed={previewPlaying}
                disabled={reducedMotion}
                icon="play"
                onClick={() => setShowMotion(!previewPlaying)}
              >
                {previewPlaying ? "Dừng mô phỏng" : "Xem mô phỏng"}
              </Button>
              <Button aria-pressed={selfCompare} onClick={() => setSelfCompare(!selfCompare)}>
                {selfCompare ? "Ẩn âm dễ nhầm" : "So sánh âm dễ nhầm"}
              </Button>
            </div>
            <small>
              Tham khảo{" "}
              <a
                href="https://adrianunderhill.com/pronunciation-resources-video-primers/"
                target="_blank"
                rel="noreferrer"
                className="text-link"
              >
                phương pháp luyện ngữ âm của Adrian Underhill
              </a>
              .
            </small>
            {clip && showBrowserResult && browserResult.heard && (
              <BrowserFeedback
                heard={browserResult.heard}
                phrase={phrase}
                sound={sound}
                reducedMotion={reducedMotion}
              />
            )}
            {clip && showBrowserResult && browserResult.error && (
              <Notice tone="warn">{browserResult.error}</Notice>
            )}
            {assessment && (
              <Feedback assessment={assessment} sound={sound} reducedMotion={reducedMotion} />
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}
