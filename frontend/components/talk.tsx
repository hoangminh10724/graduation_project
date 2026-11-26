"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, AudioConnectionError, api, sendAudio, type Level, type TalkSession } from "@/lib/api";
import { hasRecognition, startRecognition, type RecognitionHandle } from "@/lib/recognition";
import { useRecorder, type Clip } from "@/lib/recorder";
import { speak, stopSpeech } from "@/lib/voice";
import { Action, Button, Busy, Empty, Icon, Notice, Panel } from "./ui";
import { PracticeBanner } from "./practice-banner";
import { RecorderDisplay } from "./audio-controls";
import { useApp } from "./provider";

function hintLanguage(text: string) {
  return /đ|[aeiouy][\u0300\u0301\u0302\u0303\u0306\u0309\u031b\u0323]/iu.test(text.normalize("NFD"))
    ? "vi-VN"
    : "en-GB";
}

export function Talk() {
  const { account, ready, profile, study, log, logout } = useApp();
  const [level, setLevel] = useState<Level>(profile.level);
  const [selected, setSelected] = useState<string[]>([]);
  const [session, setSession] = useState<TalkSession>();
  const [creating, setCreating] = useState(false);
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [reply, setReply] = useState("");
  const [hint, setHint] = useState("");
  const [speechUnavailable, setSpeechUnavailable] = useState(false);
  const [browserSpeech, setBrowserSpeech] = useState(false);
  const [browserSupported, setBrowserSupported] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [retry, setRetry] = useState(false);
  const [unknownDelivery, setUnknownDelivery] = useState(false);
  const recentWords = study.slice(0, 14);
  const words = selected.filter((word) => study.some((item) => item.word === word));
  const request = useRef<AbortController>();
  const recognizer = useRef<RecognitionHandle>();
  const recognized = useRef("");
  const pressed = useRef(false);
  const skipClick = useRef(false);
  const authKey = account?.id;

  useEffect(() => {
    setBrowserSupported(hasRecognition());
  }, []);
  useEffect(() => {
    setLevel(profile.level);
  }, [profile.level]);
  useEffect(() => {
    setSession(undefined);
    setSelected([]);
    setReply("");
    setHint("");
    setSpeechUnavailable(false);
    setUnknownDelivery(false);
    setStatus("");
    return () => {
      request.current?.abort();
      recognizer.current?.cancel();
      stopSpeech();
    };
  }, [authKey]);

  function playReply(text: string, language: "en-GB" | "vi-VN" = "en-GB") {
    stopSpeech();
    setSpeaking(true);
    speak(text, {
      rate: 0.91,
      language,
      end: () => setSpeaking(false),
      error: (message) => {
        setSpeaking(false);
        setError(message);
      },
    });
  }

  async function send(clip: Clip, browserText?: string) {
    if (!account || !session || request.current) return;
    setSending(true);
    setError("");
    setRetry(false);
    setUnknownDelivery(false);
    setReply("");
    setHint("");
    setSpeechUnavailable(false);
    let replyReady = false;
    const controller = new AbortController();
    request.current = controller;
    try {
      setStatus(
        browserSpeech && !browserText ? "Đang nhận dạng bằng trình duyệt…" : "Đang gửi bản thu…",
      );
      const text = browserSpeech ? browserText || (await recognizer.current?.finish()) : undefined;
      if (browserSpeech && !text) throw new Error("Chưa có kết quả nhận dạng. Hãy ghi lại lượt nói.");
      recognized.current = text ?? "";
      if (controller.signal.aborted) return;
      await sendAudio({
        blob: clip.blob,
        token: account.token,
        sessionId: session.id,
        text,
        signal: controller.signal,
        onEvent(event) {
          if (event.type === "partial") setStatus("Đang gửi bản thu…");
          if (event.type === "transcript") setStatus("Gia sư đang chuẩn bị câu trả lời…");
          if (event.type === "done") {
            replyReady = true;
            setStatus("Đã nhận phản hồi của gia sư.");
            setReply(event.text);
            log(`Hội thoại · ${words.join(", ")}`, "talk");
            playReply(event.text);
          }
          if (event.type === "final" || event.type === "coaching") {
            const hints = event.type === "final" ? event.assessment.hints : event.hints;
            const next = hints?.find((item) => item.trim())?.trim();
            if (next) setHint(next);
          }
          if (event.type === "error" && event.code === "speech_unavailable") setSpeechUnavailable(true);
          if (event.type === "error" && event.code === "llm_unavailable") {
            setError("Gia sư AI chưa phản hồi được. Vui lòng thử sau.");
            setStatus("");
          }
          if (event.type === "error" && event.code === "unauthorized") logout();
        },
      });
      if (!replyReady && !controller.signal.aborted) setStatus("");
    } catch (error) {
      if (!controller.signal.aborted) {
        setError(error instanceof Error ? error.message : "Không gửi được lượt nói.");
        setStatus(replyReady ? "Đã nhận phản hồi của gia sư." : "");
        const delivery = error instanceof AudioConnectionError ? error.delivery : undefined;
        setUnknownDelivery(!replyReady && delivery === "unknown");
        setRetry(
          !replyReady && delivery === "unsent" && (!browserSpeech || Boolean(recognized.current)),
        );
      }
    } finally {
      recognizer.current = undefined;
      if (request.current === controller) request.current = undefined;
      if (!controller.signal.aborted) setSending(false);
    }
  }

  const recorder = useRecorder({
    maxSeconds: 24,
    preferWav: false,
    onClip: (clip) => {
      void send(clip);
    },
  });
  useEffect(() => {
    if (recorder.status !== "recording" || !browserSpeech) return;
    try {
      recognizer.current = startRecognition();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Không mở được nhận dạng giọng nói.");
    }
  }, [recorder.status, browserSpeech]);

  useEffect(() => {
    if (recorder.status === "idle" && !recorder.clip) {
      recognizer.current?.cancel();
      recognizer.current = undefined;
    }
  }, [recorder.status, recorder.clip]);

  async function create() {
    if (!account || !words.length || creating) return;
    setCreating(true);
    setError("");
    setReply("");
    setHint("");
    setSpeechUnavailable(false);
    try {
      const session = await api<TalkSession>("/sessions", {
        token: account.token,
        data: {
          cefr_level: level,
          topic: `Voice practice: use these learned words naturally: ${words.join(", ")}`,
        },
      });
      setSession(session);
      setStatus("");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) logout();
      setError(error instanceof Error ? error.message : "Không tạo được phiên luyện.");
    } finally {
      setCreating(false);
    }
  }

  function start() {
    setError("");
    setStatus("");
    setRetry(false);
    setUnknownDelivery(false);
    setSpeechUnavailable(false);
    stopSpeech();
    recognized.current = "";
    void recorder.start();
  }
  function endHold() {
    if (!pressed.current) return;
    pressed.current = false;
    recorder.stop();
  }
  const capturing = recorder.status === "recording" || recorder.status === "permission";
  const busy = creating || sending || recorder.status !== "idle";
  const controlDisabled = sending || recorder.status === "preparing";
  const prompt = `Tell me about your day. Try to use at least one of these words: ${words.join(", ")}.`;

  return (
    <>
      <PracticeBanner area="talk" />
      {!ready ? (
        <Busy>Đang kiểm tra phiên đăng nhập…</Busy>
      ) : !account ? (
        <Empty title="Đăng nhập để nói với gia sư" icon="talk">
          <p>Phiên luyện cần tài khoản WordSpeak.</p>
          <Action href="/dang-nhap" primary>
            Đăng nhập
          </Action>
        </Empty>
      ) : !recentWords.length ? (
        <Empty title="Hãy học một từ trước" icon="book">
          <p>Đánh dấu từ đã học trong từ điển hoặc hoàn thành một lượt luyện ngữ âm.</p>
          <Action href="/tu-dien" primary>
            Mở từ điển
          </Action>
        </Empty>
      ) : (
        <div className="grid talk-grid practice-conversation practice-workspace">
          <Panel className="stack">
            <h2>Chuẩn bị buổi luyện</h2>
            <p>Chọn tối đa 4 từ đã học để đưa vào cuộc nói chuyện.</p>
            <div className="row" role="group" aria-label="Từ dùng trong buổi luyện">
              {recentWords.map(({ word }) => (
                <Button
                  key={word}
                  aria-pressed={words.includes(word)}
                  disabled={Boolean(session) || busy || (!words.includes(word) && words.length >= 4)}
                  onClick={() =>
                    setSelected(
                      words.includes(word) ? words.filter((item) => item !== word) : [...words, word],
                    )
                  }
                >
                  {word}
                </Button>
              ))}
            </div>
            <label className="field">
              Trình độ
              <select
                disabled={Boolean(session) || busy}
                value={level}
                onChange={(event) => setLevel(event.target.value as Level)}
              >
                <option>A2</option>
                <option>B1</option>
                <option>B2</option>
              </select>
            </label>
            {browserSupported && (
              <label className="row">
                <input
                  type="checkbox"
                  checked={browserSpeech}
                  disabled={busy}
                  onChange={(event) => {
                    setBrowserSpeech(event.target.checked);
                    setRetry(false);
                  }}
                />{" "}
                Dùng nhận dạng của trình duyệt
              </label>
            )}
            {browserSpeech && (
              <small>
                Trình duyệt có thể gửi tiếng nói tới dịch vụ nhận dạng của nhà cung cấp trình duyệt.
              </small>
            )}
            {session ? (
              <Button
                disabled={busy}
                onClick={() => {
                  stopSpeech();
                  recorder.clear();
                  setSession(undefined);
                  setReply("");
                  setHint("");
                  setSpeechUnavailable(false);
                  setStatus("");
                  setError("");
                }}
              >
                Đổi bài luyện
              </Button>
            ) : (
              <Button
                tone="primary"
                icon="talk"
                disabled={busy || !words.length}
                onClick={() => void create()}
              >
                {creating ? "Đang mở phiên…" : "Bắt đầu luyện nói"}
              </Button>
            )}
          </Panel>
          <Panel className="stack">
            <div className="row spread">
              <h2>Phòng luyện giọng nói</h2>
              {session && <span className="badge mint">Phiên {level}</span>}
            </div>
            {!session ? (
              <p>Chọn từ, mở phiên và bật micro để trả lời bằng tiếng Anh.</p>
            ) : (
              <>
                <div className="row">
                  <Button icon="volume" disabled={busy || speaking} onClick={() => playReply(prompt)}>
                    Nghe câu gợi mở
                  </Button>
                  {reply && (
                    <Button icon="volume" disabled={busy || speaking} onClick={() => playReply(reply)}>
                      Nghe lại gia sư
                    </Button>
                  )}
                  {hint && (
                    <Button
                      icon="volume"
                      disabled={busy || speaking}
                      onClick={() => playReply(hint, hintLanguage(hint))}
                    >
                      Nghe gợi ý phát âm
                    </Button>
                  )}
                  {speaking && (
                    <Button icon="stop" onClick={stopSpeech}>
                      Dừng phát
                    </Button>
                  )}
                </div>
                <div className="talk-stage recorder stack">
                  <Button
                    className="record"
                    tone="primary"
                    icon={capturing ? "stop" : "mic"}
                    disabled={controlDisabled}
                    aria-label={capturing ? "Dừng ghi âm hội thoại" : "Giữ để nói"}
                    onPointerDown={(event) => {
                      if (event.button !== 0 || capturing) return;
                      event.currentTarget.setPointerCapture(event.pointerId);
                      pressed.current = true;
                      skipClick.current = true;
                      start();
                    }}
                    onPointerUp={endHold}
                    onPointerCancel={endHold}
                    onLostPointerCapture={endHold}
                    onKeyDown={(event) => {
                      if ((event.key !== " " && event.key !== "Enter") || event.repeat || capturing)
                        return;
                      event.preventDefault();
                      pressed.current = true;
                      start();
                    }}
                    onKeyUp={(event) => {
                      if (event.key === " " || event.key === "Enter") {
                        event.preventDefault();
                        endHold();
                      }
                    }}
                    onBlur={endHold}
                    onClick={() => {
                      if (skipClick.current) {
                        skipClick.current = false;
                        return;
                      }
                      if (capturing) recorder.stop();
                      else start();
                    }}
                  />
                  <strong>{capturing ? "Nhả để gửi" : "Nhấn giữ để nói"}</strong>
                  <Button
                    disabled={controlDisabled}
                    onClick={() => {
                      if (capturing) recorder.stop();
                      else start();
                    }}
                  >
                    {capturing ? "Dừng và gửi" : "Bấm để ghi âm"}
                  </Button>
                </div>
                <RecorderDisplay recorder={recorder} />
                <p role="status">{speaking ? "Gia sư đang nói…" : status}</p>
                {recorder.clip && (
                  <audio
                    src={recorder.clip.url}
                    aria-label="Nghe lại lượt nói"
                    controls
                    className="audio"
                  />
                )}
                {retry && recorder.clip && (
                  <Button
                    disabled={busy}
                    onClick={() => {
                      if (recorder.clip) void send(recorder.clip, recognized.current);
                    }}
                  >
                    Gửi lại bản thu
                  </Button>
                )}
              </>
            )}
            {error && (
              <Notice tone="error">
                {error}
                {unknownDelivery && (
                  <div>
                    <Action href="/lich-su">Kiểm tra Lịch sử trước khi nói lại</Action>
                  </div>
                )}
                {speechUnavailable && !browserSpeech && browserSupported && (
                  <div>
                    <Button
                      disabled={busy}
                      onClick={() => {
                        setBrowserSpeech(true);
                        setRetry(false);
                      }}
                    >
                      Dùng nhận dạng trình duyệt cho lần tiếp theo
                    </Button>
                  </div>
                )}
              </Notice>
            )}
          </Panel>
        </div>
      )}
    </>
  );
}
