"""Extract whole-word, time-consistent ASR-agreement sections for exploration.

Retains original participant IDs. Agreement is not human transcription or a
pronunciation label. The complete, difficult learner recordings remain separate.
"""
from difflib import SequenceMatcher
import argparse
from html import escape
import json
from pathlib import Path
import re
import wave

ROOT=Path('data/processed/vietnamese')
OUT=ROOT/'segments'


def tokens(asr):
    result=[];words=[]
    for seg in asr['segments']:
        for word in seg['words'] or []:
            word=dict(word);word['id']=len(words);words.append(word)
            norm=re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",word['word'].lower().replace('\u2019',"'"))
            for i,text in enumerate(norm):
                result.append(dict(text=text,word_id=word['id'],first=i==0,last=i==len(norm)-1,
                    start=word['start'],end=word['end']))
    return result,words


def main(allow_incomplete=False):
    summary=json.loads((ROOT/'summary.json').read_text())
    assert summary['complete'] or allow_incomplete
    (OUT/'audio').mkdir(parents=True,exist_ok=True)
    rows=[json.loads(s) for s in (ROOT/'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    results=[]
    for row in rows:
        if 'checks' not in row:continue
        unsafe={'possible_music_or_singing','possible_applause','possible_overlapping_speech',
            'possible_multiple_speakers','no_speech_detected','clipping','decoder_recovery_used'}
        if unsafe.intersection(row['flags']) or row['transcription_language']!='en':continue
        a,words=tokens(row['primary_asr']);b,_=tokens(row['checks']['cross_asr'])
        blocks=SequenceMatcher(None,[x['text'] for x in a],[x['text'] for x in b],autojunk=False).get_matching_blocks()
        groups=[]
        for block in blocks:
            lo,hi=block.a,block.a+block.size
            while lo<hi and not a[lo]['first']:lo+=1
            while hi>lo and not a[hi-1]['last']:hi-=1
            if hi-lo<5:continue
            drift=max((abs((a[i]['start']+a[i]['end'])/2-(b[block.b+i-block.a]['start']+b[block.b+i-block.a]['end'])/2) for i in range(lo,hi)),default=99)
            if drift>.65:continue
            word_ids=list(dict.fromkeys(a[i]['word_id'] for i in range(lo,hi)))
            group=[]
            for wid in word_ids:
                w=words[wid]
                if group and (w['end']-words[group[0]]['start']>15 or
                    w['start']-words[group[-1]]['end']>.8 or
                    (words[group[-1]]['end']-words[group[0]]['start']>=3 and
                     re.search(r'[.!?][\"\u201d]*$',words[group[-1]]['word']))):
                    groups.append((group,drift));group=[]
                group.append(wid)
            if group:groups.append((group,drift))
        with wave.open(str(ROOT/row['audio'])) as source:
            rate=source.getframerate();full=source.readframes(source.getnframes())
        for index,(ids,drift) in enumerate(groups,1):
            first,last=words[ids[0]],words[ids[-1]]
            start=max(0,first['start']-.08)
            end=min(len(full)/2/rate,last['end']+.12)
            if ids[0]>0:start=max(start,(words[ids[0]-1]['end']+first['start'])/2)
            if ids[-1]+1<len(words):end=min(end,(last['end']+words[ids[-1]+1]['start'])/2)
            if len(ids)<4 or not 3<=end-start<=15.3:continue
            left,right=int(start*rate),int(end*rate)
            cid=f'{row["clip_id"]}_S{index:03d}'
            rel='audio/'+cid+'.wav'
            with wave.open(str(OUT/rel),'wb') as dest:
                dest.setparams((1,2,rate,0,'NONE','not compressed'));dest.writeframes(full[left*2:right*2])
            text=''.join(words[i]['word'] for i in ids).strip()
            results.append(dict(clip_id=cid,participant_id=row['participant_id'],audio=rel,
                parent_clip_id=row['clip_id'],source=row['source'],source_sha256=row['source_sha256'],
                parent_start_seconds=left/rate,parent_end_seconds=right/rate,
                source_start_seconds=row['start_seconds']+left/rate,
                source_end_seconds=row['start_seconds']+right/rate,duration_seconds=(right-left)/rate,
                transcript=text,transcript_status='aligned_two_model_word_agreement_unverified',
                max_model_timestamp_difference_seconds=round(drift,4),
                ends_with_sentence_punctuation=bool(re.search(r'[.!?][\"\u201d]*$',text)),
                pronunciation_label=None,human_verified=False,permission_status=row['permission_status'],
                participant_id_status=row['participant_id_status'],recommended_use='exploratory_only'))
    (OUT/'manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results),encoding='utf-8')
    (OUT/'transcripts.txt').write_text('\n'.join(r['clip_id']+'\t'+r['transcript'] for r in results),encoding='utf-8')
    info=dict(complete=summary['complete'],clips=len(results),minutes=round(sum(r['duration_seconds'] for r in results)/60,2),
        declared_participants=len(set(r['participant_id'] for r in results)),
        human_verified_transcripts=0,pronunciation_labels=0,
        note='Contiguous matching words with timestamps within 0.65s. Related recognizers can share errors. Selection favors easier speech; use full learner set for representative evaluation after human labeling.')
    (OUT/'summary.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    cards=['<article><b>'+r['clip_id']+'</b><p>'+escape(r['transcript'])+'</p><audio controls preload="none" src="'+r['audio']+'"></audio></article>' for r in results]
    (OUT/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Learner agreement sections</title>'
        '<style>body{font:16px system-ui;max-width:960px;margin:40px auto;background:#f5f7fa}article{background:white;margin:12px 0;padding:16px}audio{width:100%}</style>'
        '<h1>Vietnamese learner: matching word sections</h1><p>Automatically aligned clips. No human-verified transcription or pronunciation labels. Difficult full recordings remain in the parent dataset.</p>'+''.join(cards),encoding='utf-8')
    print(json.dumps(info,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-incomplete',action='store_true')
    main(parser.parse_args().allow_incomplete)
