from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from .pronunciation_demo import ASSETS, router as demo_router

from .transcription import router as transcription_router
from .word_assessment import WORDS, assess_word
from .transcription import MAX_BYTES
from starlette.concurrency import run_in_threadpool
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


@app.post("/assess")
async def assess(audio: UploadFile = File(...), text: str = Form(...)):
    word = text.strip().lower().strip(".!?")
    try:
        if word not in WORDS:
            raise HTTPException(422, "Choose a supported isolated practice word.")
        payload = await audio.read(MAX_BYTES + 1)
    finally:
        await audio.close()
    if len(payload) > MAX_BYTES:
        raise HTTPException(413, "Recording exceeds 8 MiB.")
    return await run_in_threadpool(assess_word, payload, word)
