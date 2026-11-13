import os

from fastapi import FastAPI, Request, Response, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from . import audio, auth, cards, dialogue, progress
from .db import DatabaseConfigurationError, get_engine

app = FastAPI(title="WordSpeak backend")
app.include_router(auth.router)
app.include_router(cards.router)
app.include_router(dialogue.router)
app.include_router(progress.router)
app.include_router(audio.router)

app.state.cors_origins = [
    origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=app.state.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatabaseConfigurationError)
@app.exception_handler(OperationalError)
async def database_unavailable(request: Request | WebSocket, exc: Exception):
    if isinstance(request, WebSocket):
        await request.close(code=1013, reason="Database unavailable")
        return None
    return JSONResponse({"detail": "Database unavailable"}, status_code=503)


@app.get("/health", responses={503: {"description": "Database unavailable"}})
def health(response: Response) -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (DatabaseConfigurationError, SQLAlchemyError):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ok"}
