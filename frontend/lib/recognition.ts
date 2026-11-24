type RecognitionResult = { isFinal: boolean; 0: { transcript: string } };
type Recognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<RecognitionResult> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => Recognition;
  webkitSpeechRecognition?: new () => Recognition;
};
export type RecognitionHandle = { finish: () => Promise<string>; cancel: () => void };

export function hasRecognition() {
  if (typeof window === "undefined") return false;
  const browser = window as SpeechWindow;
  return Boolean(browser.SpeechRecognition ?? browser.webkitSpeechRecognition);
}

export function startRecognition(): RecognitionHandle {
  const browser = window as SpeechWindow;
  const Constructor = browser.SpeechRecognition ?? browser.webkitSpeechRecognition;
  if (!Constructor) throw new Error("Trình duyệt chưa hỗ trợ nhận dạng tiếng nói.");
  const engine = new Constructor();
  engine.lang = "en-US";
  engine.continuous = true;
  engine.interimResults = true;
  let captured = "";
  let failed = false;
  let ended = false;
  let settle: (() => void) | undefined;
  engine.onresult = (event) => {
    captured = Array.from(event.results)
      .filter((item) => item.isFinal)
      .map((item) => item[0].transcript)
      .join(" ")
      .trim();
  };
  engine.onerror = () => {
    failed = true;
  };
  engine.onend = () => {
    ended = true;
    settle?.();
  };
  engine.start();
  return {
    async finish() {
      if (!ended) {
        await new Promise<void>((resolve) => {
          const timeout = window.setTimeout(() => {
            try {
              engine.abort();
            } catch {
              /* The browser may already have ended capture. */
            }
            resolve();
          }, 2400);
          settle = () => {
            clearTimeout(timeout);
            resolve();
          };
          try {
            engine.stop();
          } catch {
            settle();
          }
        });
      }
      if (!captured)
        throw new Error(
          failed
            ? "Trình duyệt không nhận dạng được câu nói. Kiểm tra hỗ trợ và quyền giọng nói rồi thử lại."
            : "Chưa nghe rõ câu bạn nói. Thử nói chậm và rõ hơn.",
        );
      return captured;
    },
    cancel() {
      if (!ended) {
        try {
          engine.abort();
        } catch {
          /* Already stopped. */
        }
      }
    },
  };
}
