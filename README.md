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
- `GET /sessions` và `GET /sessions/{id}/turns` trả `{items, next_cursor}` thuộc người dùng hiện tại, phân trang mới nhất trước bằng `before_id` và `limit`. Một phiên chỉ xử lý một lượt Talk tại một thời điểm. Request trùng thời gian trả 409 hoặc `session_busy`.
- Sau sự kiện `transcript`, Talk và chấm phát âm chạy song song. `done` kết thúc phản hồi Talk, `final` trả kết quả chấm và có thể tới sau `done`. Nếu chấm lỗi, backend phát `assessment_unavailable` và vẫn cho Talk hoàn thành.
- Sự kiện `coaching` chứa `errors` và `hints` do AI service cung cấp, frontend hiển thị khi kết quả chấm tới. Phản hồi Talk được giới hạn tối đa 40 từ bằng bộ lọc streaming.
- `GET /progress?timezone_name=Asia/Ho_Chi_Minh` trả streak và dữ liệu `daily` theo ngày địa phương. Có thể truyền múi giờ IANA khác, mặc định là Việt Nam.

- Gọi `POST /auth/register` hoặc `POST /auth/login` để lấy JWT. Gửi JWT qua header `Authorization: Bearer <token>` cho API flashcard, Talk và tiến độ.
- Phòng Talk dạng văn bản dùng `POST /sessions`, sau đó `POST /chat/stream` với `request_id` dạng UUID, `session_id` và `text`. Đọc sự kiện SSE `token`, `done` và `error`.
- Với audio, gửi `{"type":"auth","token":"<JWT>"}` vào `/ws/audio` trong 10 giây đầu và chờ sự kiện `authenticated`. Sau đó gửi các chunk nhị phân và kết thúc bằng `{"type":"end","request_id":"<UUID>","media_type":"audio/webm"}`. Thêm `text` khi có câu mẫu hoặc `session_id` khi cần phản hồi Talk. Giao thức đầy đủ nằm trong `docs/openapi.yaml`.
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

Sau cập nhật, chạy `alembic upgrade head` (hiện tại là `0012_request_cancellation`). Bộ đếm dùng chung DB và cửa sổ một phút. Đăng ký giới hạn 5 lần/IP, đăng nhập 30 lần/IP và 10 lần/email, tạo phiên 20 lần/tài khoản, gọi AI 20 lượt/tài khoản, mở WebSocket 30 lần/IP. HTTP trả 429 kèm Retry-After. WebSocket trả rate_limited.

WebSocket yêu cầu xác thực trước audio, giới hạn 8 MiB/lượt, thời gian thu tối đa 120 giây và xử lý tối đa 180 giây. Token được kiểm tra lại mỗi lượt. Hợp đồng này yêu cầu frontend cập nhật bước xác thực đầu kết nối.

Backend chỉ publish cổng 8000 trên localhost. AI service dùng mạng nội bộ Compose. Khi chạy sau reverse proxy, cấu hình FORWARDED_ALLOW_IPS của Uvicorn đúng địa chỉ proxy được tin cậy để limiter nhận IP người dùng. Triển khai public cần TLS tại ingress và thử lại HTTPS/WSS.

### Tiến độ hoàn thiện backend demo

- Đã bổ sung xác thực đầu WebSocket, hạn thời gian, bộ đếm request dùng chung DB và kiểm tra token giữ khóa tại thời điểm ghi lượt Talk.
- Đã bổ sung bộ thẻ, tìm kiếm/phân trang flashcard, sửa/xóa thẻ, tạm ngừng ôn, xem trước lịch và lịch sử đánh giá.
- Đã bổ sung hồ sơ người học, refresh token luân chuyển, danh sách/thu hồi phiên đăng nhập và đổi mật khẩu.
- Đã bổ sung lịch sử phát âm phân trang, chi tiết điểm/lỗi/gợi ý và liên kết phiên Talk. Lượt mới phân biệt câu mẫu với transcript STT.
- Đã bổ sung request_id bắt buộc cho audio/Talk, tra cứu trạng thái và phát lại kết quả đã lưu khi mất phản hồi, không gọi AI lại bằng cùng mã.
- Đã bổ sung quên/đặt lại mật khẩu, xác minh email và worker gửi email từ hàng đợi DB có thử lại khi lỗi.
- Đã bổ sung tiêu đề phiên Talk, tìm kiếm/phân trang phiên và hội thoại, sửa bài học và xóa phiên cùng các bản sao phản hồi.
- Đã bổ sung buổi ôn có hàng đợi lưu trong DB, tiếp tục sau tải lại trang, kết thúc sớm và tổng kết đánh giá.
- Đã bổ sung hủy request audio/Talk, đóng luồng AI khi nhận thấy trạng thái hủy và giữ kết quả đã commit.
- Đang hoàn thiện dashboard và quản lý dữ liệu cá nhân.
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

### Lịch sử luyện phát âm

- `GET /attempts`: lịch sử mới nhất trước, phân trang bằng `before_id` và `limit` (mặc định 50, tối đa 100). Response gồm `items` và `next_cursor`. Có thể lọc `session_id` và tìm câu chấm bằng `q` (ký tự `%`/`_` được tìm như văn bản).
- `GET /attempts/{attempt_id}`: chi tiết kết quả, bao gồm điểm từng từ/âm vị, lỗi và gợi ý trong `assessment`. Chỉ chủ sở hữu được xem. Trả 404 khi không tìm thấy lượt của người dùng hiện tại.
- Sự kiện audio `final` có thêm `attempt_id` sau khi lưu thành công. Sự kiện `transcript` có `text_source=reference` khi dùng câu mẫu hoặc `stt` khi gọi nhận dạng giọng nói.
- `assessment_text` là câu đã gửi đi chấm. Nếu gửi `text` trong message `end`, backend lưu vào `reference_text` và không gọi STT; `transcript` là null. Nếu không gửi câu mẫu, `transcript` chứa kết quả STT và `reference_text` là null. Luồng Talk hiện cũng sử dụng câu đã gửi đi chấm.
- Lượt cũ chỉ có câu chấm được giữ nguyên, không suy đoán đó là câu mẫu hay transcript. Trường nguồn và phiên Talk cũ là null. Chi tiết cũ sai định dạng trả `assessment=null`, không tạo điểm hoặc lỗi phát âm thay thế.
- Thời gian trả về theo UTC. `attempt_id` là mã tra cứu kết quả; `request_id` do client tạo là mã chống gửi trùng.

### Gửi lại audio/Talk sau gián đoạn

1. FE tạo UUID cho mỗi lượt mới và giữ nguyên `request_id` nếu gửi lại lượt đó. Với audio, phải giữ cùng bytes audio, câu mẫu, định dạng và phiên Talk. Việc chia lại chunk không thay đổi lượt.
2. `GET /requests/{request_id}` yêu cầu JWT và chỉ trả request của tài khoản hiện tại. Response có `status` (`running`, `completed`, `failed`, `cancelled`) và `events` đã lưu. 404 nghĩa là chưa tìm thấy request được chấp nhận cho tài khoản này.
3. Request đang chạy trả HTTP 409 `request_processing` với `Retry-After: 2`, hoặc sự kiện lỗi WebSocket cùng mã. Chờ rồi tra cứu lại. Dùng lại UUID với nội dung khác trả `request_conflict`.
4. Request đã kết thúc sẽ phát lại kết quả có `replayed=true`, không gọi STT/LLM/chấm điểm và không tạo thêm lượt luyện. Trước khi hiển thị replay, FE xóa phần text tạm của request đó. Replay Talk gửi một `token` chứa toàn bộ câu trả lời, sau đó `done` với `turn_id` đã lưu.
5. `done` và `final` được lưu trong cùng transaction với bản ghi hội thoại/lượt luyện. `events` không chứa token tạm. Khi Talk thành công nhưng chấm điểm thất bại (hoặc ngược lại), trạng thái là `failed` và phần kết quả thành công vẫn có thể xem lại.
6. Mất kết nối/hủy tác vụ trước khi xong đánh dấu `request_interrupted`. Nếu tiến trình bị dừng đột ngột, lần tra cứu hoặc gửi lại sau hạn 4 phút đánh dấu `request_expired`. Worker cũ không được ghi kết quả sau hạn đó. Khóa phiên Talk tự hết hạn sau tối đa 5 phút nếu tiến trình không dọn được.

Request đã được chấp nhận không tự chạy lại dưới cùng UUID, kể cả khi thất bại hoặc bị hủy. Sau khi xem trạng thái và phần kết quả đã lưu, người dùng có thể chủ động tạo lượt mới với UUID mới. Request bị từ chối trước khi chấp nhận do phiên bận, không thuộc quyền sở hữu hoặc hết giới hạn không giữ mã trong DB.

Bộ kiểm thử hiện kiểm tra gửi lại, xung đột nội dung, quyền truy cập, mất phản hồi sau commit, lỗi từng dịch vụ, hủy tác vụ và hai worker tranh cùng mã trên SQLite. Vẫn cần kiểm thử các giao dịch đồng thời trên PostgreSQL thật trước khi nghiệm thu triển khai.

### Khôi phục tài khoản và xác minh email

| API | Chức năng |
|---|---|
| `POST /auth/forgot-password` | Gửi `{email}` để yêu cầu link khôi phục. Luôn trả cùng phản hồi 202 cho email tồn tại và không tồn tại khi cấu hình hợp lệ |
| `POST /auth/reset-password` | Gửi `{token, new_password}`; thành công trả 204, thu hồi mọi phiên đăng nhập và link tài khoản cũ |
| `POST /auth/verification/request` | Yêu cầu JWT; xếp hàng email xác minh của chính tài khoản hiện tại, trả 202 |
| `POST /auth/verify-email` | Gửi `{token}`; thành công trả 204 và đặt `email_verified=true` trong hồ sơ |

Token đặt lại mật khẩu có hạn 30 phút, token xác minh email có hạn 24 giờ và chỉ được dùng một lần đúng mục đích. API trả 400 nếu token sai, hết hạn, đã dùng hoặc bị vô hiệu hóa. Đổi mật khẩu/đăng xuất tất cả cũng vô hiệu hóa các link tài khoản được tạo trước đó. Đặt lại mật khẩu không tự đăng nhập và không tự đánh dấu email đã xác minh. Tài khoản hiện vẫn sử dụng tính năng học khi chưa xác minh email; FE có thể nhắc người dùng xác minh dựa trên `GET /me`.

Yêu cầu khôi phục giới hạn 10 lần/IP/phút và 3 lần/email/phút. Yêu cầu xác minh giới hạn 3 lần/tài khoản/phút. Các API tiêu thụ token giới hạn 20 lần/IP/phút cho mỗi loại. 202 chỉ xác nhận tiếp nhận yêu cầu, không xác nhận email đã đến hộp thư. Thiếu cấu hình email trả 503 trước khi kiểm tra email có tồn tại.

Cấu hình trong `.env` theo `.env.example`:

- `APP_PUBLIC_URL`: địa chỉ FE tin cậy dùng tạo link, HTTPS khi public; HTTP chỉ được chấp nhận với localhost/loopback. Backend không tạo link từ Host header.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`: máy chủ và địa chỉ gửi.
- `SMTP_SECURITY`: `starttls` (mặc định), `ssl`, hoặc `plain` chỉ dùng với SMTP thử nghiệm trong môi trường cô lập.
- `SMTP_USERNAME`, `SMTP_PASSWORD`: cùng điền hoặc cùng để trống, tùy SMTP server.

Sau migration và cấu hình SMTP, chạy worker riêng:

```powershell
docker compose --profile email up -d --build mail-worker
```

Không dùng Docker: từ thư mục `backend`, đặt cùng `DATABASE_URL`, `JWT_SECRET` và cấu hình SMTP như API rồi chạy `python -m app.mail_worker`. Có thể dùng `python -m app.mail_worker --once --limit 100` để xử lý các thư đang đến hạn rồi thoát. Worker không tự nạp file `.env` khi chạy ngoài Compose.

Hàng đợi chỉ lưu mã băm token. Worker tái tạo token bằng HMAC với `JWT_SECRET`, UUID ngẫu nhiên và ngữ cảnh tài khoản; không lưu hoặc ghi log token thô. Thay `JWT_SECRET` khiến các thư chưa gửi với khóa cũ bị đánh dấu lỗi; người dùng cần yêu cầu link mới. Worker thử gửi tối đa 5 lần, giãn thời gian 30/60/120/240 giây. Nếu worker dừng, worker khác có thể nhận lại thư sau 2 phút. SMTP có thể giao trùng thư nếu tiến trình dừng ngay sau khi server nhận email, nhưng token vẫn chỉ dùng được một lần. Giữ nguyên `Message-ID` cho các lần gửi lại.

FE cần trang `/reset-password` và `/verify-email`. Token nằm trong URL fragment `#token=...`; FE đọc, xóa fragment khỏi thanh địa chỉ và gửi token qua body POST tương ứng. Không gọi GET để tiêu thụ token, tránh trình quét link email tự thực hiện thao tác.

Đã kiểm thử gửi thư tới SMTP giả lập trên localhost, thử lại sau lỗi, khôi phục worker bị dừng, token dùng một lần và hai yêu cầu đặt lại mật khẩu đồng thời trên SQLite. Chưa nghiệm thu SMTP nhà cung cấp thật, các trang FE nhận link và PostgreSQL đồng thời.

### Quản lý phiên Talk

- `POST /sessions` nhận thêm `title` tùy chọn. Nếu bỏ trống, tiêu đề lấy từ chủ đề hoặc `New conversation`. Response có `title`, `started_at` (UTC), `processing`, `topic`, `cefr_level` và `id`.
- `GET /sessions`: trả `items` và `next_cursor`, thứ tự ID giảm dần (phiên tạo mới nhất trước). Có `before_id`, `limit` (mặc định 50, tối đa 100) và `q` tìm trong tiêu đề/chủ đề. `%` và `_` được tìm như ký tự thường.
- `GET /sessions/{id}`: xem chi tiết phiên của mình. `PATCH /sessions/{id}` cho phép sửa `title`, `topic`, `cefr_level`. Đổi tiêu đề không thay đổi chủ đề gửi tới AI. Khi `processing=true`, chỉ cho phép đổi tiêu đề; sửa chủ đề/CEFR trả 409.
- `GET /sessions/{id}/turns`: cùng dạng `{items, next_cursor}` và tham số `before_id`, `limit`, trả lượt mới nhất trước. FE cần đảo thứ tự từng trang khi hiển thị hội thoại từ cũ đến mới, rồi chèn các trang cũ lên đầu.
- `DELETE /sessions/{id}`: trả 204 sau khi xóa phiên và hội thoại. Lượt phát âm vẫn được giữ, với `session_id=null`. Kết quả request gắn với phiên được thay bằng lỗi `session_deleted`, giữ UUID để chống thực hiện lại. Gửi lại request với phiên đã xóa trả 404. Phiên đang xử lý trả 409 và chưa xóa gì.

Đây là thay đổi response của hai API danh sách: FE dùng `response.items` thay cho mảng trực tiếp. Lượt cũ và các trạng thái FSRS không bị thay đổi.

Migration `0010_talk_management` đặt tiêu đề cho phiên cũ và liên kết request cũ qua bản ghi hội thoại/lượt phát âm đã lưu. Các snapshot dở dang không xác định được phiên chỉ giữ lỗi, bỏ transcript tạm và chuyển sang `failed`; bản ghi hội thoại/lượt phát âm đã lưu vẫn còn. Dừng worker/API cũ trước khi chạy migration rồi khởi động phiên bản mới.

### Buổi ôn tập

1. `POST /study-sessions` với `{request_id, deck_id?, limit?}` chọn các thẻ đang đến hạn, không tạm ngừng, ưu tiên thẻ quá hạn lâu nhất. `request_id` là UUID; `limit` mặc định 20, tối đa 100. Mỗi tài khoản chỉ có một buổi đang hoạt động. Request khác khi đang có buổi ôn trả 409 kèm `study_session_id`; gửi lại cùng UUID và cùng lựa chọn trả lại buổi đó.
2. `GET /study-sessions/{id}` trả tổng kết hiện tại và `queue` để tiếp tục sau tải lại trang. Danh sách chọn lúc bắt đầu được giữ cố định; thẻ mới không tự thêm vào buổi đang học. Nếu không có thẻ phù hợp, buổi ôn hoàn tất ngay với số lượng 0.
3. Gửi `POST /reviews` như trước, thêm `study_session_id`. Mỗi thẻ trong buổi chỉ được đánh giá một lần. Gửi lại cùng `request_id` của lượt đánh giá trả lại kết quả cũ, kể cả sau khi buổi đã kết thúc. Dùng mã mới để chấm lại một thẻ đã hoàn thành trong cùng buổi trả 409. Thay đổi `study_session_id` nhưng giữ mã đánh giá cũ cũng trả 409.
4. Buổi ôn tự hoàn tất khi hết thẻ chờ. `POST /study-sessions/{id}/finish` kết thúc sớm, đánh dấu phần còn lại là bỏ qua, không thay đổi lịch ôn. Gọi lại endpoint này giữ nguyên thời gian kết thúc và tổng kết.
5. `GET /study-sessions` liệt kê tổng kết mới nhất trước với `items`, `next_cursor`, `before_id`, `limit` (mặc định 20, tối đa 100) và bộ lọc `status=active|completed`.

Tổng kết có `selected`, `reviewed`, `skipped`, `remaining`, số lần chọn `again/hard/good/easy`, `skipped_reasons`, thời gian bắt đầu/kết thúc UTC và `elapsed_seconds`. Đây là thời gian từ lúc bắt đầu đến lúc kết thúc, bao gồm thời gian nghỉ, không phải phép đo thời gian học chủ động.

Khi mở lại buổi ôn, thẻ bị xóa, tạm ngừng hoặc đổi lịch (ví dụ được ôn ngoài buổi hiện tại) được bỏ qua với lý do `card_deleted`, `card_suspended` hoặc `schedule_changed`. Thẻ được ôn ngoài buổi không được tính thành lượt hoàn thành của buổi đó. Kết thúc sớm dùng lý do `ended_early`.

FSRS vẫn áp dụng cho từng lượt đánh giá: chọn Again hẹn lại sau 10 phút, thẻ được tính đã đánh giá trong buổi hiện tại và có thể xuất hiện ở buổi mới khi đến hạn. Xóa thẻ vẫn giữ thống kê đánh giá của buổi; xóa bộ thẻ giữ hàng đợi hiện có và đặt `deck_id=null`. Thống kê không giữ nội dung thẻ đã xóa. Migration giữ nguyên các lượt đánh giá cũ với `study_session_id=null`.

Tạo buổi mới giới hạn 20 lần/tài khoản/phút. Bộ kiểm thử có tranh chấp tạo buổi và chấm cùng thẻ từ hai worker trên SQLite; vẫn cần nghiệm thu các giao dịch này trên PostgreSQL.

### Hủy lượt AI

`POST /requests/{request_id}/cancel` yêu cầu JWT của chủ request, không cần body. Dùng API này cho cả SSE Talk và WebSocket audio trong lúc đang chờ STT, LLM hoặc chấm điểm. Response trả cùng cấu trúc với API tra cứu request.

- Request đang chạy chuyển sang `cancelled`, thêm sự kiện lỗi `request_cancelled` và giải phóng đúng khóa phiên Talk của lượt đó. Gửi lại lệnh hủy không tạo thêm sự kiện. Có thể bắt đầu lượt mới với UUID mới.
- Kết quả đã commit trước khi hủy vẫn nằm trong `events` và lịch sử. Ví dụ Talk đã trả `done` nhưng đang đợi chấm điểm: phản hồi Talk được giữ, chưa tạo lượt phát âm. Nếu toàn bộ kết quả đã commit trước lệnh hủy, API trả `completed` và không xóa kết quả.
- Worker kiểm tra trạng thái qua kết nối DB riêng, khoảng 250 ms giữa các lần kiểm tra trong lúc chờ AI. Khi thấy đã hủy, worker ngừng nhận token, hủy tác vụ I/O và đóng kết nối tới dịch vụ AI. Thời gian thực tế còn phụ thuộc DB/network; đây không phải cam kết SLA. Nhà cung cấp AI có thể vẫn tiếp tục tính toán sau khi kết nối bị đóng.
- SSE/WebSocket đang mở nhận lỗi `request_cancelled`. FE nên bỏ phần text tạm chưa có `done`, đồng thời dùng `events` từ response hủy/tra cứu để giữ các kết quả đã lưu. Token đã gửi trước khi worker nhận thấy yêu cầu hủy có thể vẫn tới client.
- Worker cũ không được ghi thêm kết quả hoặc giải phóng khóa của lượt mới. Hủy request không thuộc tài khoản hoặc không tồn tại trả 404. Request đã kết thúc giữ trạng thái cũ; request đã quá hạn chuyển sang `failed` với lỗi `request_expired`.

Migration `0012_request_cancellation` lưu mã khóa phiên trên các request mới. Request có từ trước migration không có mã này, nên lệnh hủy không tự giải phóng khóa cũ; khóa sẽ hết hạn theo cơ chế hiện có. Dừng API cũ trước migration và khởi động phiên bản mới để dùng đầy đủ chức năng.

Kiểm thử bao gồm HTTP hủy trong khi WebSocket/SSE đang chạy, hủy ở từng giai đoạn AI, giữ kết quả thành công một phần, hủy cạnh tranh với commit, khóa phiên cũ/mới và timeout khi client đọc chậm. Các dịch vụ AI trong kiểm thử vẫn được giả lập; cần nghiệm thu hủy kết nối với dịch vụ triển khai thật.
