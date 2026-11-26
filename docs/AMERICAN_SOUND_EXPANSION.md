# General American sound expansion

Updated 21 November 2026. The user selected American English as the reference.
This supersedes the ten-target scope for current practice; older dated reports
remain historical evidence.

## Current practice inventory

**41 core practice entries**: 12 steady/r-colored vowel entries, 5 diphthongs and
24 consonants. Stress variants /ɝ/ and /ɚ/ are listed separately for teaching;
this is not a claim that every American accent has exactly 41 phonemes.

| Group | Entries |
|---|---|
| Steady and r-colored vowels | /i ɪ ɛ æ u ʊ ə ʌ ɑ ɔ ɝ ɚ/ |
| Diphthongs | /eɪ aɪ ɔɪ oʊ aʊ/ |
| Consonants | /p b t d k ɡ f v θ ð s z ʃ ʒ h tʃ dʒ m n ŋ l ɹ w j/ |
| Additional r-vowel combinations | /ɪɹ ɛɹ ɑɹ ɔɹ ʊɹ aɪɹ/ |

All core entries and extra r-combinations have a word prompt, reference artwork,
a short physical cue and optional guided movement. The catalogue is searchable
by IPA/word and filterable by vowel/consonant. Primary American notation uses
/i u oʊ/ and rhotic /ɹ/. British-only teaching targets are not core selections.
The code retains legacy guides for interpreting older model labels and results.

Open http://127.0.0.1:8013/demo?american=1. Restart with START_WORDSPEAK.cmd if
offline; the current build is `american-sounds-v1`. Browser assets are versioned.

## Observations and feedback

- The recognizer receives audio only. The intended word and target are used by
  the subsequent matcher to select a configured position, never to fill the
  observed label. Changing a target does not select a more convenient candidate.
- Word-only mode supports a vowel nucleus by ordinal position, initial
  consonants, medial /ʒ/ in vision, and final /ŋ/ in sing. Two-syllable examples
  about and teacher have explicit nucleus positions. Missing or ambiguous
  locations retain an explanation rather than an invented sound.
- Adjacent decoded vowel or stop/fricative labels can be combined into a
  diphthong, r-colored unit or affricate, without looking at the target. Such
  combinations remain tentative. Pauses prevent joining; raw labels are retained.
- An extra coda label after /ŋ/ is shown as possible extra material, not used to
  replace the actual /ŋ/ candidate. This is not a confirmed deletion/insertion
  annotation.
- Nasal, lateral, approximant and affricate airflow have separate descriptions.
  Nasal references show a nasal-air route; moving vowels show start/finish
  references rather than a fabricated single-position guide.
- Cot/caught merger is accepted. Normal aspiration, dark-l/r notation and
  length-marked model /iː uː/ are interpreted using explicit English mappings,
  while raw labels remain visible. Opaque multilingual labels are not guessed.
- /ɝ/ versus /ɚ/ is not scored as a stress error. A non-rhotic model label alone
  does not prove the learner omitted r coloring. Steady /e o/ labels do not prove
  the absence of an American glide. Relevant guidance remains conditional.
- The same one-cue practice, paired reference views, microphone boost, WAV
  playback/download, result export and Words & meaning activities are retained.

## What has not been established

All sound comparisons remain experimental. Catalogue completeness and passing
tests do not establish reliable recognition across all speakers. The model has
not been trained on the new collection. No calibrated accuracy, severity score,
measured mouth geometry, vowel duration, stress or prosody assessment is claimed.

The pretrained vocabulary can emit most core labels directly. Stressed /ɝ/ can
require a combination or interpretation of r-related model labels rather than a
direct /ɝ/ token. Such evidence is kept provisional; the decoder is not expanded
by pretending a new acoustic output class was trained.

## New recordings

The collection adds 86 source files in folders P16–P22 relative to the previous
211-file preparation manifest. The audit prepared 73 unique recordings and
retained 13 duplicate records, totaling approximately 30.6 minutes of unique
prepared audio. All 297 source files were hash-checked unchanged.

Outputs: `data/prepared/new_collection_20261121/manifest.jsonl`, `audio/`,
`summary.json`. Source paths and hashes stay in local data. Duplicate entries
retain provenance; raw audio is not deleted or renamed. New rows have null
pronunciation labels, human_verified=false and an unassigned split.

Seven representative new recordings were transcribed using a local Whisper
model solely to prepare approximate word crops. Those automatic transcripts are
not pronunciation ground truth. The ASR transcript is not sent to the acoustic
phoneme recognizer. Only matching exact practice words were selected, without
confidence-based filtering. Existing-corpus integration uses the train partition;
no untouched test partition is repurposed.

## Reproducible checks

From the project root:

```powershell
& data/phoneme-env/Scripts/python.exe ai-service/scripts/build_reference_guides.py
& data/phoneme-env/Scripts/python.exe ai-service/scripts/audit_new_learner_batch.py
& data/phoneme-env/Scripts/python.exe ai-service/scripts/check_american_expansion.py
```

Run the Python tests inside ai-service. JavaScript checks are test_*.mjs; browser
checks include browser_american_inventory.cjs and the existing recorder, lips,
teaching and feedback checks. Browser tests require a local server and the
installed Playwright/Chrome paths; synthetic decoded-label fixtures verify UI
behavior, not classification accuracy.

The optional crop-preparation script uses the local speech-tools dependencies
and Whisper checkpoint. Results and screenshots are under
`data/results/american_expansion/`. Real-request outcomes, coverage gaps and
source kind are recorded separately from mock browser tests.

## References and original artwork

- [American chart and notation](https://soundsamerican.net/)
- [University of Kansas: American vowels and r coloring](https://opentext.ku.edu/amenglishpronunciation/chapter/chapter-1/)
- [Underhill: physical awareness and iteration](https://oxfordtefl.com/blog/my-top-ten-pronunciation-tips-physicality-and-integration-by-adrian-underhill/)

Artwork and lesson text are original project adaptations. The American reference
does not impose one exact tongue geometry or claim endorsement by these sources.
