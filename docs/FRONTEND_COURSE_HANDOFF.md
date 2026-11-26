# WordSpeak Self-Study Course — Frontend Team Handoff

Use this guide alongside the shared [course integration guide](COURSE_HANDOFF.md), [curriculum coverage table](COURSE_COVERAGE.md), and [API contract](openapi.yaml).

## 1. Status at handoff

| Area | Status | Reference implementation |
|---|---|---|
| Existing reused assets | **Existing** | Sound chart & articulation lab (`/demo`), PCM recorder (`audio.mjs`), phrase/pitch assessment (`phrase-assessment.mjs`, `pitch.mjs`), saved word bank (`conversation.mjs`). |
| Working course player | **New & verified** | `ai-service/app/demo_static/course.html`, `course.css`, `course.mjs` — verified on 390×844 mobile viewport in `ai-service/tests/browser_course.cjs`. |
| Main Next.js app integration | **Required from Frontend team** | Entry link added in `docs/integration/self-study-course.patch` (`frontend/app/page.tsx` → `/demo/course`). Adopt the 4 screens and player components into Next.js while preserving the contracts below. |

## 2. Five web screens & required UX behaviors

1. **Today**
   - First visit (`doneItems` empty): show **Find my starting point** (`guide-start`) and **Start from the beginning** (`ship-01`), plus quick cards for the 3 practice studios, while keeping **Library** open.
   - Returning visits: call `GET /api/course/state` (signed-in) or `POST /demo/course/study` (guest), show daily practice streak, and surface one primary action (`state.next` + `state.phase`). Show separate placement recommendations (`Listening`, `IPA reading`, `IPA writing`, `Meaning`) when present.
   - Include the header **`EN | VI`** bilingual toggle and the persistent **`Microphone · Auto-level on`** bar (input device selector, 1×–8× boost slider, live `<meter>`, `autoGain: true`, `autoNormalize: true`).
2. **Studios** (3 sub-tabs for the 3 core MVP pillars)
   - **IPA & Mouth**: Underhill grouped phoneme chart (Monophthongs / Diphthongs & R-vowels / Consonants), animated silent miming SVG + open 4 muscle controls (*Lips, Tongue, Jaw, Voice*), live `/demo/analyze` acoustic check estimating lip/tongue/jaw adjustment cues (never claiming direct mouth-geometry measurement), real human US dictionary audio (`/demo/course/human-word`), and the **"Speak from IPA (spelling hidden)"** drill.
   - **Intonation**: Synchronized moving SVG pitch/stress curve (`intonation-visual.mjs`) that lights up syllables/words simultaneously — synced to real human Wiktionary WAV audio for words (`a-BOUT`, `fif-TEEN`, `FIF-ty`, `RE-cord` vs `re-CORD`, `pho-TOG-ra-phy`) and real lesson audio models for situational sentences (`use-53`, `use-55`, `use-33`, `use-43`, `use-38`).
   - **Talk with AI**: Multi-turn spoken coach working both locally (`/tutor/observe` + `assessRecording`) and signed-in (`/api/sessions/{id}/spoken-turn`), showing 3 structured cards (*Meaning & transcript*, *Pronunciation & mouth guidance*, *Intonation, stress & rhythm*) plus clarifying follow-ups.
3. **Library**
   - Open all 281 entries immediately (280 source-linked + 1 placement). Never lock lessons behind prerequisites; display `after` only as a suggested sequence.
   - Filter client-side by `book`, `topics` (4 skills), `symbols` (IPA), and text search (`id`, `title`, `goal`). No `/course/state` fetch needed on this tab.
4. **Reusable Lesson Player** (`?lesson={id}&phase=practice|review`)
   - Fetch `GET /demo/course/lesson/{id}?phase=...`. **Never** bundle or cache private answer keys client-side.
   - Show visual lesson progress bar. Blind listening/reading items (`kind === "choice"` for Listening or `"Which word fits"`): hide lesson title/goal until graded.
   - **Always-open IPA phoneme tile keyboard**: grouped into General American Vowels, Diphthongs & R-vowels, Consonants, Stress & editing (digraph-aware Backspace + Clear), and optional British reference symbols, with example-word tooltips. Tile clicks must **not** blur the input (`course.mjs` attaches direct synchronous click handlers outside the `inert` busy lock). Show per-symbol `diff`, accepted `reference`, and `contrast` audio on retry.
   - **Audio & Accent labels**: play `/demo/course/audio/{key}` (serves real human Wiktionary WAV for single words, bundled MP3 for sentences; `X-Audio-Source` header) and clearly label `en-GB` vs `en-US`.
   - **Recording & Replay**: reuse `startPCMRecording({gain, deviceId, autoGain: true, autoNormalize: true})` + `assessRecording`. For 2-model intonation/prominence lessons (e.g. `use-53`), show the synchronized moving stress visual synced to `<audio>` and require recording both target readings before saving. Always provide **Continue without microphone** (`unavailable`).
   - **Reply, Optional Listener Check & AI Coach**: inline AI coaching works locally via `/tutor/observe` and signed-in via `/api/sessions/{id}/spoken-turn` (guard `turn.reply === null`; never award intelligibility credit from AI replies). Optional listener `<dialog>` uses inline validation before revealing intention.
5. **My Words & Progress**
   - **My Words**: save via `PUT /api/practice-words` (signed-in) or `wordBank` (guest). Check `GET /demo/course/word?word=...`; play real human dictionary audio via `GET /demo/course/human-word?word=...` with browser fallback.
   - **Progress**: display Listening, IPA, Speaking (`recorded` vs `unavailable` skips), Message interpretation/authored exchanges, Optional listener checks, and Delayed first responses separately. Only make **due** reviews (`state.due`) clickable; show future `reviewDates` as scheduled/not due yet.

## 3. Resilience, auth, and offline states

- **Retry-safe submission**: generate one UUID `attempt_id` per `(version, lesson, exercise, answer)` and persist it in `sessionStorage` until a `200` response arrives. Re-send the exact same `attempt_id` on network retry; generate a new UUID if the answer changes.
- **Expired token (`401`)**: clear stored bearer token, update account UI to signed-out, and prompt sign-in (never trap the learner in a failing `refresh()` loop).
- **Catalog update (`409`)**: prompt the learner to reopen the lesson so it fetches the latest `version`.
- **Offline / mic denied / acoustic unavailable**: display clear, non-blocking status messages; allow audio replay of loaded takes and explicit microphone skip (`unavailable`).

## 4. Verification checklist for Frontend

1. Run `node ai-service/tests/browser_course.cjs http://127.0.0.1:8013` (or full integrated run via `python ai-service/tests/check_account_review_browser.py --backend <receiver>/backend --course`).
2. Manually test on mobile (390px): IPA tile insertion keeps cursor focus, `/sɪt/` on `ship-01` highlights `ɪ → i` with *sit*/*seat* audio, `use-53` plays both readings and requires two takes, mic denial shows skip path, offline retry reuses `attempt_id`, and zero horizontal overflow.
