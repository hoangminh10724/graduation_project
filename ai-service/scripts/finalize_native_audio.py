"""Transcribe, diarize and conservatively screen all native source recordings.

Outputs are machine-screened exploratory data, never human-scored references.
Uses local Whisper base.en, pyannote segmentation, NeMo speaker embeddings,
and CED audio-event classification models. ASR/diarization are checkpointed.
"""
import argparse
import ctypes
import importlib.util
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import html
import json
from pathlib import Path
import re
import wave

import av
import numpy as np
# Windows may otherwise resolve a system copy of ONNX Runtime (e.g. 1.17)
# before the version installed with these tools. Load the matching DLL first.
ort_spec = importlib.util.find_spec('onnxruntime')
ort_dll = Path(ort_spec.origin).parent/'capi'/'onnxruntime.dll'
if ort_dll.exists():
    _ort_library = ctypes.WinDLL(str(ort_dll.resolve()))
import sherpa_onnx as so
from faster_whisper import WhisperModel

RATE = 16000


def decode_audio(path, sampling_rate=RATE):
    resampler = av.AudioResampler(format='fltp', layout='mono', rate=sampling_rate)
    buffers = []
    with av.open(path) as container:
        for frame in container.decode(audio=0):
            buffers.extend(f.to_ndarray().ravel() for f in resampler.resample(frame))
        buffers.extend(f.to_ndarray().ravel() for f in resampler.resample(None))
    return np.concatenate(buffers).astype(np.float32)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_scalar), encoding='utf-8')


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def wav_write(path, audio):
    peak = max(float(np.max(np.abs(audio))), 1e-8)
    gain = min(3.981, .7079 / peak)
    with wave.open(str(path), 'wb') as f:
        f.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        f.writeframes((np.clip(audio * gain, -1, 1)*32767).astype('<i2').tobytes())
    return round(float(20*np.log10(gain)), 3)


def event_scores(tagger, samples):
    # CED expects at most ~10s. Classify all windows, including the tail.
    windows = []
    for start in range(0, len(samples), RATE * 8):
        window = samples[start:start + RATE * 8]
        if len(window) < RATE:
            continue
        stream = tagger.create_stream()
        stream.accept_waveform(sample_rate=RATE, waveform=window)
        result = tagger.compute(stream)
        windows.append({e.name: float(e.prob) for e in result})
    combined = {}
    for window in windows:
        for name, score in window.items():
            combined[name] = max(combined.get(name, 0), score)
    return combined


def main(args):
    out = args.output
    for directory in ['cache', 'clips', 'excluded']:
        (out/directory).mkdir(parents=True, exist_ok=True)
    model_dir = args.models
    print('Loading local models', flush=True)
    whisper = WhisperModel(str(model_dir/'whisper'), device='cpu', compute_type='int8',
                           cpu_threads=6, local_files_only=True)
    diar_config = so.OfflineSpeakerDiarizationConfig(
        segmentation=so.OfflineSpeakerSegmentationModelConfig(
            pyannote=so.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(model_dir/'sherpa-onnx-pyannote-segmentation-3-0/model.onnx')),
            num_threads=4),
        embedding=so.SpeakerEmbeddingExtractorConfig(
            model=str(model_dir/'nemo_en_titanet_small.onnx'), num_threads=4),
        clustering=so.FastClusteringConfig(num_clusters=-1, threshold=.85),
        min_duration_on=.25, min_duration_off=.35)
    tagger = so.AudioTagging(so.AudioTaggingConfig(
        model=so.AudioTaggingModelConfig(ced=str(model_dir/'tagger/model.int8.onnx'),
                                       num_threads=4),
        labels=str(model_dir/'tagger/class_labels_indices.csv'), top_k=30))
    all_records, source_summaries = [], []
    paths = sorted(args.source.glob('*.mp3'))
    for source_num, source in enumerate(paths, 1):
        source_id = f'source_{source_num:02d}'
        print(f'BEGIN {source_id} {source.name}', flush=True)
        audio = decode_audio(str(source), sampling_rate=RATE)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        cache_path = out/'cache'/f'{source_id}_asr.json'
        if cache_path.exists():
            asr = json.loads(cache_path.read_text(encoding='utf-8'))
            assert asr['source_sha256'] == digest
        else:
            segments, info = whisper.transcribe(audio, language='en', beam_size=5,
                word_timestamps=True, vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
                condition_on_previous_text=False)
            asr = dict(source_sha256=digest, segments=[])
            for seg in segments:
                asr['segments'].append(asdict(seg))
                if len(asr['segments']) % 20 == 0:
                    print(f'ASR {source_id} {seg.end:.1f}/{len(audio)/RATE:.1f}s', flush=True)
            save_json(cache_path, asr)
        diar_path = out/'cache'/f'{source_id}_speakers.json'
        diar_cache = json.loads(diar_path.read_text()) if diar_path.exists() else {}
        # The source_08 introduction explicitly describes two conversation partners.
        num_speakers = 2 if digest=='4c9059afc562bff3a2642052b4d14850448a1cac4b01c691967d5bc1021f43d0' else -1
        if diar_cache.get('threshold') == .85 and diar_cache.get('num_speakers',-1)==num_speakers:
            assert diar_cache['source_sha256'] == digest
            turns = diar_cache['turns']
        else:
            print('DIARIZATION '+source_id, flush=True)
            diar_config.clustering.num_clusters = num_speakers
            source_diar = so.OfflineSpeakerDiarization(diar_config)
            turns = [dict(start=float(t.start), end=float(t.end), speaker=int(t.speaker))
                     for t in source_diar.process(audio).sort_by_start_time()]
            save_json(diar_path, dict(source_sha256=digest, threshold=.85,num_speakers=num_speakers,turns=turns))
        clip_cache=out/'cache'/f'{source_id}_clips.json'
        if num_speakers == -1 and clip_cache.exists():
            source_rows=json.loads(clip_cache.read_text(encoding='utf-8'))
            assert all(r['source_sha256']==digest for r in source_rows)
            all_records.extend(source_rows)
            accepted=[r for r in source_rows if r['status']=='machine_screened']
            source_summaries.append(dict(source_id=source_id,source_file=source.name,
                duration_seconds=len(audio)/RATE,speaker_clusters=len(set(t['speaker'] for t in turns)),
                machine_screened_clips=len(accepted),machine_screened_minutes=round(sum(r['duration_seconds'] for r in accepted)/60,2),
                excluded_clips=len(source_rows)-len(accepted)))
            export(out,all_records,source_summaries,len(paths))
            print('REUSED '+source_id,flush=True)
            continue
        words = []
        for seg in asr['segments']:
            for w in seg['words']:
                w = dict(w, avg_logprob=seg['avg_logprob'])
                duration = max(w['end']-w['start'], .01)
                coverage = defaultdict(float)
                for turn in turns:
                    coverage[turn['speaker']] += max(0, min(w['end'], turn['end'])-
                                                       max(w['start'], turn['start']))
                ranked = sorted(coverage.items(), key=lambda p:p[1], reverse=True)
                w['speaker'] = ranked[0][0] if ranked and ranked[0][1]/duration >= .75 else None
                w['overlap'] = bool(len(ranked)>1 and ranked[1][1]/duration > .1)
                words.append(w)
        groups, group = [], []
        for word in words:
            split = group and (word['speaker'] != group[-1]['speaker'] or
                word['start']-group[-1]['end'] > .7 or
                word['end']-group[0]['start'] > 18 or
                (re.search(r'[.!?][\"\u201d]*$', group[-1]['word']) and
                 group[-1]['end']-group[0]['start'] >= 3))
            if split:
                groups.append(group); group=[]
            group.append(word)
        if group:
            groups.append(group)
        # Remove only this script's generated WAV names for this source on resumption.
        for directory in ['clips', 'excluded']:
            for old in (out/directory).glob(f'{source_id}_[0-9][0-9][0-9][0-9].wav'):
                old.unlink()
        source_rows = []
        for index, group in enumerate(groups, 1):
            start = max(0, group[0]['start']-.08)
            end = min(len(audio)/RATE, group[-1]['end']+.12)
            # Never pad into another ASR group, even by a fraction of a second.
            if index > 1:
                start = max(start, (groups[index-2][-1]['end']+group[0]['start'])/2)
            if index < len(groups):
                end = min(end, (group[-1]['end']+groups[index][0]['start'])/2)
            text = ''.join(w['word'] for w in group).strip()
            reasons=[]
            chunk = audio[int(start*RATE):int(end*RATE)]
            if not 3 <= end-start <= 20:
                reasons.append('duration_outside_3_20_seconds')
            if len(group)<4:
                reasons.append('too_few_words')
            if any(w['speaker'] is None for w in group):
                reasons.append('speaker_unresolved')
            if any(w['overlap'] for w in group):
                reasons.append('overlapping_speakers')
            # Reject any competing speaker activity in the clip, including in gaps.
            speaker = group[0]['speaker']
            competing = sum(max(0,min(end,t['end'])-max(start,t['start']))
                            for t in turns if t['speaker'] != speaker)
            if competing > .12:
                reasons.append('competing_speaker_in_clip')
            probs = [w['probability'] for w in group]
            avgprob = float(np.mean(probs))
            if avgprob < .85 or min(probs)<.2 or min(w['avg_logprob'] for w in group)<-.7:
                reasons.append('low_asr_confidence')
            if max(Counter(re.findall(r'\w+',text.lower())).values(), default=0) > max(4,len(group)*.35):
                reasons.append('possible_repetition_hallucination')
            events = event_scores(tagger, chunk) if len(chunk)>=RATE*3 else {}
            music = max((v for k,v in events.items() if 'music' in k.lower() or
                         'singing' in k.lower()), default=0)
            applause = max((v for k,v in events.items() if 'applause' in k.lower() or
                            'clapping' in k.lower()), default=0)
            if music >= .15:
                reasons.append('music_or_singing_detected')
            if applause >= .15:
                reasons.append('applause_detected')
            clipped = float(np.mean(np.abs(chunk) >= .999)) if len(chunk) else 1
            rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) else 0
            if clipped>.005:
                reasons.append('clipping')
            if rms<.005:
                reasons.append('very_quiet')
            clip_id = f'{source_id}_{index:04d}'
            status = 'excluded' if reasons else 'machine_screened'
            rel = f'{"excluded" if reasons else "clips"}/{clip_id}.wav' if len(chunk) else None
            gain = wav_write(out/rel, chunk) if len(chunk) else 0
            record = dict(clip_id=clip_id, source_id=source_id, source_file=source.name,
                source_sha256=digest, start_seconds=round(start,3), end_seconds=round(end,3),
                duration_seconds=round(end-start,3), audio=rel, transcript=text,
                transcript_status='automatic_unverified', mean_word_probability=round(avgprob,4),
                word_timestamps=group, local_speaker_id=f'{source_id}_speaker_{speaker}' if speaker is not None else None,
                speaker_status='automatic_source_local_cluster',
                cross_source_identity_verified=False, native_status='unverified', accent='unverified',
                status=status, exclusion_reasons=list(dict.fromkeys(reasons)),
                events={k:round(v,5) for k,v in events.items()}, music_score=round(music,5),
                applause_score=round(applause,5), gain_db=gain,
                permission_status='unverified', source_url=None, pronunciation_label=None,
                human_verified=False, recommended_use='exploratory_comparison_only')
            source_rows.append(record)
        save_json(out/'cache'/f'{source_id}_clips.json', source_rows)
        all_records.extend(source_rows)
        accepted=[r for r in source_rows if r['status']=='machine_screened']
        source_summaries.append(dict(source_id=source_id, source_file=source.name,
            duration_seconds=len(audio)/RATE, speaker_clusters=len(set(t['speaker'] for t in turns)),
            machine_screened_clips=len(accepted), machine_screened_minutes=round(sum(r['duration_seconds'] for r in accepted)/60,2),
            excluded_clips=len(source_rows)-len(accepted)))
        print('DONE '+json.dumps(source_summaries[-1]),flush=True)
        # Incremental export permits resuming without repeating inference.
        export(out,all_records,source_summaries,len(paths))


def export(out, rows, sources, expected):
    for row in rows:
        if row['duration_seconds'] <= 0 and row['status']=='excluded':
            row['audio']=None
            row['exclusion_reasons']=[x for x in row['exclusion_reasons'] if x not in ('clipping','very_quiet')]
            if 'zero_duration_asr_artifact' not in row['exclusion_reasons']:
                row['exclusion_reasons'].append('zero_duration_asr_artifact')
    accepted=[r for r in rows if r['status']=='machine_screened']
    (out/'manifest_all.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,default=json_scalar)+'\n' for r in rows),encoding='utf-8')
    (out/'manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,default=json_scalar)+'\n' for r in accepted),encoding='utf-8')
    (out/'transcripts.txt').write_text('\n'.join(r['clip_id']+'\t'+r['transcript'] for r in accepted),encoding='utf-8')
    speakers=defaultdict(lambda:dict(clips=0,seconds=0))
    for row in accepted:
        s=speakers[row['local_speaker_id']];s['clips']+=1;s['seconds']+=row['duration_seconds']
    summary=dict(processed_sources=len(sources),expected_sources=expected,complete=len(sources)==expected,
        machine_screened_count=len(accepted),machine_screened_minutes=round(sum(r['duration_seconds'] for r in accepted)/60,2),
        excluded_count=len(rows)-len(accepted),human_verified_count=0,
        exclusion_reasons=dict(Counter(reason for r in rows for reason in r['exclusion_reasons'])),
        sources=sources,speaker_clusters=speakers,
        limitations=['Automatic transcripts and speaker clusters are not human verified.',
            'Music and overlap detectors can miss contamination or falsely reject speech.',
            'Speaker clusters are source-local; they are not confirmed people or identities.',
            'Native status, accent, licenses, source URLs and pronunciation ratings remain unverified.',
            'No clip is a ground-truth pronunciation reference; use only for exploratory comparisons.'])
    save_json(out/'summary.json',summary)
    cards=[]
    for row in rows:
        text=html.escape(row['transcript'])
        reasons=html.escape(', '.join(row['exclusion_reasons']))
        player = f'<audio controls preload="none" src="{row["audio"]}"></audio>' if row['audio'] else '<p>No audio: zero-duration ASR artifact.</p>'
        cards.append(f'<article class="{row["status"]}"><b>{row["clip_id"]}</b> '
            f'{row["local_speaker_id"]} · {row["start_seconds"]}–{row["end_seconds"]}s '
            f'<strong>{row["status"]}</strong><p>{text}</p><small>{reasons}</small>'
            f'{player}</article>')
    (out/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Native audio export</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;background:#f5f7fa}'
        'article{background:white;padding:16px;margin:12px 0;border-left:5px solid #2b8}'
        '.excluded{border-color:#b65}audio{width:100%;margin-top:12px}small{color:#944}</style>'
        '<h1>Native audio: transcripts and speaker turns</h1><p>All labels are automatic. '
        'Green: passed machine screening. Brown: excluded. No human pronunciation ratings '
        'or verified speaker identities are supplied.</p>'
        '<label><input type="checkbox" checked onchange="document.querySelectorAll(\'.excluded\').forEach(x=>x.hidden=this.checked)"> Hide excluded clips</label>'
        +''.join(cards)+'<script>document.querySelectorAll(".excluded").forEach(x=>x.hidden=true)</script>',encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/collecting/native'))
    parser.add_argument('--output',type=Path,default=Path('data/processed/native_final'))
    parser.add_argument('--models',type=Path,default=Path('data/models/native-preparation'))
    main(parser.parse_args())
