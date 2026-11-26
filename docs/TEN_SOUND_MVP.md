# WordSpeak ten-sound MVP

Current local app: **http://127.0.0.1:8013/demo**.

Double-click `OPEN_WORDSPEAK.url` in the project root to open it. If the server
is offline, double-click `START_WORDSPEAK.cmd`; keep its terminal open.
Earlier prototype ports 8011/8012 are obsolete. The current build identifies
itself as `ten-sound-mvp-v2` and shows ten sound chips.

## Implemented scope

| Category | Target | Main word |
|---|---|---|
| Vowel | /iː/ | seat |
| Vowel | /ɪ/ | sit |
| Vowel | /ɛ/ | bed |
| Vowel | /æ/ | bad |
| Vowel | /uː/ | food |
| Consonant | /p/ | pen |
| Consonant | /t/ | ten |
| Consonant | /k/ | key |
| Consonant | /s/ | see |
| Consonant | /ʃ/ | she |

Additional practice words and contrast guides do not expand the primary target
count. The SVGs are original schematic references, not measured speaker anatomy.

## Use the app

1. Choose a sound chip or a word from the grouped selector.
2. Leave **Just the word** selected and say the word once, with a short pause
   before and after it. PCM recording stops after three seconds. Use **Word inside
   the suggested phrase** for existing contextual passages.
   Alternatively, upload audio and prepare a 0.25–4 second selection containing
   the complete word and a little surrounding speech.
3. Listen and choose **Analyze word**. The first valid request loads the model.
4. Read **Sound difference and adjustment**. It lists the likely sound, feature
   differences (tongue height/region/lips or consonant place/airflow/voicing) and
   actions to try. The starting diagram is the category reference for the likely
   sound, not a measurement of your original tongue position. Weak candidates
   appear explicitly as tentative; their suggestions are conditional.
5. **Save this result** exports JSON, without audio. It does not create a training label.

### Microphone volume

The recorder requests automatic gain control off and applies no attenuation at
the default **1×** input boost. If playback is quiet, set **Microphone input boost**
to **2×** or **4×**. It applies to the current microphone clip as well as future
recordings. After adjusting, wait for **Recording volume updated**, then press
Play. The app rebuilds the WAV from the original unboosted recording, so changing
8× back to 1× restores its original level without compounding gains. Re-analyze
after changing volume; previous predictions are cleared. Uploaded files retain
their supplied level. Boost can also amplify background noise.

The level meter shows captured peaks and warns about low input or clipping.
Lower boost if it reports **Too loud**. The microphone name is shown after access,
so you can check which device is being captured. Choose another input with the
**Microphone** selector and record again to use it. **Save audio** downloads the
exact prepared WAV used for playback and analysis. The original and boosted
peaks are shown separately. If the recorded peak rises but browser playback stays
quiet, use the saved WAV in another player to distinguish recording level from
browser/system playback volume. If input remains low at higher boost, check that
device's system input level and microphone placement. The
muted monitoring output only prevents live feedback; it is downstream of capture.

The four development examples replay stored predictions and teacher comments in
an explicit cached mode. `mistakes` retains disagreement and `improvements`
retains unresolved timing. They are never represented as fresh inference.

### Visual discovery practice

Select a sound, read one short cue, then choose **Try word**. It records once and
automatically requests analysis. After feedback, **Try again** starts another
attempt. Supported differences produce just one adjustment at a time; uncertain
outputs invite a fresh recording without inventing a correction. The manual
**Record word** / **Analyze word** path remains available.

**More help (optional)** opens the longer **Find, Move, Feel, Use** activity with
**Lips, Tongue, Jaw, Voice** cues. **Watch movement** opens and replays that example.
Stops use closure/release examples; phone layouts stack the two views and
reduced-motion preferences are respected. No activity checklist is mandatory.

**Sound reference** is open by default and shows the front lip shape alongside
the inside tongue view. It remains visible when changing words or after analysis.
Lip spreading, rounding and opening have separate illustration controls: seat
shows gentle outward arrows, sit has a less-spread shape, and food is rounded.
This is a broad practice reference; students should not force an exaggerated grin.

After a supported sound prediction, both the likely-sound reference and the
target reference remain visible, including their word examples. /ɪ/ (sit) and
/iː/ (seat) use different tongue and lip references. Model /i/ versus target /iː/
keeps both cards with the same shape and an explicit unassessed-length explanation;
unmarked /i/ is not silently treated as /ɪ/. Detailed feature
tables and model diagnostics are optional. Students may collapse the reference
manually, while the longer discovery activities remain closed by default.

These are original practice activities informed by Adrian Underhill's physical
teaching approach. Each links to its reading source and official demonstrations.
The example's starting sound is a teaching anchor, not a diagnosis of the learner.
Model-derived comparisons remain separately labeled. Study notes and sources:
[UNDERHILL_REFERENCE.md](UNDERHILL_REFERENCE.md).

## Start, status and stop

From the project root:

```powershell
& data/phoneme-env/Scripts/python.exe -u ai-service/scripts/serve_demo.py --replace
& data/phoneme-env/Scripts/python.exe ai-service/scripts/serve_demo.py --status
& data/phoneme-env/Scripts/python.exe ai-service/scripts/serve_demo.py --stop
```

Run the first command in a separate terminal; Ctrl+C stops it. The launcher binds
only to loopback. A random local token and checked instance identity allow a
graceful restart of the owned service, without killing a remembered OS PID.
Runtime metadata is under `data/results/` and excluded from git; do not share its
stop token. The footer reports service online, model loading, inference, or ready.
There is no background training. Inference is serialized to bound memory use.

## Reproduce the environment

Tested: Python 3.12, Windows x64. Existing setup is under `data/phoneme-env`.

```powershell
py -3.12 -m venv data/phoneme-env
& data/phoneme-env/Scripts/python.exe -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
& data/phoneme-env/Scripts/python.exe -m pip install -r ai-service/scripts/requirements-demo-lock.txt
& data/phoneme-env/Scripts/python.exe ai-service/scripts/download_phoneme_model.py
& data/phoneme-env/Scripts/python.exe -u ai-service/scripts/serve_demo.py
```

The pinned model download is approximately 1.3 GB. `WORDSPEAK_PHONEME_MODEL` can
select another compatible local directory; the default is
`data/models/phoneme-recognition`. Models, recordings and datasets are excluded
from the source-only archive.

## Result meaning and limits

- The acoustic recognizer receives audio only. In word mode a subsequent matcher
  selects the single decoded vowel nucleus or initial consonant, without requiring
  neighboring sounds to match the target. Multiple nuclei or a missing onset
  produce an explanation and retry guidance. In context mode it uses surrounding
  phone anchors. The target never fills the observed label. Only the selected
  sound is compared; other sounds in the word are not graded.
- Missing or ambiguous anchors, weak evidence and unsupported multilingual
  labels produce uncertainty. Raw predictions remain visible.
- Unmarked /i/ and /u/ are not silently certified as long vowels. /e/ versus /ɛ/
  notation ambiguity remains flagged. CTC emission width is not vowel duration.
- `model_match` reports label compatibility, not expert-certified pronunciation.
  Numeric scores remain null. Guides require instructional review before use as
  validated teaching material. They are generic diagrams, not audio-derived anatomy.
- Legacy `/assess` now returns **501**, replacing the fabricated fixed score.
  `/demo/analyze` is the working experimental sound comparison endpoint.
- Microphone capture uses AudioWorklet PCM WAV without Opus/MP3 encoding. Files
  decode directly at 16 kHz, and PCM round trips preserve existing sample values.
  Uploads use temporary files removed after inference; they are not sent to an
  external transcription service or retained automatically for training.
- Managed inference enables offline model loading and blocks external Python
  socket connections. This process guard is not an operating-system firewall
  for unrelated applications or native dependencies.

Reference categories: [IPA](https://www.internationalphoneticassociation.org/IPAcharts/IPA_charts_EI/IPA_charts_EI.html),
[Sheffield](https://sheffield.ac.uk/linguistics/home/all-about-linguistics/about-website/branches-linguistics/phonetics/what-do-phoneticians-study/articulatory),
[PolyU](https://elc.polyu.edu.hk/sounds/lesson8.htm).

## Checks and evidence

```powershell
Push-Location ai-service
& ../data/phoneme-env/Scripts/python.exe -m pytest -q
Pop-Location
```

66 Python checks and PCM encoder checks passed. Browser checks cover all ten
reference cards/images, fresh vowel and consonant uploads, target changes without
rewriting the observed vowel, result export, uncertainty and mobile layout.
Microphone tests use file-backed simulated input and verify automatic stop and
track release; a physical microphone has not been validated.
Microphone gain checks in `data/results/microphone_level_checks/` use synthetic
file-backed input to verify actual WAV amplitude changes, low-level/clipping
warnings, track release and mobile layout; they do not test physical hardware.

The earlier v1 context-mode run in `data/results/ten_sound_mvp/` retains 24 deterministic real-audio requests covering
all ten categories from 22 existing training-partition participant IDs. Outcomes:
nine model-label matches, two different-label suggestions, thirteen abstentions.
These are **not** correct/incorrect labels or accuracy. No untouched corpus-test
data, confidence-based filtering, training or threshold tuning was used.

V2 word-mode checks and the updated browser report are under
`data/results/word_feedback_v2/`. These are development regression checks,
not an accuracy or error-severity benchmark.

`data/results/discovery_guides/` contains checks of all ten visual activities,
step/control changes, manual and replayed movement, closure/release, mobile layout
and reduced-motion behavior. Student learning outcomes have not been measured.

The feature scope is implemented. Recognition reliability remains unvalidated:
many inputs abstain, teacher labels are partial, and no measured mouth positions
are available. This is a development MVP, not an automatic pronunciation grader.
