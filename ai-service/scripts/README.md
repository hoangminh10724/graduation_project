# Native recording preparation

## Current General American expansion (21 November 2026)

The live demo now covers 41 core practice entries and six additional r-vowel
combinations. See [the current scope](../../docs/AMERICAN_SOUND_EXPANSION.md).
Older ten-sound experiments below describe historical checkpoints.

From the repository root, with the local demo running:

```powershell
& data/phoneme-env/Scripts/python.exe ai-service/scripts/audit_new_learner_batch.py
& data/phoneme-env/Scripts/python.exe ai-service/scripts/prepare_american_audio_checks.py
& data/phoneme-env/Scripts/python.exe ai-service/scripts/check_american_expansion.py
```

The batch audit preserves originals and retains duplicate provenance. Preparation
outputs already exist; the audit rejects reuse if the source batch has changed.
Crop preparation
uses local Whisper to obtain approximate word boundaries from seven representative
recordings, not human pronunciation labels. Integration checks use the existing
training partition and these crops; outcomes are not recognition accuracy. Use
a new `--output` directory for another integration run. The earlier
`check_ten_sound_mvp.py` remains a historical ten-prompt subset.

From the repository root, using Python 3.14 and PowerShell:

```powershell
python -m pip install --target data/audio-tools -r ai-service/scripts/requirements-audio.txt
$env:PYTHONPATH = (Resolve-Path data/audio-tools).Path
python ai-service/scripts/prepare_native_audio.py --output data/processed/native_refined
```

The output directory must not already exist. The MP3 originals are read-only inputs.
Dependencies and generated audio live under `data/`, which the repository ignores.

## Output

- `clips/`: 16 kHz mono PCM-16 WAV candidate clips, approximately 3--20 seconds.
- `manifest.jsonl`: source timestamps, signal checks, processing gain, and review fields.
- `summary.json`: per-source counts, source SHA-256 hashes, and limitations.
- `review.html`: local playback page for a shortlist of up to five minutes per source.

The preparation decodes MP3, uses WebRTC voice activity detection, joins short
pauses, and rejects short/long, mostly non-speech, very quiet, or heavily clipped
segments. Long passages are cut at low-energy points; these cuts are flagged.
Peak normalization targets -3 dBFS with amplification capped at +12 dB.
It does not denoise, compress dynamics, alter pitch, or time-stretch speech.

## Review required

Candidates are not approved or labeled evaluation data. VAD can accept music,
overlapping voices, applause, and unintelligible speech. Source IDs identify
recordings, **not people**. The shortlist does not establish five minutes for
any individual speaker. No native-language or American-accent inference is made.

Before evaluation:

1. Listen to candidates in `review.html`; discard music, overlap, bad boundaries,
   incomplete utterances, and unintelligible speech. Adjust boundaries from originals
   when needed. Review remaining candidates if the shortlist does not suffice.
2. Assign stable speaker IDs across all recordings. Exclude unresolved identities;
   keep a person's clips together when forming data splits.
3. Fill in verified transcripts, accent metadata, source URLs, and permission/license
   information in the manifest. `null` means unknown, not approved.
4. Obtain human pronunciation judgments. Never assign a perfect score based on
   native-speaker status. Keep the comparison set out of training.

Automated ASR, diarization, music/overlap detection, and human listening are not
implemented by this script. Approved counts remain zero until review occurs.

## Full-source machine screening

`finalize_native_audio.py` is a separate second pass over **all originals**, not
just the shortlist. It uses Python 3.12 packages under `data/speech-tools` and local
models under `data/models/native-preparation`. In PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path data/speech-tools).Path
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -u ai-service/scripts/finalize_native_audio.py
```

Tested package versions are listed in `requirements-speech.txt`. On Windows the
script explicitly loads the matching ONNX Runtime DLL before Sherpa to avoid
resolving an older system DLL. The decoder uses PyAV's current resampling API.

Local models and original distribution locations:

- Whisper base.en: https://huggingface.co/Systran/faster-whisper-base.en
- Pyannote segmentation ONNX: https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models
- NeMo English TitaNet-small embeddings: https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models
- CED-tiny int8 audio tagging: https://huggingface.co/k2-fsa/sherpa-onnx-ced-tiny-audio-tagging-2024-04-19

The second pass writes `data/processed/native_final/`:

- `manifest.jsonl`, `clips/`, `transcripts.txt`: clips passing automatic screening.
- `manifest_all.jsonl`, `excluded/`: all drafted clips and exclusion reasons.
- `cache/`: full-source word-timestamped ASR and estimated speaker turns, allowing
  resumption without repeating successful transcription or diarization.
- `summary.json`: completeness, retained/excluded totals and source-local speakers.
- `review.html`: playback and automatic transcripts, with excluded clips hidden
  by default and a toggle to display them.

Speaker boundaries are estimated with pyannote segmentation and TitaNet embedding
clustering; the number of speakers is normally inferred. The Vanessa conversation
uses two speakers, based on its spoken introduction describing the presenter and
her husband; this override is tied to the exact original file SHA-256. ASR
word timestamps prevent arbitrary cuts inside recognized words. The screen
rejects unresolved/mixed speakers, detected overlap, low ASR confidence, extreme
duration, suspected repetition, detected music/applause, clipping and quiet audio.
CED audio-event scores are heuristics, not calibrated guarantees. Noise is not
removed by a generative enhancement model, preserving original pronunciation.

**Important:** `machine_screened` means suitable for exploratory comparisons,
not human-verified transcription, speaker identity, accent/native status,
license approval, or ground-truth pronunciation scores. The same person can have
different source-local IDs across recordings. Keep the whole native set out of
training; do not use local IDs to claim a unique-person count or a speaker-disjoint
cross-source split. ASR agreement with model scores is not independent human
validation. Source and pronunciation review remain distinct from audio processing.

## Stronger transcript cross-check and integrity audit

`check_native_transcripts.py` reads every completed source checkpoint, transcribes
every machine-screened clip with a local Whisper small.en model at
`data/models/native-preparation/whisper-small.en`, and compares normalized words
against base.en. It can run while the full-source pipeline is still processing:

```powershell
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -u ai-service/scripts/check_native_transcripts.py
```

The `data/processed/native_screened/` directory contains:

- `clips/`, `manifest.jsonl`, `transcripts.txt`: the strict subset with exact
  normalized word agreement and good second-pass confidence.
- `transcript_checks.json`: both model transcripts for every checked clip,
  including disagreements and low-confidence matches.
- `review.html`: playback of the strict subset and all flagged comparisons.
- `summary.json`: totals and explicit human-verification/label counts (zero).
- `cache/`: per-clip results for resumption.

Source material is not uploaded to an external transcription API. Both Whisper
models operate locally. Related model agreement is a consistency check, not
independent validation, and can retain common errors. Capitalization/punctuation
differences are ignored, but numbers, contractions and word differences are not
silently rewritten. The strict subset can be small; do not relax acceptance just
to achieve a person/minute target.

After both pipelines finish:

```powershell
python ai-service/scripts/audit_native_export.py
```

The audit decodes all generated WAVs, checks their format/duration/peak, validates
manifest counts and strict-subset copies, detects orphan accepted files, and
verifies that original source hashes are unchanged. Its `audit.json` is a
technical-integrity report, not certification of labels, speech quality or rights.

## Vietnamese learner recordings

`prepare_vietnamese_audio.py` handles the existing `data/collecting/vietnamese/P*/`
folders and mixed OGG/MP3/M4A inputs. It preserves supplied participant IDs rather
than inventing identities from voice clustering. Run the two stages in separate
Python 3.12 processes with `PYTHONPATH=data/speech-tools`:

```powershell
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -u ai-service/scripts/prepare_vietnamese_audio.py primary
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -u ai-service/scripts/prepare_vietnamese_audio.py check
```

The check stage can watch primary checkpoints while the first stage is running.
Checkpoints are atomic and resumable. Originals remain read-only. This pipeline
uses the existing local models plus multilingual Whisper small under
`data/models/vietnamese-preparation/whisper-small`, downloaded from
https://huggingface.co/Systran/faster-whisper-small.

The primary stage deduplicates originals/decoded PCM, recovers decodable MP3
frames with FFmpeg if PyAV fails (and records recovery warnings), trims only outer
silence with Silero VAD, normalizes/exports WAVs, detects likely language and
generates word-timestamped transcripts. Internal pauses, hesitation and accent
are preserved. Existing 16--39 second recordings are not arbitrarily chopped.

The second stage uses Whisper base.en for transcript comparisons, CED-tiny for
music/applause flags and direct pyannote powerset inference for overlap flags.
The 10-second segmentation model's seven output classes are documented at
https://huggingface.co/pyannote/segmentation-3.0. Overlap/multiple-speaker flags
are fallible and do not change the supplied participant ID.

**Learner speech is treated differently from the native reference:** low ASR
confidence is a transcript-review signal, never a reason to erase difficult
pronunciation from the broad learner export. Except for duplicates or processing
failures, recordings are retained with flags. Matching transcriptions are not
pronunciation labels and preferentially select easier speech.

When both stages finish, refresh the final export and run:

```powershell
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' ai-service/scripts/prepare_vietnamese_audio.py export
python ai-service/scripts/segment_vietnamese_audio.py
python ai-service/scripts/audit_vietnamese_export.py
```

`data/processed/vietnamese/` contains the broad unique WAVs, both transcripts,
review flags, per-participant counts, recovery logs, original hashes, manifests,
playback page, an empty human-annotation template and integrity report.
`segments/` adds shorter whole-word sections where both recognizers agree and
their timestamps differ by at most 0.65 seconds. It excludes specified quality
flags and keeps each segment linked to its original participant and recording.
These sections remain unverified, may be sentence fragments, and are not a
representative benchmark of learner errors. Do not randomly split segments from
one participant across training and test sets.

## Human-score agreement experiment

`benchmark_pronunciation_baseline.py` fits a lightweight GOP-feature scorer and
evaluates it against existing speechocean762 expert ratings. It uses the GOPT
authors' published intermediate LibriSpeech/Kaldi acoustic features, documented
at https://github.com/YuanGongND/gopt/tree/master/data, stored under
`data/baselines/gopt/`. Archive/source hashes are recorded alongside the download.

```powershell
$env:PYTHONPATH = (Resolve-Path data/speech-tools).Path
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -u ai-service/scripts/benchmark_pronunciation_baseline.py
```

Dependencies are in `requirements-benchmark.txt`. The experiment cross-checks all
94,445 feature rows against original phone positions and human labels. Model
fitting/scaling uses only 2,000 training utterances; ridge regularization is chosen
by RMSE on 500 validation utterances. The official 2,500-utterance test set is
untouched during selection. Controls include training-mean and phone-identity-only
predictors. Correlation uncertainty is bootstrapped by speaker rather than phone.

`data/results/pronunciation_baseline/` contains the report, numerical metrics,
actual held-out phone/sentence predictions, and plot. Model weights/configuration
are under `data/models/gop_linear_baseline/`. Scores use the original human 0--2
phone scale; sentence aggregation is explicitly a heuristic, not prosody scoring.

This experiment **does not call `/assess`**, which currently returns HTTP 501, and
does not implement the planned wav2vec2 raw-audio frontend. Published Kaldi
features provide a measured reference baseline, not validation of WordSpeak's
future production pipeline. It establishes no accuracy on Vietnamese/native
comparison clips without independent ratings for those clips. Ground-truth
ratings are never synthesized from group membership or ASR confidence.

## Raw-audio phoneme pilot (first articulation MVP checkpoint)

This is a separate experimental CLI, not a replacement for `/assess`. It uses
the Apache-2.0 `facebook/wav2vec2-lv-60-espeak-cv-ft` model to predict phonetic
labels directly from audio. The upstream model card specifies 16 kHz input:
https://huggingface.co/facebook/wav2vec2-lv-60-espeak-cv-ft

Use an isolated Python 3.12 environment; existing preparation tools are unchanged:

```powershell
& 'C:/Users/ADMIN/AppData/Local/Programs/Python/Python312/python.exe' -m venv data/phoneme-env
& data/phoneme-env/Scripts/python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
& data/phoneme-env/Scripts/python.exe -m pip install -r ai-service/scripts/requirements-phoneme.txt
& data/phoneme-env/Scripts/python.exe ai-service/scripts/download_phoneme_model.py
& data/phoneme-env/Scripts/python.exe ai-service/scripts/run_phoneme_pilot.py --manifest data/prepared/validation.jsonl --manifest data/prepared/comparison_vietnamese.jsonl --manifest data/prepared/comparison_native.jsonl --per-manifest 2
```

Only public model files are downloaded; audio inference is local. The downloader
pins the upstream revision and records source URLs, sizes and SHA-256 hashes under
`data/models/phoneme-recognition/provenance.json`. The checkpoint is roughly 1.3 GB.
The pilot uses short prepared mono WAVs, limits CPU threads, and does not train.
It selects recordings by a fixed ID hash and distinct supplied speaker IDs; it
does not select by expert scores. Native identities remain source-local estimates.
The held-out `test.jsonl` is not used for this initial experiment.

Results go to `data/results/phoneme_pilot/` (use a new `--output` for another run):

- `predictions.jsonl`: full predicted phone sequences, approximate CTC spans,
  raw peak-probability diagnostics, reference transcripts marked review-only.
- `human_review.jsonl`: empty actual-heard-phone/boundary annotations, without
  model predictions. A reviewer should listen and fill these independently.
- `review.html`: local playback page with predictions hidden; annotation instructions
  point to the JSONL template. The playback page itself does not save annotations.
- `summary.json`: provenance, selection and status; accuracy is null until measured.

The recognizer never receives the reference text, and it does not force outputs
into the ten proposed sounds. Only exact IPA matches are tagged with the proposed
ARPAbet target; other phones remain visible. Model frame probabilities are not
calibrated accuracy or pronunciation scores. Span timestamps are not verified
phone boundaries. No mouth position, error diagnosis, or articulation animation
is inferred by this checkpoint. Canonical corpus labels are not actual-heard
phonetic transcriptions of learner errors.

Next gates: independent listening review, phoneme error analysis and target-phone
coverage; then a small prompted-word demo with reviewed reference diagrams and
an uncertainty state. The engineering work can proceed before that review, but
claims of recognition accuracy and pedagogical correctness depend on it.

Decoder checks (no model download needed):

```powershell
Push-Location ai-service
& ../data/phoneme-env/Scripts/python.exe -m pytest tests/test_phoneme_recognition.py -q
Pop-Location
```

## Teacher-feedback model investigation

`investigate_teacher_feedback.py` runs the pinned local phoneme recognizer on all
12 parent recordings and 55 candidate passages from the two imported feedback
batches. Words and teacher comments are review metadata, never acoustic-model
inputs. The three unresolved word locations remain unresolved rather than being
assigned invented timestamps or errors.

```powershell
& data/phoneme-env/Scripts/python.exe -u ai-service/scripts/investigate_teacher_feedback.py
```

Outputs are under `data/results/teacher_feedback_investigation/`: raw parent/crop
predictions, per-candidate context comparisons, six predeclared positional probes,
source/model/runtime hashes, a report and local playback. Successful recordings
are checkpointed. For an interrupted run, `--resume` requires unchanged source,
model and implementation configuration and verifies audio hashes. For a changed
experiment, use a new `--output`; keep prior results intact.

Word-window phone sequences are selected by approximate CTC-event midpoints in
ASR word windows. Full-recording and crop outputs are compared at 0, 80 and
200 ms window padding. A probe is context-stable only when all six variants
produce the same resolvable pattern. This is a sensitivity check, not calibrated
confidence or classification accuracy. Positional probes prevent, for example,
the final /s/ in `mistakes` from hiding an omitted internal /s/ before /t/.

Teacher reports are sparse references, not exhaustive actual-heard transcripts.
Context-stable disagreement calls for examination; it does not adjudicate whether
the teacher or recognizer is correct. No training, threshold fitting, ten-class
accuracy, model selection or measured tongue-position evaluation is performed.
Vowel-duration and stress coaching are not converted into arbitrary exact-phone
error labels. Keep the original prediction-hidden pages for independent review;
the investigation page intentionally reveals model predictions.

Run meaningful decoder/probe checks without a model download:

```powershell
Push-Location ai-service
& ../data/phoneme-env/Scripts/python.exe -m pytest tests/test_phoneme_recognition.py tests/test_feedback_probes.py -q
Pop-Location
```
