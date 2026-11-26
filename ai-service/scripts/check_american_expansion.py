"""Real-audio integration outcomes; no human correctness labels are inferred."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ai-service'))
from app.sound_catalog import PROMPTS, PRIMARY_TARGETS

def main():
    out=ROOT/'data/results/american_expansion';cases=[]
    corpus=[json.loads(line) for line in (ROOT/'data/prepared/train.jsonl').read_text(encoding='utf-8').splitlines()]
    missing=[]
    for prompt_id,prompt in PROMPTS.items():
        if not prompt['primary']:continue
        eligible=[r for r in corpus if .25<=r['duration_seconds']<=4 and re.findall(r'[a-z]+',r['text'].lower()).count(prompt['word'])==1]
        eligible.sort(key=lambda r:hashlib.sha256(('american-expansion-v1:'+r['id']).encode()).hexdigest())
        if not eligible:missing.append(prompt_id);continue
        row=eligible[0]
        cases.append({'id':row['id'],'prompt_id':prompt_id,'speaker_id':row['speaker_id'],'audio_path':row['audio_path'],
                      'input_scope':'context','source_split':'train','source_kind':'existing_corpus','classification_correct':None})
    new=out/'new_word_cases.jsonl'
    if new.is_file():
        for line in new.read_text(encoding='utf-8').splitlines():
            row=json.loads(line);cases.append({**row,'input_scope':'word','source_split':'unassigned','source_kind':'new_collection'})
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8013',timeout=180,trust_env=False) as client:
        config=client.get('/demo/config').json();assert config['accent']['id']=='general_american'
        for index,case in enumerate(cases,1):
            audio=ROOT/case['audio_path'];payload=audio.read_bytes()
            response=client.post('/demo/analyze',data={'prompt_id':case['prompt_id'],'input_scope':case['input_scope']},files={'audio':('case.wav',payload,'audio/wav')})
            assert response.status_code==200,(case['id'],response.text)
            result=response.json();assert result['score'] is None and result['mode']=='live_audio'
            assert result['target_phone']==PROMPTS[case['prompt_id']]['target_phone']
            results.append({**case,'audio_sha256':hashlib.sha256(payload).hexdigest(),'response':result})
            (out/'real_audio_checks.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results),encoding='utf-8')
            print(json.dumps({'done':index,'total':len(cases),'source_kind':case['source_kind'],'prompt':case['prompt_id'],'status':result['status']}),flush=True)
    summary={'status':'PASS','build':config['build'],'core_targets':len(PRIMARY_TARGETS),'requests':len(results),
             'by_source':dict(Counter(r['source_kind'] for r in results)),
             'statuses':dict(Counter(r['response']['status'] for r in results)),
             'core_targets_with_real_audio':len({r['response']['target_phone'] for r in results}),
             'no_existing_exact_word_source':missing,'classification_accuracy':None,'training_performed':False,
             'untouched_test_used':False,'note':'Functional model requests with approximate context/crop placement; outcomes are not accuracy or learning gain.'}
    (out/'real_audio_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
