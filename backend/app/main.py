import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="WordSpeak backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    """Stub: nhận chunk audio, trả số byte đã nhận. Thay bằng buffer + STT ở tuần 3/6."""
    await ws.accept()
    total = 0
    try:
        while True:
            chunk = await ws.receive_bytes()
            total += len(chunk)
            await ws.send_json({"type": "partial", "received_bytes": total})
    except WebSocketDisconnect:
        pass
