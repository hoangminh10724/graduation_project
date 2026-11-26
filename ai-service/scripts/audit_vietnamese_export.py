"""Audit learner export integrity and write a readable quantity/quality report."""
from array import array
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import wave

ROOT=Path('data/processed/vietnamese')
SOURCE=Path('data/collecting/vietnamese')


def main():
    summary=json.loads((ROOT/'summary.json').read_text(encoding='utf-8'))
    assert summary['complete'], 'Both processing stages must finish first'
    rows=[json.loads(s) for s in (ROOT/'manifest_all.jsonl').read_text(encoding='utf-8').splitlines()]
    prepared=[r for r in rows if r['status']=='prepared']
    assert len(rows)==summary['expected_original_files']==summary['processed_files']
    assert len(prepared)==summary['prepared_files']
    assert len({r['clip_id'] for r in rows})==len(rows)
    assert len({r['decoded_sha256'] for r in prepared})==len(prepared)
    durations=[];max_peak=0;checked=0
    originals=[]
    by_id={r['clip_id']:r for r in rows}
    for row in rows:
        original=SOURCE/row['source']
        with original.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        assert digest==row['source_sha256']
        originals.append(dict(source=row['source'],sha256=digest))
        assert row['participant_id']==original.parent.name.upper()
        assert row['human_verified'] is False and row['pronunciation_label'] is None
        if row['status']=='excluded':
            assert row['excluded_reasons']
            continue
        assert row['screening_complete'] and row['checks']['source_sha256']==digest
        assert row['start_seconds']>=0 and row['end_seconds']<=row['original_duration_seconds']+.001
        with wave.open(str(ROOT/row['audio'])) as f:
            assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
            duration=f.getnframes()/16000
            assert abs(duration-row['duration_seconds'])<.0001
            assert abs(duration-(row['end_seconds']-row['start_seconds']))<.0001
            values=array('h',f.readframes(f.getnframes()))
            assert values
            peak=max(abs(v) for v in values)/32768
            assert peak<=.708
            max_peak=max(max_peak,peak)
            durations.append(duration);checked+=1
    assert set(p.name for p in (ROOT/'audio').glob('*.wav'))=={Path(r['audio']).name for r in prepared}
    assert abs(sum(durations)/60-summary['prepared_minutes'])<.01
    strict=[r for r in rows if r['transcript_agreement_subset']]
    assert len(strict)==summary['agreement_files']
    assert all(r['checks']['normalized_word_agreement'] for r in strict)
    segment_root=ROOT/'segments'
    segment_summary=json.loads((segment_root/'summary.json').read_text())
    assert segment_summary['complete']
    segments=[json.loads(s) for s in (segment_root/'manifest.jsonl').read_text(encoding='utf-8').splitlines()]
    parents={r['clip_id']:r for r in prepared}
    intervals={}
    for row in segments:
        parent=parents[row['parent_clip_id']]
        assert row['participant_id']==parent['participant_id']
        assert row['source_sha256']==parent['source_sha256']
        assert 2.9999<=row['duration_seconds']<=15.301
        left=round(row['parent_start_seconds']*16000)
        right=round(row['parent_end_seconds']*16000)
        with wave.open(str(ROOT/parent['audio'])) as f:
            assert 0<=left<right<=f.getnframes()
            f.setpos(left);expected=f.readframes(right-left)
        with wave.open(str(segment_root/row['audio'])) as f:
            assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
            assert f.getnframes()==right-left
            assert f.readframes(f.getnframes())==expected
        assert abs(row['source_start_seconds']-parent['start_seconds']-left/16000)<.0001
        intervals.setdefault(row['parent_clip_id'],[]).append((left,right))
    for spans in intervals.values():
        spans.sort()
        assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    assert len(segments)==segment_summary['clips']
    assert set(p.name for p in (segment_root/'audio').glob('*.wav'))=={Path(r['audio']).name for r in segments}
    class AudioLinks(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            if tag=='audio':self.links.append(dict(attrs)['src'])
    parser=AudioLinks();parser.feed((ROOT/'review.html').read_text(encoding='utf-8'))
    assert all((ROOT/link).is_file() for link in parser.links)
    report=dict(status='PASS',original_files_verified=len(originals),wav_files_decoded=checked,
        word_agreement_segments_verified=len(segments),segment_samples_match_parent_audio=True,
        total_wav_files_checked=checked+len(segments),
        duplicate_originals=sum('duplicate' in x for r in rows for x in r['excluded_reasons']),
        max_output_peak=round(max_peak,6),playback_links_verified=len(parser.links),
        no_orphan_audio=True,human_verified_transcripts=0,human_pronunciation_labels=0,
        original_hashes=originals,
        note='Checks file integrity and provenance, not transcription correctness, participant identity or pronunciation quality.')
    (ROOT/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    inventory=[]
    for row in rows:
        duration=row.get('original_duration_seconds')
        if duration is None and row.get('duplicate_of'):
            duration=by_id[row['duplicate_of']].get('original_duration_seconds')
        inventory.append(dict(source=row['source'],participant_id=row['participant_id'],
            source_sha256=row['source_sha256'],original_duration_seconds=duration,
            status=row['status'],decoder=row.get('decoder'),duplicate_of=row.get('duplicate_of'),
            decoder_recovery_used='decoder_recovery_used' in row['flags'],
            decoder_messages=row.get('decoder_messages'),excluded_reasons=row['excluded_reasons']))
    final_inventory=dict(original_files=len(rows),declared_participants=summary['declared_participants'],
        decoded_original_minutes_including_duplicates=round(sum(r['original_duration_seconds'] or 0 for r in inventory)/60,2),
        recovered_files=sum(r['decoder_recovery_used'] for r in inventory),files=inventory,
        note='inventory_initial.json records the first strict-decoder scan. This inventory reflects completed recovery and deduplication.')
    (ROOT/'inventory.json').write_text(json.dumps(final_inventory,indent=2),encoding='utf-8')
    annotations=[dict(clip_id=r['clip_id'],participant_id=r['participant_id'],audio=r['audio'],
        automatic_transcript=r['transcript'],cross_transcript=r['checks']['cross_asr']['text'],
        verified_transcript=None,intended_text=None,phoneme_errors=None,pronunciation_score=None,
        reviewer_id=None,review_status='pending') for r in prepared]
    (ROOT/'annotation_template.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in annotations),encoding='utf-8')
    segment_annotations=[dict(clip_id=r['clip_id'],participant_id=r['participant_id'],
        audio=r['audio'],parent_clip_id=r['parent_clip_id'],automatic_transcript=r['transcript'],
        verified_transcript=None,intended_text=None,phoneme_errors=None,pronunciation_score=None,
        reviewer_id=None,review_status='pending') for r in segments]
    (segment_root/'annotation_template.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in segment_annotations),encoding='utf-8')
    lines=['# Vietnamese learner audio: preparation results','','## Quantity','',
        f'- Original recordings: **{len(rows)}** across **{summary["declared_participants"]} supplied participant IDs**.',
        f'- Prepared, unique WAV recordings: **{len(prepared)}**, totaling **{summary["prepared_minutes"]} minutes**.',
        f'- Excluded original files: **{summary["excluded_files"]}**; reasons are in `manifest_all.jsonl`.',
        f'- Transcript-agreement subset: **{len(strict)} recordings / {summary["agreement_minutes"]} minutes**.',
        f'- Shorter aligned word-agreement sections: **{len(segments)} clips / {segment_summary["minutes"]} minutes**, across **{segment_summary["declared_participants"]} supplied IDs**.',
        '- Participant IDs come from folders. They are not independently verified identities.','',
        '| Participant | Original files | Unique prepared files | Minutes | Whole-file agreement | Word-matched sections |',
        '|---|---:|---:|---:|---:|---:|']
    for p in summary['participants']:
        count=sum(r['participant_id']==p['participant_id'] for r in segments)
        lines.append(f'| {p["participant_id"]} | {p["original_files"]} | {p["prepared_files"]} | {p["prepared_minutes"]} | {p["agreement_files"]} | {count} |')
    lines+=['','## Processing and quality findings','',
        '- Originals are unchanged; their SHA-256 hashes were checked.',
        '- Audio is decoded to 16 kHz mono PCM-16 WAV, with peak normalization capped at +12 dB.',
        '- Only outer silence is trimmed. Pauses, hesitations, accent and learner errors are preserved.',
        '- MP3s that require FFmpeg recovery retain decoder warnings; damaged packets may have been dropped.',
        '- Recovered MP3 timestamps refer to the decoded recovered stream; dropped packets can shift timing relative to the damaged compressed original.',
        '- ASR: Whisper small multilingual, cross-checked with Whisper base.en. English is the intended task; high-confidence other-language detections are flagged and transcribed in the detected language.',
        '- Overlap: local pyannote segmentation powerset model; music/applause: CED-tiny. These are fallible flags, not human listening.',
        '- No voice identity matching is performed. Folder participant IDs are preserved.',
        '- Low ASR confidence does not exclude learner recordings from the broad dataset. Otherwise difficult pronunciation would be systematically removed.','',
        '| Review flag | Recordings |','|---|---:|']
    lines.extend(f'| {flag} | {count} |' for flag,count in sorted(summary['flags'].items()))
    lines+=['','## Which files to use','',
        '- `manifest.jsonl`: all prepared unique learner recordings, including flagged and difficult speech.',
        '- `manifest_agreement.jsonl`: an exploratory subset with matching normalized words and no specified music/overlap/recovery flags. It is biased toward easier speech and is not a representative evaluation set.',
        '- `segments/manifest.jsonl` and `segments/review.html`: shorter word-matched sections with consistent timestamps. These are exploratory and may be sentence fragments; they do not replace full learner recordings.',
        '- Sections reuse the prepared recordings. Their minutes are a subset, not additional independent audio; keep a parent recording and all its sections in the same split.',
        '- `manifest_all.jsonl`: includes duplicates, exclusions, recovery information, source timestamps and original hashes.',
        '- `audio/`: processed WAVs. `review.html`: playback, both ASR transcripts and review flags.',
        '- `annotation_template.jsonl`: empty human-review fields; no pronunciation scores are invented.',
        '- `audit.json`: file-integrity results.','',
        '## MVP interpretation','',
        'This collection supports an initial Vietnamese learner pilot and pipeline development. Keep it out of training if using it to evaluate the model. Do not randomly split clips from one participant across training and test sets.',
        'Human-verified transcripts and independent pronunciation judgments are still required to measure scoring accuracy. Automatic ASR agreement does not supply those judgments. A transcript describes words; it does not label phoneme correctness.',
        'Do not treat flagged learner speech as incorrect pronunciation, or unflagged speech as correct. Source permissions and the supplied participant grouping are not independently verified.','',
        '## Model references','',
        '- https://huggingface.co/Systran/faster-whisper-small',
        '- https://huggingface.co/Systran/faster-whisper-base.en',
        '- https://huggingface.co/pyannote/segmentation-3.0',
        '- https://huggingface.co/k2-fsa/sherpa-onnx-ced-tiny-audio-tagging-2024-04-19']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='original_hashes'},indent=2))


if __name__=='__main__':main()
