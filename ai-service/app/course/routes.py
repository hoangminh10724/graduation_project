"""Course delivery and authoritatively marked symbolic exercises."""
from datetime import date
from io import BytesIO
import os
import re
import sys
from typing import Literal
from urllib.parse import quote
from uuid import UUID
import wave
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import httpx
from pydantic import BaseModel, Field
from .catalog import AUDIO, BOOKS, LESSONS, LESSON_VERSIONS, ORDER, ROOT, SYMBOLS, VERSION, grade, public_lesson, study_state, summary

router=APIRouter(prefix="/demo/course",tags=["self-study course"])
HUMAN_AUDIO_DIR=ROOT/"audio_human"
_MISS_CACHE:set[tuple[str,str]]=set()
_MAX_MISS_CACHE=2000


def _record_miss(key:tuple[str,str]):
    if len(_MISS_CACHE)>=_MAX_MISS_CACHE:
        _MISS_CACHE.clear()
    _MISS_CACHE.add(key)


def _atomic_write(path, data:bytes):
    tmp=path.with_suffix(f".tmp.{os.getpid()}.wav")
    try:
        tmp.write_bytes(data)
        os.replace(tmp,path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def _ogg_to_wav_bytes(ogg_bytes:bytes)->bytes|None:
    """Transcode OGG/Opus to universal 16 kHz mono WAV so Chrome, Edge, Firefox & Safari all play it."""
    try:
        tools=ROOT.parents[2]/"data/speech-tools"
        if tools.is_dir() and str(tools) not in sys.path:
            sys.path.append(str(tools))
        import av
        import numpy as np
        with av.open(BytesIO(ogg_bytes)) as container:
            resampler=av.audio.resampler.AudioResampler(format="s16",layout="mono",rate=16000)
            pcm=[]
            for frame in container.decode(audio=0):
                for out in resampler.resample(frame):
                    pcm.append(out.to_ndarray().reshape(-1))
            if not pcm:
                return None
            samples=np.concatenate(pcm).astype("<i2")
        buf=BytesIO()
        with wave.open(buf,"wb") as wf:
            wf.setparams((1,2,16000,0,"NONE","not compressed"))
            wf.writeframes(samples.tobytes())
        return buf.getvalue()
    except Exception:
        return None


def _fetch_human_dictionary_audio(word:str, accent:str="en-US", sense:str=""):
    """Fetch & locally cache a real human Wiktionary/Wikimedia Commons recording (universal WAV)."""
    clean=re.sub(r"[^a-zA-Z'-]","",word.strip()).lower()
    if not clean or " " in word.strip() or os.environ.get("WORDSPEAK_OFFLINE_AUDIO")=="1":
        return None
    tag="uk" if accent=="en-GB" else "us"
    suffix=f"-{sense}" if sense in ("noun","verb") else ""
    HUMAN_AUDIO_DIR.mkdir(exist_ok=True)
    cached_wav=HUMAN_AUDIO_DIR/f"{clean}{suffix}-{tag}.wav"
    if cached_wav.is_file() and cached_wav.stat().st_size>500:
        return cached_wav,"audio/wav"
    cached_ogg=HUMAN_AUDIO_DIR/f"{clean}{suffix}-{tag}.ogg"
    if cached_ogg.is_file() and cached_ogg.stat().st_size>500:
        wav_bytes=_ogg_to_wav_bytes(cached_ogg.read_bytes())
        if wav_bytes:
            _atomic_write(cached_wav,wav_bytes)
            return cached_wav,"audio/wav"
        return None
    cache_key=(clean+suffix,tag)
    if cache_key in _MISS_CACHE:
        return None
    if suffix:
        # Strict homograph sense isolation: never fall back to the opposite stress pattern.
        candidates=[f"File:En-{tag}-{clean}{suffix}.ogg"]
    else:
        candidates=[f"File:En-{tag}-{clean}.ogg"]
        if tag=="us":
            candidates.append(f"File:En-us-ncalif-{clean}.ogg")
    try:
        with httpx.Client(timeout=10.0,follow_redirects=True,headers={"User-Agent":"WordSpeak/1.0 (https://github.com/wordspeak)"}) as client:
            r=client.get("https://commons.wikimedia.org/w/api.php",params={
                "action":"query","titles":"|".join(candidates),"prop":"imageinfo","iiprop":"url","format":"json"
            })
            if r.status_code!=200:
                _record_miss(cache_key); return None
            pages=r.json().get("query",{}).get("pages",{})
            by_title={p.get("title","").lower():p.get("imageinfo",[{}])[0].get("url") for p in pages.values() if isinstance(p,dict)}
            url=next((by_title.get(c.lower()) for c in candidates if by_title.get(c.lower())),None)
            if not url:
                _record_miss(cache_key); return None
            og=client.get(url)
            if og.status_code==200 and len(og.content)>500:
                wav_bytes=_ogg_to_wav_bytes(og.content)
                if wav_bytes:
                    _atomic_write(cached_wav,wav_bytes)
                    return cached_wav,"audio/wav"
    except Exception:
        return None
    _record_miss(cache_key)
    return None


class Submission(BaseModel):
    attempt_id:UUID
    version:str=Field(max_length=80)
    lesson:str=Field(max_length=80)
    exercise:str=Field(max_length=24)
    answer:str=Field(max_length=500)


class Event(BaseModel):
    version:str
    lesson_version:str|None=None
    lesson:str
    exercise:str
    day:date
    skill:Literal["Listening","IPA","Speaking","Meaning"]
    outcome:Literal["correct","retry","recorded","unavailable"]
    listener:Literal["listener_recovered","listener_repair"]|None=None


@router.get("")
def home():
    return FileResponse(ROOT.parent/"demo_static/course.html")


@router.get("/catalog")
def catalog():
    return {"version":VERSION,"books":BOOKS,"symbols":SYMBOLS,"lessons":[summary(k) for k in ORDER]}


@router.get("/lesson/{lesson}")
def lesson(lesson:str,phase:Literal["practice","review"]="practice"):
    if lesson not in LESSONS:raise HTTPException(404,"Unknown lesson")
    return public_lesson(lesson,phase)


@router.get("/audio/{key}")
def model_audio(key:str):
    if key not in AUDIO:raise HTTPException(404,"Unknown reference audio")
    line,accent,_speaker=AUDIO[key]
    human=_fetch_human_dictionary_audio(line,accent)
    if human:
        hpath,hmime=human
        return FileResponse(hpath,media_type=hmime,headers={"X-Audio-Source":"human-wiktionary"})
    path=ROOT/"audio"/(key+".mp3")
    if not path.is_file():raise HTTPException(503,"Reference audio unavailable")
    return FileResponse(path,media_type="audio/mpeg",headers={"X-Audio-Source":"bundled-model"})


@router.get("/human-word")
def human_word_audio(word:str,accent:Literal["en-US","en-GB"]="en-US",sense:str=""):
    human=_fetch_human_dictionary_audio(word,accent,sense)
    if human:
        hpath,hmime=human
        return FileResponse(hpath,media_type=hmime,headers={"X-Audio-Source":"human-wiktionary"})
    # Graceful fallback to bundled model if this word isn't hosted on Wikimedia Commons
    clean=word.strip().casefold()
    for key,(line,acc,_spk) in AUDIO.items():
        if acc==accent and line.strip().casefold()==clean:
            path=ROOT/"audio"/(key+".mp3")
            if path.is_file():
                return FileResponse(path,media_type="audio/mpeg",headers={"X-Audio-Source":"bundled-model"})
    raise HTTPException(404,"Audio recording unavailable for this word")


@router.post("/grade")
def mark(payload:Submission):
    if payload.version!=VERSION:raise HTTPException(409,"Content changed. Reopen this lesson.")
    try:
        result=grade(payload.lesson,payload.exercise,payload.answer)
    except KeyError as exc:raise HTTPException(404,"Unknown lesson or exercise") from exc
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    return {**result,"day":date.today().isoformat(),"lesson":payload.lesson,"exercise":payload.exercise,
            "version":VERSION,"lesson_version":LESSON_VERSIONS[payload.lesson],"attempt_id":str(payload.attempt_id)}


@router.post("/study")
def study(payload:list[Event]):
    return study_state([e.model_dump(mode="json") for e in payload])


@router.get("/word")
def word_lookup(word:str):
    query=word.strip().casefold()
    for phase in ("practice","review"):
        for lid in ORDER:
            for item in LESSONS[lid][phase]:
                if item["kind"]=="ipa" and item["question"].casefold()==f"write the broad ipa for “{query}”.":
                    return {"available":True,"lesson":lid,"exercise":item["id"],"phase":phase}
    return {"available":False}

