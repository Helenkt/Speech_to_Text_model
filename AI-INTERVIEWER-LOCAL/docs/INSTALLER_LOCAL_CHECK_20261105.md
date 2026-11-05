# Kiểm tra launcher thực tế ngày 05/11/2026

Phạm vi: project cũ AI-INTERVIEWER-LOCAL, launcher cài/chạy tự động. Không thay
thuật toán STT/chấm, không fine-tune hoặc sửa dữ liệu của project đang dùng.

## Đã thực hiện

- Chạy `setup_and_run.ps1 -VerifyStartup -Port 8093` bằng Windows PowerShell.
- Dùng Python 3.11 x64 đã có; tạo môi trường .venv riêng cho checkout và cài thật requirements.txt từ Internet. Lượt cài trước bị ngắt chưa có dấu hoàn tất; launcher đã tiếp tục cài, không báo sẵn sàng giả.
- Pip cài thành công và `pip check` trả `No broken requirements found`.
- Khởi động Ollama portable thật, đọc được model qwen2.5:3b đã tải sẵn; tái sử dụng Whisper và Transformer qua biến môi trường cấu hình cache. Không tải lại hoặc thay các model đó.
- Khởi động Uvicorn thật; `/api/health`, `/` và `/static/app.js` đều HTTP 200; nội dung HTML/JavaScript được đối chiếu với ứng dụng.
- Chạy lại toàn bộ bước kiểm tra lần hai: thư viện được nhận là đã sẵn sàng, không gọi pip install hoặc setup lại model. Exit code 0; tổng thời gian 33,51 giây, gồm kiểm thư viện, khởi động Ollama/backend, HTTP và dọn tiến trình. Không phải thời gian STT hay cam kết khởi động trên mọi máy.
- Đối chiếu SHA-256 trọng số RubricGuard INT8 và training_summary trước/sau: giữ nguyên.
- Chế độ VerifyStartup tự dừng các tiến trình nó tạo; không để tab trình duyệt trỏ vào server thử đã dừng. Không ghi lại voice hoặc câu trả lời sinh viên.

Các receipt và log local nằm trong `.runtime`, bị loại khỏi Git. Cấu hình dùng
lại cache chỉ áp dụng cho tiến trình thử; `.env.example` trên Git vẫn dùng các
đường dẫn trong project để máy khác tự chuẩn bị model của mình.

## Kiểm tra hồi quy

Toàn bộ **996 test qua trong 78,63 giây**, gồm hai test mới xác minh startup chỉ
chấp nhận đúng HTML/JavaScript và dọn tiến trình khi thành công/lỗi. Có hai cảnh
báo deprecation của môi trường TestClient; không có test lỗi hoặc bỏ qua.
Parser PowerShell không có lỗi.

## Chưa được phép suy ra

- Đây không phải cài sạch trên Windows chưa có Python/Ollama/model. Nhánh WinGet tải/cài Python và Ollama chưa được thực thi trong lượt thử này.
- Không thử gỡ/cài lại phần mềm hệ thống, không thử cấu hình mọi trường hoặc mọi máy RAM 4/8GB.
- Không đo WER, độ chính xác chấm, thời gian phiên âm thực hoặc chất lượng model trong lượt này.
- `.env`, database, voice, môi trường Python và trọng số không nằm trong commit. Model fine-tune vẫn cần artifact riêng như REQUIREMENTS.md.
