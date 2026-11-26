"""Build local listening bookmarks from indexed teacher comments and original audio."""
import argparse
import wave
import numpy as np
import hashlib
from html import escape
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"ai-service"))
sys.path.append(str(ROOT/"data/speech-tools"))
from app.transcription import model
from app.tutor_observation import catalog
from prepare_teacher_feedback import normalized_word


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notes",type=Path)
    args=parser.parse_args()
    output=args.notes.resolve().parent
    records=list(map(json.loads,args.notes.read_text(encoding="utf-8").splitlines()))
    manifest={r["id"]:r for r in map(json.loads,(ROOT/"data/prepared/new_collection_20261121/manifest.jsonl").read_bytes().splitlines())}
    review=[]
    for record in records:
        audio=ROOT/record["source"]
        digest=hashlib.sha256(audio.read_bytes()).hexdigest()
        if digest!=record["source_sha256"]:
            raise ValueError(f"Source recording changed: {record['id']}")
        row=manifest[record["id"]]
        wav=ROOT/row["audio_path"] if row.get("audio_path") else ROOT/"data/processed/vietnamese/audio"/(row["duplicate_of"]+".wav")
        with wave.open(str(wav),"rb") as source:
            if (source.getframerate(),source.getnchannels(),source.getsampwidth())!=(16000,1,2):
                raise ValueError(f"Expected 16 kHz mono PCM16: {wav}")
            samples=np.frombuffer(source.readframes(source.getnframes()),dtype="<i2").astype(np.float32)/32768
        segments,_=model().transcribe(samples,language="en",beam_size=5,vad_filter=True,
                                      word_timestamps=True,condition_on_previous_text=False)
        words=[{"word":w.word.strip(),"start":w.start,"end":w.end}
               for s in segments for w in (s.words or [])]
        items=[]
        for item in record["items"]:
            candidates={target:[w for w in words if normalized_word(w["word"])==normalized_word(target)]
                        for target in item["review_words"]}
            items.append({**item,"asr_candidates":candidates})
        review.append({**record,"playback_audio":wav.relative_to(ROOT).as_posix(),"items":items,"transcript_words":words})
        print(record["id"],flush=True)
    (output/"candidate_passages.json").write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding="utf-8")
    render_review(review,output)


def render_review(review,output):
    page=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Teacher feedback listening review</title>',
          '<style>body{max-width:56rem;margin:auto;padding:1rem;font:1rem/1.5 system-ui}section{margin:1rem 0}button,audio{margin:.25rem;max-width:100%}summary{cursor:pointer}</style>',
          '<h1>Review teacher feedback against the recording</h1><p>Open a recording and select a candidate to hear it in context. Times are automatic estimates. Use the full recording when a word is missing or repeated.</p>']
    for record in review:
        url=escape(os.path.relpath(ROOT/record["playback_audio"],output).replace(os.sep,"/"),quote=True)
        playback_digest=hashlib.sha256((ROOT/record["playback_audio"]).read_bytes()).hexdigest()
        page.append(f'<details data-recording="{escape(record["id"])}" data-hash="{record["source_sha256"]}" data-playback="{playback_digest}"><summary>{escape(record["id"])}</summary><audio controls preload="none" src="{url}"></audio>')
        if record.get("duplicate_audio_of"):
            page.append('<p>Audio also catalogued as '+escape(record["duplicate_audio_of"])+'.</p>')
        if record.get("duplicate_comment_review"):
            page.append('<p>Confirm attribution. P19_02 and P19_04 have identical comments.</p>')
        for index,item in enumerate(record["items"]):
            page.append(f'<section data-item="{index}"><p lang="vi">'+escape(item["text"])+'</p>')
            for target,hits in item["asr_candidates"].items():
                phone=catalog.get(target.lower(),{}).get("target_phone","")
                attrs=f'data-word="{escape(target,quote=True)}" data-phone="{escape(phone,quote=True)}"'
                if not hits:
                    page.append('<span>'+escape(target)+': no exact transcript match.</span> ')
                    page.append(f'<button {attrs}>Mark {escape(target)} manually</button>')
                for hit in hits:
                    page.append(f'<button {attrs} data-end="{hit["end"]}" data-start="{hit["start"]}">{escape(target)} · {hit["start"]:.2f} s</button>')
            page.append('</section>')
        page.append('</details>')
    page.append(Path(__file__).with_name("teacher_passage_editor.html").read_text(encoding="utf-8"))
    (output/"review.html").write_text('\n'.join(page),encoding="utf-8")


if __name__=="__main__":
    main()
