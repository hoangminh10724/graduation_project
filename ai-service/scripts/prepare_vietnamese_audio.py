"""Prepare learner audio without filtering out difficult pronunciation.

Run primary and check stages in separate processes; check can watch primary.
All ASR/event/overlap outputs remain automatic, not pronunciation labels.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from difflib import SequenceMatcher
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

from finalize_native_audio import (np, so, WhisperModel, decode_audio, wav_write,
                                   json_scalar, event_scores)
from faster_whisper.vad import get_speech_timestamps, VadOptions
import onnxruntime as ort

SOURCE=Path('data/collecting/vietnamese')
OUT=Path('data/processed/vietnamese')
MODELS=Path('data/models/native-preparation')
EXTENSIONS={'.ogg','.mp3','.m4a','.wav','.flac','.mp4','.webm'}


def save_json(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=json_scalar),encoding='utf-8')
    temporary.replace(path)


def natural(text):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',str(text))]


def inputs():
    return sorted((p for p in SOURCE.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSIONS),key=lambda p:natural(p.relative_to(SOURCE)))


def normalize(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",text.lower().replace('\u2019',"'"))


def recover_decode(path):
    try:
        return decode_audio(str(path)), 'pyav', None
    except Exception as original:
        executable=next(Path('data/audio-tools/imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
        result=subprocess.run([str(executable),'-v','warning','-i',str(path),'-vn',
            '-ac','1','-ar','16000','-f','f32le','pipe:1'],capture_output=True)
        audio=np.frombuffer(result.stdout,dtype='<f4').copy()
        if result.returncode or len(audio)<1600 or not np.isfinite(audio).all():
            raise RuntimeError(str(original)+'; fallback: '+result.stderr.decode(errors='replace')[:1500])
        return audio,'ffmpeg_recovery',result.stderr.decode(errors='replace')[:4000]


def transcript(model,audio,language):
    segs,_=model.transcribe(audio,language=language,beam_size=5,word_timestamps=True,
        condition_on_previous_text=False,vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400))
    segs=list(segs)
    probs=[w.probability for s in segs for w in (s.words or [])]
    return dict(text=''.join(s.text for s in segs).strip(),segments=[asdict(s) for s in segs],
        mean_probability=float(np.mean(probs)) if probs else 0,
        min_probability=float(min(probs,default=0)))


def primary():
    model=WhisperModel('data/models/vietnamese-preparation/whisper-small',
        device='cpu',compute_type='int8',cpu_threads=6,local_files_only=True)
    files=inputs();seen={};pcm_seen={};ids=set()
    for i,path in enumerate(files,1):
        rel=path.relative_to(SOURCE).as_posix();clip_id=path.stem.upper()
        assert clip_id not in ids, 'Colliding clip IDs: '+clip_id
        ids.add(clip_id)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        cache=OUT/'primary_cache'/f'{clip_id}.json'
        keeper=seen.get(digest);seen.setdefault(digest,clip_id)
        if cache.exists():
            record=json.loads(cache.read_text(encoding='utf-8'));assert record['source_sha256']==digest
            if record.get('decoded_sha256'):pcm_seen.setdefault(record['decoded_sha256'],clip_id)
            continue
        record=dict(clip_id=clip_id,source=rel,source_sha256=digest,
            participant_id=path.parent.name.upper(),participant_id_status='user_supplied_folder_label',
            identity_verified=False,group='Vietnamese learner (user supplied)',
            permission_status='unverified',pronunciation_label=None,human_verified=False,
            flags=[],excluded_reasons=[],audio=None,transcript=None)
        if keeper:
            record.update(duplicate_of=keeper,status='excluded',excluded_reasons=['exact_duplicate'])
        else:
            try:
                audio,decoder,messages=recover_decode(path)
                assert len(audio)>0 and np.isfinite(audio).all()
                duration=len(audio)/16000
                pcm_hash=hashlib.sha256((np.clip(audio,-1,1)*32767).astype('<i2').tobytes()).hexdigest()
                record.update(original_duration_seconds=duration,decoder=decoder,
                    decoder_messages=messages,decoded_sha256=pcm_hash)
                if pcm_hash in pcm_seen:
                    record.update(duplicate_of=pcm_seen[pcm_hash],status='excluded',excluded_reasons=['decoded_audio_duplicate'])
                else:
                    pcm_seen[pcm_hash]=clip_id
                    if decoder=='ffmpeg_recovery':record['flags'].append('decoder_recovery_used')
                    speech=get_speech_timestamps(audio,VadOptions(min_silence_duration_ms=400,speech_pad_ms=200))
                    first=speech[0]['start'] if speech else 0
                    last=speech[-1]['end'] if speech else len(audio)
                    cut=audio[first:last]
                    peak=float(np.max(np.abs(cut)))
                    rms=float(20*np.log10(max(float(np.sqrt(np.mean(cut**2))),1e-10)))
                    clipping=float(np.mean(np.abs(cut)>=.999))
                    if not speech:record['flags'].append('no_speech_detected')
                    if clipping>.005:record['flags'].append('clipping')
                    if rms< -38:record['flags'].append('very_quiet')
                    record.update(start_seconds=first/16000,end_seconds=last/16000,
                        duration_seconds=len(cut)/16000,original_peak=peak,rms_dbfs=rms,
                        clipping_fraction=clipping,vad_speech_seconds=sum(x['end']-x['start'] for x in speech)/16000)
                    language,prob,all_probs=model.detect_language(cut)
                    record.update(detected_language=language,language_probability=prob,
                        language_top3=all_probs[:3])
                    # Non-English detection is a flag, not a learner-quality judgment.
                    chosen=language if language!='en' and prob>=.9 else 'en'
                    if language!='en':record['flags'].append('language_detection_needs_review')
                    result=transcript(model,cut,chosen)
                    record.update(transcript=result['text'],primary_asr=result,
                        transcription_language=chosen,transcript_status='automatic_unverified',
                        primary_model='Whisper small multilingual')
                    if result['mean_probability']<.8 or not result['text']:
                        record['flags'].append('transcript_uncertain')
                    record['audio']='audio/'+clip_id+'.wav'
                    record['gain_db']=wav_write(OUT/record['audio'],cut)
                    record['status']='prepared'
            except Exception as e:
                record.update(status='excluded',excluded_reasons=['processing_error'],error=str(e))
        save_json(cache,record)
        if i%5==0 or record['status']=='excluded':
            print('PRIMARY',i,'/',len(files),clip_id,record['status'],record['flags'],flush=True)
        if i%15==0:export()
    save_json(OUT/'primary_complete.json',dict(expected=len(files),complete=True))
    export();print('PRIMARY COMPLETE',len(files),flush=True)


def overlap_stats(session,audio):
    # Model's seven classes: silence; 3 single speakers; 3 speaker pairs.
    # https://huggingface.co/pyannote/segmentation-3.0
    windows=[];lengths=[]
    for start in range(0,len(audio),160000):
        a=audio[start:start+160000];lengths.append(len(a))
        windows.append(np.pad(a,(0,160000-len(a))))
    scores=session.run(None,{session.get_inputs()[0].name:np.stack(windows)[:,None,:]})[0]
    overlapping=0;multi=False
    for y,length in zip(scores,lengths):
        centers=(np.arange(len(y))*270+495.5)
        y=y[centers<length]
        classes=y.argmax(-1)
        overlapping+=float(np.sum((classes>=4)&(np.exp(y[:,4:]).sum(-1)>=.6)))*270/16000
        activity=[np.sum(np.isin(classes,ids))*270/16000 for ids in [(1,4,5),(2,4,6),(3,5,6)]]
        multi=multi or sum(x>=.75 for x in activity)>1
    return dict(estimated_overlap_seconds=round(overlapping,3),possible_multiple_speakers=bool(multi))


def check():
    model=WhisperModel(str(MODELS/'whisper'),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
    tagger=so.AudioTagging(so.AudioTaggingConfig(model=so.AudioTaggingModelConfig(
        ced=str(MODELS/'tagger/model.int8.onnx'),num_threads=2),
        labels=str(MODELS/'tagger/class_labels_indices.csv'),top_k=30))
    options=ort.SessionOptions();options.intra_op_num_threads=2
    overlap=ort.InferenceSession(str(MODELS/'sherpa-onnx-pyannote-segmentation-3-0/model.onnx'),
        sess_options=options,providers=['CPUExecutionProvider'])
    completed=set();start=time.monotonic()
    while True:
        for cache in sorted((OUT/'primary_cache').glob('*.json'),key=natural):
            if cache.stem in completed:continue
            try:r=json.loads(cache.read_text(encoding='utf-8'))
            except json.JSONDecodeError:continue
            target=OUT/'checks'/cache.name
            if r['status']=='prepared' and not target.exists():
                a=decode_audio(str(OUT/r['audio']))
                result=transcript(model,a,'en')
                events=event_scores(tagger,a)
                music=max((v for k,v in events.items() if 'music' in k.lower() or 'singing' in k.lower()),default=0)
                applause=max((v for k,v in events.items() if 'applause' in k.lower() or 'clapping' in k.lower()),default=0)
                stats=overlap_stats(overlap,a)
                flags=[]
                if music>=.2:flags.append('possible_music_or_singing')
                if applause>=.2:flags.append('possible_applause')
                if stats['estimated_overlap_seconds']>=.2:flags.append('possible_overlapping_speech')
                if stats['possible_multiple_speakers']:flags.append('possible_multiple_speakers')
                match=bool(normalize(r['transcript'])) and normalize(r['transcript'])==normalize(result['text'])
                if not match:flags.append('transcript_disagreement')
                row=dict(clip_id=r['clip_id'],source_sha256=r['source_sha256'],cross_asr=result,
                    normalized_word_agreement=match,transcript_similarity=SequenceMatcher(None,normalize(r['transcript']),normalize(result['text'])).ratio(),
                    events=events,music_score=music,applause_score=applause,
                    overlap=stats,flags=flags)
                save_json(target,row)
            completed.add(cache.stem)
            if len(completed)%5==0:
                print('CHECKED',len(completed),flush=True);export()
        done_path=OUT/'primary_complete.json'
        if done_path.exists():
            done=json.loads(done_path.read_text())
            if len(completed)==done['expected']:
                export();print('CHECK COMPLETE',len(completed),flush=True);return
        if time.monotonic()-start>10800:raise TimeoutError('Primary stage incomplete; checkpoints preserved')
        time.sleep(3)


def export():
    rows=[]
    for cache in sorted((OUT/'primary_cache').glob('*.json'),key=natural):
        try:r=json.loads(cache.read_text(encoding='utf-8'))
        except json.JSONDecodeError:continue
        cp=OUT/'checks'/cache.name
        if cp.exists():
            c=json.loads(cp.read_text(encoding='utf-8'));assert c['source_sha256']==r['source_sha256']
            r['checks']=c;r['flags']=list(dict.fromkeys(r['flags']+c['flags']))
        r['screening_complete']=r['status']=='excluded' or cp.exists()
        # Difficulty/ASR confidence never excludes learner audio from the broad set.
        r['transcript_agreement_subset']=bool(r['status']=='prepared' and cp.exists() and
            r['checks']['normalized_word_agreement'] and r.get('transcription_language')=='en' and
            not any(f in r['flags'] for f in ['possible_music_or_singing','possible_overlapping_speech',
                'possible_multiple_speakers','no_speech_detected','clipping','decoder_recovery_used']))
        rows.append(r)
    prepared=[r for r in rows if r['status']=='prepared']
    strict=[r for r in rows if r['transcript_agreement_subset']]
    for name,subset in [('manifest_all.jsonl',rows),('manifest.jsonl',prepared),('manifest_agreement.jsonl',strict)]:
        (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in subset),encoding='utf-8')
    (OUT/'transcripts.txt').write_text('\n'.join(r['clip_id']+'\t'+r['transcript'] for r in prepared),encoding='utf-8')
    participants=[]
    for pid in sorted(set(r['participant_id'] for r in rows),key=natural):
        all_p=[r for r in rows if r['participant_id']==pid];p=[r for r in prepared if r['participant_id']==pid]
        participants.append(dict(participant_id=pid,original_files=len(all_p),prepared_files=len(p),
            prepared_minutes=round(sum(r['duration_seconds'] for r in p)/60,2),
            agreement_files=sum(r['transcript_agreement_subset'] for r in p)))
    expected=len(inputs())
    complete=len(rows)==expected and all(r['screening_complete'] for r in rows) and (OUT/'primary_complete.json').exists()
    summary=dict(complete=complete,expected_original_files=expected,processed_files=len(rows),
        declared_participants=len(participants),prepared_files=len(prepared),
        prepared_minutes=round(sum(r['duration_seconds'] for r in prepared)/60,2),
        excluded_files=len(rows)-len(prepared),checked_prepared_files=sum('checks' in r for r in prepared),
        agreement_files=len(strict),agreement_minutes=round(sum(r['duration_seconds'] for r in strict)/60,2),
        exclusions=dict(Counter(x for r in rows for x in r['excluded_reasons'])),
        flags=dict(Counter(x for r in rows for x in r['flags'])),participants=participants,
        human_verified_transcripts=0,human_pronunciation_labels=0,
        limitations=['Folder IDs are supplied labels, not verified identities.',
            'Automatic transcripts can normalize learner errors or invent words.',
            'Language, overlap and audio-event detectors can make accent-dependent mistakes.',
            'Transcript agreement selects easier speech; it is a biased exploratory subset.',
            'No pronunciation correctness labels, proficiency ratings or permissions are inferred.',
            'Keep this collection out of training if using it as Vietnamese evaluation data.'])
    save_json(OUT/'summary.json',summary)
    cards=[]
    for r in rows:
        audio=f'<audio controls preload="none" src="{r["audio"]}"></audio>' if r['audio'] else ''
        other=r.get('checks',{}).get('cross_asr',{}).get('text',
            'Not applicable: original excluded' if r['status']=='excluded' else 'Check pending')
        cards.append(f'<article><b>{r["clip_id"]}</b> | {r["participant_id"]} | {r["status"]}'
            f'<p>Primary: {html.escape(r["transcript"] or "")}</p><p>Cross-check: {html.escape(other)}</p>'
            f'<small>{html.escape(", ".join(r["flags"]+r["excluded_reasons"]))}</small>{audio}</article>')
    (OUT/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Vietnamese learner audio</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;background:#f5f7fa}'
        'article{background:white;padding:16px;margin:12px 0}audio{display:block;width:100%;margin-top:12px}'
        'small{color:#955}</style><h1>Vietnamese learner audio</h1><p>Folder participant labels preserved. '
        'Transcripts and screening are automatic. Flags are review signals, not pronunciation scores. '
        'Difficult learner speech is retained; duplicates are not counted twice.</p>'+''.join(cards),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['primary','check','export'])
    args=parser.parse_args()
    for directory in ['audio','primary_cache','checks']:(OUT/directory).mkdir(parents=True,exist_ok=True)
    if args.stage=='primary':primary()
    elif args.stage=='check':check()
    else:export()
