# WordSpeak Frontend

Ứng dụng Next.js 14 App Router, React 18, TypeScript strict và Tailwind CSS. Giao diện dùng tiếng Việt, giữ IPA và nội dung luyện tiếng Anh.

## Chạy trên localhost

Dùng Node.js 22 trở lên và Python. Từ thư mục gốc của dự án, chạy lệnh bên dưới để mở giao diện, FastAPI và AI service cùng lúc. Lệnh tạo môi trường Python, cài các gói cần thiết và cập nhật SQLite ở lần chạy đầu tiên. Nếu chưa có `frontend/node_modules`, chạy `npm install` một lần trong thư mục frontend.

```powershell
python frontend/scripts/local.py --build
```

Nếu PowerShell trên máy hiện tại chỉ nhận alias Python của Microsoft Store, dùng Python đã cài trên máy:

```powershell
& "$env:LOCALAPPDATA/Programs/Python/Python314/python.exe" frontend/scripts/local.py --build
```

Khi terminal hiện địa chỉ, mở [WordSpeak](http://localhost:3000) và chọn **Đăng ký**. Tài khoản được lưu trong `%LOCALAPPDATA%/WordSpeak/wordspeak.db` trên Windows. Dùng lại lệnh bỏ `--build` khi giao diện chưa thay đổi. Bấm Ctrl+C để dừng cả ba dịch vụ.

### Chạy riêng frontend

Khi backend đã chạy ở cổng 8000, có thể chạy chế độ phát triển từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở [WordSpeak](http://localhost:3000). Phiên bản production tự build bằng `npm run build` rồi `npm start`. Nếu dùng pnpm, lockfile được tạo bằng pnpm 11, dùng `pnpm install --frozen-lockfile` và `pnpm dev`.

Trên máy Windows đã có dependencies nhưng PowerShell chưa nhận lệnh `node` hoặc `npm`, có thể dùng runtime Node đi kèm Codex. Chạy từ `frontend/`:

```powershell
$runtime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
$env:Path = "$runtime/bin;$env:Path"
& "$runtime/bin/node.exe" 'node_modules/next/dist/bin/next' dev
```

Auth, chấm ngữ âm, phiên Talk và số liệu tài khoản dùng FastAPI tại `http://localhost:8000` theo mặc định. Chạy Docker Compose hoặc dịch vụ riêng theo [README của dự án](../README.md). Khi mở qua Nginx trên cổng 8080, frontend mặc định dùng `/api`. Nếu dùng địa chỉ khác, đặt `NEXT_PUBLIC_API_URL` trước khi chạy dev hoặc build frontend. Biến này là URL công khai. Backend cần cho phép origin của frontend qua `CORS_ORIGINS`.

Micro cần HTTPS hoặc localhost và quyền của trình duyệt. Chrome và Edge hỗ trợ luồng chính. Nhận dạng trình duyệt, giọng mẫu bản đồ IPA và phát lại phản hồi gia sư phụ thuộc tính năng giọng nói sẵn có trên thiết bị. Sáu mẫu nghe ngữ điệu và các mẫu từ điển đi kèm ứng dụng.

## Các màn hình và luồng

| Khu vực | Route và hành vi |
| --- | --- |
| Tài khoản | Khách được đưa tới `/dang-nhap`. Đăng nhập hoặc đăng ký thành công sẽ mở trang chủ. Hồ sơ ở `/ho-so`. |
| Luyện ngữ âm | `/luyen-ngu-am` có 10 âm mục tiêu, bài từ/cụm, đồ hình môi–lưỡi, micro, waveform, nghe lại và **Kiểm tra**. Quá trình kiểm tra gửi WAV mono 16 kHz qua WebSocket. |
| Bản đồ IPA | `/ipa` có 44 âm, bộ lọc nhóm/âm hay nhầm, từ mẫu có nút nghe và đánh dấu từng âm đã luyện. |
| Luyện ngữ điệu | `/luyen-ngu-dieu` có bốn chủ điểm và sáu mẫu nghe. Người học theo dõi đường cao độ, chọn **Nghe lại bản thu** để phát bản vừa thu và so sánh hai lượt gần nhất. |
| Từ điển | `/tu-dien` và `/tu-da-luu` xếp từ theo chủ đề. Nút **Chi tiết** mở nghĩa, ví dụ, audio và thao tác học từ. |
| Hội thoại AI | `/talk` chọn 1–4 từ đã học và trình độ. Dùng giữ phím/nút để nói hoặc bấm ghi rồi dừng. Backend tạo phiên và nhận audio nhị phân. Phản hồi được đọc bằng giọng trình duyệt. |
| Tiến độ và lịch sử | `/tien-do`, `/lich-su` xem hoạt động cục bộ, dữ liệu tài khoản và các lượt Talk đã lưu. Có thể nghe giọng tổng hợp đọc lại lượt nhận dạng/đáp lời trong lịch sử. |
| Giao diện | `/cai-dat` và nút ngoài thanh trên cùng hỗ trợ sáng/tối. Cài đặt có giảm chuyển động và thông tin dữ liệu. |

Mỗi mục từ điển có hai tệp WAV trong `public/audio/dictionary/`, một tệp cho từ và một tệp cho câu ví dụ. Các mẫu do giọng Zira tiếng Anh-Mỹ tổng hợp để phát ngay cả khi trình duyệt thiếu giọng đọc tiếng Anh. Khi thêm mục từ, bổ sung hai tệp theo mẫu `<từ>.wav` và `<từ>-example.wav`.

Từ đã lưu, tên hiển thị, đánh giá từ và lịch sử tự luyện được lưu riêng theo tài khoản trên trình duyệt hiện tại. Bản thu ngữ điệu giữ trong màn luyện. Lịch sử Talk từ backend chứa nội dung đã nhận dạng và phản hồi, vì vậy phần nghe lại ở đây đọc lại nội dung bằng giọng tổng hợp.

Khi AI service gửi gợi ý phát âm trong lượt Talk, nút **Nghe gợi ý phát âm** đọc gợi ý bằng giọng trình duyệt. Nếu gia sư đã trả lời và phần chấm phát âm gặp lỗi, người học vẫn có thể nghe lại gia sư.

Nếu kết nối rớt trước khi gửi tín hiệu kết thúc bản thu, WordSpeak thử kết nối lại một lần và giữ clip để người học có thể gửi lại. Nếu kết nối rớt sau khi gửi tín hiệu kết thúc, người học có thể kiểm tra Lịch sử để biết lượt nói đã được lưu hay chưa.

Trong Luyện ngữ âm, kết quả đã nhận được gắn với bản thu hiện tại. Nếu mất kết nối hoặc bấm **Dừng chờ kết quả** sau khi gửi, ứng dụng giữ bản thu để nghe lại và yêu cầu ghi bản mới trước khi kiểm tra tiếp.

## Khác biệt với kế hoạch Dev 3

Danh sách chỉnh sửa áp dụng ưu tiên cho giao diện. Flashcards, nhắn tin Talk, tải tệp audio, cấu hình thu trong Cài đặt và menu kịch bản demo đã được loại khỏi phiên bản frontend này. Mức lĩnh hội âm trong bản đồ IPA hiển thị dựa trên hoạt động luyện. Danh mục từ điển đi kèm và đánh giá ghi nhớ hoạt động ngay trên thiết bị.

| Đầu việc Excel | Vị trí hoặc cách xử lý |
| --- | --- |
| D3-01 | App Router, `components/shell.tsx`, `lib/api.ts`, ESLint, Prettier và fixture HTTP/WebSocket trong smoke test. |
| D3-02, D3-O1 | MediaRecorder, push-to-talk, waveform và mức thu trong các màn luyện. |
| D3-03 | Bản đồ IPA và dấu đã luyện theo âm. |
| D3-04 | Bỏ Flashcards theo danh sách chỉnh sửa. |
| D3-05, D3-07 | Talk chỉ có giọng nói, gợi ý từ đã học, WebSocket audio và xử lý trạng thái phiên. |
| D3-06 | Phản hồi âm vị, điểm và gợi ý khi dịch vụ trả dữ liệu âm vị. |
| D3-08 | `tests/smoke.mjs` và `scripts/plot_results.py`. Biểu đồ thực nghiệm cần CSV của nhóm. |
| D3-O2 | Tiến độ, chuỗi ngày học, hoạt động gần đây và điểm theo âm từ máy chủ. |

Khung minh họa môi–lưỡi là sơ đồ giáo học tham khảo cách tiếp cận cơ thể của [Adrian Underhill](https://adrianunderhill.com/pronunciation-resources-video-primers/). Âm dễ nhầm là một ví dụ đối chiếu. Khi dịch vụ cung cấp nhãn âm đã nhận dạng, kết quả sẽ dùng nhãn đó. Checkout AI service mặc định trả điểm mẫu và thiếu `/transcribe`, vì vậy giao diện hiển thị thiếu dữ liệu âm vị và thiếu nhận dạng thay vì trình bày điểm mẫu. Talk hỗ trợ tùy chọn nhận dạng từ trình duyệt khi thiết bị có hỗ trợ. Gia sư vẫn cần cấu hình LLM hoạt động. Kết quả âm vị đầy đủ cần AI service thực.

Ở Luyện ngữ âm, có thể bật **Đối chiếu từ bằng nhận dạng của trình duyệt** trước khi ghi âm. Ví dụ khi luyện *she* và trình duyệt nhận dạng *see*, kết quả hiển thị sơ đồ tham chiếu của cả hai từ. Phần này dùng kết quả nhận dạng từ và không cung cấp điểm âm vị. Tính khả dụng tùy trình duyệt và một số trình duyệt gửi tiếng nói đến máy chủ của nhà cung cấp để nhận dạng. [Tài liệu Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition)

Khi kết quả chấm trả âm thay thế đã có sơ đồ, hoặc chế độ đối chiếu từ nhận ra một cặp âm đã định nghĩa, bấm **Xem mô phỏng hai âm** để thấy hai hình chuyển động đồng thời. Nếu hệ điều hành hoặc cài đặt WordSpeak yêu cầu giảm chuyển động, hai hình giữ nguyên ở tư thế tham chiếu.

## Kiểm thử

```powershell
npm run lint
npm run typecheck
npm run format:check
npm run build
npx playwright install chromium
npm run test:e2e
```

Khởi động frontend ở cổng 3000 trước khi chạy smoke test. Test dùng fixture HTTP/WebSocket theo OpenAPI và thiết bị micro giả của Chromium, giúp kiểm tra giao diện độc lập với AI service. Có thể đặt `WORDSPEAK_TEST_URL`, `WORDSPEAK_TEST_API` và `WORDSPEAK_CHROMIUM` để trỏ tới địa chỉ hoặc executable có sẵn. Các lượt được kiểm thử chỉ chạy với fixture trong tiến trình kiểm thử.

### Nghiệm thu kết nối AI

Chạy frontend với backend, AI service và LLM của môi trường kiểm thử. Dùng một tài khoản kiểm thử đã đăng ký. Lệnh dưới đây chạy qua giao diện và WebSocket của cấu hình hiện tại. Lệnh tạo phiên Talk và có thể lưu lượt luyện vào tài khoản đó.

```powershell
$credential = Get-Credential -Message 'Tài khoản WordSpeak dành cho kiểm thử'
$env:WORDSPEAK_LIVE_EMAIL = $credential.UserName
$env:WORDSPEAK_LIVE_PASSWORD = $credential.GetNetworkCredential().Password
try { npm run test:e2e:live }
finally { Remove-Item Env:WORDSPEAK_LIVE_EMAIL, Env:WORDSPEAK_LIVE_PASSWORD }
```

Kịch bản dùng mẫu nghe `she.wav` làm đầu vào của micro trình duyệt để tái lập phép thử. Có thể đặt `WORDSPEAK_LIVE_AUDIO` tới bản WAV khác chứa từ *she*. Kết quả đạt khi dịch vụ trả điểm hợp lệ cho /ʃ/, Talk có cả transcript từ máy chủ và lời gia sư, đồng thời lượt xuất hiện trong Lịch sử. Đây là kiểm tra kết nối và hợp đồng dữ liệu. Độ chính xác của mô hình cần được đo bằng bộ dữ liệu thực nghiệm của nhóm.

## Biểu đồ số liệu thực nghiệm

Từ gốc repository, dùng Python có matplotlib:

```powershell
python frontend/scripts/plot_results.py --input results --output docs/figures
```

CSV có cột `label` hoặc `model` và một hoặc nhiều cột `per`, `wer`, `gop_correlation`, `latency_ms`. PER và WER dùng đơn vị phần trăm; tương quan nằm trong khoảng −1 đến 1; độ trễ tính bằng mili giây. Script xuất PNG và PDF theo cột có dữ liệu. Bộ thu số liệu và các kết quả thực nghiệm cần chạy trên cấu hình nhóm đã chốt.
