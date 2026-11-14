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
- AI service chạy trong mạng Compose, backend truy cập qua http://ai-service:8001.

### Backend và phòng Talk

Sau khi cập nhật backend, chạy lại `alembic upgrade head` để thêm dữ liệu chống ghi trùng lượt ôn và trạng thái lượt Talk.

- `POST /reviews` yêu cầu `request_id` dạng UUID. Frontend tạo một UUID cho mỗi lần người học đánh giá thẻ và dùng lại UUID đó khi gửi lại request. Backend trả lại kết quả đã lưu. Dùng cùng UUID cho dữ liệu khác sẽ trả 409.
- Chọn Again sẽ hẹn ôn lại sau 10 phút. Các mức khác dùng lịch FSRS theo ngày. Dùng `interval_seconds` hoặc `card.due` để hiển thị lịch chính xác.
- `GET /sessions` và `GET /sessions/{id}/turns` trả các phiên và lịch sử thuộc người dùng hiện tại. Một phiên chỉ xử lý một lượt Talk tại một thời điểm. Request trùng thời gian trả 409 hoặc `session_busy`.
- Sau sự kiện `transcript`, Talk và chấm phát âm chạy song song. `done` kết thúc phản hồi Talk, `final` trả kết quả chấm và có thể tới sau `done`. Nếu chấm lỗi, backend phát `assessment_unavailable` và vẫn cho Talk hoàn thành.
- Sự kiện `coaching` chứa `errors` và `hints` do AI service cung cấp, frontend hiển thị khi kết quả chấm tới. Phản hồi Talk được giới hạn tối đa 40 từ bằng bộ lọc streaming.
- `GET /progress?timezone_name=Asia/Ho_Chi_Minh` trả streak và dữ liệu `daily` theo ngày địa phương. Có thể truyền múi giờ IANA khác, mặc định là Việt Nam.

- Gọi `POST /auth/register` hoặc `POST /auth/login` để lấy JWT. Gửi JWT qua header `Authorization: Bearer <token>` cho API flashcard, Talk và tiến độ.
- Phòng Talk dạng văn bản dùng `POST /sessions`, sau đó `POST /chat/stream` với `session_id` và `text`. Đọc sự kiện SSE `token`, `done` và `error`.
- Với audio, gửi `{"type":"auth","token":"<JWT>"}` vào `/ws/audio` trong 10 giây đầu và chờ sự kiện `authenticated`. Sau đó gửi các chunk nhị phân và kết thúc bằng `{"type":"end","media_type":"audio/webm"}`. Thêm `text` khi có câu mẫu hoặc `session_id` khi cần phản hồi Talk. Giao thức đầy đủ nằm trong `docs/openapi.yaml`.
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

### Giới hạn cho bản demo

Sau cập nhật, chạy `alembic upgrade head` (hiện tại là `0006_accounts`). Bộ đếm dùng chung DB và cửa sổ một phút. Đăng ký giới hạn 5 lần/IP, đăng nhập 30 lần/IP và 10 lần/email, tạo phiên 20 lần/tài khoản, gọi AI 20 lượt/tài khoản, mở WebSocket 30 lần/IP. HTTP trả 429 kèm Retry-After. WebSocket trả rate_limited.

WebSocket yêu cầu xác thực trước audio, giới hạn 8 MiB/lượt, thời gian thu tối đa 120 giây và xử lý tối đa 180 giây. Token được kiểm tra lại mỗi lượt. Hợp đồng này yêu cầu frontend cập nhật bước xác thực đầu kết nối.

Backend chỉ publish cổng 8000 trên localhost. AI service dùng mạng nội bộ Compose. Khi chạy sau reverse proxy, cấu hình FORWARDED_ALLOW_IPS của Uvicorn đúng địa chỉ proxy được tin cậy để limiter nhận IP người dùng. Triển khai public cần TLS tại ingress và thử lại HTTPS/WSS.

### Tiến độ hoàn thiện backend demo

- Đã bổ sung xác thực đầu WebSocket, hạn thời gian, bộ đếm request dùng chung DB và kiểm tra token giữ khóa tại thời điểm ghi lượt Talk.
- Đã bổ sung bộ thẻ, tìm kiếm/phân trang flashcard, sửa/xóa thẻ, tạm ngừng ôn, xem trước lịch và lịch sử đánh giá.
- Đã bổ sung hồ sơ người học, refresh token luân chuyển, danh sách/thu hồi phiên đăng nhập và đổi mật khẩu.
- Đang hoàn thiện khôi phục tài khoản, phiên ôn tập, vòng đời lượt audio/Talk và dashboard.
- Cần nghiệm thu PostgreSQL đồng thời, email, STT/chấm phát âm và LLM thật trước khi chốt bản demo khách hàng.

### Quản lý flashcard và bộ thẻ

Các API sau yêu cầu JWT của chủ sở hữu.

| API | Chức năng |
|---|---|
| `POST /decks`, `GET /decks` | Tạo và liệt kê bộ thẻ |
| `PUT /decks/{id}`, `DELETE /decks/{id}` | Đổi tên/mô tả hoặc xóa bộ thẻ |
| `POST /cards` | Tạo thẻ, có thể truyền `deck_id` |
| `GET /cards` | Tìm theo `q`, lọc `deck_id`/`suspended`, phân trang bằng `cursor` và `limit` |
| `GET /cards/{id}`, `PATCH /cards/{id}`, `DELETE /cards/{id}` | Xem, sửa và xóa thẻ |
| `GET /cards/{id}/schedule` | Xem trước lịch cho bốn mức đánh giá, không ghi lượt ôn |
| `GET /cards/{id}/reviews` | Lịch sử ôn mới nhất trước, phân trang bằng `before_id` |
| `GET /cards/due` | Thẻ đến hạn đang hoạt động, lọc bộ thẻ và giới hạn số lượng |

Danh sách có giới hạn mặc định 50, tối đa 100. Response của danh sách quản lý chứa `items` và `next_cursor`; lịch sử dùng giá trị `next_cursor` làm `before_id` ở lần gọi tiếp. Danh sách thẻ đến hạn giữ response dạng mảng.

Gửi `{"suspended":true}` để tạm ngừng thẻ. Khi bật lại, thẻ tiếp tục dùng lịch đã lưu. Sửa nội dung thẻ giữ thông số FSRS hiện có. Xóa bộ thẻ sẽ chuyển thẻ về trạng thái chưa phân loại, còn xóa một thẻ sẽ xóa cả lịch sử ôn của thẻ đó.

Migration mới giữ lịch ôn của thẻ cũ, gán `deck_id=null` và `suspended=false`. Lịch xem trước được tính tại thời điểm truy vấn và có thể thay đổi nếu người dùng ôn thẻ trước khi gửi đánh giá.

### Tài khoản và phiên đăng nhập

Đăng ký/đăng nhập trả `access_token`, `refresh_token`, `session_id` và `expires_in`. Access token có hiệu lực 15 phút, phiên refresh có thời hạn cố định 30 ngày từ lúc đăng nhập.

| API | Chức năng |
|---|---|
| `GET /me`, `PATCH /me` | Xem/sửa tên hiển thị, múi giờ IANA, CEFR và mục tiêu ngày |
| `POST /auth/refresh` | Đổi refresh token lấy cặp token mới |
| `GET /auth/sessions` | Xem các phiên đăng nhập còn hoạt động |
| `DELETE /auth/sessions/{session_id}` | Đăng xuất một phiên, thu hồi access và refresh token của phiên đó |
| `POST /auth/logout-all` | Đăng xuất tất cả thiết bị |
| `POST /auth/password` | Đổi mật khẩu với current_password và new_password, thu hồi tất cả phiên cũ |

Frontend phải gửi refresh tuần tự và thay refresh token ngay sau khi nhận cặp mới. Dùng lại refresh token đã tiêu thụ sẽ thu hồi cả phiên tương ứng, kể cả token mới nhất. Nếu mất phản hồi refresh và không còn token hợp lệ, người dùng cần đăng nhập lại. Backend chỉ lưu mã băm của refresh token.

API tiến độ dùng múi giờ trong hồ sơ khi không truyền timezone_name. Tạo phiên Talk dùng CEFR của hồ sơ khi không truyền cefr_level. Người dùng cũ được gán mặc định Asia/Ho_Chi_Minh, A2 và mục tiêu 10 hoạt động/ngày.

JWT của bản cũ được tiếp nhận tới khi hết hạn hoặc người dùng đổi mật khẩu/đăng xuất toàn bộ. WebSocket kiểm tra token lại mỗi lượt nói; sau khi refresh access token, frontend mở kết nối đã xác thực mới.
