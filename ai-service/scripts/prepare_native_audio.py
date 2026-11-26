"""Create review candidates, not labeled/approved speech, from local recordings.

Run with Python 3.14 and PYTHONPATH=data/audio-tools from the repository root.
Dependencies: numpy, soundfile, imageio-ffmpeg, webrtcvad-wheels.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import subprocess

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import webrtcvad

RATE = 16000
FRAME = 480  # WebRTC VAD requires 10/20/30 ms frames; use 30 ms.


def regions(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=False)
    clips_dir = output / 'clips'
    clips_dir.mkdir()
    vad = webrtcvad.Vad(2)
    records, sources = [], []
    for number, path in enumerate(sorted(source.glob('*.mp3')), 1):
        source_id = f'source_{number:02d}'
        result = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(path),
             '-vn', '-ac', '1', '-ar', str(RATE), '-f', 'f32le', 'pipe:1'],
            capture_output=True, check=True,
        )
        audio = np.frombuffer(result.stdout, dtype='<f4').copy()
        if not len(audio) or not np.isfinite(audio).all():
            raise ValueError(f'Empty/non-finite decoded audio: {path}')
        count = len(audio) // FRAME
        frames = audio[:count * FRAME].reshape(count, FRAME)
        rms = np.sqrt(np.mean(frames ** 2, axis=1))
        pcm = (np.clip(frames, -1, 1) * 32767).astype('<i2')
        voiced = np.array([vad.is_speech(frame.tobytes(), RATE) for frame in pcm])
        # Join pauses shorter than 450 ms, then split only at longer pauses.
        joined = voiced.copy()
        for a, b in regions(~voiced):
            if a > 0 and b < count and b - a <= 15:
                joined[a:b] = True
        chunks = []
        for a, b in regions(joined):
            # Long continuous passages: seek a low-energy point near the end.
            # Such boundaries require manual review; this is not sentence detection.
            forced_start = False
            while (b - a) * .03 > 20:
                lo, hi = a + 400, min(b, a + 650)  # 12--19.5 seconds
                smooth = np.convolve(rms, np.ones(5) / 5, mode='same')
                cut = lo + int(np.argmin(smooth[lo:hi]))
                chunks.append((a, cut, True, forced_start))
                a, forced_start = cut, True
            chunks.append((a, b, False, forced_start))
        accepted = []
        for a, b, forced_end, forced_start in chunks:
            start = max(0, a * FRAME - (0 if forced_start else 1920))
            end = min(len(audio), b * FRAME + (0 if forced_end else 1920))
            chunk = audio[start:end]
            seconds = len(chunk) / RATE
            ratio = float(np.mean(voiced[a:b]))
            db = 20 * math.log10(max(float(np.sqrt(np.mean(chunk ** 2))), 1e-10))
            clipped = float(np.mean(np.abs(chunk) >= .999))
            if not (3 <= seconds <= 20.5) or ratio < .55 or db < -42 or clipped > .01:
                continue
            peak = float(np.max(np.abs(chunk)))
            gain = min(10 ** (12 / 20), 10 ** (-3 / 20) / max(peak, 1e-10))
            accepted.append(dict(start=start, end=end, seconds=seconds,
                vad_speech_ratio=round(ratio, 4), rms_dbfs=round(db, 2),
                original_peak=round(peak, 5), clipping_fraction=round(clipped, 6),
                gain_db=round(20 * math.log10(gain), 2), gain=gain,
                forced_boundary=bool(forced_start or forced_end)))
        # Spread a <=5 minute review shortlist across each source, not each speaker.
        order = range(len(accepted))
        shortlist, total = set(), 0
        # Rank by low clipping and reliable VAD; ties favor natural boundaries.
        ranked = sorted(order, key=lambda i: (accepted[i]['forced_boundary'],
            accepted[i]['clipping_fraction'], -accepted[i]['vad_speech_ratio']))
        for i in ranked:
            if total + accepted[i]['seconds'] <= 300:
                shortlist.add(int(i))
                total += accepted[i]['seconds']
        for i, info in enumerate(accepted):
            clip_id = f'{source_id}_{i+1:04d}'
            rel = f'clips/{clip_id}.wav'
            sf.write(output / rel, audio[info['start']:info['end']] * info['gain'],
                     RATE, subtype='PCM_16')
            record = {k: v for k, v in info.items() if k not in ('gain', 'start', 'end')}
            record.update(clip_id=clip_id, audio=rel, source_id=source_id,
                source_file=path.name, source_start_seconds=round(info['start']/RATE, 3),
                source_end_seconds=round(info['end']/RATE, 3),
                shortlist=i in shortlist, review_status='pending', speaker_id=None,
                transcript=None, accent=None, permission_status='unverified',
                source_url=None, pronunciation_label=None)
            records.append(record)
        with path.open('rb') as original:
            checksum = hashlib.file_digest(original, 'sha256').hexdigest()
        source_info = dict(source_id=source_id, source_file=path.name,
            sha256=checksum,
            duration_seconds=round(len(audio)/RATE, 3), candidates=len(accepted),
            candidate_seconds=round(sum(x['seconds'] for x in accepted), 2),
            shortlisted_seconds=round(total, 2),
            decode_messages=result.stderr.decode(errors='replace')[:2000])
        sources.append(source_info)
        print(json.dumps(source_info), flush=True)
    with (output/'manifest.jsonl').open('w', encoding='utf-8') as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False)+'\n')
    summary = dict(sources=sources, source_count=len(sources),
        candidate_count=len(records), candidate_minutes=round(sum(r['seconds'] for r in records)/60, 2),
        shortlist_count=sum(r['shortlist'] for r in records),
        shortlist_minutes=round(sum(r['seconds'] for r in records if r['shortlist'])/60, 2),
        approved_count=0, sample_rate=RATE, channels=1, sample_format='PCM_16',
        limitations=['VAD is not a music, language, overlap, or speaker-identity detector.',
            'Clips have not been listened to or transcribed.',
            'Shortlists are per source, not per person. Speaker IDs must be reviewed.',
            'Forced boundaries may divide words; check and adjust before evaluation.',
            'No pronunciation labels or reuse permissions are inferred.'])
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    cards = []
    for src in sources:
        items=[]
        for row in records:
            if row['source_id'] != src['source_id'] or not row['shortlist']:
                continue
            items.append(f'<article><b>{row["clip_id"]}</b> '
                f'{row["source_start_seconds"]:.1f}–{row["source_end_seconds"]:.1f}s '
                f'{" · Check cut boundary" if row["forced_boundary"] else ""}'
                f'<audio controls preload="none" src="{row["audio"]}"></audio></article>')
        cards.append(f'<section><h2>{html.escape(src["source_file"])}</h2>{"".join(items)}</section>')
    (output/'review.html').write_text('<!doctype html><meta charset="utf-8">'
        '<title>Native audio review</title><style>body{font:16px system-ui;max-width:960px;'
        'margin:40px auto;background:#f8fafc;color:#172033}article{padding:12px;background:white;'
        'margin:8px 0;border:1px solid #ddd}audio{display:block;width:100%;margin-top:8px}</style>'
        '<h1>Native audio: candidate shortlist</h1><p>Not approved evaluation data. '
        'Listen for music, overlap, bad cuts, and unintelligible speech. Record speaker IDs, '
        'verified transcripts, and permission information in manifest.jsonl. '
        'Source numbers identify files, not people. No automatic accent or identity verification.</p>'
        + ''.join(cards), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='sources'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/collecting/native'))
    parser.add_argument('--output', type=Path, default=Path('data/processed/native_v1'))
    args = parser.parse_args()
    if not args.source.is_dir() or not list(args.source.glob('*.mp3')):
        parser.error('Source must contain MP3 files')
    prepare(args.source, args.output)
