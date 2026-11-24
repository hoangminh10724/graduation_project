type SpeechOptions = {
  rate?: number;
  pitch?: number;
  language?: "en-GB" | "vi-VN";
  start?: () => void;
  boundary?: (event: SpeechSynthesisEvent) => void;
  end?: () => void;
  error?: (message: string) => void;
};

type Playback = { stop: () => void; done: () => void };
let current: Playback | undefined;

export function stopSpeech() {
  const stopping = current;
  current = undefined;
  if (!stopping) return;
  stopping.stop();
  stopping.done();
}

export function playSample(source: string, { end, error }: Pick<SpeechOptions, "end" | "error"> = {}) {
  stopSpeech();
  const player = new Audio(source);
  const playback = { stop: () => player.pause(), done: () => end?.() };
  function finish(failed: boolean) {
    if (current !== playback) return;
    current = undefined;
    end?.();
    if (failed) error?.("Không phát được tệp âm thanh mẫu. Vui lòng thử lại.");
  }
  player.onended = () => finish(false);
  player.onerror = () => finish(true);
  current = playback;
  void player.play().catch(() => finish(true));
  return () => {
    if (current === playback) stopSpeech();
  };
}

export function speak(text: string, options: SpeechOptions = {}) {
  if (!("speechSynthesis" in window)) {
    options.error?.("Trình duyệt chưa hỗ trợ đọc mẫu.");
    return;
  }
  stopSpeech();
  const utterance = new SpeechSynthesisUtterance(text);
  const language = options.language ?? "en-GB";
  const prefix = language.slice(0, 2).toLowerCase();
  const voices = speechSynthesis
    .getVoices()
    .filter((voice) => voice.lang.slice(0, 2).toLowerCase() === prefix);
  const voice =
    voices.find((item) => item.localService && item.lang === language) ??
    voices.find((item) => item.localService) ??
    voices.find((item) => item.lang === language) ??
    voices[0];
  if (voice) utterance.voice = voice;
  utterance.lang = voice?.lang ?? language;
  utterance.rate = options.rate ?? 0.86;
  utterance.pitch = options.pitch ?? 1;
  const playback = { stop: () => speechSynthesis.cancel(), done: () => options.end?.() };
  utterance.onstart = () => {
    if (current === playback) options.start?.();
  };
  utterance.onboundary = (event) => {
    if (current === playback) options.boundary?.(event);
  };
  utterance.onend = () => {
    if (current !== playback) return;
    current = undefined;
    options.end?.();
  };
  utterance.onerror = () => {
    if (current !== playback) return;
    current = undefined;
    options.end?.();
    options.error?.("Không phát được giọng đọc. Kiểm tra giọng đọc của trình duyệt.");
  };
  current = playback;
  speechSynthesis.speak(utterance);
  return () => {
    if (current === playback) stopSpeech();
  };
}
