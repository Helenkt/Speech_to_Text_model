# Hướng dẫn duyệt nhãn theo ý rubric

## 1. Duyệt rubric trước

Đọc câu hỏi, `source_criteria`, `source_review_note` và `rubric_draft`. Mỗi ý nhỏ phải thuộc nội dung nguồn, xác định được khi nào đúng và không gộp nhiều mệnh đề độc lập. Không thêm yêu cầu ngoài câu hỏi hoặc ngoài tài liệu được phép.

Các ý con giữ tổng điểm của tiêu chí gốc. Chia đều chỉ là dự thảo. Nếu phải thay ngân sách tiêu chí hoặc định nghĩa nguồn, cần một phiên bản rubric mới có truy vết, không sửa âm thầm điểm nguồn trong bộ này. Nếu hai ý là đồng nghĩa, không coi một cách diễn đạt đầy đủ là thiếu chỉ vì sinh viên không nhắc cả hai cách. Cần xem xét gộp tiêu chí trùng ở phiên bản sau.

Sau khi xác nhận, điền `rubric_review.status = "approved"`, `reviewer_id`, `reviewed_at` có múi giờ và `comment` nêu việc xác nhận phạm vi/điểm.

## 2. Quyết định nhãn

| Nhãn | Khi nào dùng | Bằng chứng |
| --- | --- | --- |
| `supported` | Nội dung đúng, trực tiếp hoặc hàm ý tương đương đủ rõ trong ngữ cảnh câu hỏi | Trích nguyên văn câu sinh viên |
| `missing` | Chưa thấy sinh viên trình bày ý đó | `null`, không bịa câu trích dẫn |
| `contradicted` | Sinh viên khẳng định điều trái ý rubric hoặc đảo vai trò/số/điều kiện | Trích phát biểu sai đã được chốt |
| `needs_review` | Không đủ căn cứ, mơ hồ điều kiện hoặc hai ý trái nhau chưa rút lại | Trích đoạn chứa vấn đề, chưa xuất huấn luyện |

Không bắt sinh viên nói đúng từ khóa hoặc giống hệt đáp án. Không coi mọi câu ngắn là thiếu. Đồng thời không tự bổ sung phép tính, điều kiện hay giải thích chưa được nói chỉ vì người chấm biết kiến thức đó. Khi hai cách hiểu đều hợp lý, chuyển cần xem lại thay vì ép nhãn.

Một câu trả lời có thể đúng ý A, thiếu ý B, sai ý C. Không gán một nhãn chung rồi sao chép cho tất cả tiêu chí. Không tự cho 50% một ý đang mơ hồ.

## 3. Phủ định và tự sửa

- Đọc cả câu trả lời, không chỉ lấy câu cuối hoặc tìm từ khóa.
- “Em nói X là nhầm, sửa lại Y”: đánh giá kết luận Y nếu X được rút lại rõ.
- Nói đúng rồi rút lại để chốt sai: nhãn cuối có thể `contradicted`, không luôn coi có từ “sửa” là đúng.
- Hai khẳng định ngược nhau không chốt: `needs_review` cho ý bị ảnh hưởng. Các ý độc lập khác vẫn đánh giá riêng.
- Không đọc phủ định trong câu được trích để phản bác thành quan điểm cuối của sinh viên.
- Số, mẫu số, ký hiệu độ phức tạp, vai trò chủ thể và điều kiện áp dụng đều có thể làm thay đổi nghĩa.

## 4. Bằng chứng và lý do

`start` và `end` dùng số thứ tự Unicode code point, đầu gồm/cuối không gồm. `student_answer[start:end]` phải bằng chính xác `quote`. Nếu sửa đoạn trích, phải sửa offset; có thể dùng hàm `evidence(text, quote)` trong công cụ để tính lại. Không dùng vị trí byte UTF-8 hoặc UTF-16.

Lý do duyệt cần chỉ rõ vì sao câu trích đúng/sai/thiếu so với ý rubric. Ví dụ: “Sinh viên dùng tổng dự đoán dương làm mẫu số cho recall, nhưng ý rubric yêu cầu tổng dương thật”. Không chỉ ghi “đúng” hoặc “AI bảo vậy”.

## 5. Điền kết quả duyệt

Trong mỗi `point_assessments`:

- `reviewed_relation`: một trong supported/missing/contradicted sau khi người duyệt đã kết luận.
- `reviewed_evidence`: bằng chứng đúng với nhãn đã duyệt; missing phải là null.
- `reviewed_reason`: lý do người duyệt viết hoặc xác nhận sau khi kiểm tra.
- `review_status`: approved nếu đã quyết định chắc; needs_review nếu còn bất đồng; rejected nếu mẫu không phù hợp.
- `reviewer_id`: mã người duyệt, không cần ghi thông tin cá nhân không liên quan.
- `reviewed_at`: ví dụ `2026-10-22T14:00:00+07:00`, là thời điểm thực sự duyệt.

Giữ các trường `proposed_*` để thấy bản AI đề xuất ban đầu. Không đổi nhãn đề xuất cho khớp kết quả nhằm xóa dấu vết. Nhãn needs_review chưa giải quyết không được biến thành missing để đủ số lượng.

Công cụ chỉ xuất một câu trả lời khi mọi ý của câu đó đã duyệt và rubric của câu hỏi được duyệt. Toàn bộ file vẫn giữ thông tin đây là dữ liệu tổng hợp, không đổi thành câu trả lời sinh viên thật.

## 6. Kiểm soát chất lượng

Ưu tiên người duyệt thứ hai cho câu có phủ định lồng nhau, điều kiện, tự đính chính, phản ví dụ số và ghi chú phạm vi nguồn. Nếu hai người bất đồng, cần thảo luận/quyết định có lý do; không tự dùng đa số AI làm chuẩn.

Lấy mẫu ngẫu nhiên cả những nhãn nhìn có vẻ dễ. Chỉ xem câu model không chắc sẽ bỏ sót trường hợp model rất tự tin nhưng sai. Kiểm tra công cụ chỉ xác nhận cấu trúc và truy vết, không xác nhận ý nghĩa nhãn đúng 100%.

## 7. Tách lỗi STT khỏi kiến thức

Bộ hiện tại không có audio. Khi bổ sung dữ liệu thật, lưu riêng audio, transcript STT và transcript đối chiếu đã xác nhận từ audio. Không sửa đáp án sai của sinh viên thành đáp án đúng. Lỗi hệ thống nghe “không” thành “có” phải được ghi là lỗi STT, không dùng nó để kết luận sinh viên không hiểu bài.

Ẩn danh và có quyền sử dụng dữ liệu thật. Giữ riêng dữ liệu kiểm thử; không đưa các lỗi trong bộ test vào train rồi tiếp tục báo kết quả trên cùng test như thể chưa từng nhìn thấy.
