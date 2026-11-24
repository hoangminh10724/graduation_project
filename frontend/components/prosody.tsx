"use client";

import { useEffect, useRef, useState } from "react";
import { prosody } from "@/lib/content";
import { samples } from "@/lib/prosody-audio";
import { stopSpeech } from "@/lib/voice";
import { useRecorder } from "@/lib/recorder";
import { RecorderDisplay, RecordButton } from "./audio-controls";
import { Button, Notice, Panel } from "./ui";
import { PracticeBanner } from "./practice-banner";
import { useApp } from "./provider";

type Attempt = { id: string; blob: Blob; label: string };
function Playback({
  item,
  number,
  latest,
  disabled,
  onPlay,
}: {
  item: Attempt;
  number: number;
  latest: boolean;
  disabled: boolean;
  onPlay: (audio: HTMLAudioElement) => void;
}) {
  const [url, setUrl] = useState("");
  const [playing, setPlaying] = useState(false);
  const [failed, setFailed] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const player = audio.current;
    const created = URL.createObjectURL(item.blob);
    setUrl(created);
    return () => {
      player?.pause();
      URL.revokeObjectURL(created);
    };
  }, [item.blob]);
  return (
    <div className="list-item">
      <strong>Bản thử {number}</strong>
      {latest && (
        <Button
          tone="primary"
          icon={playing ? "stop" : "volume"}
          disabled={!url || disabled}
          onClick={() => {
            if (playing) audio.current?.pause();
            else {
              setFailed(false);
              void audio.current?.play().catch(() => setFailed(true));
            }
          }}
        >
          {playing ? "Tạm dừng bản thu" : "Nghe lại bản thu"}
        </Button>
      )}
      <audio
        ref={audio}
        src={url || undefined}
        controls={!disabled}
        className="audio"
        aria-label={`Bản thử ${number} · ${item.label}`}
        onPlay={(event) => {
          setPlaying(true);
          onPlay(event.currentTarget);
        }}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
      {failed && <Notice tone="error">Chưa phát được bản thu. Vui lòng thử lại.</Notice>}
    </div>
  );
}

export function Prosody() {
  const { log } = useApp();
  const [lesson, setLesson] = useState(0);
  const [variant, setVariant] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [reflection, setReflection] = useState("");
  const [attempts, setAttempts] = useState<Record<string, Attempt[]>>({});
  const track = useRef(0);
  const player = useRef<HTMLAudioElement>(null);
  const attemptPlayer = useRef<HTMLAudioElement | null>(null);
  const activity = prosody[lesson];
  const example = activity.examples[variant];
  const sample = samples[lesson][variant];
  const key = `${lesson}-${variant}`;
  const contour = sample.contour;
  const firstTime = contour[0][0];
  const lastTime = contour[contour.length - 1][0];
  const x = (time: number) => 30 + ((time - firstTime) / (lastTime - firstTime)) * 298;
  const y = (hz: number) => 108 - ((hz - 125) / 150) * 85;
  const points = contour.map(([time, hz]) => [x(time), y(hz)]);
  const active = position === null ? -1 : sample.words.findLastIndex((start) => start <= position);
  const marker =
    position === null
      ? null
      : (() => {
          const time = Math.min(lastTime, Math.max(firstTime, position));
          const right = contour.findIndex(([offset]) => offset >= time);
          if (right < 1) return points[0];
          const [before, low] = contour[right - 1];
          const [after, high] = contour[right];
          return [x(time), y(low + ((time - before) / (after - before)) * (high - low))];
        })();
  const recorder = useRecorder({
    maxSeconds: 5,
    onClip: (clip) => {
      setAttempts((previous) => ({
        ...previous,
        [key]: [...(previous[key] ?? []), { id: clip.url, blob: clip.blob, label: example.text }].slice(
          -2,
        ),
      }));
      log(`${activity.title} · ${example.text}`, "prosody");
    },
  });
  function stopExample() {
    if (player.current) {
      player.current.pause();
      player.current.currentTime = 0;
    }
    clearMarker();
  }
  function clearMarker() {
    cancelAnimationFrame(track.current);
    setPosition(null);
    setPlaying(false);
  }
  useEffect(() => () => cancelAnimationFrame(track.current), []);
  useEffect(() => {
    if (recorder.status !== "idle") attemptPlayer.current?.pause();
  }, [recorder.status]);

  function play() {
    setError("");
    stopSpeech();
    attemptPlayer.current?.pause();
    void player.current?.play().catch(() => {
      clearMarker();
      setError("Chưa phát được tệp âm thanh mẫu. Vui lòng thử lại.");
    });
  }
  function trackPlayback() {
    setPlaying(true);
    cancelAnimationFrame(track.current);
    function update() {
      const audio = player.current;
      if (!audio || audio.paused || audio.ended) return;
      setPosition(audio.currentTime);
      track.current = requestAnimationFrame(update);
    }
    track.current = requestAnimationFrame(update);
  }

  return (
    <>
      <PracticeBanner area="luyen-ngu-dieu" />
      <div className="stack practice-prosody practice-workspace">
        <div className="row" role="group" aria-label="Chủ điểm ngữ điệu">
          {prosody.map((item, index) => (
            <Button
              key={item.title}
              aria-pressed={index === lesson}
              disabled={recorder.status !== "idle"}
              onClick={() => {
                stopExample();
                recorder.clear();
                setLesson(index);
                setVariant(0);
                setReflection("");
                setError("");
              }}
            >
              {item.title}
            </Button>
          ))}
        </div>
        <div className="grid two">
          <Panel className="stack">
            <h2>{activity.title}</h2>
            <p>{activity.cue}</p>
            {activity.examples.length > 1 && (
              <div className="row" role="group" aria-label="Mẫu câu">
                {activity.examples.map((item, index) => (
                  <Button
                    key={index}
                    disabled={recorder.status !== "idle"}
                    aria-pressed={index === variant}
                    onClick={() => {
                      stopExample();
                      recorder.clear();
                      setVariant(index);
                      setReflection("");
                      setError("");
                    }}
                  >
                    {item.emphasize < 0
                      ? item.text
                      : `Nhấn ${item.segments[item.emphasize].replace(/\W/g, "").toUpperCase()}`}
                  </Button>
                ))}
              </div>
            )}
            <div className="pitch stack">
              <div className="row pitch-labels" lang="en">
                {example.segments.map((segment, index) => (
                  <span className={`pitch-segment ${active === index ? "active" : ""}`} key={segment}>
                    {example.emphasize === index ? <strong>{segment.toUpperCase()}</strong> : segment}
                  </span>
                ))}
              </div>
              <svg viewBox="0 0 360 125" role="img" aria-label="Đường ngữ điệu tham chiếu">
                <path d="M24 108H335" stroke="var(--muted)" strokeDasharray="3 5" />
                <polyline
                  points={points.map((point) => point.join(",")).join(" ")}
                  fill="none"
                  stroke="var(--primary)"
                  strokeWidth="4"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                {marker && (
                  <circle
                    cx={marker[0]}
                    cy={marker[1]}
                    r="7"
                    fill="var(--primary)"
                    stroke="var(--surface)"
                    strokeWidth="2"
                  />
                )}
              </svg>
              <small>Cao độ của mẫu nghe · giọng tổng hợp</small>
            </div>
            <audio
              ref={player}
              src={`/audio/${sample.file}.wav`}
              preload="metadata"
              onPlay={trackPlayback}
              onPause={clearMarker}
              onEnded={clearMarker}
            />
            <div>
              <Button
                icon={playing ? "stop" : "volume"}
                disabled={recorder.status !== "idle"}
                onClick={playing ? stopExample : play}
              >
                {playing ? "Dừng mẫu" : "Nghe mẫu"}
              </Button>
            </div>
            {error && <Notice tone="error">{error}</Notice>}
          </Panel>
          <Panel className="stack">
            <h2>Nghe lại hai lần nói</h2>
            <div className="recorder stack">
              <RecordButton recorder={recorder} disabled={playing} />
            </div>
            <RecorderDisplay recorder={recorder} />
            <div className="stack">
              {(attempts[key] ?? []).map((item, index) => (
                <Playback
                  item={item}
                  number={index + 1}
                  latest={index === attempts[key].length - 1}
                  disabled={recorder.status !== "idle"}
                  key={item.id}
                  onPlay={(audio) => {
                    if (attemptPlayer.current !== audio) attemptPlayer.current?.pause();
                    attemptPlayer.current = audio;
                    stopExample();
                  }}
                />
              ))}
            </div>
            <div className="row">
              <Button aria-pressed={reflection === "hear"} onClick={() => setReflection("hear")}>
                Tôi nghe thấy thay đổi
              </Button>
              <Button aria-pressed={reflection === "retry"} onClick={() => setReflection("retry")}>
                Tôi muốn thử lại
              </Button>
            </div>
            {reflection && (
              <p role="status">
                {reflection === "hear"
                  ? "So sánh từ bạn nhấn với mẫu trước khi chuyển bài."
                  : "Thu thêm một lần. Hai bản thử gần nhất sẽ được giữ."}
              </p>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}
