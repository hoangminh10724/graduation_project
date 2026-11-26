"""Pronunciation evidence for a spoken tutor turn, scoped to its source recording."""
from io import BytesIO
import re
import wave
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from .pronunciation_demo import get_demo_service
from .sound_catalog import PROMPTS
from .english_inventory import prompt
from .transcription import MAX_BYTES, RATE, decode, recognize

router = APIRouter()
catalog = {p["word"].lower(): p for key,p in PROMPTS.items() if key not in {"seat_long","food_long"}}
# Focal comparisons for common words in the teacher review. Other sounds in
# the word are not graded. The teacher's individual comments are never passed in.
for word, phone, position in [
    ("both","θ","final"), ("up","p","final"), ("make","k","final"),
    ("sale","eɪ","initial"), ("kit","ɪ","initial"), ("coat","oʊ","initial"),
    ("teeth","i","initial"), ("eat","i","initial"), ("cube","b","final"),
    ("fifteen","i","medial"), ("fifty","ɪ","initial"), ("really","i","initial"),
    ("can","æ","medial"), ("about","aʊ","medial"), ("record","ɛ","medial"),
]:
    catalog[word] = prompt(word,phone,position=position,primary=False)


def phrasing_observation(samples, words):
    """Find a quiet interval between stretches of recorded speech for replay."""
    import numpy as np

    if len(words) < 2:
        return None
    frame = RATE // 50
    first = max(0, round(words[0]["start"] * RATE))
    last = min(len(samples), round(words[-1]["end"] * RATE))
    count = (last-first) // frame
    if count < 25:
        return None
    frames = samples[first:first+count*frame].reshape(-1,frame)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    foreground = float(np.percentile(rms,90))
    if foreground < .01:
        return None
    quiet = rms < min(.008, foreground*.10)
    edges = np.diff(np.r_[0,quiet,0].astype(int))
    intervals = []
    for left,right in zip(np.flatnonzero(edges==1), np.flatnonzero(edges==-1)):
        if right-left < 15 or left < 5 or right+5 > count:
            continue
        if min(rms[max(0,left-15):left].max(),rms[right:right+15].max()) < foreground*.3:
            continue
        intervals.append((right-left,left,right))
    if not intervals:
        return None
    length,left,right=max(intervals,key=lambda interval:interval[0])
    start=(first+left*frame)/RATE
    end=(first+right*frame)/RATE
    return {"start":start,"end":end,"message":
            f"Listen around {start:.1f} s. The recording gets quiet for about {length/50:.1f} s. "
            "Does the break fit where you meant one idea to end?"}


_NUM_WORDS={
    "0":"zero","1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine","10":"ten",
    "11":"eleven","12":"twelve","13":"thirteen","14":"fourteen","15":"fifteen","16":"sixteen","17":"seventeen","18":"eighteen","19":"nineteen",
    "20":"twenty","30":"thirty","40":"forty","50":"fifty","60":"sixty","70":"seventy","80":"eighty","90":"ninety",
}


def lexical_words(text):
    raw = re.findall(r"[^\W_]+(?:'[^\W_]+)*", text.lower().replace("’", "'"))
    return [_NUM_WORDS.get(w, w) for w in raw]


def locate_focus(words, focus):
    """Return the timed tokens for a complete occurrence, including joined compounds."""
    if not focus.strip():
        return words
    wanted = lexical_words(focus)
    if not wanted:
        return []
    tokens = [(word, lexical_words(word["word"])) for word in words]
    pieces = [(part, i) for i, (_, parts) in enumerate(tokens) for part in parts]
    for start in range(len(pieces)-len(wanted)+1):
        span = pieces[start:start+len(wanted)]
        if [part for part, _ in span] != wanted:
            continue
        first, last = span[0][1], span[-1][1]
        if start and pieces[start-1][1] == first:
            continue
        following = start+len(wanted)
        if following < len(pieces) and pieces[following][1] == last:
            continue
        match = words[first:last+1]
        if all(0 <= token["start"] < token["end"] for token in match):
            return match
    return []


def observe(payload, focus):
    result = recognize(payload)
    words = result["words"]
    samples = decode(payload)
    scope = locate_focus(words, focus)
    chosen = None
    for token in scope:
        parts = lexical_words(token["word"])
        if len(parts) == 1 and parts[0] in catalog and 0 < token["end"]-token["start"] <= 3.9:
            chosen = parts[0], token
            break
    evidence = {"kind":"unresolved", "message":"No supported word could be checked in this recording. Choose a practice word and record it again."}
    if focus.strip() and not scope:
        evidence["message"]="The recognizer could not locate the complete practice expression in this recording. Listen back or try it again."
    elif focus.strip() and not chosen:
        evidence["message"]="The recognizer located your expression. Replay it and listen for the word you emphasized. Sound checking is unavailable for this expression."
    if chosen:
        word, token = chosen
        length = min(len(samples), max(RATE//4, round((token["end"]-token["start"]+.08)*RATE)))
        start = max(0,min(len(samples)-length,round((token["start"]+token["end"])*RATE/2-length/2)))
        if length >= RATE//4:
            buf = BytesIO()
            with wave.open(buf,"wb") as out:
                out.setparams((1,2,RATE,0,"NONE","not compressed"))
                out.writeframes((samples[start:start+length].clip(-1,1)*32767).astype("<i2").tobytes())
            try:
                sound = get_demo_service().analyze_prompt(buf.getvalue(),catalog[word],"word")
            except HTTPException as exc:
                if exc.status_code != 503:raise
                evidence["message"]="Sound analysis is unavailable for this recording."
            else:
                status=sound["status"]
                target=sound["target_phone"]
                candidate=sound["predicted_phone"]
                message=f'Listen to “{word}” in your recording. '
                if status=="possible_difference" and candidate:
                    message+=f'The model suggests a possible /{candidate}/ near the /{target}/ target. '+sound["diagnosis"]["adjustment"]
                elif status=="model_match":
                    message+=f'The model found a target-like sound for /{target}/.'
                else:
                    message=f'“{word}” was clearly recognized in your sentence. The isolated /{target}/ phoneme check was inconclusive in connected speech — replay it or test “{word}” on its own in IPA & Mouth for a closer check.'
                evidence=dict(kind=status,word=word,target=target,candidate=candidate,
                              start=start/RATE,end=(start+length)/RATE,message=message)
    if scope and focus.strip() and (not chosen or len(lexical_words(focus)) > 1):
        evidence["expression"]={"start":scope[0]["start"], "end":scope[-1]["end"]}
    phrasing = phrasing_observation(samples, words)
    if phrasing:
        evidence["phrasing"]=phrasing
    return {"text":result["text"],"observation":evidence}


@router.post("/tutor/observe")
async def tutor_observe(audio: UploadFile=File(...),focus:str=Form("",max_length=120)):
    try:
        payload=await audio.read(MAX_BYTES+1)
    finally:
        await audio.close()
    if len(payload)>MAX_BYTES:raise HTTPException(413,"Maximum upload size is 8 MiB.")
    return await run_in_threadpool(observe,payload,focus)
