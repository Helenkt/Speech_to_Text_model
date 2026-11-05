# Rà soát tài liệu ngày 05/11/2026

Phạm vi là project cũ AI-INTERVIEWER-LOCAL trong checkout Git
`work/speech-to-text-publish-20261022`, sau commit b530a72. Đối chiếu với mã nguồn,
file cấu hình, dữ liệu được theo dõi trên Git, tài liệu và lệnh cài/chạy. Không sửa
thuật toán, giao diện, model, database hoặc dữ liệu người dùng trong lượt này.

## Kết quả đối chiếu

| Nội dung | Kết quả |
| --- | --- |
| Cổng khuyến nghị uvicorn | 8001; main.py/CHAY_WEB.bat vẫn là 8000; launcher chọn cổng trống |
| Python đã kiểm thử | 3.11 x64; requirements runtime/dev/training tách riêng |
| Ollama mặc định | qwen2.5:3b sửa transcript/chấm; qwen3:8b chỉ sinh đề theo nhu cầu |
| STT | Faster-Whisper tự chọn medium/small theo tài nguyên, chấm lại dùng large-v3; không phải PhoWhisper của project thi mới |
| Dữ liệu khởi tạo | 900 VI + 900 EN, mỗi ngôn ngữ có 300 Easy/300 Medium/300 Hard |
| Demo | Ba tài khoản trong accounts_demo.csv đang được theo dõi trên Git; tạo có điều kiện trên database mới |
| Model fine-tune | Không có trên Git; setup Transformer tải baseline |
| Luyện tập | Chấm cuối phiên, xem transcript chỉ đọc/ghi lại trước xác nhận; chưa đủ bằng chứng giữ điểm chưa chốt, không đưa giáo viên |
| Interview thật | Có model phiên âm lại, quyết định giảng viên và lịch sử chấm; kiểm tra ngưỡng trước dùng điểm AI |
| SpecialistGrader | Shadow/offline, chưa thay pipeline chính |

## Đã sửa và bổ sung

- RubricGuard không còn mô tả luyện tập dưới ngưỡng sẽ chuyển giảng viên.
- Làm rõ nguồn sinh câu hỏi là ngân hàng learning, có thể gồm dữ liệu import; hai JSON chỉ là nguồn khởi tạo.
- Bổ sung cấu hình .env không ghi đè, các mặc định quan trọng và ưu tiên biến môi trường.
- Phân biệt STT setup-ready, trạng thái chuẩn bị theo phiên và model đang nằm trong RAM.
- Nêu Node.js là yêu cầu cho test frontend, không phải runtime; test DOM giả lập không phải kiểm chứng browser/micro thật.
- Bổ sung lỗi cổng/kết nối/Ollama/model, sao lưu database cùng voice và migration khi cập nhật.
- Cập nhật changelog theo asset 1.18.11, liên kết tài liệu mới và cách tính điểm luyện tập.
- Làm rõ JSON mới tải lên thư mục gốc Git không tự đi vào database; không thay dữ liệu đã nhập bằng việc chép đè tệp khởi tạo.

## Giới hạn kiểm chứng

Đã kiểm 36 file Markdown: không có liên kết nội bộ thiếu đích hoặc khối code
chưa đóng; `git diff --check` không có lỗi whitespace. Năm test trong
`test_documentation.py` và `test_requirements_manifest.py` đã qua (hai cảnh báo
deprecation từ môi trường). Đã kiểm sự tồn tại của tài liệu/script/file
khởi tạo và số lượng câu hỏi. Không có phép thử cài sạch trên máy khác hoặc tải
lại model trong lượt rà soát này. Lần test phần mềm ngay trước đó ngày 05/11/2026
đạt 974 test, hai cảnh báo deprecation từ môi trường; không phải đo WER/chất lượng
chấm trên sinh viên thật.

Các số liệu fine-tune/STT cũ vẫn là hồ sơ theo ngày; không chuyển thành cam kết
chính xác 99–100%, tốc độ mọi máy 8GB hay bảo đảm không có câu chưa chấm được.
Sau đợt rà soát đã bổ sung launcher [cài và chạy một lần bấm](../ONE_CLICK_SETUP.md).
Đây chưa phải bộ cài .exe hoặc gói offline, chưa kiểm chứng cài sạch trên máy
Windows mới và chưa kèm checkpoint fine-tune để tái lập nguyên trạng máy phát triển.
