# WordSpeak MVP handoff - 15 November 2026

## Delivered

The local MVP implements five vowel and five consonant targets, PCM recording,
upload/selection/playback, local acoustic inference, independent sound matching,
predicted/target reference diagrams, explicit uncertainty, teacher-example replay,
JSON export, service state and authenticated graceful startup/restart/stop.
Open `http://127.0.0.1:8013/demo`. See `docs/TEN_SOUND_MVP.md` for setup and targets.

V2 defaults to isolated-word input. It selects a decoded vowel nucleus or starting
consonant without requiring neighboring sounds to be correct, then presents a
feature-difference table and concrete practice adjustments. The likely starting
position is a sound-category reference hypothesis, never reconstructed anatomy.
Weak candidates are visible as tentative, with conditional guidance. Unsupported
sounds and ambiguous recordings still abstain with a specific explanation.

Microphone capture now includes a 1×–8× input-boost control, live peak meter,
post-recording level feedback, clipping warnings and the captured device name.
Default 1× preserves amplitude. Boost is applied directly to PCM samples and
rebuilds an existing microphone clip from its unboosted original. Changing 8× to
1× restores the original instead of compounding gains. The UI also includes an
input-device selector and exact prepared-WAV download. Both playback and
inference use the rebuilt clip; uploads remain at their supplied level. Versioned
module URLs and no-store demo responses prevent stale audio-control modules.

Visual discovery practice adds ten original activities informed by Adrian
Underhill's published approach: four physical controls, four short practice
steps, a manually controlled/replayed schematic movement, self-checks and source
links. These are teaching examples, separate from model predictions. See
`docs/UNDERHILL_REFERENCE.md` for the source study and adaptation limits.
The default flow is one cue and one-click recording/checking, with the reference
visible. Four-step exploration and feature tables are optional. A supported
prediction keeps both the likely-sound and target cards visible, with word
examples. Shared-shape labels such as /i/ versus /iː/ keep the same shape on both
cards and an explicit unassessed-length explanation; /i/ is not relabeled /ɪ/.
Front lip references and the movement animation separate sideways spread,
rounding and opening. Seat includes gentle outward arrows, sit is less spread,
food is rounded and bilabial closures visibly meet.

## Evidence

- 66 Python checks passed: legacy API behavior, positional probes, ten-target
  coverage, independent vowel predictions, stop contrasts, multilingual-label
  abstention, PCM validation, model state and temporary-file cleanup.
- Word-mode substitution tests cover all ten targets with wrong neighboring
  sounds. They also check feature differences, voicing-only corrections, missing
  onsets, multiple nuclei and loopback-only Python network enforcement.
- PCM encoder round-trip checks passed.
- Browser checks passed for ten target cards and images, real vowel/consonant
  upload, unchanged prediction when the target changes, export, uncertainty,
  mobile layout and simulated microphone recording/track release.
- Discovery guide checks cover all ten activities, control/step changes, visual
  movement, stop closure/release, mobile stacking and reduced-motion support.
  These checks do not measure teaching effectiveness.
- Earlier V1 context run: 24 real-model requests covered all ten categories across 22 existing corpus
  participant IDs. Nine model-label matches, two different-label suggestions,
  thirteen abstentions. This is integration evidence, not recognition accuracy.
- V2: the same cropped teacher-commented initial /s/ remained /s/ under three
  targets, giving an /s/ to /ʃ/ reference-place adjustment where appropriate,
  even when the target's vowel context differed. This is one development audio
  example and does not establish learner accuracy. Word boundaries remain approximate.
- Earlier teacher-feedback investigation: twelve full recordings, 55 passages;
  four of six positional probes reproduced a reported pattern, one disagreed,
  one was unresolved. This must not be reported as 66.7% accuracy.

## Acceptance boundary

Software feature scope is complete for the development MVP. No measured tongue
geometry, validated accuracy, calibrated numeric score, complete actual-heard
phonetic labels, physical-microphone validation or new acoustic-model training is
claimed. Teacher feedback remains partial. Generic praise does not certify every
unmentioned sound. Ten supported targets do not establish a balanced error test set.

Diagrams illustrate generic sound categories, not the speaker's actual anatomy.
Vowel quality is not conflated with length or CTC emission width. The existing
corpus test set remains untouched. Recognition quality requires independent
phonetic evaluation before an accuracy target or automatic grading claim.

The fabricated fixed-score `/assess` stub was retired to HTTP 501. Callers must
use `/demo/analyze` and handle provisional statuses and a null numeric score.

## Reproducibility

- Code: `ai-service/app/`, `ai-service/scripts/`, `ai-service/tests/`.
- API contract: `docs/openapi.yaml`.
- Exact tested environment: `ai-service/scripts/requirements-demo-lock.txt`, after
  separate installation of CPU torch 2.6.0.
- Pinned model and hashes: `data/models/phoneme-recognition/`.
- Teacher annotations: `data/annotations/`; prior investigation:
  `data/results/teacher_feedback_investigation/`.
- Ten-target integration evidence: `data/results/ten_sound_mvp/`.
- V2 word-mode and feedback evidence: `data/results/word_feedback_v2/`.
- Current recording/browser evidence: `data/results/ten_sound_mvp/`.
- Server lifecycle metadata: `data/results/pronunciation_demo_runtime/` (private;
  excluded from the source package).

The source-only package uses an explicit code/documentation allowlist. It excludes
model weights, recordings, datasets, user uploads, environment secrets and local
lifecycle tokens. Existing local data remains in the project.
