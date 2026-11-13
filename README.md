# WordSpeak Core

Ứng dụng web luyện nói tiếng Anh cho người Việt: chấm phát âm theo âm vị (GOP), hội thoại với gia sư AI, ôn tập thẻ bằng FSRS.

## Cấu trúc (monorepo)

| Thư mục | Vai trò | Công nghệ | Phụ trách |
|---|---|---|---|
| `ai-service/` | STT, chấm điểm phát âm | FastAPI, faster-whisper, wav2vec2 | Dev 1 |
| `backend/` | API, WebSocket, DB, FSRS, LLM | FastAPI, SQLAlchemy, PostgreSQL | Dev 2 |
| `frontend/` | Giao diện web | Next.js, TailwindCSS | Dev 3 |
| `docs/` | Hợp đồng API (OpenAPI) | | Cả nhóm |


## Chạy nhanh bằng Docker Compose

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Chép giá trị vừa tạo vào `JWT_SECRET` trong `.env`. Sau đó chạy từ thư mục gốc.

```powershell
docker compose up -d --wait db
docker compose run --build --rm --no-deps backend alembic upgrade head
docker compose up -d --build
Invoke-RestMethod http://localhost:8000/health
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs
- AI service: http://localhost:8001/docs

### Backend và phòng Talk

- Gọi `POST /auth/register` hoặc `POST /auth/login` để lấy JWT. Gửi JWT qua header `Authorization: Bearer <token>` cho API flashcard, Talk và tiến độ.
- Phòng Talk dạng văn bản dùng `POST /sessions`, sau đó `POST /chat/stream` với `session_id` và `text`. Đọc sự kiện SSE `token`, `done` và `error`.
- Với audio, gửi các chunk nhị phân vào `/ws/audio`, rồi gửi JSON `{"type":"end","token":"<JWT>","media_type":"audio/webm"}`. Thêm `text` khi có câu mẫu hoặc `session_id` khi cần phản hồi Talk. Giao thức đầy đủ nằm trong `docs/openapi.yaml`.
- AI service hiện trả dữ liệu mẫu cho `/assess`. Dùng câu mẫu `text` để thử đường đi audio và lưu lượt luyện. Luồng tự nhận dạng cần AI service triển khai `POST /transcribe`; backend trả sự kiện `speech_unavailable` nếu endpoint chưa sẵn sàng.
- Compose mặc định trỏ tới Ollama chạy trên máy host. Chạy `ollama pull qwen2.5:3b` trên host và kiểm tra Ollama đang lắng nghe cổng 11434. Có thể thay `LLM_BASE_URL`, `LLM_MODEL` và `LLM_API_KEY` để dùng endpoint tương thích OpenAI khác.
- Để chạy Ollama bằng Compose, đặt `LLM_BASE_URL=http://llm:11434/v1`, rồi chạy `docker compose --profile local-llm up -d llm` và `docker compose exec llm ollama pull qwen2.5:3b`. Khởi động lại bằng `docker compose up -d backend` để nạp biến môi trường mới.
- Để mở proxy tại `http://localhost:8080`, chạy `docker compose --profile proxy up -d proxy`. API và WebSocket qua proxy dùng tiền tố `/api/`.

## Chạy từng phần (không Docker)

```bash
# backend (sau khi đặt DATABASE_URL và JWT_SECRET)
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000

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
