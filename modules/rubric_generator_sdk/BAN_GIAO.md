# Bàn giao: Bộ sinh rubric V15

**Đầu vào:** một câu hỏi và đáp án chuẩn. **Đầu ra:** rubric nháp có tiêu chí, nguồn và mức điểm để hệ thống khác dùng. Phần này chạy độc lập với hệ thống phỏng vấn, không ghi âm và không chấm câu trả lời của thí sinh.

**Windows, lần đầu:** cài Python 3.11 x64 có Tk và Ollama. Kiểm tra bằng `ollama list`; nếu thiếu, chạy `ollama pull qwen3:4b-instruct-2507-q4_K_M`. Mở Ollama và nhấp đôi **START_GUI.cmd**. SDK và các thư viện Python được cài từ wheelhouse đi kèm. Trọng số Qwen không nằm trong gói; sau khi chuẩn bị model, ứng dụng dùng Ollama cục bộ ở 127.0.0.1:11434.

**Thử một câu:** Mở TXT / JSON → chọn gui/Stack.txt (UTF-8) hoặc examples/input.json → Tạo rubric. TXT dùng hai nhãn đầu dòng “câu hỏi:” và “câu trả lời:”. Khi DRAFT_READY, chọn Lưu rubric JSON. NEEDS_REVIEW là chưa có rubric hợp lệ; xem báo cáo lỗi. Mỗi lần bấm tạo là một lượt mới để đo thời gian. Dữ liệu cục bộ nằm tại gui/runtime/. Kiểm tra nội dung trước khi sử dụng để chấm thật.

Bảy dạng trong mã: DEFINITION, COMPARISON, EXPLANATION, PROCEDURE, ENUMERATION, APPLICATION, ANALYSIS. Hỗ trợ nhiều yêu cầu trong cùng câu hỏi. Mẫu Stack chỉ kiểm tra dạng định nghĩa; examples/input.json là câu ghép.

Tích hợp Python/CLI: xem README_VI.md và INTEGRATION.md. Kiểm thử phần mềm sau cài đặt: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Chạy kiểm thử offline không chứng minh độ chính xác của Qwen trên câu hỏi thực tế.
