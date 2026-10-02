# AI Interviewer Local

Hệ thống phỏng vấn kiến thức chạy local dành cho sinh viên, hỗ trợ tiếng Việt và tiếng Anh.

## Dự án chính

Toàn bộ mã nguồn, dữ liệu câu hỏi và hướng dẫn cài đặt nằm tại:

- [AI-INTERVIEWER-LOCAL](./AI-INTERVIEWER-LOCAL)
- [Hướng dẫn cài đặt và sử dụng](./AI-INTERVIEWER-LOCAL/README.md)

## Thành phần AI

- Speech-to-Text: Faster-Whisper.
- Sửa transcript và hỗ trợ chấm rubric: Qwen2.5 3B qua Ollama.
- Dữ liệu: hai ngân hàng câu hỏi VI/EN thuộc bốn môn học.
- Môi trường: chạy local bằng FastAPI, SQLite và giao diện web.

Xem hướng dẫn trong thư mục dự án để cài Python, tải model Whisper và chạy `ollama pull qwen2.5:3b`.
