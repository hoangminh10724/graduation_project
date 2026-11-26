# WORDSPEAK
## Đặc tả tính năng và bàn giao UI/UX – Frontend

**Khóa tự học.** Gửi cùng một ZIP cho frontend và backend. Mở [bảng đối chiếu giáo trình](COURSE_COVERAGE.md), sau đó dùng [hướng dẫn tích hợp](COURSE_HANDOFF.md). Frontend có thể chạy ngay bốn màn hình Today, Library, My Words và Progress tại `/demo/course`. Trong buổi ghép hệ thống, thử hai bài `ship-01` và `use-53`, kiểm tra nhập IPA trên điện thoại, lỗi micro, lưu tiến độ theo tài khoản và bài ôn hôm sau.

**Cập nhật ngày 24/11/2026.** Trong mục Phrases & conversation, sau khi dừng thu, mỗi bản ghi hiển thị phản hồi ngay dưới trình phát. Bài luyện câu kiểm tra một dấu hiệu âm học theo mục tiêu đã chọn. Lượt hội thoại kiểm tra âm được hỗ trợ trong cụm từ đang luyện. Giao diện nêu rõ dấu hiệu phù hợp, điều nên thử lại, trường hợp chưa đủ bằng chứng và lỗi dịch vụ. Hướng dẫn này thay cho mô tả chỉ tự nghe lại ở các mục cũ bên dưới.

**Cập nhật phạm vi ngày 21/11/2026:** người dùng chọn General American. Demo hiện
mở rộng thành 41 mục luyện chính (17 mục nguyên âm và 24 phụ âm), thêm 6 tổ hợp
nguyên âm với /ɹ/. Dùng /i u oʊ/ và tham chiếu r-colored theo tiếng Anh Mỹ.
Các đoạn bên dưới ghi “10 âm” thuộc bản đặc tả gốc ngày 19/11; số lượng và
phạm vi hiện hành lấy từ /demo/config và [AMERICAN_SOUND_EXPANSION.md](AMERICAN_SOUND_EXPANSION.md).
Frontend phải dùng cấu hình động và giữ nhãn nhận dạng đang thử nghiệm.

Phiên bản 1.0 • Ngày 19/11/2026 • Ngôn ngữ giao diện đề xuất: tiếng Việt, giữ nguyên từ luyện và ký hiệu IPA tiếng Anh.

Đối tượng sử dụng tài liệu: thành viên thiết kế UI/UX, lập trình frontend và AI hỗ trợ triển khai. Phạm vi: toàn bộ sản phẩm WordSpeak theo kế hoạch dự án, đồng thời phân biệt rõ khả năng hiện có của demo và phần cần xây dựng tiếp.

## 1. Mục tiêu và cách dùng tài liệu

WordSpeak hỗ trợ người Việt luyện nói tiếng Anh thông qua luyện âm, tham chiếu khẩu hình, luyện trọng âm – ngữ điệu, hội thoại với AI và ôn từ vựng. Giá trị cốt lõi của màn hình luyện phát âm là giúp người học hiểu ba việc: hệ thống có thể đã nghe thấy gì; khác mục tiêu ở đâu; nên thử thay đổi nhỏ nào ở lần tiếp theo.

Đọc mục 2 trước khi thiết kế. Dùng mục 4–10 để dựng màn hình và trạng thái. Dùng mục 11–13 để kết nối dữ liệu và nghiệm thu. Mục 14 có prompt mẫu; bản prompt riêng đi kèm có thể gửi trực tiếp cho AI. Mục 15 là kế hoạch hoàn thiện cuối tháng 11.

Đây là đặc tả sản phẩm và đề xuất thiết kế, không phải xác nhận mọi chức năng đã triển khai. Thông tin trạng thái được đối chiếu với mã nguồn và tài liệu hiện có trong workspace, không suy ra từ ảnh giao diện hay tiến độ dự kiến.

## 2. Hiện trạng, nền tảng và phạm vi

### 2.1. Quy ước trạng thái

| Mã | Ý nghĩa | Cách xử lý khi thiết kế và lập trình |
|---|---|---|
| A | Đã có trong demo local và có kiểm tra chức năng | Giữ hành vi cốt lõi; có thể thiết kế lại giao diện và chuyển sang frontend chính. |
| B | Có mã API trong bản tích hợp hoặc có hợp đồng; chưa xác nhận đang chạy cùng frontend chính | Dựng trạng thái và adapter; chỉ đánh dấu tích hợp xong khi thử với dịch vụ thực tế. |
| C | Nằm trong kế hoạch, chưa có triển khai hoàn chỉnh được xác nhận | Dùng dữ liệu mẫu có nhãn ở môi trường phát triển; chuẩn bị trạng thái chưa khả dụng cho bản chạy thật. |
| D | Đề xuất giai đoạn sau | Không đưa vào phạm vi bắt buộc của đợt hoàn thiện tháng 11. |

Demo hoạt động tại http://127.0.0.1:8013/demo. Đây là địa chỉ trên máy phát triển, không phải đường dẫn triển khai dùng chung cho mọi thành viên.

Frontend hiện tại trong repository dùng Next.js 14, React, TypeScript và Tailwind CSS; trang chính còn là khung đơn giản. Demo AI dùng HTML, CSS và JavaScript riêng trong ai-service. Bản kế hoạch dạng ảnh có nhắc Flutter/mobile, nhưng repository được rà soát chưa có ứng dụng Flutter hoàn chỉnh. Đợt bàn giao này ưu tiên web responsive trên nền hiện có; nếu nhóm chuyển sang Flutter cần chốt riêng, không để AI tự tạo thêm một ứng dụng khác.

Backend tại checkout gốc còn đơn giản. Một bản tích hợp trong workspace, commit 3774a6c, có router đăng nhập, thẻ ôn tập, hội thoại và tiến độ. Tài liệu chỉ ghi nhận mã đó tồn tại; chưa xác nhận các API đã được triển khai hoặc có mặt trên nhánh mà thành viên frontend đang dùng. Trước khi tích hợp cần thống nhất đúng phiên bản backend.

### 2.2. Danh mục tính năng toàn dự án

| ID | Tính năng | Trạng thái | Ưu tiên thiết kế/triển khai |
|---|---|---|---|
| F01 | Đăng ký, đăng nhập, đăng xuất và phiên đăng nhập | B: API xác thực có trong bản tích hợp; giao diện cần làm | P1 |
| F02 | Trang chủ, điều hướng và truy cập luyện thử | C | P0 |
| F03 | Danh mục IPA; lộ trình mở rộng bản đồ 44 âm | A: chọn 10 âm trong demo; C: bản đồ đủ 44 âm và âm mẫu | P0 cho 10 âm; P1 cho danh mục mở rộng |
| F04 | Chọn từ luyện, chọn âm mục tiêu và chế độ từ/cụm có ngữ cảnh | A | P0 |
| F05 | Thu âm, tải tệp, chọn đoạn, phát lại và tải WAV | A | P0 |
| F06 | Chọn micro, tăng mức thu, đo mức âm, cảnh báo nhỏ/vỡ tiếng | A | P0 |
| F07 | Phân tích âm và phản hồi nghe được – khác biệt – điều chỉnh | A; độ chính xác nhận dạng chưa được xác nhận | P0 |
| F08 | Hai thẻ tham chiếu: âm có thể đã phát ra và âm mục tiêu | A | P0 |
| F09 | Minh họa chuyển động, luyện thầm và hướng dẫn mở rộng | A | P0 |
| F10 | Trọng âm từ, nhấn ý trong câu, ngữ điệu, nối âm | A ở mức tự luyện và nghe lại; C cho đánh giá tự động | P0 cho tự luyện |
| F11 | Tra từ: IPA, nghĩa, âm mẫu, ví dụ và chuyển sang luyện | C; chưa có API từ điển hoàn chỉnh được xác nhận | P1 |
| F12 | My Words: tạo thẻ, lưu từ và xem danh sách | B cho tạo thẻ; C cho danh sách toàn bộ/sửa/xóa/tìm kiếm | P1 |
| F13 | Ôn thẻ FSRS với bốn mức ghi nhớ và lịch kế tiếp | B cho API trong bản tích hợp; giao diện cần làm | P1 |
| F14 | Talk bằng văn bản, chủ đề, trình độ và phản hồi dạng streaming | B; phụ thuộc cấu hình LLM thực tế | P1 |
| F15 | Talk bằng giọng nói và nhận xét phát âm trong hội thoại | B/C; còn thiếu nhận dạng lời nói và chấm điểm đã xác thực ở AI service | P1 có điều kiện |
| F16 | Danh sách phiên Talk và xem lại hội thoại | B; cần nối giao diện | P1 |
| F17 | Tiến độ: số lượt luyện, ngày học, dữ liệu theo ngày | B cho API dựa trên Assessment cũ; cần adapter cho demo | P1 có điều kiện |
| F18 | Xuất kết quả luyện âm dạng JSON | A; không kèm audio | P0 |
| F19 | Phát lại ví dụ phát triển và nhận xét giáo viên đã có | A; dữ liệu phát triển, không phải phản hồi mới | Nội bộ; không đưa vào luồng chính của học viên |
| F20 | Trạng thái dịch vụ, tải mô hình, xử lý và lỗi kết nối | A trong demo; cần tích hợp vào frontend | P0 |
| F21 | Cài đặt, trợ năng, hiển thị quyền micro và thông tin dữ liệu | A một phần; C cho trang cài đặt tổng hợp | P0/P1 |
| F22 | Âm mẫu/video giáo viên, bài nghe phân biệt âm | C/D; cần nội dung được duyệt và nguồn âm thanh phù hợp | P1 nội dung mẫu tối thiểu; P2 cho kho bài lớn |
| F23 | Giáo viên quản lý lớp, giao bài, duyệt lỗi và nhận xét | D; chưa có role/API hoàn chỉnh | P2 |
| F24 | Gói trả phí, thanh toán, thông báo đẩy, bảng xếp hạng | D; chưa thuộc bản hiện tại | P2 |

P0: phần phải bảo toàn để bàn giao được luồng luyện cốt lõi. P1: phần tích hợp tiếp theo của sản phẩm, phụ thuộc dữ liệu/API. P2: hướng mở rộng, không tự thêm vào màn hình chính trong đợt này. Các ưu tiên này là đề xuất bàn giao, không thay thế các đầu việc Core/Optional trong bảng kế hoạch gốc.

### 2.3. Khả năng AI cần phản ánh đúng trên UI

- Demo so sánh một âm được chọn trong một từ; không chấm toàn bộ từ/câu hay mọi âm được nói.
- Mục tiêu chính hiện có: /iː/, /ɪ/, /ɛ/, /æ/, /uː/, /p/, /t/, /k/, /s/, /ʃ/.
- Trường score của kết quả demo là null. Không đổi thành 0, 90 hoặc một phần trăm tự tính.
- Endpoint /assess hiện trả 501; /transcribe có trong hợp đồng nhưng chưa được hiện thực trong AI service đang dùng. Việc có schema Assessment không đồng nghĩa đã có bộ chấm điểm.
- Hình môi/lưỡi mô tả vị trí điển hình của một nhóm âm; không phải hình tái dựng miệng người nói từ audio.
- Nguyên âm /i/ không đánh dấu độ dài không tự động tương đương lỗi /ɪ/. Demo chưa đo hoặc chấm độ dài nguyên âm.
- Đường nét ở phần ngữ điệu là mẫu thực hành. Chưa có đường cao độ đo từ bản thu hoặc kết luận tự động về ý định người nói.

## 3. Người dùng và nguyên tắc trải nghiệm

### 3.1. Vai trò

Khách có thể xem giới thiệu và thử luyện âm nếu chính sách sản phẩm cho phép. Học viên có tài khoản sử dụng các chức năng cá nhân như thẻ từ, phiên Talk và tiến độ sau khi API tương ứng hoạt động. Giáo viên/quản trị là vai trò đề xuất giai đoạn sau; không dựng quyền hạn thật chỉ bằng việc ẩn/hiện nút trên frontend.

### 3.2. Nguyên tắc học và hiển thị

1. Mỗi lượt luyện tập trung vào một việc có thể làm ngay. Mặc định chỉ có một gợi ý điều chỉnh và một hành động ghi âm/thử lại.
2. Vận dụng tinh thần Adrian Underhill: chú ý cảm giác của môi, lưỡi, hàm và giọng; có thể quan sát chuyển động im lặng, hình dung âm rồi mới nói. Đây là gợi ý tùy chọn, không phải bài kiểm tra đủ bước.
3. Hướng dẫn đi từ điểm xuất phát có cơ sở đến mục tiêu. Nếu chưa có ứng viên đáng tin, giải thích điều đang thiếu thay vì tự đặt một khẩu hình sai.
4. Giữ hình tham chiếu mục tiêu dễ thấy; có dự đoán phù hợp thì giữ cả hai hình để so sánh. Bảng kỹ thuật và bài khám phá dài nằm trong phần mở rộng.
5. Ưu tiên dễ hiểu trong giao tiếp. Một lần trùng nhãn âm không được hiển thị thành “phát âm hoàn hảo”.
6. Dùng tiếng Việt tự nhiên, không để các nhãn như alveolar, posterior hoặc CTC trở thành nội dung bắt buộc với học viên.
7. Người học được dừng sau một lần thử. Không ép lặp đến khi đạt một điểm số chưa được kiểm chứng; không dùng âm báo thất bại cho mọi kết quả chưa rõ.

## 4. Kiến trúc thông tin và danh sách màn hình

Các route dưới đây là đề xuất cho frontend, không phải tuyên bố đã có sẵn. Màn hình kết quả luyện âm nên nằm trong ngữ cảnh của lần luyện hiện tại thay vì bắt buộc chuyển trang.

| Màn hình | Route đề xuất | Nội dung chính | Ghi chú |
|---|---|---|---|
| S01 – Giới thiệu/trang chủ | / | Giá trị, luyện thử, các khu vực học | Không bắt đăng nhập trước khi xem giá trị cốt lõi |
| S02 – Tài khoản | /login, /register | Biểu mẫu và thông báo lỗi | Chưa có API khôi phục mật khẩu được xác nhận |
| S03 – Danh mục IPA | /ipa | Nhóm âm, tìm/lọc, chọn âm để luyện | Phân biệt có hướng dẫn với có nhận dạng tự động |
| S04 – Luyện âm | /practice | Từ, âm mục tiêu, micro, ghi/tải âm thanh | Màn hình ưu tiên P0 |
| S05 – Kết quả luyện âm | Trong /practice | Nghe được, khác biệt, điều chỉnh, hai tham chiếu | Có trạng thái phù hợp/chưa chắc/chưa đủ dữ liệu |
| S06 – Khám phá khẩu hình | Drawer hoặc phần mở rộng trong /practice | Xem chuyển động; môi/lưỡi/hàm/giọng | Không biến thành quy trình bắt buộc |
| S07 – Từ và ý nghĩa | /practice/meaning | Bốn chủ điểm trọng âm/ngữ điệu/nối âm | Tự luyện, không hiển thị điểm AI |
| S08 – Từ điển | /dictionary, /dictionary/[word] | Tìm từ, IPA, nghĩa, ví dụ, lưu từ, luyện | Cần nguồn dữ liệu và API riêng |
| S09 – My Words | /my-words | Tạo thẻ, danh sách, xem chi tiết | API hiện có chưa đủ CRUD đầy đủ |
| S10 – Ôn thẻ | /flashcards | Thẻ đến hạn, lật, bốn mức ghi nhớ | Lấy lịch từ backend |
| S11 – Phòng Talk | /talk, /talk/[sessionId] | Chủ đề, trình độ, hội thoại, nhập chữ/PTT | Có chế độ dịch vụ giọng nói chưa khả dụng |
| S12 – Tiến độ và lịch sử | /dashboard, /history | Ngày học, lượt luyện, phiên Talk | Lịch sử luyện âm đầy đủ còn thiếu API |
| S13 – Cài đặt/trợ giúp | /settings, /help | Micro, mức thu, chuyển động, quyền dữ liệu | Chỉ cho thao tác được backend hỗ trợ |
| S14 – Công cụ phát triển | Route dev riêng hoặc cờ môi trường | Ví dụ lưu sẵn, raw output, thông tin kỹ thuật | Không mặc định hiện với học viên |

Điều hướng mobile đề xuất: Trang chủ, Luyện tập, Từ của tôi, Talk, Hồ sơ. Từ điển nằm trong tìm kiếm chung hoặc màn hình Từ của tôi; màn hình ôn thẻ mở từ đó. Desktop có thể dùng sidebar với cùng thứ tự. Không đặt cả hai thanh điều hướng khác cấu trúc khiến người dùng phải học lại.

## 5. Đặc tả nhóm luyện âm – P0

### 5.1. Danh mục IPA và chọn mục tiêu

Mỗi mục âm gồm ký hiệu IPA, từ ví dụ, nhóm nguyên âm/phụ âm, khả năng luyện hiện có. Lấy danh sách mục tiêu chính từ /demo/config thay vì viết cứng 10 nút ở nhiều nơi. Phân biệt rõ bộ 10 mục tiêu nhận dạng hiện tại với mục tiêu xây dựng danh mục 44 âm trong kế hoạch gốc.

| Âm chính | Từ luyện | Nhấn mạnh trong hình/hướng dẫn |
|---|---|---|
| /iː/ | seat | Môi giãn nhẹ ngang, khe mở nhỏ; tham chiếu lưỡi cao phía trước |
| /ɪ/ | sit | Môi ít giãn hơn; tham chiếu lưỡi thấp và lùi nhẹ so với /iː/ |
| /ɛ/ | bed | Độ mở ít hơn /æ/; giữ hướng dẫn đơn giản theo từ |
| /æ/ | bad | Hàm mở hơn /ɛ/; không coi mở miệng là giãn ngang |
| /uː/ | food | Môi tròn với lỗ mở nhỏ; vị trí cụ thể có thể thay đổi theo giọng |
| /p/ | pen | Khép hai môi, rồi nhả vào nguyên âm |
| /t/ | ten | Tiếp xúc đầu lưỡi gần gờ sau răng trên, rồi nhả |
| /k/ | key | Tiếp xúc phía sau lưỡi với vùng vòm mềm, rồi nhả |
| /s/ | see | Luồng hơi hẹp phía trước; không rung giọng trong phụ âm |
| /ʃ/ | she | So sánh vùng lưỡi hơi lùi hơn /s/; không suy ra vị trí cá nhân |

Các từ đối chiếu như zoo hoặc shows có thể xuất hiện trong cấu hình nhưng không làm tăng số mục tiêu chính. Chỉ bật nút “Nghe mẫu” khi có tệp/nguồn âm thật; nếu chưa có, thể hiện đang bổ sung hoặc dùng liên kết tài nguyên phù hợp. Không tạo đường dẫn mp3 giả.

### 5.2. Luồng luyện nhanh

Chọn âm/từ, đọc một gợi ý ngắn, bấm “Thử từ này”, nói một lần, nhận phản hồi, nghe lại hoặc thử tiếp nếu muốn. Nút luyện nhanh tự thu rồi gọi phân tích. Giữ đường thủ công “Ghi âm” rồi “Phân tích” cho người cần nghe/chọn đoạn trước.

Thứ tự nội dung ở màn luyện: mục tiêu; hành động ghi âm; phản hồi ba phần; hai tham chiếu; trợ giúp tùy chọn. Desktop có thể chia khối nhập và khối phản hồi thành hai cột. Trên điện thoại dùng một cột; sau khi phân tích có thể cuộn tới tiêu đề phản hồi và quản lý focus phù hợp, không giấu hình mục tiêu trong accordion đóng mặc định.

### 5.3. Ghi âm, tải tệp và chọn đoạn

- Chế độ mặc định “Chỉ nói từ”: thu tự dừng sau khoảng 3 giây. Người học có thể dừng sớm.
- Chế độ có ngữ cảnh: hiển thị cụm gợi ý từ cấu hình. Không gọi đây là đánh giá mọi âm trong câu.
- Cho chọn micro, hiển thị thiết bị đã được trình duyệt cấp quyền. Luôn có đường tải tệp khi không thu được.
- Audio gửi vào /demo/analyze phải là WAV PCM-16, mono, 16 kHz; đoạn dài 0,25–4 giây, tối đa 2 MiB ở API. Tệp đầu vào trình duyệt có thể dài hơn để người dùng chọn đoạn; giới hạn giải mã hiện tại là 30 MiB. Hai giới hạn này có vai trò khác nhau.
- Giữ lựa chọn đoạn đầy đủ từ và một ít khoảng lặng/ngữ cảnh. Không yêu cầu học viên tự xác định ranh giới âm vị.
- Có phát lại, tải WAV đã chuẩn bị và đổi tệp. “Lưu âm thanh” tải đúng tệp đang dùng cho phân tích; “Lưu kết quả” là JSON riêng, không chứa audio.
- Khi đổi từ/mục tiêu, sửa đoạn hoặc đổi audio, kết quả cũ không còn đại diện cho đầu vào mới. Hiển thị trạng thái cần phân tích lại.
- Thả toàn bộ track micro và tài nguyên Web Audio sau khi dừng/rời màn hình. Không phát âm thu trực tiếp ra loa để tránh vòng hồi âm.

### 5.4. Điều khiển mức thu

Mức 1× giữ mức gốc; thanh tăng từ 1× đến 8×, bước 0,5. Trong luyện âm, thay mức sau khi thu phải dựng lại clip hiện tại từ bản gốc, không nhân chồng. Chuyển 8× về 1× cần khôi phục bản gốc; phát lại và phân tích phải dùng cùng tệp đã cập nhật. Tệp tải lên giữ mức vốn có theo hành vi hiện tại.

Hiển thị meter, mức gốc/mức sau tăng, cảnh báo quá nhỏ và vỡ tiếng, cùng thông báo “Đã cập nhật âm lượng bản thu”. Sau khi thay mức của clip dùng phân tích, bỏ kết quả cũ và cho phân tích lại. Meter là mức tín hiệu âm thanh, không phải thước đo phát âm đúng.

### 5.5. Phản hồi cho bản thu

| Phần | Nội dung | Ví dụ /s/ khi mục tiêu /ʃ/ |
|---|---|---|
| Âm hệ thống có thể đã nghe | Nhãn dự đoán và từ ví dụ; giữ mức độ chắc chắn phù hợp | “Có thể bạn đang tạo âm /s/, như đầu từ see.” |
| Khác mục tiêu ở đâu | So sánh đặc trưng tham chiếu; không kết luận trực tiếp về cơ thể người học | “Tham chiếu /s/ ở phía trước hơn tham chiếu /ʃ/.” |
| Thử thay đổi này | Một điều chỉnh cụ thể cho lần tiếp theo | “Thử đưa vùng lưỡi tạo khe hơi lùi nhẹ rồi nói she.” |

Khi mô hình có dữ liệu đủ cho so sánh theo quy tắc hiện tại, dùng “Âm có khả năng…”; không đổi thành “Chắc chắn bạn…”. Với ứng viên yếu, dùng câu điều kiện: “Nếu /s/ giống điều bạn nghe trong bản thu, hãy thử…”. Với im lặng, nhiễu hoặc không có ứng viên hỗ trợ, giải thích giới hạn của bản thu và đề nghị một thao tác khắc phục; không chỉ để lại từ “Không rõ”.

Nếu trùng nhóm âm mục tiêu, dùng “Âm nhận được phù hợp với mục tiêu ở mức nhãn nhận dạng”. Không khẳng định mọi âm trong từ đều đúng, không phát huy hiệu hoàn hảo. Nút thử lại là lựa chọn, không bắt buộc.

### 5.6. Hai thẻ hình tham chiếu

Thẻ thứ nhất: “Âm có thể đã phát ra – hình tham chiếu”. Thẻ thứ hai: “Âm mục tiêu – hình tham chiếu”. Mỗi thẻ có IPA, từ ví dụ, mặt trước của môi và mặt bên của vùng lưỡi; một mô tả ngắn dễ hiểu. Trên desktop đặt cạnh nhau; trên điện thoại xếp dọc hoặc dùng bố cục cân đối nhưng không che mất một bên.

- /ɪ/ và /iː/ cần khác về nét môi và vùng lưỡi tham chiếu. Môi không tròn không có nghĩa luôn giãn rộng.
- /i/ và /iː/ có thể dùng cùng hình. Giữ đúng nhãn mỗi bên, giải thích chưa đánh giá độ dài, không vẽ khác để tạo cảm giác có lỗi.
- Không có predicted_phone hoặc không có hình hỗ trợ: giữ thẻ mục tiêu, thay phần xuất phát bằng lời giải thích; không vẽ vị trí lưỡi giả.
- Minh họa dùng kích thước tương đối và nguồn asset kiểm soát được. Không gọi hình là “miệng thực tế của bạn”.

### 5.7. Chuyển động và trợ giúp mở rộng

“Xem chuyển động” mở một minh họa gọn, có nút ẩn và phát lại. Với đối chiếu nguyên âm hoặc âm xát được hỗ trợ, bắt đầu từ nhóm âm mô hình gợi ý; ứng viên yếu phải có nhãn điều kiện. Khi hai nhãn dùng cùng hình, chỉ trình bày tư thế mục tiêu và lời giải thích chưa có thay đổi hình được xác lập. Với âm tắc hoặc chuyển đổi không phù hợp để nội suy, dùng bài khép/nhả mục tiêu và ghi rõ đó là ví dụ luyện tập.

“Cần thêm trợ giúp” mới mở các bước Tìm – Di chuyển – Cảm nhận – Dùng trong từ, điều khiển Môi – Lưỡi – Hàm – Giọng và thanh khám phá chuyển động. Người học không phải hoàn thành bốn bước mới được ghi âm. Có thể gợi ý làm động tác thầm hoặc hình dung âm trước khi nói. Chế độ giảm chuyển động phải giữ được thông tin ở trạng thái tĩnh.

## 6. Đặc tả Từ và ý nghĩa – P0

Màn hình có bốn chủ điểm, một gợi ý chính, một mẫu nhấn/đường chuyển động tham khảo và ghi âm tối đa khoảng 5 giây. Lưu hai lần thử gần nhất cho từng chủ điểm trong tab để nghe đối chiếu; lần thứ ba thay bản cũ hơn. Không gửi câu ở khu vực này vào endpoint so sánh một từ.

| Chủ điểm | Ví dụ đang có | Tương tác cần thiết | Điều người học tự kiểm tra |
|---|---|---|---|
| Trọng âm từ | a-BOUT | Âm tiết nhẹ/nổi bật, cử chỉ nhịp | Phần đầu nhẹ hơn, phần sau rõ hơn; không chỉ nói to hơn |
| Nhấn ý trong câu | What do YOU think? / What do you THINK? | Chọn ý định, đổi từ nổi bật | Người nghe có nhận ra điểm mình muốn nhấn không? |
| Ngữ điệu | Really? / Really. | Chọn ngữ cảnh, vẽ theo đường lên/xuống bằng tay | Phần kết nghe đi lên hay xuống; có phù hợp ý định không? |
| Nối âm và nói liền | Take a SEAT | Dấu nối take‿a, âm a nhẹ, nhịp ở seat | Cụm từ có liền và seat còn rõ không? |

Các đường trong hình là mẫu dạy học. Không chồng một đường giả lên bản thu hoặc ghi “AI phát hiện ngữ điệu sai” khi chưa có phép đo. Không dạy quy tắc tuyệt đối “câu hỏi luôn lên giọng”.

Nút chính: “Ghi âm cụm”, “Dừng”, nghe từng bản. Có “Thử cử chỉ”, “Tôi nghe thấy thay đổi”, “Thử cách khác”. Phần tự nhận xét không được ghi thành kết quả chấm điểm. Đổi chủ điểm phải dừng phát audio cũ; hai clip thuộc từng chủ điểm không được trộn lẫn.

Có chọn micro, meter và mức tăng 1×–8×. Trong khu vực này, điều chỉnh mức hiện tại áp dụng cho lần thu mới; hai clip đã thu giữ mức tại thời điểm ghi. Phải nói rõ khác biệt với chế độ luyện âm, hoặc thống nhất lại hành vi sau khi bổ sung và kiểm tra. Clip ở khu vực tự luyện hiện chưa đồng bộ tài khoản và mất khi đóng/tải lại trang.

## 7. Từ điển, My Words và ôn tập – P1

### 7.1. Từ điển

Tìm theo từ tiếng Anh; hiển thị đang tải, không có kết quả, không kết nối được. Chi tiết từ dự kiến gồm từ, loại từ, IPA, nghĩa tiếng Việt, ví dụ tiếng Anh, nguồn âm mẫu nếu có, nút lưu từ và chuyển sang luyện. Mỗi trường chỉ xuất hiện khi có dữ liệu; CMUdict hỗ trợ cách đọc, không tự cung cấp đủ nghĩa và ví dụ.

Chưa xác nhận API /dictionary hay /words. AI làm frontend phải đặt lớp dữ liệu riêng và nhãn mock trong môi trường phát triển; không viết một endpoint mới vào UI rồi coi như backend đã có. Cách phát âm/giọng đọc khác nhau cần được ghi nhãn theo nguồn khi có, không tự suy từ một nhãn IPA.

Chỉ chuyển sang phân tích khi từ/âm nằm trong khả năng matcher hiện có. Với từ bất kỳ chưa hỗ trợ, vẫn cho xem hướng dẫn hoặc lưu từ, nhưng không hứa sẽ chấm từng âm của từ đó.

### 7.2. My Words

Có hành động “Tạo thẻ” với mặt trước và mặt sau; có thể điền trước từ màn từ điển. POST /cards hiện chỉ nhận front và back. IPA, audio, ví dụ, tag và ghi chú riêng là dữ liệu mở rộng cần chốt schema, không giả định đều đã lưu được.

Danh sách toàn bộ từ, tìm kiếm, chỉnh sửa, xóa và lọc theo tag là yêu cầu sản phẩm cần bổ sung API. GET /cards/due chỉ cho thẻ đến hạn, không thay thế API liệt kê toàn bộ thẻ. Không báo “Đã lưu vào tài khoản” nếu chỉ lưu local hoặc request thất bại. Có trạng thái chưa đăng nhập, đang lưu, lưu thành công, lỗi và danh sách trống.

### 7.3. Ôn tập FSRS

Lấy thẻ đến hạn từ GET /cards/due. Trước khi lật, chỉ hiện mặt trước và nút “Hiện đáp án”. Sau khi lật, hiển thị bốn mức: Học lại = 1, Khó = 2, Nhớ = 3, Dễ = 4. Đây là tự đánh giá ghi nhớ, không phải kết quả nhận dạng phát âm.

Gửi POST /reviews với card_id, rating và request_id dạng UUID. Một hành động ôn dùng một UUID; nếu thử gửi lại cùng hành động phải giữ UUID đó. Khóa nút trong lúc gửi để tránh chấm hai lần. Chỉ chuyển thẻ khi backend xác nhận; giữ thẻ và mức chọn nếu mất kết nối.

Lịch kế tiếp lấy từ due và interval_seconds/interval_days của phản hồi. Không tự tính lại FSRS trong frontend. Bản tích hợp có chính sách “Học lại” sau 10 phút, do đó chỉ dùng interval_days có thể làm hiển thị sai. Khi chưa có dữ liệu khoảng ôn trước khi chấm, không dựng thời gian giả trên bốn nút. Có màn hoàn thành khi hết thẻ đến hạn, không tuyên bố đã thuộc mọi từ.

## 8. Phòng Talk và lịch sử – P1 có điều kiện

### 8.1. Tạo phiên và hội thoại văn bản

Cho chọn chủ đề và trình độ A2/B1/B2, tạo phiên, xem tin nhắn người học và gia sư. API bản tích hợp có POST/GET /sessions, GET /sessions/{session_id}/turns và POST /chat/stream. Phản hồi truyền dần qua SSE theo sự kiện token, done, error; frontend ghép token và chỉ xác nhận hoàn tất khi nhận done.

Có các trạng thái: phiên trống, đang tạo phiên, đang gửi, đang nhận phản hồi, lỗi LLM, phiên đang xử lý, mất kết nối. Không mở hai lượt gửi đồng thời trong cùng phiên. Nếu stream lỗi sau một phần nội dung, giữ phần đã nhận với nhãn chưa hoàn tất; không tự gửi lại làm trùng lượt.

Prompt tutor hiện hướng tới câu trả lời ngắn, có thể sửa diễn đạt nhẹ nhàng và đặt một câu hỏi mở. Không suy luận người học phát âm sai từ tin nhắn chữ. Chưa có đường âm thanh TTS thì không dùng trạng thái “Gia sư đang nói” chỉ vì có token văn bản.

### 8.2. Talk bằng giọng nói

Push-to-Talk cần hoạt động bằng chuột, cảm ứng và bàn phím: nhấn giữ để nói, nhả để dừng/gửi theo thiết kế đã chốt; có lựa chọn bấm bắt đầu/dừng cho người không giữ nút thuận tiện. Cần xử lý trường hợp ngón tay trượt khỏi nút, trình duyệt mất focus, hết quyền micro và người dùng hủy lượt.

WebSocket /ws/audio trong bản tích hợp nhận audio rồi xử lý sau thông điệp end. Sự kiện partial hiện đếm received_bytes; không phải transcript từng phần. Không hiển thị “AI nghe được…” bằng cách chuyển số byte thành chữ. Protocol hỗ trợ audio/webm hoặc audio/wav, giới hạn bộ đệm 8 MiB ở bản tích hợp; đây là luồng khác với WAV 2 MiB của demo luyện từ.

Chuỗi STT và đánh giá trong Talk còn bị chặn bởi /transcribe chưa triển khai và /assess trả 501. Frontend phải có trạng thái “Tính năng phân tích giọng nói chưa sẵn sàng” và đề nghị nhập văn bản; không dựng transcript hay điểm giả để che lỗi. Nếu có transcript nhưng đánh giá lỗi, giữ transcript/phản hồi đã có, chỉ báo phần đánh giá chưa dùng được.

Sau ngắt kết nối, có thể giữ audio cục bộ tạm thời để người dùng chủ động gửi lại. Không tự động phát lại toàn bộ lượt gửi khi protocol chưa có cơ chế chống trùng. Chỉ hiển thị gia sư đang phát âm thanh khi có audio thực sự phát; TTS là phần chưa xác nhận triển khai.

### 8.3. Lịch sử

Danh sách phiên Talk lấy từ API, chọn phiên để xem các lượt đã lưu. Không giả định có API xóa/đổi tên phiên vì chưa được xác nhận. Lịch sử toàn bộ lượt luyện âm, audio đám mây, đồng bộ hai clip tự luyện và bài nhận xét giáo viên là yêu cầu riêng cần chốt, không đồng nhất với danh sách phiên Talk.

## 9. Tài khoản, trang chủ, tiến độ và cài đặt

### 9.1. Tài khoản

Đăng ký/đăng nhập dùng email và mật khẩu; lỗi nhập đặt cạnh trường, lỗi dịch vụ ở mức biểu mẫu. API bản tích hợp trả access_token/token_type; có lỗi email đã đăng ký và thông tin không đúng. Xử lý token hết hạn bằng lời nhắc đăng nhập lại, tránh xóa bản thu đang giữ nếu không cần thiết. Không nhúng khóa LLM/JWT hay thông tin bí mật vào frontend.

Đăng xuất là thao tác xóa phiên phía frontend theo cơ chế ứng dụng; chưa có API đăng xuất/refresh/quên mật khẩu được xác nhận. Màn quên mật khẩu hoặc đăng nhập Google chỉ được đưa vào bản thật khi có tích hợp tương ứng. Đăng nhập không được chặn người học xem toàn bộ nội dung giới thiệu.

### 9.2. Trang chủ

Cho thấy một hành động chính “Bắt đầu luyện” và các lối vào Từ của tôi, Talk, tự luyện trọng âm/ngữ điệu. Với người mới, dùng hướng dẫn ngắn hoặc ví dụ, tránh dashboard đầy biểu đồ trống. Với người quay lại, chỉ hiển thị số thẻ đến hạn/ngày học nếu có nguồn dữ liệu đúng. Mục “Tiếp tục” cần dẫn về một phiên/bài thực, không sinh nhiệm vụ ngẫu nhiên được giới thiệu là cá nhân hóa từ AI.

### 9.3. Tiến độ

GET /progress trong bản tích hợp có attempts, streak_days, phoneme_averages, timezone, daily. Dữ liệu này dựa trên Assessment có điểm của luồng cũ. Kết quả demo có score = null và chưa tự động được lưu vào bảng Attempt theo schema đó. Vì vậy chưa thể vẽ biểu đồ điểm âm từ các lượt demo mà không bổ sung hợp đồng lưu trữ.

Ưu tiên thể hiện hoạt động khi có dữ liệu: số lần đã luyện, ngày có hoạt động, thẻ đã ôn. Những số này cũng cần nguồn lưu trữ phù hợp. Phân biệt “chưa có dữ liệu”, “chưa kết nối”, “chưa hỗ trợ đo” với giá trị thật bằng 0. Không vẽ đường cải thiện giả hay ghi tỷ lệ chính xác mô hình vào tiến độ cá nhân.

Hiển thị ngày theo Asia/Ho_Chi_Minh. Nếu dữ liệu chưa có timezone đầy đủ, trao đổi backend trước khi tính streak ở client. Dữ liệu gợi ý điểm yếu chỉ dùng khi có cơ sở; không suy thành “bạn luôn sai /s/” từ một ứng viên yếu.

### 9.4. Cài đặt, quyền và dữ liệu

Có chọn micro, mức thu, trợ giúp khi âm quá nhỏ/vỡ, chế độ giảm chuyển động và ngôn ngữ hướng dẫn nếu đã triển khai. Không buộc người học bật camera để dùng hình tham chiếu; demo hiện không đo khẩu hình qua camera.

Trong demo local, xử lý audio nằm trên dịch vụ local; tệp upload tạm được xóa sau suy luận. JSON xuất không chứa audio; clip tự luyện cụm nằm trong tab. Khi chuyển sang hệ thống triển khai từ xa, nội dung mô tả nơi gửi/lưu audio phải được điều chỉnh theo kiến trúc thật. Không sao chép câu “audio chỉ ở trên máy bạn” sang ứng dụng có gửi audio ra server.

Các nút xóa tài khoản, xóa audio đám mây hoặc xuất toàn bộ dữ liệu cá nhân cần API và chính sách thực tế. Chưa có thì không làm nút giả báo thành công.

## 10. Thành phần giao diện và quy chuẩn thiết kế

### 10.1. Bộ component tối thiểu

| Component đề xuất | Trách nhiệm |
|---|---|
| AppShell / ResponsiveNav | Điều hướng thống nhất desktop/mobile, trạng thái đăng nhập |
| SoundPicker / PromptSelector | Chọn âm/từ từ cấu hình, thể hiện khả năng luyện |
| AudioRecorder / AudioPlayer | Xin quyền, ghi/dừng, timer, phát lại, giải phóng tài nguyên |
| MicrophoneSettings / InputLevelMeter | Thiết bị, gain, mức gốc/mức tăng, cảnh báo |
| AudioSegmentSelector | Chọn đoạn hợp lệ, chuẩn bị lại sau khi chỉnh |
| RecordingDiagnosis | Ba phần nghe được – khác biệt – thử điều chỉnh |
| ReferencePair / LipView / TongueView | Hai thẻ tham chiếu, nhãn IPA, bố cục responsive |
| MovementPreview / PracticeHelp | Chuyển động gọn và phần khám phá tùy chọn |
| ProsodyExercise / AttemptComparison | Ngữ cảnh, nhấn ý, cử chỉ và hai clip tự luyện |
| DictionaryResult / WordDetail | Chi tiết từ theo trường dữ liệu có sẵn |
| VocabularyCard / ReviewActions | Thẻ lật, bốn mức FSRS, chặn gửi trùng |
| SessionList / TalkThread / PushToTalk | Phiên, streaming, nhập chữ/giọng nói |
| ServiceStatus / EmptyState / ErrorState | Hiển thị đang tải, rỗng, lỗi, phần chưa hỗ trợ |

Đây là cách tách component đề xuất; có thể điều chỉnh tên theo repository. Không tạo một component khổng lồ chứa cả thu âm, API, thẻ ôn và hội thoại.

### 10.2. Thị giác và nội dung

Hướng phong cách: rõ, nhẹ, có khoảng thở; một màu chính cho hành động và màu hổ phách cho thông tin cần nghe lại. Trạng thái luôn có chữ/icon, không chỉ tô xanh/đỏ. Font phải hiển thị đúng tiếng Việt và IPA, đặc biệt /ɪ/, /ʃ/, /ɛ/, /æ/, /ə/, dấu dài /ː/.

Nội dung mặc định: một gợi ý chính; mục tiêu luôn dễ thấy; thông tin chưa chắc chắn vẫn dễ đọc. Nút và vùng chạm nên đủ lớn cho thao tác một tay, mục tiêu thiết kế tối thiểu khoảng 44 px. Chữ nhập/chữ nội dung chính đủ đọc trên mobile; không thu nhỏ ký hiệu IPA để nhét một bảng 44 ô trên một hàng.

Các mốc responsive đề xuất: khoảng 390 px điện thoại, 768 px máy tính bảng, 1280 px desktop. Bảng hai tham chiếu và bốn nút đánh giá phải đổi bố cục khi thiếu chỗ. Kiểm tra hover, focus và selected để tránh chữ trắng trên nền nhạt. Có label cho input, focus rõ ràng, thao tác được bằng bàn phím và thông báo hoàn tất/lỗi phù hợp với trình đọc màn hình.

Đối với minh họa: phân biệt giãn ngang, tròn môi, độ mở hàm và tiếp xúc môi. Khi chuyển động bị tắt, giữ tư thế/nhãn đủ hiểu. Không dùng ảnh AI để minh họa vị trí cần chính xác rồi xem đó như bằng chứng giải phẫu.

## 11. Hợp đồng dữ liệu và tích hợp cho frontend

### 11.1. Ma trận API

| Nhóm | Endpoint | Nguồn/trạng thái | Yêu cầu frontend |
|---|---|---|---|
| Demo | GET /demo/config | A – AI service | Đọc mục tiêu, prompts, guides, teaching và ví dụ khả dụng |
| Demo | POST /demo/analyze | A – AI service | Multipart audio, prompt_id, input_scope; xử lý score null |
| Demo | GET /demo/status | A – AI service | Hiển thị idle/loading_model/inference và khả năng kết nối |
| Demo | GET /demo/examples/{id}, /audio | A – dữ liệu local khi có | Ghi nhãn ví dụ đã tính sẵn; không gọi là phân tích mới |
| Xác thực | POST /auth/register, /auth/login | B – backend bản tích hợp | Token; 401/409/422/503; xác nhận phiên bản server |
| Thẻ | POST /cards; GET /cards/due | B – backend bản tích hợp | Tạo thẻ và hàng đợi đến hạn; không thay thế full CRUD |
| Ôn tập | POST /reviews | B – backend bản tích hợp | request_id chống trùng; đọc lịch từ phản hồi |
| Talk | POST/GET /sessions; GET /sessions/{id}/turns | B – backend bản tích hợp | Phiên theo người dùng; không suy có API sửa/xóa |
| Talk | POST /chat/stream | B – backend bản tích hợp | Đọc SSE token/done/error qua fetch streaming |
| Talk audio | WS /ws/audio | B, luồng speech còn thiếu dịch vụ | partial là byte; các lỗi riêng transcript/assessment/LLM |
| Tiến độ | GET /progress | B, schema phụ thuộc Assessment | Không gán kết quả demo chưa lưu thành điểm tiến độ |
| Chấm điểm cũ | POST /assess | A về hành vi trả 501 | Hiển thị chưa hỗ trợ; không fallback sang điểm giả |
| Nhận dạng câu | POST /transcribe | C ở AI service hiện tại | Có trong contract, chưa có triển khai chạy được xác nhận |
| Từ điển/CRUD đầy đủ/giáo viên | Chưa chốt | C/D | Tạo adapter mock; đề xuất schema riêng trước khi tích hợp |

Route tương đối là phần hợp đồng; hostname/cổng phải lấy từ cấu hình. Không viết cứng 127.0.0.1 vào giao diện sản phẩm. /demo và backend là hai nhóm API, không cùng schema kết quả. Khi frontend khác origin với AI service, cần proxy hoặc cấu hình CORS được thống nhất; demo hiện được phục vụ cùng origin nên không thể mặc định fetch trực tiếp từ mọi frontend đều được.

### 11.2. Trạng thái kết quả demo

| Trường/giá trị | Ý nghĩa trên UI | Không được suy diễn |
|---|---|---|
| status = model_match | Nhãn nhận dạng tương thích mục tiêu | Phát âm hoàn hảo hoặc toàn bộ câu đúng |
| status = possible_difference | Có đối chiếu ứng viên khác mục tiêu | Lỗi chắc chắn hoặc mức độ sai theo % |
| status = uncertain | Chưa đủ chắc; có thể vẫn có ứng viên để tham khảo | Bắt buộc giấu mọi thông tin hoặc tự chọn âm mục tiêu |
| predicted_phone = null | Chưa xác lập âm có thể đã phát ra | Dùng target_phone thay thế làm kết quả nghe được |
| score = null | Chưa cung cấp điểm | 0 điểm hoặc 100 điểm |
| diagnosis | Phần giải thích cho bản thu và gợi ý hành động | Đo vị trí lưỡi thực tế |
| articulation_feedback | Đối chiếu các đặc trưng tham chiếu | Bản đồ hình học của người học |
| details.vowel_duration_assessed = false | Chưa đánh giá độ dài | Kết luận i bị ngắn hơn iː |
| mode = cached_development_example | Ví dụ phát triển được phát lại | Kết quả mới của người đang dùng |

diagnosis.kind có thể gồm comparison, tentative_comparison, audio_quality và các trường hợp khác theo response. Ưu tiên dựng nội dung từ dữ liệu có thật, có fallback cho kind chưa nhận biết. Không chỉ dùng một câu “Đọc theo hướng dẫn mục tiêu” cho mọi trường hợp uncertain.

### 11.3. Quy tắc đồng bộ và lỗi

Khi đổi prompt/audio/gain/đoạn chọn, hủy hoặc bỏ qua response thuộc request cũ. Khóa các thao tác xung đột trong lúc đang thu, chuẩn bị hoặc gửi phân tích; vẫn giữ hành động dừng/hủy phù hợp. Không bật hai micro cùng lúc ở Luyện âm và Talk/Từ và ý nghĩa.

Không đồng nhất HTTP 200 với kết quả đúng: response uncertain vẫn là phân tích thành công về kỹ thuật. HTTP 400/413/422 cần chỉ ra vấn đề đầu vào; 401 cần đăng nhập lại; 409 có thể là phiên bận/xung đột; 501 là phần chưa triển khai; 503 hoặc mất mạng là lỗi dịch vụ. Thông báo cho học viên dùng tiếng Việt; log kỹ thuật để riêng.

Token, API key và dữ liệu nhạy cảm không xuất hiện trong URL chia sẻ, console công khai hoặc file JSON mẫu. Không sửa schema/backend âm thầm để làm cho một thiết kế đẹp hoạt động; thay đổi API phải được thống nhất qua docs/openapi.yaml.

## 12. Ma trận trạng thái cần có trong thiết kế

| Tình huống | Nội dung hiển thị | Hành động chính |
|---|---|---|
| Chưa bắt đầu | Từ/âm mục tiêu, một gợi ý, hình mục tiêu | Thử từ này |
| Đang xin quyền micro | Lý do cần micro, trạng thái chờ | Cho phép; hoặc tải tệp |
| Từ chối/không có micro | Giải thích cách cấp quyền hoặc chọn tệp | Tải audio / thử lại |
| Đang thu | Timer, meter, thiết bị; khóa chuyển bài | Dừng |
| Đã thu | Nghe lại và mức âm | Phân tích / thu lại |
| Đang đổi mức hoặc chọn đoạn | Đang chuẩn bị clip mới | Chờ; chưa phân tích clip cũ |
| Đang tải model | Thông báo lần đầu có thể lâu hơn | Chờ; không tạo phần trăm giả |
| Đang phân tích | Giữ mục tiêu, trạng thái xử lý rõ | Hủy nếu luồng hỗ trợ |
| Có đối chiếu khác âm | Âm nghe được, khác biệt, một thay đổi, hai hình | Nghe lại / thử lại |
| Ứng viên yếu | Câu điều kiện và hướng dẫn so sánh | Nghe và quyết định thử |
| Không có ứng viên | Lý do cụ thể; giữ hình mục tiêu | Thu lại hoặc chọn đoạn khác |
| Âm phù hợp mục tiêu | Xác nhận giới hạn ở âm được chọn | Tiếp tục tự nguyện |
| Quá nhỏ/vỡ tiếng | Meter và gợi ý thiết bị/mức thu | Điều chỉnh và thu lại |
| Lỗi dịch vụ | Phân biệt server tắt với đầu vào sai | Kết nối lại, không chấm điểm |
| Chưa có từ/thẻ/phiên | Empty state mô tả bước tiếp theo | Tạo thẻ / tạo phiên |
| Chưa có dữ liệu tiến độ | Giải thích chưa ghi nhận hoặc chưa hỗ trợ | Bắt đầu luyện |
| Một phần Talk bị lỗi | Giữ nội dung đã có, đánh dấu phần thiếu | Nhập chữ / thử gửi chủ động |

## 13. Tiêu chí nghiệm thu và bàn giao

### 13.1. Nghiệm thu chức năng

- Luyện nhanh từ chọn âm đến phản hồi chạy được với API demo, không chỉ với mock.
- Cả ba trạng thái model_match, possible_difference, uncertain đều có giao diện và nội dung phù hợp.
- Trường hợp /s/ so với /ʃ/ có âm nghe được, khác biệt và một điều chỉnh; hai hình hiện khi có dữ liệu hỗ trợ.
- /ɪ/ và /iː/ có hình tham chiếu phân biệt; /i/ và /iː/ giữ đúng nhãn và không bịa kết luận độ dài.
- Không có predicted_phone thì không tự điền một âm “đã nghe”. Không hiển thị score null thành 0.
- Thay mức thu của cùng clip luyện âm làm thay đổi WAV thật và không nhân chồng; quay về 1× khôi phục bản gốc.
- Bốn bài Từ và ý nghĩa đổi mẫu theo lựa chọn, giữ tối đa hai clip/chủ điểm và không gọi API so sánh từ để chấm câu.
- FSRS gửi đúng rating/request_id; retry không tạo thêm lần ôn và lịch hiển thị theo backend.
- Talk chữ đọc đúng stream. Lỗi speech/assessment có đường lui rõ; partial byte không thành transcript.
- Sau rời màn hình không còn track micro đang bật. Mọi tài nguyên phát lại/animation được dọn phù hợp.

### 13.2. Nghiệm thu UI/UX

- Kiểm tra ít nhất kích thước điện thoại, tablet và desktop đã nêu; không tràn ngang hoặc che nút dừng.
- Bàn phím sử dụng được; focus thấy rõ; thông báo thu/phân tích hoàn tất dễ nhận biết.
- Tiếng Việt và ký hiệu IPA hiển thị đúng. Selected/hover/focus không mất tương phản.
- Hình mục tiêu không biến mất sau khi đơn giản hóa giao diện. Hướng dẫn dài đóng mặc định và vẫn tìm được.
- Mock, cached example và live result được phân biệt. Không có tài khoản/thanh toán/giáo viên “giả hoạt động”.

### 13.3. Gói thành viên frontend cần bàn giao

Sitemap; wireframe các màn chính; thiết kế desktop/mobile và trạng thái; bộ component/tokens; danh sách API và khoảng trống; mã frontend; dữ liệu mock có nhãn; hướng dẫn cấu hình/chạy; kiểm thử trọng yếu; ảnh chụp hoặc video luồng chính khi nhóm cần nghiệm thu; danh sách phần chưa tích hợp.

Bằng chứng chức năng gần nhất của demo ghi nhận ngày 18/11/2026: 83 kiểm tra Python, 5 nhóm kiểm tra JavaScript, 6 nhóm kiểm tra trình duyệt. Các số này thuộc demo ở thời điểm kiểm tra, không phải chứng nhận cho frontend được viết mới hoặc bằng chứng hiệu quả học tập. Frontend mới cần kiểm tra lại các hành vi đã thay đổi.

## 14. Prompt mẫu để giao cho AI

### 14.1. Prompt khởi đầu

```text
Bạn là lập trình viên frontend kiêm người hỗ trợ UI/UX cho WordSpeak,
ứng dụng luyện nói tiếng Anh cho người Việt. Hãy đọc tài liệu đặc tả
WORDSPEAK_DAC_TA_UIUX_FRONTEND_VI.md trước khi làm việc.

Trước hết kiểm tra repository và phiên bản backend thực tế. Frontend hiện
dùng Next.js, React, TypeScript và Tailwind; không tự chuyển sang Flutter.
Chỉ sửa frontend và các tệp thiết kế/tài liệu thuộc nhiệm vụ. Nếu API cần
đổi, nêu đề xuất cụ thể và thống nhất hợp đồng trước khi sửa phía dịch vụ.

Ưu tiên P0: chọn một âm/từ, ghi âm/tải tệp, mức thu 1x–8x, phản hồi ba phần,
hai hình tham chiếu, chuyển động tùy chọn và Từ & ý nghĩa. Giữ trải nghiệm
một gợi ý – một lần thử; không ép hoàn thành danh sách hoạt động dài.

Dùng API demo cho khả năng đã có. score=null nghĩa là chưa có điểm;
uncertain vẫn có thể có ứng viên để tham khảo. Không suy ra hình miệng
thực tế, độ dài nguyên âm hoặc đánh giá ngữ điệu từ dữ liệu chưa đo.
Không biến partial.received_bytes thành transcript. Không gọi /assess
để lấy điểm vì endpoint đang trả 501.

Tách dữ liệu thật và mock bằng adapter/cấu hình. Không tự tạo endpoint
backend, khóa bí mật, file audio mẫu hoặc phần trăm chính xác. Các tính năng
P1 chưa có API phải có trạng thái chưa khả dụng và danh sách tích hợp còn thiếu.

Làm theo từng phần có thể kiểm tra. Bàn giao màn hình responsive, các trạng
thái loading/empty/error/uncertain, cách chạy, kiểm thử hành vi quan trọng
và những giới hạn còn lại. Bắt đầu bằng kiểm kê mã hiện có và luồng P0.
```

### 14.2. Quy tắc dùng prompt theo từng phần

Gửi prompt gốc cùng tài liệu này, sau đó giao một phạm vi nhỏ: chỉ bộ layout; chỉ recorder; chỉ phản hồi; chỉ hai tham chiếu; chỉ Từ và ý nghĩa; chỉ adapter FSRS hoặc Talk. Tránh yêu cầu AI tạo toàn bộ ứng dụng trong một lượt rồi tự đoán dữ liệu còn thiếu. File PROMPT_AI_UIUX_FRONTEND_VI.md đi kèm chứa các prompt chuyên biệt và mẫu dữ liệu rút gọn.

## 15. Kế hoạch hoàn thiện tháng 11/2026

### 15.1. Nội dung ngắn để điền cột Tháng 11

- Hoàn thiện giao diện và tích hợp luồng luyện phát âm: thu âm/tải audio, nhận diện âm có thể đã phát ra, so sánh với âm mục tiêu và gợi ý điều chỉnh.
- Chuẩn hóa hình tham chiếu môi – lưỡi, minh họa chuyển động và bài luyện ngắn theo định hướng Adrian Underhill; bổ sung tự luyện trọng âm, ngữ điệu và nối âm.
- Tích hợp các phân hệ Từ điển, My Words/FSRS và Talk theo API đã sẵn sàng; xử lý rõ các chức năng còn thiếu dịch vụ.
- Kiểm thử toàn luồng trên desktop/mobile; đánh giá phản hồi với giáo viên và ghi nhận các trường hợp chưa chắc chắn.
- Hoàn thiện tài liệu, kết quả thực nghiệm, báo cáo đồ án, slide và kịch bản trình diễn cuối cùng.

### 15.2. Chặng hoàn thiện còn lại, đề xuất từ ngày 19/11

| Thời gian | Công việc | Đầu ra và điều kiện hoàn thành |
|---|---|---|
| 19–21/11 | Chốt phạm vi, rà phiên bản frontend/backend, API và thiết kế P0 | Danh mục tính năng, thiết kế các trạng thái, adapter và danh sách API còn thiếu được nhóm thống nhất |
| 22–25/11 | Chuyển luồng luyện âm và Từ & ý nghĩa vào frontend; ghép P1 có API khả dụng | Luồng luyện cốt lõi chạy thực; không dùng điểm/transcript giả khi dịch vụ thiếu |
| 26–28/11 | Kiểm thử, sửa lỗi, rà nội dung với giáo viên nếu bố trí được | Biên bản lỗi và kết quả kiểm tra; phản hồi chuyên môn tách khỏi kiểm tra phần mềm |
| 29–30/11 | Đóng gói bản trình diễn, báo cáo, slide, hướng dẫn chạy và danh sách giới hạn | Bản demo tái hiện được, tài liệu bàn giao và kịch bản bảo vệ; phần chưa đủ điều kiện được ghi rõ |

Các mốc trên là kế hoạch đề xuất, không phải công việc đã hoàn thành hoặc cam kết mọi P1 sẽ sẵn sàng. Ưu tiên bản demo nhất quán và có bằng chứng. Chưa coi chấm điểm GOP, hội thoại giọng nói đầy đủ hoặc đánh giá ngữ điệu tự động là hoàn thành nếu chưa có dịch vụ và kiểm thử tương ứng.

## 16. Tài liệu đối chiếu và các quyết định còn mở

Nguồn trong project: sheet/Dev1_AI_Speech.xlsx, Dev2_Backend_NLP.xlsx, Dev3_Frontend.xlsx; README.md; docs/openapi.yaml; docs/MVP_HANDOFF.md; docs/PHYSICAL_PRACTICE_VALIDATION.md; docs/PRONUNCIATION_PRODUCT_STUDY.md. Các bảng kế hoạch là định hướng; cột trạng thái trong sheet chưa được coi là bằng chứng phần mềm hiện đang chạy.

Nguồn mã chính: frontend/app; backend/app; ai-service/app/pronunciation_demo.py; sound_catalog.py; sound_diagnosis.py; teaching_guides.py; demo_static/audio.mjs, teaching.mjs, practice-plan.mjs, prosody.mjs và prosody-lessons.mjs. API backend mở rộng được đối chiếu ở bản tích hợp local commit 3774a6c. Bản demo có các thay đổi sau commit đó, nên không mặc định commit này chứa mọi cập nhật giao diện mới nhất.

Các quyết định nhóm cần chốt khi triển khai: nền tảng web/mobile; phiên bản backend sẽ dùng; nguồn từ điển và audio/video mẫu; cách lưu tiến độ cho response không có điểm; phạm vi Talk chữ/giọng; lưu clip hay chỉ metadata; quyền giáo viên; tiêu chí đánh giá nhận dạng độc lập. Những khoảng trống này không chặn thiết kế màn hình và trạng thái, nhưng chặn việc công bố một số tính năng đã hoạt động hoàn chỉnh.
