from fastapi import FastAPI, File, Form, UploadFile

from .gop import normalize_gop

app = FastAPI(title="WordSpeak AI service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/assess")
async def assess(audio: UploadFile = File(...), text: str = Form(...)):
    """Stub theo docs/openapi.yaml. Thay bằng wav2vec2 + alignment + GOP thật."""
    await audio.read()
    words = [
        {"word": w, "score": normalize_gop(-0.5), "phonemes": []}
        for w in text.split()
    ]
    avg = sum(w["score"] for w in words) / len(words) if words else 0.0
    return {"sentence_score": round(avg, 1), "words": words}
