# RUBRIC KIỂM ĐỊNH CÂU HỎI DO AI SINH

## 1. Mục tiêu

Rubric này kiểm soát câu hỏi do LLM sinh trước khi đưa vào phiên phỏng vấn. Câu hỏi phải:

- Chỉ sử dụng kiến thức từ `question_bank_vi.json` và `question_bank_en.json`.
- Có độ khó xác định được bằng tiêu chí đo lường, không dựa vào cảm tính.
- Có các mức `Dễ`, `Trung bình`, `Khó` theo cấu hình đề; lộ trình thích ứng cũ được mô tả riêng ở mục 6.
- Có đáp án tham chiếu và các ý chấm điểm phù hợp với câu hỏi.
- Phù hợp với phỏng vấn trực tiếp bằng giọng nói.

File cấu hình máy đọc nằm tại `data/question_generation_rubric.json`.

**Phạm vi hiện tại:** đây là tiêu chuẩn thiết kế, không phải chứng nhận mọi câu sinh
ra đã đúng. Phiên mới mặc định lưu đề và độ khó từ đầu, chấm cuối phiên; không đổi
độ khó theo điểm từng câu. Mục 6 chỉ mô tả cơ chế thích ứng cũ.

## 2. Quy trình sinh và kiểm định

1. Hệ thống lấy nguồn nội bộ còn hoạt động trong ngân hàng `learning`, đúng môn/ngôn ngữ và chủ đề nếu có chọn. Chưa lọc bắt buộc trạng thái giảng viên đã duyệt của nguồn.
2. LLM sinh một câu hỏi mới và trả về đầy đủ dữ liệu theo schema quy định.
3. Backend kiểm tra điều kiện bắt buộc, cấp độ khó, độ trùng và cấu trúc dữ liệu.
4. Backend lưu kết quả quy tắc cùng `semantic_review_required=true`; chưa có một LLM độc lập tự kiểm chứng nội dung. Giảng viên cần kiểm tra câu hỏi, đáp án và key points.
5. Từ 85/100 và không lỗi bắt buộc nhận nhãn rubric `practice_eligible`, không đồng nghĩa tự đưa vào ngân hàng.
6. Luồng sinh hiện lưu bản nháp; giảng viên duyệt trước khi xuất bản vào ngân hàng, kể cả câu luyện tập đạt ngưỡng.

LLM không được tự coi điểm do chính nó chấm là bằng chứng duy nhất. Kết quả phải qua kiểm tra quy tắc của backend; câu kiểm tra thật cần thêm quyết định của giáo viên.

Các hàng G1/G3 và nhóm “Đáp án tham chiếu” là mục tiêu cần kiểm định nội dung.
Mã hiện tại kiểm tra ID/trích dẫn khớp nguồn, trường bắt buộc, key points không rỗng/trùng
và khai báo độ khó; điểm `reference_correctness` chủ yếu phản ánh có reference.
Không suy ra tính đúng đắn ngữ nghĩa hoặc độ khó thực tế chỉ từ tổng điểm này.

## 3. Điều kiện bắt buộc

Chỉ cần vi phạm một điều kiện dưới đây thì câu hỏi bị loại, dù tổng điểm cao:

| Mã | Điều kiện |
|---|---|
| G1 | Có ID câu nguồn hợp lệ; không bổ sung kiến thức Internet hoặc kiến thức ngoài dữ liệu đã duyệt. |
| G2 | Đủ câu hỏi, đáp án tham chiếu, key points, mục tiêu học tập và bằng chứng độ khó. |
| G3 | Câu hỏi, đáp án và key points cùng đánh giá một mục tiêu học tập chính. |
| G4 | Các chỉ số độ khó phải nằm đúng phạm vi của cấp đã gắn nhãn. |
| G5 | Không để lộ nguyên đáp án hoặc toàn bộ key points trong câu hỏi. |
| G6 | Không trùng hoặc gần trùng câu đã hỏi trong phiên. |
| G7 | Câu hỏi phải rõ khi nghe một lần và trả lời được bằng lời nói trong thời gian quy định. |

## 4. Tiêu chuẩn ba cấp độ

| Tiêu chí | Dễ | Trung bình | Khó |
|---|---:|---:|---:|
| Bloom | Nhớ, hiểu | Áp dụng, phân tích | Phân tích, đánh giá, sáng tạo |
| Số khái niệm | 1 | 1-2 | 2-4 |
| Số bước suy luận | 1 | 2-3 | 3-5 |
| Số ràng buộc | 0-1 | 1-2 | 2-4 |
| Thời lượng trả lời | 20-45 giây | 45-90 giây | 90-180 giây |
| Số key points | 2-3 | 3-4 | 4-6 |
| Dạng câu hỏi | Định nghĩa, nhận biết, mô tả, ví dụ cơ bản | Áp dụng, so sánh, chẩn đoán, giải thích vì sao | Thiết kế, bảo vệ lựa chọn, đánh giá đánh đổi, phân tích lỗi |

### Dễ

Câu hỏi kiểm tra một khái niệm nền tảng. Sinh viên chỉ cần nhớ hoặc giải thích trực tiếp, không cần ghép nhiều ý hay xử lý tình huống phức tạp.

### Trung bình

Câu hỏi yêu cầu dùng kiến thức trong một tình huống, so sánh hai lựa chọn hoặc giải thích nguyên nhân. Câu trả lời phải có chuỗi suy luận ngắn và ít nhất một ràng buộc.

### Khó

Câu hỏi yêu cầu tổng hợp nhiều khái niệm, đánh giá đánh đổi hoặc thiết kế giải pháp có nhiều ràng buộc. Câu dài, nhiều thuật ngữ hoặc đánh đố không tự động được xem là câu khó.

## 5. Thang điểm 100

| Nhóm đánh giá | Điểm tối đa | Cách đánh giá |
|---|---:|---|
| Bám nguồn đã duyệt | 20 | Mọi nội dung và đáp án đều truy vết được về câu nguồn. |
| Mục tiêu học tập | 10 | Mục tiêu rõ, cụ thể và chỉ có một trọng tâm chính. |
| Đúng cấp độ khó | 25 | Bloom, số khái niệm, bước suy luận, ràng buộc và thời lượng đều phù hợp. |
| Đáp án tham chiếu | 15 | Chính xác, trả lời trực tiếp câu hỏi và không thêm kiến thức ngoài nguồn. |
| Key points | 10 | Đủ ý, không trùng nhau, có thể dùng để chấm câu trả lời. |
| Rõ ràng khi hỏi miệng | 10 | Một nghĩa, không mơ hồ, không quá dài và nghe một lần có thể hiểu. |
| Ngôn ngữ | 5 | Đúng tiếng Việt hoặc tiếng Anh, thuật ngữ nhất quán. |
| Không trùng lặp | 5 | Không sao chép hoặc diễn đạt lại gần như nguyên câu đã dùng. |

### Quyết định

| Kết quả | Điều kiện | Xử lý |
|---|---|---|
| Đủ điều kiện luyện tập | Từ 85 điểm, không lỗi bắt buộc | Nhận nhãn rubric; vẫn cần duyệt bản nháp trước khi vào ngân hàng. |
| Cần giáo viên duyệt | 75-84 điểm, không lỗi bắt buộc | Giáo viên sửa hoặc phê duyệt. |
| Loại | Dưới 75 điểm hoặc có lỗi bắt buộc | Không đưa vào ngân hàng câu hỏi. |
| Kiểm tra thật | Bất kỳ mức điểm nào | Luôn cần giáo viên duyệt trước khi mở đợt kiểm tra. |

## 6. Quy tắc chuyển độ khó cũ

Không áp dụng cho phiên mặc định `DEFER_GRADING_UNTIL_FINISH=true`. Phiên mới
chuẩn bị toàn bộ câu hỏi/độ khó trước khi trả lời. Không phải mọi phiên đều bắt buộc
đi từ Dễ đến Khó; cấu hình đề do người dùng/giảng viên chọn quyết định phạm vi.

- Bắt đầu ở mức Dễ nếu giáo viên không chọn mức khác.
- Điểm câu trước từ 80 trở lên và độ tin cậy đánh giá từ 0,65: tăng một cấp.
- Điểm từ 45 đến dưới 80: giữ nguyên cấp, nhưng đổi góc hỏi.
- Điểm dưới 45: giảm một cấp và hỏi lại theo hướng chẩn đoán phần chưa hiểu.
- Không nhảy trực tiếp từ Dễ lên Khó và không thay đổi quá một cấp sau một câu trả lời.
- Khi đã ở mức Khó, kết quả thấp chỉ được giảm về Trung bình.

Ví dụ lộ trình hợp lệ: `Dễ -> Dễ -> Trung bình -> Trung bình -> Khó`.

Ví dụ lộ trình không hợp lệ: `Dễ -> Khó`.

## 7. Dữ liệu LLM phải trả về

Mỗi câu sinh mới phải có: ID, ngôn ngữ, môn học, năng lực, chủ đề, khái niệm, độ khó, mức Bloom, mục tiêu học tập, câu hỏi, đáp án tham chiếu, key points, ID câu nguồn, bằng chứng nguồn và bằng chứng độ khó.

Phần bằng chứng độ khó phải khai báo rõ:

- Số khái niệm cần sử dụng.
- Số bước suy luận cần có.
- Số ràng buộc trong tình huống.
- Thời lượng dự kiến để trả lời.
- Lý do câu hỏi thuộc cấp độ đã chọn.

Nhờ đó backend có thể bác bỏ trường hợp LLM gắn nhãn `Hard` cho một câu chỉ yêu cầu định nghĩa đơn giản.
