"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type Clip = { blob: Blob; url: string; seconds: number; peak: number };
type Session = {
  stream: MediaStream;
  context: AudioContext;
  recorder: MediaRecorder;
  frame: number;
  started: number;
  peak: number;
  chunks: Blob[];
  timeout: number;
  discarded: boolean;
};
const flatWave = Array<number>(30).fill(5);

async function wav16k(source: Blob, context: AudioContext) {
  const decoded = await context.decodeAudioData(await source.arrayBuffer());
  const rate = 16000;
  const frames = Math.max(1, Math.round(decoded.duration * rate));
  const output = new OfflineAudioContext(1, frames, rate);
  const input = output.createBufferSource();
  input.buffer = decoded;
  input.connect(output.destination);
  input.start();
  const pcm = (await output.startRendering()).getChannelData(0);
  const result = new DataView(new ArrayBuffer(44 + frames * 2));
  function write(offset: number, value: string) {
    for (let index = 0; index < value.length; index++)
      result.setUint8(offset + index, value.charCodeAt(index));
  }
  write(0, "RIFF");
  result.setUint32(4, 36 + frames * 2, true);
  write(8, "WAVEfmt ");
  result.setUint32(16, 16, true);
  result.setUint16(20, 1, true);
  result.setUint16(22, 1, true);
  result.setUint32(24, rate, true);
  result.setUint32(28, rate * 2, true);
  result.setUint16(32, 2, true);
  result.setUint16(34, 16, true);
  write(36, "data");
  result.setUint32(40, frames * 2, true);
  for (let index = 0; index < frames; index++) {
    const sample = Math.max(-1, Math.min(1, pcm[index]));
    result.setInt16(44 + index * 2, sample * (sample < 0 ? 32768 : 32767), true);
  }
  return new Blob([result.buffer], { type: "audio/wav" });
}

function release(session: Session) {
  window.clearTimeout(session.timeout);
  cancelAnimationFrame(session.frame);
  session.stream.getTracks().forEach((track) => track.stop());
}

export function useRecorder({
  maxSeconds = 4,
  preferWav = true,
  onClip,
}: {
  maxSeconds?: number;
  preferWav?: boolean;
  onClip?: (clip: Clip) => void;
} = {}) {
  const session = useRef<Session>();
  const phase = useRef<"idle" | "permission" | "recording" | "preparing">("idle");
  const generation = useRef(0);
  const url = useRef("");
  const [status, setStatus] = useState(phase.current);
  const [clip, setClip] = useState<Clip>();
  const [message, setMessage] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [wave, setWave] = useState(flatWave);
  const notify = useRef(onClip);
  useEffect(() => {
    notify.current = onClip;
  }, [onClip]);

  function change(next: typeof phase.current) {
    phase.current = next;
    setStatus(next);
  }
  const cancel = useCallback(() => {
    generation.current++;
    const active = session.current;
    session.current = undefined;
    if (active) {
      active.discarded = true;
      if (active.recorder.state !== "inactive") active.recorder.stop();
      release(active);
      void active.context.close().catch(() => {});
    }
    phase.current = "idle";
  }, []);

  useEffect(
    () => () => {
      cancel();
      if (url.current) URL.revokeObjectURL(url.current);
    },
    [cancel],
  );

  function clear() {
    cancel();
    if (url.current) URL.revokeObjectURL(url.current);
    url.current = "";
    setClip(undefined);
    setSeconds(0);
    setLevel(0);
    setWave(flatWave);
    setMessage("");
    setStatus("idle");
  }

  function stop() {
    if (phase.current === "permission") {
      clear();
      return;
    }
    const active = session.current;
    if (active?.recorder.state !== "recording") return;
    change("preparing");
    active.recorder.stop();
    release(active);
  }

  async function start() {
    if (phase.current !== "idle") return;
    clear();
    if (
      !navigator.mediaDevices?.getUserMedia ||
      !("MediaRecorder" in window) ||
      !("AudioContext" in window)
    ) {
      setMessage("Micro chưa khả dụng. Hãy dùng trình duyệt hỗ trợ ghi âm qua HTTPS hoặc localhost.");
      return;
    }
    const ticket = ++generation.current;
    change("permission");
    let stream: MediaStream | undefined;
    let context: AudioContext | undefined;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true },
        video: false,
      });
      if (ticket !== generation.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      context = new AudioContext();
      await context.resume();
      if (ticket !== generation.current) {
        stream.getTracks().forEach((track) => track.stop());
        await context.close();
        return;
      }
      const format = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((item) =>
        MediaRecorder.isTypeSupported(item),
      );
      const recorder = new MediaRecorder(stream, format ? { mimeType: format } : undefined);
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      context.createMediaStreamSource(stream).connect(analyser);
      const owner: Session = {
        stream,
        context,
        recorder,
        frame: 0,
        started: performance.now(),
        peak: 0,
        chunks: [],
        timeout: 0,
        discarded: false,
      };
      session.current = owner;
      const samples = new Float32Array(analyser.fftSize);
      let sampledAt = 0;
      function sample() {
        if (phase.current !== "recording" || owner.discarded) return;
        const now = performance.now();
        if (now - sampledAt >= 65) {
          sampledAt = now;
          analyser.getFloatTimeDomainData(samples);
          const power = samples.reduce((sum, value) => sum + value * value, 0) / samples.length;
          const bars = flatWave.map((_, bar) => {
            const offset = Math.floor((bar * samples.length) / flatWave.length);
            const stride = Math.floor(samples.length / flatWave.length);
            let peak = 0;
            for (let index = offset; index < offset + stride; index++)
              peak = Math.max(peak, Math.abs(samples[index]));
            owner.peak = Math.max(owner.peak, peak);
            return Math.min(54, 5 + peak * 123);
          });
          setWave(bars);
          setLevel(Math.min(100, Math.round(Math.sqrt(power) * 245)));
          setSeconds((now - owner.started) / 1000);
        }
        owner.frame = requestAnimationFrame(sample);
      }
      recorder.ondataavailable = (event) => {
        if (event.data.size) owner.chunks.push(event.data);
      };
      recorder.onerror = () => {
        if (generation.current !== ticket) return;
        clear();
        setMessage("Không thể tiếp tục ghi âm. Kiểm tra quyền micro rồi thử lại.");
      };
      recorder.onstop = async () => {
        release(owner);
        try {
          if (owner.discarded || ticket !== generation.current) return;
          const elapsed = Math.min(maxSeconds, (performance.now() - owner.started) / 1000);
          const source = new Blob(owner.chunks, { type: recorder.mimeType || format || "" });
          if (!source.size || elapsed < 0.25)
            throw new Error("Bản thu quá ngắn. Hãy nói ít nhất một từ.");
          const blob =
            preferWav || !source.type.startsWith("audio/webm")
              ? await wav16k(source, owner.context)
              : new Blob([source], { type: "audio/webm" });
          if (ticket !== generation.current) return;
          const next = { blob, url: URL.createObjectURL(blob), seconds: elapsed, peak: owner.peak };
          url.current = next.url;
          setClip(next);
          setSeconds(elapsed);
          notify.current?.(next);
        } catch (error) {
          if (ticket === generation.current)
            setMessage(error instanceof Error ? error.message : "Không đọc được bản thu.");
        } finally {
          void owner.context.close().catch(() => {});
          if (ticket === generation.current) {
            session.current = undefined;
            change("idle");
          }
        }
      };
      recorder.start(250);
      change("recording");
      owner.timeout = window.setTimeout(stop, maxSeconds * 1000);
      owner.frame = requestAnimationFrame(sample);
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      if (context) void context.close().catch(() => {});
      if (ticket !== generation.current) return;
      session.current = undefined;
      change("idle");
      const name = error instanceof DOMException ? error.name : "";
      setMessage(
        name === "NotAllowedError"
          ? "Micro chưa được cấp quyền. Hãy bật quyền micro rồi thử lại."
          : name === "NotFoundError"
            ? "Không tìm thấy micro đang kết nối."
            : "Không mở được micro. Kiểm tra thiết bị rồi thử lại.",
      );
    }
  }

  return { status, clip, message, seconds, level, wave, start, stop, clear };
}
export type Recorder = ReturnType<typeof useRecorder>;
