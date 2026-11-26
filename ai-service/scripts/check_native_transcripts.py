"""Cross-check every machine-screened clip with Whisper small.en.

Watches the full-source pipeline's per-source checkpoints. Only exact normalized
word agreement and good second-pass confidence enter the conservative export.
Two ASR models agreeing is not a human-verified reference transcript.
"""
from collections import Counter
from difflib import SequenceMatcher
import html
import json
from pathlib import Path
import re
import shutil
import time

from finalize_native_audio import WhisperModel, decode_audio, save_json


def normalized(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",text.lower().replace('\u2019',"'"))


def export(out, rows, processed, base_summary):
    passed=[r for r in rows if r['transcript_check']=='agreement']
    save_json(out/'transcript_checks.json', rows)
    (out/'manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in passed),encoding='utf-8')
    (out/'transcripts.txt').write_text('\n'.join(r['clip_id']+'\t'+r['transcript'] for r in passed),encoding='utf-8')
    summary=dict(complete=base_summary.get('complete',False) and len(processed)==10,
        completed_sources=sorted(processed),processed_source_count=len(processed),
        cross_checked_clips=len(rows),consensus_clips=len(passed),
        consensus_minutes=round(sum(r['duration_seconds'] for r in passed)/60,2),
        disagreements=sum(r['transcript_check']=='disagreement' for r in rows),
        low_second_pass_confidence=sum(r['transcript_check']=='low_confidence' for r in rows),
        source_local_speaker_clusters=len(set(r['local_speaker_id'] for r in passed)),
        human_verified_clips=0,pronunciation_labeled_clips=0,
        status='exploratory_machine_screened_dataset',
        limitations=base_summary.get('limitations',[])+[
            'Whisper base.en and small.en are related models; agreement is not independent ground truth.',
            'Disagreements remain available in transcript_checks.json and review.html.'])
    save_json(out/'summary.json',summary)
    cards=[]
    for row in rows:
        passed_row=row['transcript_check']=='agreement'
        audio=row['audio'] if passed_row else '../native_final/'+row['original_audio']
        cards.append(f'<article class="{"pass" if passed_row else "flag"}"><b>{row["clip_id"]}</b> '
            f'{row["local_speaker_id"]} · {row["transcript_check"]}'
            f'<p>First pass: {html.escape(row["base_transcript"])}</p>'
            f'<p>Second pass: {html.escape(row["second_pass_transcript"])}</p>'
            f'<audio controls preload="none" src="{audio}"></audio></article>')
    (out/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Native speech cross-check</title>'
        '<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;background:#f7fafc}'
        'article{background:white;padding:16px;margin:12px 0;border-left:5px solid #2a8}'
        '.flag{border-color:#c84}audio{width:100%}</style><h1>Native speech: two-model transcript check</h1>'
        '<p>Conservative automatic export. No human-verified transcripts, identities, licenses, '
        'or pronunciation scores. Green means normalized word agreement, not proven correctness.</p>'
        +''.join(cards),encoding='utf-8')


def main():
    base=Path('data/processed/native_final')
    out=Path('data/processed/native_screened')
    (out/'clips').mkdir(parents=True,exist_ok=True)
    (out/'cache').mkdir(exist_ok=True)
    model=WhisperModel('data/models/native-preparation/whisper-small.en',device='cpu',
                       compute_type='int8',cpu_threads=6,local_files_only=True)
    processed=set();rows=[];start=time.monotonic()
    while True:
        for checkpoint in sorted((base/'cache').glob('source_??_clips.json')):
            source_id=checkpoint.stem.removesuffix('_clips')
            if source_id in processed or (base/'cache'/f'{source_id}.pending').exists():
                continue
            try:
                records=json.loads(checkpoint.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                continue
            print('CROSS-CHECK '+source_id,flush=True)
            for r in records:
                if r['status']!='machine_screened':
                    continue
                cache=out/'cache'/f'{r["clip_id"]}.json'
                if cache.exists():
                    row=json.loads(cache.read_text(encoding='utf-8'))
                    assert row['base_transcript']==r['transcript']
                else:
                    segments,_=model.transcribe(decode_audio(str(base/r['audio'])),
                        language='en',beam_size=5,word_timestamps=True,
                        condition_on_previous_text=False,vad_filter=False)
                    segments=list(segments)
                    text=''.join(s.text for s in segments).strip()
                    probs=[w.probability for s in segments for w in (s.words or [])]
                    confidence=sum(probs)/len(probs) if probs else 0
                    match=normalized(text)==normalized(r['transcript'])
                    status='agreement' if match else 'disagreement'
                    if match and (confidence<.9 or min(probs,default=0)<.25 or
                                  min((s.avg_logprob for s in segments),default=-10)<-.6):
                        status='low_confidence'
                    row=dict(r,original_audio=r['audio'],base_transcript=r['transcript'],
                        second_pass_transcript=text,second_pass_confidence=round(confidence,4),
                        transcript_check=status,transcript_status='two_model_agreement_unverified' if status=='agreement' else 'needs_review',
                        transcript_similarity=round(SequenceMatcher(None,normalized(r['transcript']),normalized(text)).ratio(),4),
                        second_pass_model='Whisper small.en',first_pass_model='Whisper base.en')
                    if status=='agreement':
                        row['audio']='clips/'+Path(r['audio']).name
                    save_json(cache,row)
                if row['transcript_check']=='agreement':
                    shutil.copy2(base/r['audio'],out/row['audio'])
                rows.append(row)
                if len(rows)%20==0:
                    print('CHECKED',len(rows),'CONSENSUS',sum(x['transcript_check']=='agreement' for x in rows),flush=True)
            processed.add(source_id)
            try:
                summary=json.loads((base/'summary.json').read_text())
            except (FileNotFoundError,json.JSONDecodeError):
                summary={}
            export(out,rows,processed,summary)
        try:
            summary=json.loads((base/'summary.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):
            summary={}
        if summary.get('complete') and len(processed)==10:
            export(out,rows,processed,summary)
            print('CROSS-CHECK COMPLETE',len(rows),flush=True)
            return
        if time.monotonic()-start>7200:
            raise TimeoutError('Upstream pipeline did not finish; checkpoints preserved')
        time.sleep(10)


if __name__=='__main__':
    main()
