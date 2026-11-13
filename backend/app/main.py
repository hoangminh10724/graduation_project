import os

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import auth, cards
from .db import DatabaseConfigurationError, get_engine

app = FastAPI(title="WordSpeak backend")
app.include_router(auth.router)
app.include_router(cards.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", responses={503: {"description": "Database unavailable"}})
def health(response: Response) -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (DatabaseConfigurationError, SQLAlchemyError):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
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
