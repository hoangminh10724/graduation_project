"""Decode new local recordings; retain duplicates and uncertain quality in an audit.

Originals and previous prepared datasets are never modified. No transcript,
pronunciation label or training split is invented from a filename or model output.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'data/prepared/new_collection_20261121')
    args=parser.parse_args();out=args.output
    baseline=ROOT/'data/processed/vietnamese/manifest_all.jsonl'
    previous=[json.loads(line) for line in baseline.read_text(encoding='utf-8').splitlines() if line.strip()]
    old={r['clip_id']:r['source_sha256'] for r in previous}
    source=ROOT/'data/collecting/vietnamese'
    all_files=sorted((p for p in source.rglob('*') if p.suffix.lower() in {'.ogg','.wav','.mp3','.m4a','.flac','.webm'}),key=lambda p:p.stem)
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in all_files}
    candidates=[p for p in all_files if old.get(p.stem.upper())!=hashes[p]]
    if out.exists() and (out/'manifest.jsonl').exists():
        cached=[json.loads(line) for line in (out/'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
        if {r['id']:r['source_sha256'] for r in cached}!={p.stem.upper():hashes[p] for p in candidates}:
            raise RuntimeError('Source batch changed; choose a new output directory rather than overwrite an earlier audit')
    (out/'audio').mkdir(parents=True,exist_ok=True)
    ffmpeg=next((ROOT/'data/audio-tools/imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
    source_seen={r['source_sha256']:r['clip_id'] for r in previous}
    decoded_seen={};rows=[]
    for index,path in enumerate(candidates,1):
        clip_id=path.stem.upper();speaker=re.match(r'P\d+',clip_id).group()
        row={'id':clip_id,'speaker_id':speaker,'source':path.relative_to(ROOT).as_posix(),
             'source_sha256':hashes[path],'pronunciation_labels':None,'transcript':None,
             'human_verified':False,'split':'unassigned','flags':[]}
        if hashes[path] in source_seen:
            row.update(status='duplicate',duplicate_of=source_seen[hashes[path]])
        else:
            source_seen[hashes[path]]=clip_id
            decoded=subprocess.run([str(ffmpeg),'-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],capture_output=True)
            if decoded.returncode or len(decoded.stdout)<3200:
                row.update(status='decode_failed',decoder_error=decoded.stderr.decode(errors='replace')[:800])
            else:
                pcm=decoded.stdout;digest=hashlib.sha256(pcm).hexdigest();values=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
                row.update(decoded_sha256=digest,duration_seconds=round(len(values)/16000,4),
                           rms=float(np.sqrt(np.mean(values**2))),peak=float(np.max(np.abs(values))),
                           clipping_fraction=float(np.mean(np.abs(values)>=.99)))
                if digest in decoded_seen:row.update(status='duplicate',duplicate_of=decoded_seen[digest])
                else:
                    decoded_seen[digest]=clip_id;target=out/'audio'/f'{clip_id}.wav'
                    with wave.open(str(target),'wb') as stream:
                        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(pcm)
                    row.update(status='prepared',audio_path=target.relative_to(ROOT).as_posix())
                    if row['rms']<.003:row['flags'].append('quiet')
                    if row['clipping_fraction']>.01:row['flags'].append('clipping')
        rows.append(row)
        (out/'manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
        if index%10==0:print(json.dumps({'decoded':index,'total':len(candidates)}),flush=True)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p] for p in all_files)
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'source_files':len(all_files),'baseline_files':len(previous),
             'new_files':len(rows),'participant_ids':sorted({r['speaker_id'] for r in rows}),
             'statuses':dict(Counter(r['status'] for r in rows)),
             'prepared_minutes':round(sum(r['duration_seconds'] for r in rows if r['status']=='prepared')/60,2),
             'human_verified_pronunciation_labels':0,'training_performed':False,'originals_unchanged':True,
             'baseline_manifest_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
