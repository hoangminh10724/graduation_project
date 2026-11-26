# WordSpeak American English pronunciation demo

Open the [guided course](http://127.0.0.1:8013/demo/course) for Today, Library, My Words and Progress. Setup below starts the same service. See [the course handoff](../docs/COURSE_HANDOFF.md) for account integration and learner testing.

Current app: http://127.0.0.1:8013/demo

On a prepared Windows workstation, run `START_WORDSPEAK.cmd` and open the local address above. For a fresh Windows checkout, run these commands from the repository root with Python 3.11 or 3.12 installed:

```powershell
py -3.12 -m venv data/phoneme-env
data/phoneme-env/Scripts/python.exe -m pip install -r ai-service/requirements.txt
data/phoneme-env/Scripts/python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
data/phoneme-env/Scripts/python.exe -m pip install transformers==4.49.0 soundfile==0.13.1
```

Use `py -3.11` if using Python 3.11. Copy the existing model directories listed in the [team handoff](../docs/CONVERSATION_HANDOFF.md) and check them with `data/phoneme-env/Scripts/python.exe ai-service/scripts/verify_speech_models.py` before testing inference. The account and tutor features use the integrated backend deployment described in that guide.

Current guide: [American sound expansion](../docs/AMERICAN_SOUND_EXPANSION.md).

The current catalogue uses General American: **41 core practice entries**
(17 vowel entries, including stressed/unstressed r-colored vowels, and 24
consonants), plus six r-vowel combinations. This is a teaching inventory rather
than a universal phoneme-count claim. /i u oʊ/ are the primary American labels;
legacy length-marked labels remain visible in raw model output when emitted.

All targets have prompts, guides and optional teaching activities. Nasals,
affricates, diphthongs, word-final /ŋ/ and medial /ʒ/ have explicit handling.
Cot/caught merger is accepted. Vowel length, lexical stress, actual tongue
geometry and recognition accuracy are not graded or established.

Historical scope: [Ten-sound MVP](../docs/TEN_SOUND_MVP.md).

Handoff and validation: [MVP handoff](../docs/MVP_HANDOFF.md).

Earlier three-sound prototype ports 8011/8012 are obsolete.

## Physical practice and words in context

Revision `physical-practice-1` adds a **Words & meaning** practice area for word
stress/unstress, sentence focus, contextual rising/falling readings and connected
speech. Each topic has one cue, a reference gesture, browser-local recording and
playback of the two latest attempts. Stopping a recording opens its assessment.
Phrase exercises locate the practice line via transcription and check an acoustic cue.
Conversation turns automatically check the saved focus expression through `/tutor/observe`.
Audio quality, uncertainty and service failures each have their own feedback. Clips clear when the tab closes or
reloads. Microphone selection and 1x–8x input boost are available in this area.

The sound guide's **Watch movement** action opens a compact silent demonstration.
Supported vowel/fricative comparisons use the suggested starting category;
tentative predictions keep conditional wording. Equal illustrated shapes do not
produce an invented movement correction. Full exploration remains optional.

Research, competitor comparisons, learning evaluation and business assumptions:
[Pronunciation product study](../docs/PRONUNCIATION_PRODUCT_STUDY.md).

## Recording-specific feedback

Revision `recording-diagnosis-1` shows **What I heard**, **The difference**, and
**Try this** above the reference diagrams, rather than hiding the comparison in
optional details. Weak model candidates receive explicitly conditional feedback.
Adjacent vowel labels within one short nucleus retain their alternatives and
uncertainty instead of being discarded as several words. A single sustained
consonant can also be compared. Separate words and pauses remain unresolved.

These changes expose the recognizer's evidence; they do not improve or establish
its classification accuracy. Opaque labels, absent onsets, silence, and glides
receive specific explanations without inventing an actual mouth position or a
severity percentage. Known glides get a conditional steady-vowel exercise, not
a fabricated single-position diagram. Vowel length is still not measured.

Reference revision `paired-references-1` keeps the likely-sound and target
diagrams visible together after a supported prediction. Each includes a word
example and a short reference-feature description. /ɪ/ (sit) differs from /iː/
(seat); unmarked /i/ is shown separately without inventing a different mouth
shape or claiming a length error.

## Integration with the backend

This branch adds the local `/demo` workflow. `/demo/analyze` returns provisional
sound categories and a null score; it does not return the backend's `Assessment`
schema. The separate `/assess` endpoint returns experimental GOP scores for the
MVP's isolated practice words. The service also provides local `/transcribe`
for WAV or WebM conversation turns.

The shared OpenAPI contract preserves the backend endpoints, JWT definitions and
Assessment schema while documenting the demo and its isolated-word scope.
Dataset preparation scripts are included; recordings, model weights, local
environment packages, runtime tokens and generated reports remain local.

Current saved-word practice and team integration instructions: [Conversation handoff](../docs/CONVERSATION_HANDOFF.md).
