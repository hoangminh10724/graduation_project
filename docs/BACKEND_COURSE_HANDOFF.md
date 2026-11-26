# WordSpeak Self-Study Course — Backend Team Handoff

Use this guide alongside the shared [course integration guide](COURSE_HANDOFF.md), [API contract](openapi.yaml), and patch files in `docs/integration/`.

## 1. Status & architecture boundary

| Responsibility | Owner / Service | Status |
|---|---|---|
| Curriculum catalog, audio assets, IPA/choice grading, study-state calculation | `ai-service` (`/demo/course/*`) | **New & verified** (`ai-service/app/course/{catalog,routes}.py`, 163 pytest checks pass). |
| Account auth, retry-safe attempt persistence, saved words, spoken tutor | `backend` (`/course/*`, `/practice-words`, `/sessions/*`) | **Patch ready & verified** (`docs/integration/self-study-course.patch`, 36 receiver pytest checks pass). |
| Reverse proxy routing | `docs/nginx.conf` | **Patch ready** — proxies `/demo/course` (plus existing `/demo`, `/demo/assets`, `/demo/config`) to `ai-service:8001`. |

**Critical security invariant:** Answer keys (`key`), explanations (`feedback`), and choice target words stay strictly server-side inside `ai-service`. The backend only forwards submissions to `POST /demo/course/grade` and persists the graded verdict.

## 2. Merge & migration steps

Apply the patches on receiving commit `60779747bc04f34358de6365df3590e1b747315e` (or rebase onto current `main`) in exact order, skipping any already merged:

```powershell
git apply docs/integration/talk-transcript-timing.patch
git apply docs/integration/account-review-entry.patch
git apply docs/integration/account-practice-words.patch
git apply docs/integration/spoken-tutor.patch
git apply docs/integration/self-study-course.patch
docker compose --profile proxy up -d --build
docker compose exec backend alembic upgrade head
```

### What `self-study-course.patch` adds
- `backend/app/course.py`:
  - `CourseAttempt` SQLAlchemy model (`course_attempts` table with `UniqueConstraint("user_id", "request_id", name="uq_course_attempt_user_request")`).
  - `POST /course/attempts` (`BearerAuth`): hashes payload into `fingerprint`; replays exact saved verdict on identical retry; returns `409` if `request_id` is reused with a different payload; handles concurrent race via `IntegrityError` rollback + lookup; returns `503` if `ai-service` is unreachable so client retries with the same `attempt_id`.
  - `GET /course/state` (`BearerAuth`): loads user's ordered `CourseAttempt.result` rows and calls `ai-service` `POST /demo/course/study` to compute `next`, `phase`, `due`, `reviewDates`, `doneItems`, `skills`, `placement`, `communication`, `listeners`, and `delayedFirstResponses`.
  - `GET /course/words` (`BearerAuth`): returns user-owned saved practice words (`Card.practice_key IS NOT NULL`).
- `backend/migrations/versions/0005_course_attempts.py` (`down_revision = "0004_practice_words"`) + `backend/migrations/env.py` model registration.
- `backend/app/main.py`: mounts `course_router`.
- `backend/tests/test_course.py`: covers `401` unauthenticated, idempotent retry, `409` conflicting retry, cross-user isolation, sign-in resume, and saved words isolation.

## 3. Environment & deployment notes

- `AI_SERVICE_URL`: set in backend container to reach `ai-service` (default `http://localhost:8001`; in Docker Compose `http://ai-service:8001`).
- **Timezone consistency**: `ai-service` stamps `day = date.today().isoformat()` and schedules next-day (+1d) and 7-day (+7d) reviews using its calendar date. Configure a consistent `TZ` across `ai-service` and `backend` in deployment.
- **No raw audio persisted**: `course_attempts.result` stores only the structured JSON verdict (no audio blobs).
- **Nginx check**: confirm `docs/nginx.conf` proxies `/demo/course` (includes `/demo/course/human-word`), `/demo/assets`, `/demo/config`, `/demo/analyze`, `/transcribe`, and `/tutor/observe` to `ai-service:8001`, and `/api/` to `backend`.
- **Real human dictionary audio**: `ai-service` fetches & caches real human Wiktionary recordings (`audio_human/*.wav`, transcoded from OGG via PyAV for universal browser support including macOS Safari) on first request, falling back to bundled MP3s offline or for sentences. Set `WORDSPEAK_OFFLINE_AUDIO=1` in air-gapped environments to skip Wikimedia lookups.

## 4. Verification commands

```powershell
# 1. Speech & course catalog/grading suite
python -m pytest -q ai-service/tests

# 2. Coverage & audio decode check
python ai-service/scripts/check_course.py --decode-audio

# 3. Patched receiving backend suite (includes Alembic/SQLite & test_course.py)
python -m pytest -q <patched-receiver>/backend/tests

# 4. Integrated browser E2E (guest + signed-in retry + account resume)
python ai-service/tests/check_account_review_browser.py --backend <patched-receiver>/backend --course
```
