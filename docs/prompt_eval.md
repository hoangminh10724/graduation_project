# Đánh giá prompt gia sư Talk

Tạo phiên với chủ đề và CEFR tương ứng, gửi lần lượt từng câu qua `/chat/stream` và chấm nội dung của sự kiện `done`. Với tình huống phát âm, dùng `/ws/audio` có đánh giá âm vị. Ghi model, câu trả lời, số từ và thời gian tới token đầu tiên để có thể chạy lại.

| CEFR | Đầu vào | Kiểm tra |
|---|---|---|
| A2 | I goes to school by bus. | Dùng tự nhiên “I go” và hỏi thêm về việc đi học. |
| A2 | Yesterday I eat noodles. | Dùng “I ate” trong câu trả lời. |
| A2 | My sister is 15 years. | Dùng “15 years old” và hỏi câu ngắn. |
| A2 | I like music. | Tiếp tục chủ đề bằng một câu hỏi mở. |
| A2 | I don't understand. | Giải thích bằng từ đơn giản, một ý mỗi câu. |
| B1 | I have visited Da Nang last year. | Dùng thì quá khứ đơn với “last year”. |
| B1 | My city has many traffic. | Dùng “a lot of traffic” một cách tự nhiên. |
| B1 | I went to the market. Âm /θ/ có điểm 40. | Đưa tối đa một gợi ý luyện âm từ kết quả chấm. |
| B1 | I think the movie was interesting. Chỉ có transcript. | Tiếp tục hội thoại, tránh suy đoán lỗi phát âm. |
| B2 | If I would have more time, I'd volunteer. | Dùng cấu trúc điều kiện phù hợp và hỏi về hoạt động tình nguyện. |

Mỗi câu nên có tối đa 40 từ, một câu hỏi mở và mức từ vựng phù hợp. Các tình huống trên là bộ mẫu để đánh giá với LLM thật.
