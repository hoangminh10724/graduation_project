export type Level = "A2" | "B1" | "B2";
export type TalkSession = { id: number; topic: string; cefr_level: Level };
export type Turn = { id: number; text: string; reply: string };
export type Progress = {
  attempts: number;
  streak_days: number;
  phoneme_averages?: Record<string, number>;
  daily: { date: string; attempts: number }[];
};
export type Phone = { ipa: string; score: number; start: number; end: number };
export type Assessment = {
  sentence_score: number;
  words: { word: string; score: number; phonemes: Phone[] }[];
  hints?: string[];
  errors?: { ipa?: string; type?: string; actual?: string }[];
};
export type AudioEvent =
  | { type: "partial"; received_bytes: number }
  | { type: "transcript" | "token" | "done"; text: string }
  | { type: "final"; text: string; assessment: Assessment }
  | { type: "coaching"; hints: string[]; errors: NonNullable<Assessment["errors"]> }
  | { type: "error"; code: string };

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class AudioConnectionError extends Error {
  constructor(
    public readonly delivery: "unsent" | "unknown",
    message: string,
  ) {
    super(message);
    this.name = "AudioConnectionError";
  }
}

export function apiBase() {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  return typeof window !== "undefined" && location.port === "8080" ? "/api" : "http://localhost:8000";
}

export async function api<T>(
  path: string,
  options: { token?: string; data?: object; signal?: AbortSignal } = {},
) {
  const { token, data, signal } = options;
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, {
      method: data ? "POST" : "GET",
      headers: {
        ...(data && { "Content-Type": "application/json" }),
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: data ? JSON.stringify(data) : undefined,
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, "Chưa kết nối được máy chủ. Kiểm tra dịch vụ và thử lại.");
  }
  if (!response.ok) {
    const messages: Record<number, string> = {
      401: "Phiên đăng nhập đã hết hạn hoặc thông tin chưa đúng.",
      409: "Dữ liệu đang xung đột. Vui lòng thử lại.",
      422: "Thông tin gửi đi chưa hợp lệ.",
      503: "Dịch vụ tạm thời chưa sẵn sàng.",
    };
    throw new ApiError(response.status, messages[response.status] ?? "Không xử lý được yêu cầu.");
  }
  return (await response.json()) as T;
}

function audioUrl() {
  const url = new URL(`${apiBase()}/ws/audio`, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url;
}

const audioErrors: Record<string, string> = {
  speech_unavailable: "Dịch vụ nhận dạng tiếng nói chưa khả dụng. Bạn có thể nghe lại bản thu.",
  assessment_unavailable: "Dịch vụ chấm ngữ âm chưa khả dụng.",
  llm_unavailable: "Gia sư AI chưa phản hồi được. Bạn có thể thử lại sau.",
  unauthorized: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  audio_too_large: "Bản thu vượt giới hạn. Hãy nói một câu ngắn hơn.",
  empty_audio: "Bản thu trống. Hãy ghi lại.",
  session_busy: "Phiên luyện đang xử lý một lượt khác. Hãy thử lại sau.",
  database_unavailable: "Máy chủ chưa lưu được kết quả.",
};

export type AudioRequest = {
  blob: Blob;
  token: string;
  text?: string;
  sessionId?: number;
  signal: AbortSignal;
  onDispatch?: () => void;
  onEvent: (event: AudioEvent) => void;
};

async function websocketAttempt(request: AudioRequest, bytes: ArrayBuffer, requestId: string) {
  return new Promise<void>((resolve, reject) => {
    const socket = new WebSocket(audioUrl());
    const { blob, token, text, sessionId, signal, onEvent } = request;
    let settled = false;
    let dispatched = false;
    let receivedFinal = false;
    function connectionLost(message: string) {
      if (receivedFinal) {
        finish();
        return;
      }
      finish(
        new AudioConnectionError(
          dispatched ? "unknown" : "unsent",
          dispatched ? "Kết nối bị gián đoạn sau khi gửi. Máy chủ có thể đã lưu lượt này." : message,
        ),
      );
    }
    function finish(error?: Error) {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      signal.removeEventListener("abort", cancel);
      if (socket.readyState < WebSocket.CLOSING) socket.close();
      if (error) reject(error);
      else resolve();
    }
    function cancel() {
      finish(new DOMException("Đã hủy", "AbortError"));
    }
    let timeout = window.setTimeout(() => connectionLost("Chưa kết nối được dịch vụ giọng nói."), 7000);
    if (signal.aborted) {
      cancel();
      return;
    }
    signal.addEventListener("abort", cancel, { once: true });
    socket.onopen = () => socket.send(JSON.stringify({ type: "auth", token }));
    const upload = () => {
      if (settled) return;
      clearTimeout(timeout);
      try {
        for (let offset = 0; offset < bytes.byteLength; offset += 65536)
          socket.send(bytes.slice(offset, offset + 65536));
        if (socket.readyState !== WebSocket.OPEN) {
          connectionLost("Chưa gửi được bản thu.");
          return;
        }
        socket.send(
          JSON.stringify({
            type: "end",
            request_id: requestId,
            media_type: blob.type,
            text,
            session_id: sessionId,
          }),
        );
        dispatched = true;
        request.onDispatch?.();
        timeout = window.setTimeout(() => connectionLost("Máy chủ phản hồi quá lâu."), 145000);
      } catch {
        connectionLost("Chưa gửi được bản thu.");
      }
    };
    socket.onerror = socket.onclose = () => connectionLost("Chưa kết nối được dịch vụ giọng nói.");
    socket.onmessage = (message) => {
      if (settled) return;
      try {
        const event = JSON.parse(message.data) as AudioEvent | { type: "authenticated" };
        if (event.type === "authenticated") {
          if (!dispatched) upload();
          return;
        }
        onEvent(event);
        if (event.type === "final") {
          receivedFinal = true;
          if (event.assessment.hints?.length || event.assessment.errors?.length) return;
          finish();
        }
        if (event.type === "coaching") finish();
        if (event.type === "error" && event.code !== "llm_unavailable") {
          const status = event.code === "unauthorized" ? 401 : 503;
          finish(new ApiError(status, audioErrors[event.code] ?? "Máy chủ chưa xử lý được lượt nói."));
        }
      } catch {
        connectionLost("Dữ liệu phản hồi giọng nói chưa hợp lệ.");
      }
    };
  });
}

export async function sendAudio(request: AudioRequest) {
  if (!request.blob.size || request.blob.size > 8 * 1024 * 1024)
    throw new ApiError(422, "Bản thu cần có dữ liệu và nhỏ hơn 8 MiB.");
  if (request.blob.type !== "audio/webm" && request.blob.type !== "audio/wav")
    throw new ApiError(422, "Định dạng bản thu chưa được hỗ trợ.");
  const requestId = crypto.randomUUID();
  const bytes = await request.blob.arrayBuffer();
  if (request.signal.aborted) throw new DOMException("Đã hủy", "AbortError");
  try {
    await websocketAttempt(request, bytes, requestId);
  } catch (error) {
    if (
      request.signal.aborted ||
      !(error instanceof AudioConnectionError) ||
      error.delivery !== "unsent"
    )
      throw error;
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    if (request.signal.aborted) throw new DOMException("Đã hủy", "AbortError");
    await websocketAttempt(request, bytes, requestId);
  }
}
