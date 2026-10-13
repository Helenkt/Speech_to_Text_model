# Rubric label datasets

Thư mục này chứa dữ liệu gán nhãn dùng để huấn luyện hoặc đánh giá bộ chấm
điểm câu trả lời. Đây không phải ngân hàng câu hỏi để nhập trực tiếp qua màn
hình Giáo viên.

## Cấu trúc

- `rubric_labels/`: bộ đầy đủ cho AI101, DB101, DSA101 và OOP101. Mỗi môn có
  một bản JSON và một bản JSONL chứa cùng các dòng dữ liệu.
- `evaluation_samples/`: bộ mẫu nhỏ độc lập để kiểm tra pipeline. ID trong bộ
  mẫu có thể trùng với bộ đầy đủ nhưng nội dung khác, vì vậy không được gộp
  theo `question_id`.

Mỗi dòng mô tả quan hệ giữa câu trả lời sinh viên và một tiêu chí rubric, gồm
câu hỏi, tiêu chí, mệnh đề tham chiếu, bằng chứng, nhãn quan hệ, độ bao phủ và
điểm Giáo viên.

## Quy mô bộ đầy đủ

| Môn | Dòng nhãn | Câu hỏi | Câu trả lời |
| --- | ---: | ---: | ---: |
| AI101 | 100 | 10 | 40 |
| DB101 | 96 | 10 | 40 |
| DSA101 | 88 | 10 | 40 |
| OOP101 | 80 | 10 | 40 |
| **Tổng** | **364** | **40** | **160** |

Các file đã được kiểm tra trường bắt buộc, `label_id`, giới hạn điểm và số dòng
giữa JSON/JSONL trước khi đưa vào repository.
