from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from .pronunciation_demo import ASSETS, router as demo_router

from .transcription import router as transcription_router
from .course.routes import router as course_router

app = FastAPI(title="WordSpeak AI service", version="0.4.0")
app.include_router(demo_router)
from .tutor_observation import router as observation_router
app.include_router(transcription_router)
app.include_router(observation_router)
app.include_router(course_router)
app.mount("/demo/assets", StaticFiles(directory=ASSETS), name="demo-assets")


@app.middleware("http")
async def fresh_demo_assets(request, call_next):
    response = await call_next(request)
    if request.url.path == "/demo" or request.url.path.startswith("/demo/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/assess", deprecated=True)
async def assess(audio: UploadFile = File(...), text: str = Form(...)):
    """Validated numeric pronunciation scoring is not implemented."""
    await audio.close()
    raise HTTPException(501, "Validated pronunciation scoring is not implemented. Use /demo/analyze for an experimental sound comparison.")
