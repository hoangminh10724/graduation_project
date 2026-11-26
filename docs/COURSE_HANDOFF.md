# Self-study course integration

## Scope and ownership

| Owner | What ships | What to do at merge |
|---|---|---|
| Curriculum and speech | 280 source-linked entries, one separate placement activity, original solo tasks, server-side keys, reference audio and transfer items | Use the coverage table to compare each objective with the specified source edition. Listen to references in the intended accent and situation. Record decisions about variants and replace any model that does not convey the intended contrast. |
| Frontend and UX | Working player under `ai-service/app/demo_static/course.*`, entry from the sound lab and receiving frontend, five main screens (Today, Studios, Library, My Words, Progress), EN/VI toggle, recorder with auto-leveling, optional listener check and account controls | Preserve the focus order, always-open IPA tiles, IPA alignment, two reference readings, saved-word workflow and microphone skip when adopting components in the main frontend. Use only public lesson data. |
| Backend | Versioned course and marking service, account routes, Alembic revision 0005, retry-safe requests, existing authentication, word cards and spoken-turn history | Apply the five patches, migrate, configure speech and tutor services, and test resume with two separate accounts. |
| All three | Coverage, reference lessons, shared contract and integration tests | Complete the acceptance checks below together and record the human results before a release decision. |

**Existing and reused.** The physical sound chart, PCM recorder, phrase/pitch checks, recording-based tutor observations, account authentication, personal words and dialogue history predate this course. **New and implemented.** Source mapping, guided path, searchable Library, lesson player, per-symbol marking, authored reply choices, fresh review, four progress views and account attempt records ship in this overlay. Engineering tests establish reachability and persistence. Independent learner outcomes and pronunciation-expert acceptance of the new materials remain pending.

## Screen flow

1. **Today** offers a starting check or the first lesson. Placement records the first response for listening, reading IPA, writing IPA and interpreting emphasis. A learner can browse every lesson immediately. Later visits prioritize a due review, a partially completed lesson or a recommended lesson.
2. **Library** filters by book strand, teaching focus, IPA symbol or text. Source IDs are permanent links. Suggested prerequisites express a sequence and never lock access. The four strands interleave after the opening lessons.
3. **Lesson** presents a goal, model or listening task, a checked response, focused practice and transfer. A learner can type IPA, use tiles on mobile, compare a recording with the model and retry. Speech feedback concerns a measurable cue. A weak or unavailable measurement leads to replay and a new take. Sound-lab illustrations show reference positions. The course does not measure a learner's mouth position.
4. **My Words** accepts personal expressions and optional situations. Known entries open graded transcription in context. Other words support a device voice when available, recording, playback and conversation. Account words reuse the existing review cards. Guest words reuse the sound-lab bank. Guest progress belongs to the browser. Account progress resumes after signing in.
5. **Progress** separates listening and IPA answers, speaking participation, authored message choices, optional listener checks and delayed first responses. One checkable communication task is choosing the reply that corrects a host who heard fifty. An optional listener can hear a recorded reply and type the detail they understood before seeing the intended message. The learner indicates whether it matched. Only that reported outcome is persisted. A generated tutor reply gives no intelligibility credit.

## Two reference lessons

| Lesson | What to demonstrate | Delayed transfer |
|---|---|---|
| Ship or Sheep? 01 · `ship-01` | Open the original seat model. Identify the word and the symbol, then type /sɪt/. The matching /s/ and /t/ stay visible, the vowel changes to /i/, and both words can be replayed. Type /sit/ or /siːt/. Compare two takes and ask for a seat in a fresh reply. Save the word. | Distinguish *peach* from *pitch* in a different voice and clarify which fruit you want. |
| English Pronunciation in Use 53 · `use-53` | Distinguish fifteen from fifty. Hear the **same speaker** say “I booked fifteen seats” with focus on the number and then the item. Transcribe *fifteen* with stress. Produce both readings. Compare the estimated relative emphasis when the words can be aligned. Make a differently worded correction and check the host's readback. | Interpret an order for thirteen cups, write *fifty* and correct a fresh delivery. |

A learner can move forward with a recorded attempt or an explicit microphone skip. Skips and recorded attempts appear separately. The first full review is due the next calendar day. Completing a due review schedules the next in seven days. Shared materials recur across source lessons and later cycles reuse review sets. A later correct answer to a familiar item is weaker evidence than an unfamiliar-word listener trial. The service uses its calendar date for due dates. Set the service timezone consistently when deploying.

## Merge and operate

Use receiving commit `60779747bc04f34358de6365df3590e1b747315e` or reconcile newer team changes on an integration branch. Copy the ZIP overlay into that checkout. Keep local credentials and learner data outside the ZIP. Apply each patch once, in this order. If the team already applied an earlier patch, check its changes against the receiving branch and continue from the next missing patch.

```powershell
git apply docs/integration/talk-transcript-timing.patch
git apply docs/integration/account-review-entry.patch
git apply docs/integration/account-practice-words.patch
git apply docs/integration/spoken-tutor.patch
git apply docs/integration/self-study-course.patch
docker compose --profile proxy up -d --build
docker compose exec backend alembic upgrade head
```

Open `http://localhost:8080/demo/course` through the integrated proxy. Standalone preview uses `http://127.0.0.1:8013/demo/course`. Lesson assets ship inside the speech image. The original three PDFs, private learner recordings, model weights and credentials are excluded. Use [the speech setup](CONVERSATION_HANDOFF.md) for model locations and the tutor provider. The lesson catalog and bundled audio can run without model weights. Speech inference and a generated tutor reply require the respective services.

## Interfaces and retry behavior

The browser calls `/demo/course/...` on the speech service. Account routes below use the reverse proxy prefix `/api`. The shared OpenAPI file uses backend paths without that prefix.

| Operation | Request | Response |
|---|---|---|
| Catalog and recommendation | GET `/demo/course/catalog`; signed-in GET `/api/course/state` | Catalog version, summaries, symbols and prerequisites. State includes `next`, `phase`, `due`, `reviewDates` and `doneItems`. |
| Open a lesson | GET `/demo/course/lesson/use-53?phase=practice` | Ordered exercise IDs, prompts, options and opaque audio keys. Use `phase=review` for the separate transfer set. |
| Play a reference | GET `/demo/course/audio/{key}` (or `/demo/course/human-word?word=...`) | Real human Wiktionary WAV for single words when available, or packaged MP3 (`X-Audio-Source` header). Individual models and listing metadata distinguish US and British references. |
| Submit a grade | POST `/api/course/attempts` with bearer authorization; guest POST `/demo/course/grade` | Exact marking, optional IPA diff, feedback, version, date and ID. Read the current version from the catalog. Reuse the UUID for a network retry of the same answer. Generate a new UUID when the answer changes. |
| Guest recommendation | POST `/demo/course/study` with the guest's event array | Same state shape as the account query. The guest event history stays on that device. |
| Save and reuse words | PUT `/api/practice-words`; GET `/api/course/words`; GET `/demo/course/word?word=seat` | Existing user-owned cards and lookup for an exercise with an authored IPA key. |
| Spoken follow-up | POST `/api/sessions`, then POST `/api/sessions/{id}/spoken-turn?focus=fifteen` with `audio/wav` | Timed speech observation, transcript and optional tutor reply. Speech uncertainty and a service failure have explicit UI states. |

Example submission for the *seat* transcription. Substitute the version returned by your running catalog.

```json
{"attempt_id":"7d392f10-ab8f-4691-89a3-b85f2d6643c0","version":"<catalog version>","lesson":"ship-01","exercise":"p5","answer":"sɪt"}
```

The relevant response fields for this submission are shown below. Feedback, reference audio, attempt metadata and the authored answer are also returned after submission.

```json
{"kind":"ipa","skill":"IPA","outcome":"retry","diff":[{"kind":"equal","entered":"s","target":"s"},{"kind":"replace","entered":"ɪ","target":"i"},{"kind":"equal","entered":"t","target":"t"}]}
```

The account database stores the graded result, version, lesson fingerprint and user-scoped request identity. Identical retries return the saved verdict. A conflicting ID returns 409. A changed catalog version requires reopening the lesson. Unchanged lesson fingerprints retain earlier progress across a catalog update. Recording verdicts distinguish `recorded` and `unavailable`; an optional reported listener judgment is tracked separately. A saved result contains no raw audio. A failed grading request gives no result or credit. Reconnect and retry from the same exercise.

## Import or revise content

The curriculum source is under `ai-service/app/course/`. Each UTF-8 TSV-style file uses a literal pipe delimiter. The first numbered row corresponds to unit or activity 01. Preserve existing row order and IDs. `ship.tsv` lists the source sequence and seven reviews. `use.tsv` includes the 60 units followed by D1–D6. `discovery.tsv` and `classroom.tsv` hold activity-specific solo instructions and concept checks. `sounds.tsv` holds broad GA keys, US contrasts, fresh items, cues and British readings. `contexts.tsv` holds original practice and transfer situations. `exchanges.tsv` pairs an intended communicative action with two possible replies. The compiled Python catalog is private server content. Serve only the public catalog, lesson and audio routes.

1. Locate the source row in [the coverage table](COURSE_COVERAGE.md). Edit its objective, solo task, resources and checkable response. Keep a separate exercise when an activity changes from perception to using the contrast in a reply.
2. Add authored variants after a semicolon in the pronunciation field. Supply a word sense or phrase context for ambiguous readings. Check vowel mergers, weak forms, primary and secondary stress against the audio. Grade British reading in labeled activities and retain GA as the production target.
3. Use original or cleared audio. For the bundled synth workflow use Windows, two US English SAPI voices, PyAV, NumPy and an eSpeak NG British voice via `espeakng_loader`. Run `python ai-service/scripts/build_course_audio.py` (or pass `--espeak-dir PATH` for a separately installed loader). It renders missing model IDs. Use `--force` to regenerate existing models; an expert can instead replace a model MP3 at the same ID. New recording IDs derive from text, accent and speaker. Audition same-word/different-intent readings in pairs.
4. Run `python ai-service/scripts/check_course.py --write --decode-audio` to regenerate coverage, validate keys, and decode all references. Run the tests below and rebuild with `python ai-service/scripts/build_team_handoff.py`. The packer checks each ZIP entry against the workspace. Keep private answer material out of frontend bundles.

## Joint acceptance and remaining evidence

| Check | Procedure | Evidence to retain |
|---|---|---|
| Full library | Run the coverage checker and speech tests. Open one entry from each book strand, including a cumulative review and a Cambridge reference activity. | Every entry has public practice, private grading, playable audio, an activity-specific solo goal and a fresh review. |
| Mobile and device failure | Run both reference lessons. Use tiles, enter a substitution, deny the mic, reconnect after a request failure and restore the account. | Retry and skip states remain legible, correct segments are preserved, and previous attempts resume. |
| Backend merge | Run the receiving backend tests on the patched checkout. Exercise an identical retry and a conflicting retry, and sign in as a different user. | One immutable record per user/request ID and no access to another learner's words or attempts. |
| Independent learner pilot · pending | Recruit Vietnamese learners with different levels. Give the starting URL without a walkthrough. Observe whether they start, finish, explain their IPA or speech feedback and return on a later day. Use unfamiliar words and a voice they have not heard in practice. | Record task completion, help required, the learner's explanation and delayed first responses with denominators. |
| Listener transfer · pending | Privately give the learner a target detail. Play the reply to an unfamiliar listener who cannot see the prompt. Collect the listener's own words before revealing the intention. Repeat with a new situation. | Report recovered details, requests for repair and uncertain cases separately from model warnings. |
| Speech and content review · pending | A pronunciation specialist audits each source mapping, IPA variant and reference in context, especially generated prominence, reduced forms and British contrast audio. Compare acoustic warnings with independent time-aligned labels. | Record approved assets, revisions, and precision for each warning type where sufficient independent samples exist. |

Engineering commands from the workspace root use the speech Python environment for the first suite, and the receiving backend Python environment for the other two.

```text
python -m pytest -q ai-service/tests
python -m pytest -q <patched-receiver>/backend/tests
python ai-service/tests/check_account_review_browser.py --backend <patched-receiver>/backend --course
```

For the browser test, start the local course at port 8013, install Chrome and make Playwright available to Node. The harness uses disposable accounts and SQLite. It exercises the integrated routes, a browser microphone fixture and a simulated next calendar day. These are engineering checks; independent learner and unfamiliar-listener results have yet to be collected.
