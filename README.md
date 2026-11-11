# WordSpeak Core

Ứng dụng web luyện nói tiếng Anh cho người Việt: chấm phát âm theo âm vị (GOP), hội thoại với gia sư AI, ôn tập thẻ bằng FSRS.

## Cấu trúc (monorepo)

| Thư mục | Vai trò | Công nghệ | Phụ trách |
|---|---|---|---|
| `ai-service/` | STT, chấm điểm phát âm | FastAPI, faster-whisper, wav2vec2 | Dev 1 |
| `backend/` | API, WebSocket, DB, FSRS, LLM | FastAPI, SQLAlchemy, PostgreSQL | Dev 2 |
| `frontend/` | Giao diện web | Next.js, TailwindCSS | Dev 3 |
| `docs/` | Hợp đồng API (OpenAPI) | | Cả nhóm |


## Chạy nhanh

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs
- AI service: http://localhost:8001/docs

## Chạy từng phần (không Docker)

```bash
# backend
cd backend && python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# ai-service
cd ai-service && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8001

# frontend
cd frontend && npm install && npm run dev
```

Test: `pytest` trong `backend/` và `ai-service/`.

## Quy ước làm việc

- Nhánh: `feat/<phan-he>-<ten>` (ví dụ `feat/ai-gop`), gộp vào `main` qua pull request.
- Mỗi người chỉ sửa thư mục của mình; thay đổi API phải sửa `docs/openapi.yaml` trước.
- Không commit dataset, model, audio, `.env` (đã có trong `.gitignore`).
