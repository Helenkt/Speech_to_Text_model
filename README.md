# AI Interviewer Local

Hệ thống phỏng vấn kiến thức chạy local dành cho sinh viên, hỗ trợ tiếng Việt và tiếng Anh.

## Dự án chính

Toàn bộ mã nguồn, dữ liệu câu hỏi và hướng dẫn cài đặt nằm tại:

- [AI-INTERVIEWER-LOCAL](./AI-INTERVIEWER-LOCAL)
- [Hướng dẫn cài đặt và sử dụng](./AI-INTERVIEWER-LOCAL/README.md)
- [Requirements và các bước chạy trên máy mới](./AI-INTERVIEWER-LOCAL/REQUIREMENTS.md)
- [Cài đặt và chạy bằng một lần bấm](./AI-INTERVIEWER-LOCAL/ONE_CLICK_SETUP.md)
- [Rà soát tài liệu và giới hạn hiện tại](./AI-INTERVIEWER-LOCAL/docs/DOCUMENTATION_AUDIT_20261022.md)
- [Cập nhật tài liệu ngày 05/11/2026](./AI-INTERVIEWER-LOCAL/docs/DOCUMENTATION_AUDIT_20261105.md)
- [Cách tính điểm luyện tập](./AI-INTERVIEWER-LOCAL/PRACTICE_GRADING.md)

## Thành phần AI

- Speech-to-Text: Faster-Whisper.
- Sửa transcript và hỗ trợ chấm rubric: Qwen2.5 3B qua Ollama.
- Chấm theo ý rubric: RubricGuard Lite / MiniLM ONNX INT8, kèm kiểm tra logic và cơ chế chưa đủ cơ sở chấm.
- Dữ liệu: hai ngân hàng câu hỏi VI/EN thuộc bốn môn học.
- Môi trường: chạy local bằng FastAPI, SQLite và giao diện web.

Xem hướng dẫn trong thư mục dự án để cài Python, tải model Whisper và chạy `ollama pull qwen2.5:3b`.

## Trạng thái chất lượng

Luồng ghi âm, xác nhận transcript, chấm cuối phiên và giảng viên chấm lại đã có trong mã nguồn. Điều này không có nghĩa AI đã chấm đủ chính xác để tự quyết định điểm thi chính thức.

Bản Transformer thử nghiệm chưa được triển khai vì còn chấp nhận nhầm câu sai. Bộ [400 câu trả lời mẫu](./AI-INTERVIEWER-LOCAL/data/student_answer_dataset_v1/README.md) có nhãn AI dự thảo, chưa được dùng để thay model đang chạy. Xem [kết quả thử nghiệm](./AI-INTERVIEWER-LOCAL/docs/SEMANTIC_PILOT_20261021.md).

Repository chứa mã nguồn, test và dữ liệu học tập; không chứa trọng số model, cơ sở dữ liệu phiên thi hoặc voice sinh viên. Tải các model riêng theo hướng dẫn trong dự án. Tài khoản demo có sẵn chỉ dành cho kiểm thử local, không dùng mật khẩu demo khi triển khai thực tế.

Các file ngân hàng JSON ở thư mục gốc là tệp được tải lên repository; ứng dụng
không tự nhập chúng. Dữ liệu khởi tạo nằm trong `AI-INTERVIEWER-LOCAL/data`;
giảng viên nhập thêm qua giao diện quản lí câu hỏi. Project này không dùng Gemini
và không phải project thi riêng AI-EXAM-HYBRID.
