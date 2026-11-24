"use client";

import { useEffect, useRef, useState } from "react";
import { playSample, stopSpeech, speak } from "@/lib/voice";
import type { Recorder } from "@/lib/recorder";
import { Button, Notice } from "./ui";

export function SpeakButton({
  text,
  label = "Nghe mẫu",
  rate,
  audioSrc,
}: {
  text: string;
  label?: string;
  rate?: number;
  audioSrc?: string;
}) {
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState("");
  const release = useRef<() => void>();
  useEffect(() => {
    setPlaying(false);
    setError("");
    return () => release.current?.();
  }, [text, audioSrc]);
  return (
    <div className="speak-control">
      <Button
        icon={playing ? "stop" : "volume"}
        aria-label={playing ? "Dừng mẫu" : `${label}: ${text}`}
        onClick={() => {
          if (playing) {
            stopSpeech();
            return;
          }
          setPlaying(true);
          setError("");
          const callbacks = {
            end: () => setPlaying(false),
            error: (message: string) => {
              setPlaying(false);
              setError(message);
            },
          };
          release.current = audioSrc
            ? playSample(audioSrc, callbacks)
            : speak(text, { rate, ...callbacks });
        }}
      >
        {playing ? "Dừng mẫu" : label}
      </Button>
      {error && (
        <small role="alert" className="field-error">
          {error}
        </small>
      )}
    </div>
  );
}

const label = {
  idle: "Sẵn sàng thu âm",
  permission: "Đang xin quyền micro",
  recording: "Đang ghi âm",
  preparing: "Đang chuẩn bị bản thu",
};

export function RecorderDisplay({ recorder }: { recorder: Recorder }) {
  const time = Math.floor(recorder.seconds);
  return (
    <div className="stack">
      <div className="waveform" aria-hidden="true">
        {recorder.wave.map((height, index) => (
          <span key={index} style={{ height }} />
        ))}
      </div>
      <div className="row spread">
        <span role="status">{label[recorder.status]}</span>
        <time>{`0:${String(time).padStart(2, "0")}`}</time>
      </div>
      <meter className="meter" min="0" max="100" value={recorder.level} aria-label="Mức thu hiện tại" />
      {recorder.message && <Notice tone="error">{recorder.message}</Notice>}
      {recorder.clip && recorder.clip.peak < 0.02 && (
        <Notice tone="warn">Âm lượng thấp. Hãy đưa micro gần hơn và thử lại.</Notice>
      )}
      {recorder.clip && recorder.clip.peak > 0.99 && (
        <Notice tone="warn">Âm thanh có thể bị vỡ. Hãy giữ khoảng cách với micro khi thử lại.</Notice>
      )}
    </div>
  );
}
export function RecordButton({ recorder, disabled }: { recorder: Recorder; disabled?: boolean }) {
  const capturing = recorder.status === "permission" || recorder.status === "recording";
  return (
    <Button
      className="record"
      tone="primary"
      icon={capturing ? "stop" : "mic"}
      aria-label={capturing ? "Dừng ghi âm" : "Ghi âm"}
      disabled={disabled || recorder.status === "preparing"}
      onClick={() => {
        if (capturing) recorder.stop();
        else {
          stopSpeech();
          void recorder.start();
        }
      }}
    />
  );
}
