"""Build deterministic training and held-out comparison inputs from prepared data."""
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import wave

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/prepared'


def pairs(path):
    return dict(line.split(maxsplit=1) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def audio_info(path):
    with wave.open(str(path)) as f:
        assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2),str(path)
        return f.getnframes()/16000


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    corpus=ROOT/'data/speechocean762'
    scores=json.loads((corpus/'resource/scores.json').read_text(encoding='utf-8'))
    train_speakers=pairs(corpus/'train/utt2spk')
    # Selection depends only on speaker IDs, never scores or held-out test data.
    ordered=sorted(set(train_speakers.values()),key=lambda s:hashlib.sha256(('WordSpeak-validation-v1:'+s).encode()).hexdigest())
    validation=set(ordered[:25])
    partitions={name:[] for name in ['train','validation','test','comparison_native','comparison_vietnamese']}
    for official in ['train','test']:
        transcripts=pairs(corpus/official/'text')
        speakers=pairs(corpus/official/'utt2spk')
        paths=pairs(corpus/official/'wav.scp')
        assert transcripts.keys()==speakers.keys()==paths.keys()
        for uid in sorted(transcripts):
            path=corpus/paths[uid].replace('\\','/')
            split='test' if official=='test' else 'validation' if speakers[uid] in validation else 'train'
            label=scores[uid]
            normalize=lambda t:re.findall(r"[A-Z0-9]+(?:'[A-Z0-9]+)?",t.upper())
            assert normalize(label['text'])==normalize(transcripts[uid])
            partitions[split].append(dict(id='speechocean762:'+uid,dataset='speechocean762',split=split,
                speaker_id='speechocean762:'+speakers[uid],speaker_id_status='official_corpus_id',
                audio_path=relative(path),text=transcripts[uid],transcript_status='corpus_transcript',
                duration_seconds=audio_info(path),pronunciation_labels=label,
                label_scales=dict(sentence_word='0-10',phoneme='0-2'),official_split=official))
    for dataset,directory,manifest,part,speaker_field in [
        ('native_comparison','data/processed/native_screened','manifest.jsonl','comparison_native','local_speaker_id'),
        ('vietnamese_comparison','data/processed/vietnamese/segments','manifest.jsonl','comparison_vietnamese','participant_id')]:
        folder=ROOT/directory
        for r in read_jsonl(folder/manifest):
            path=folder/r['audio']
            assert r['pronunciation_label'] is None and not r['human_verified']
            partitions[part].append(dict(id=dataset+':'+r['clip_id'],dataset=dataset,split='comparison',
                speaker_id=dataset+':'+r[speaker_field],
                speaker_id_status=r.get('participant_id_status',r.get('speaker_status','unverified')),
                audio_path=relative(path),text=r['transcript'],transcript_status=r['transcript_status'],
                duration_seconds=audio_info(path),pronunciation_labels=None,
                source_manifest=relative(folder/manifest),source_clip_id=r['clip_id'],
                parent_clip_id=r.get('parent_clip_id'),permission_status=r['permission_status'],
                recommended_use='exploratory_comparison_only'))
    sets={p:{r['speaker_id'] for r in partitions[p]} for p in ['train','validation','test']}
    assert not (sets['train']&sets['validation'] or sets['train']&sets['test'] or sets['validation']&sets['test'])
    assert len(partitions['train'])+len(partitions['validation'])+len(partitions['test'])==5000
    ids=[r['id'] for data in partitions.values() for r in data]
    assert len(ids)==len(set(ids))
    for name,rows in partitions.items():
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    comparison=partitions['comparison_native']+partitions['comparison_vietnamese']
    (OUT/'comparison.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in comparison),encoding='utf-8')
    report=dict(status='PASS',speaker_overlap_train_validation_test=0,
        comparison_clips_in_training=0,selection='SHA-256 speaker order, WordSpeak-validation-v1, first 25 official training speakers',
        partitions={p:dict(clips=len(rows),speaker_ids=len(set(r['speaker_id'] for r in rows)),
            minutes=round(sum(r['duration_seconds'] for r in rows)/60,2),
            labeled_clips=sum(r['pronunciation_labels'] is not None for r in rows)) for p,rows in partitions.items()},
        note='Native speaker IDs are source-local estimated clusters, not unique people. Comparison data have no pronunciation reference labels.')
    (OUT/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# WordSpeak dataset entry point','','Audio preparation and manifest generation are complete. No new audio collection is needed to start the MVP baseline.','','| File | Clips | Speaker IDs | Use |','|---|---:|---:|---|']
    purposes={'train':'Fit/adapt the scorer','validation':'Choose settings and calibrate scores','test':'Final official-corpus evaluation','comparison_native':'Exploratory native comparison, unlabeled','comparison_vietnamese':'Exploratory learner comparison, unlabeled'}
    for name,rows in partitions.items():
        lines.append(f'| {name}.jsonl | {len(rows)} | {len(set(r["speaker_id"] for r in rows))} | {purposes[name]} |')
    lines+=['','`comparison.jsonl` combines both comparison groups. These files reference existing WAVs; audio is not duplicated. `audio_path` is relative to the project root, regardless of the working directory.','','The official speechocean762 test set is preserved. Validation speakers come only from its training set. Speaker overlap among train, validation and test is zero. Native source-local voice clusters must not be interpreted as confirmed unique people.','','Original corpus scores are kept in `pronunciation_labels` with their original scales. The transcript check ignores punctuation/case only; all 5,000 texts match lexically. Comparison labels are `null`: native status and learner status are not correctness scores. Automatic transcripts remain unverified. Both related recognizers may share errors, and word-agreement selection favors easier speech.','','Load examples with `app.datasets.iter_examples`, which resolves audio paths and can require pronunciation labels for training. Full recordings and flagged material remain under `data/processed/vietnamese` and `data/processed/native_final`.','','What remains outside data preparation: implement the real pronunciation scorer (the API is currently a fixed-score stub), and obtain independent human judgments if claiming scoring accuracy on the collected Vietnamese/native comparison audio. No human ratings were fabricated.','','Corpus attribution: Junbo Zhang et al. (2021), speechocean762: An Open-Source Non-native English Speech Corpus For Pronunciation Assessment, Interspeech 2021. Source: https://openslr.org/101/ ; CC BY 4.0. Original scores and audio references are preserved; only the official training partition is subdivided.']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
