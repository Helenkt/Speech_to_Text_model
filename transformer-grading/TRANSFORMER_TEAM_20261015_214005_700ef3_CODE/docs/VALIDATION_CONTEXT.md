# Kết quả xác minh bản nâng cấp

Ngày: 14/10/2026. Môi trường thực thi: Linux, Python 3.12; máy người dùng là
Windows, Python 3.11.9. PowerShell/driver/GPU trên máy người dùng chưa được chạy trực tiếp.

- 100 kiểm thử của dự án và module ngữ cảnh chạy thành công.
- Có kiểm thử lưu metadata Transformer qua SQLite rồi đọc lại trong báo cáo.
- Kiểm tra cú pháp Python và JavaScript thành công.
- Đã thực thi prepare với 436 dòng: 316 train, 64 validation, 56 test,
  không loại dòng nào, không trùng nhóm câu hỏi giữa các split.
- Đã thực thi train hai optimizer steps, lưu safetensors/tokenizer/manifest,
  nạp lại checkpoint và chạy evaluate đủ 56 dòng test bằng một BERT ngẫu nhiên
  rất nhỏ dùng riêng cho smoke test. Model thử này không có khả năng chấm kiến thức
  và không nằm trong gói bàn giao. Kết quả của nó không được dùng làm chỉ số chất lượng.
- Xác minh model abstain khi chưa chắc và từ chối cắt bớt câu trả lời vượt 512 tokens.
- Phụ thuộc ML đã được thử: torch 2.14.1+cpu, transformers 4.57.6,
  sentencepiece 0.2.2, safetensors 0.8.0.

Chưa fine-tune model mDeBERTa nền trên câu trả lời sinh viên thật. Chưa đo cải thiện
MAE/đồng thuận giáo viên so với hệ thống hiện tại; chưa kiểm định tốc độ CPU Windows,
GPU CUDA, độ chính xác tiếng Anh hoặc tải đồng thời. Không có cam kết “chấm đúng tuyệt đối”.

Chế độ mặc định của app là off; lệnh train-demo chỉ bật shadow sau khi hoàn thành.
Checkpoint tạo từ dữ liệu demo luôn đánh dấu cần giáo viên duyệt.
