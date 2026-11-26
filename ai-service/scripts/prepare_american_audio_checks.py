"""Make deterministic word crops from seven new speakers using local ASR.

These transcripts/timestamps are automatic. Crops are integration inputs, not
human phonetic ground truth, and are never assigned to a training/evaluation split.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys
import wave

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-service'))
from app.local_runtime import install_local_network_guard
install_local_network_guard()
sys.path.insert(0,str(ROOT/'data/speech-tools'))
import numpy as np
from faster_whisper import WhisperModel
from app.sound_catalog import PROMPTS

OUT=ROOT/'data/results/american_expansion'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'new_word_audio').mkdir(exist_ok=True)

def main():
    records=[json.loads(line) for line in (ROOT/'data/prepared/new_collection_20261121/manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    chosen={}
    for row in records:
        if row['status']=='prepared':chosen.setdefault(row['speaker_id'],row)
    model=WhisperModel(str(ROOT/'data/models/vietnamese-preparation/whisper-small'),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
    cases=[];transcripts=[];seen_words=set()
    lookup={p['word'].lower():key for key,p in PROMPTS.items() if p['primary']}
    for speaker,row in sorted(chosen.items()):
        audio_path=ROOT/row['audio_path'];digest=hashlib.sha256(audio_path.read_bytes()).hexdigest()
        with wave.open(str(audio_path),'rb') as stream:
            rate=stream.getframerate();pcm=stream.readframes(stream.getnframes());frames=len(pcm)//2
        assert rate==16000
        cache=OUT/f'{speaker}_automatic_transcript.json'
        if cache.exists():
            transcript=json.loads(cache.read_text(encoding='utf-8'));assert transcript['audio_sha256']==digest
        else:
            samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
            segments,info=model.transcribe(samples,language='en',beam_size=3,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
            transcript={'speaker_id':speaker,'id':row['id'],'audio_path':row['audio_path'],'audio_sha256':digest,
                        'segments':[asdict(s) for s in segments],'human_verified':False,'purpose':'automatic crop placement only'}
            cache.write_text(json.dumps(transcript,ensure_ascii=False,indent=2),encoding='utf-8')
        transcripts.append(transcript)
        for segment in transcript['segments']:
            for word in segment.get('words') or []:
                token=re.sub(r'[^a-z]','',word['word'].lower())
                key=lookup.get(token)
                if not key or (speaker,key) in seen_words:continue
                seen_words.add((speaker,key))
                left=max(0,int((word['start']-.14)*rate));right=min(frames,int((word['end']+.18)*rate))
                if not .25<=(right-left)/rate<=4:continue
                filename=OUT/'new_word_audio'/f'{speaker}_{key}.wav'
                with wave.open(str(filename),'wb') as stream:
                    stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(pcm[left*2:right*2])
                cases.append({'id':f'{speaker}_{key}','prompt_id':key,'speaker_id':speaker,'audio_path':filename.relative_to(ROOT).as_posix(),
                              'source_id':row['id'],'source_sha256':row['source_sha256'],'parent_audio_sha256':digest,
                              'start_seconds':left/rate,'end_seconds':right/rate,'boundary_source':'automatic_Whisper_word_times_with_padding',
                              'classification_correct':None,'human_verified':False,'selection':'first_occurrence_per_prompt_per_selected_speaker; no score filtering'})
        (OUT/'new_word_cases.jsonl').write_text(''.join(json.dumps(case,ensure_ascii=False)+'\n' for case in cases),encoding='utf-8')
        print(json.dumps({'speaker':speaker,'selected_recording':row['id'],'cumulative_word_cases':len(cases)}),flush=True)
    (OUT/'new_word_summary.json').write_text(json.dumps({'speakers':len(chosen),'word_cases':len(cases),
         'prompt_ids':sorted({c['prompt_id'] for c in cases}),'human_verified':False,'training_performed':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()
