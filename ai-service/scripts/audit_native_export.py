"""Audit actual generated files and provenance, without ML dependencies."""
from array import array
from collections import Counter
import hashlib
import json
from pathlib import Path
import wave


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def main():
    base=Path('data/processed/native_final')
    strict=Path('data/processed/native_screened')
    summary=json.loads((base/'summary.json').read_text())
    strict_summary=json.loads((strict/'summary.json').read_text())
    assert summary['complete'] and summary['processed_sources']==10
    assert strict_summary['complete'] and strict_summary['processed_source_count']==10
    records=rows(base/'manifest_all.jsonl')
    accepted=rows(base/'manifest.jsonl')
    consensus=rows(strict/'manifest.jsonl')
    assert len(accepted)==summary['machine_screened_count']
    assert len(consensus)==strict_summary['consensus_clips']
    assert len({r['clip_id'] for r in records})==len(records)
    decoded=0; missing_excluded=[]; peak=0
    for root, dataset in [(base,records),(strict,consensus)]:
        for row in dataset:
            if row['audio'] is None:
                assert row['status']=='excluded' and row['duration_seconds']<=0
                assert 'zero_duration_asr_artifact' in row['exclusion_reasons']
                continue
            path=root/row['audio']
            if not path.exists() and row.get('status')=='excluded':
                missing_excluded.append(row['clip_id']);continue
            with wave.open(str(path)) as f:
                assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
                duration=f.getnframes()/f.getframerate()
                assert abs(duration-row['duration_seconds'])<.002
                pcm=array('h',f.readframes(f.getnframes()))
                assert len(pcm)>0
                measured=max(abs(x) for x in pcm)/32768
                assert measured<=.708
                peak=max(peak,measured)
                decoded+=1
            if row['status']=='machine_screened':
                assert 3<=duration<=20.002 and row['transcript'].strip()
                assert row['local_speaker_id'] is not None and not row['exclusion_reasons']
            assert row['human_verified'] is False and row['pronunciation_label'] is None
    for row in consensus:
        assert row['transcript_check']=='agreement'
        assert row['transcript_status']=='two_model_agreement_unverified'
        assert row['base_transcript']==row['transcript']
        assert (strict/row['audio']).read_bytes()==(base/row['original_audio']).read_bytes()
    checked_sources=[]
    for source in sorted(Path('data/collecting/native').glob('*.mp3')):
        with source.open('rb') as f:
            digest=hashlib.file_digest(f,'sha256').hexdigest()
        matching={r['source_sha256'] for r in records if r['source_file']==source.name}
        assert matching=={digest}
        checked_sources.append(dict(file=source.name,sha256=digest))
    assert set(p.name for p in (base/'clips').glob('*.wav'))=={Path(r['audio']).name for r in accepted}
    assert set(p.name for p in (strict/'clips').glob('*.wav'))=={Path(r['audio']).name for r in consensus}
    report=dict(status='PASS',sources_checked=len(checked_sources),
        wav_files_decoded=decoded,machine_screened_clips=len(accepted),
        consensus_clips=len(consensus),max_output_peak=round(peak,6),
        missing_excluded_files=missing_excluded,
        human_verified_clips=0,ground_truth_pronunciation_labels=0,
        original_sources=checked_sources,
        note='Technical integrity only. Does not certify transcript accuracy, identities, rights or pronunciation.')
    assert not missing_excluded
    (strict/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='original_sources'},indent=2))


if __name__=='__main__':
    main()
