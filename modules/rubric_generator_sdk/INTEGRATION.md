# Tích hợp Rubric Engine vào AI Interviewer

## Giao diện và vòng đời

1. Teacher/HR nhập câu hỏi và đáp án chuẩn. Backend cấp question_id riêng.
2. Backend lưu tác vụ PENDING vào hàng đợi của dự án.
3. Một worker gọi SDK. Cấu hình model/đường dẫn do server quản lý.
4. DRAFT_READY: lưu bản nháp cùng rubric_sha256, package_version, model_digest, input và review_status=PENDING.
5. Người phụ trách xem nội dung/mức điểm và duyệt đúng bản rubric. Lưu reviewer_id, reviewed_at, rubric_sha256 đã duyệt ở bảng duyệt của dự án. Chỉnh rubric sau duyệt tạo phiên bản mới và duyệt lại.
6. Hệ thống interview lấy rubric đã duyệt theo question_id + phiên bản/mã băm, rồi bộ chấm riêng đối chiếu câu trả lời ứng viên.

SDK không tạo tài khoản, không tự nhập DB, không cung cấp web server, không tự gửi thông tin hay chấm câu trả lời ứng viên. Luồng trên là hợp đồng để nhóm ghép vào backend hiện có.

## Cách 1 — Python cùng môi trường

Trong môi trường Python của backend đã tương thích Pydantic >=2.10,<3:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install `
  'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\wheelhouse\rubric_generator_sdk-1.0.0-py3-none-any.whl'
```

Nếu muốn cài hoàn toàn offline trên Windows x64/3.11, thêm `--no-index --find-links 'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\wheelhouse'`. Việc cài vào backend có thể thay dependency của backend; ưu tiên Cách 2 nếu chưa kiểm tra tương thích. Không cần thêm sys.path hoặc copy thư mục rubric_builder cũ. Dùng ví dụ python_integration.py hoặc public API RubricGenerator.

## Cách 2 — Gọi Python riêng của SDK

Đây là lựa chọn dùng ngay sau INSTALL.ps1, phù hợp khi backend hiện có Pydantic/SDK khác. Sao chép examples/subprocess_adapter.py vào lớp service của backend và gọi từ worker:

```python
from subprocess_adapter import generate_rubric

result = generate_rubric(
    python_executable=r"D:\UP\RUBRIC_ENGINE_V15_PACKAGE\.venv\Scripts\python.exe",
    work_dir=r"D:\AI_INTERVIEWER_DATA\rubric_jobs",
    question_id="INTERVIEW_001",
    question="Định nghĩa mã phiên đăng nhập.",
    reference_answer="Mã phiên đăng nhập là mã định danh tạm thời đại diện cho một phiên đăng nhập.",
)
```

Adapter dùng argv và UTF-8 qua stdin, không ghép câu hỏi vào lệnh shell. stdout là đúng một JSON; stderr là tiến độ. Có thể gọi cùng CLI từ Node/Java/C# bằng quy tắc tương tự. Callback Python không được dùng để thực hiện thay đổi DB quan trọng; nó chỉ báo tiến độ và lỗi callback bị bỏ qua.

Mặc định adapter không áp một timeout tổng ngoài timeout từng lượt của engine. Nếu worker đặt timeout tổng, phải cho phép đủ nhiều lượt model, xử lý TimeoutExpired và giữ checkpoint để rà soát/tiếp tục. Không dùng timeout HTTP vài chục giây cho toàn bộ việc sinh rubric. Không tự retry liên tục khi trả NEEDS_REVIEW hoặc INVALID_INPUT.

## Trường dữ liệu cần giữ

| Trường | Công dụng |
|---|---|
| api_schema_version | Phiên bản hợp đồng kết quả |
| status | Phân nhánh xử lý và trạng thái UI |
| question_id | Liên kết câu hỏi của dự án |
| job_id | Khóa công việc nội bộ SDK, gồm input/cấu hình/runtime |
| rubric | Dữ liệu rubric; null khi chưa có bản nháp hợp lệ |
| rubric_sha256 | Gắn duyệt với đúng nội dung rubric |
| model_tag, model_digest | Truy vết trọng số đã dùng |
| package_version, engine_version | Truy vết mã chạy |
| metrics.model_calls_total, new_model_calls | Số lượt tích lũy và lượt mới của lần gọi |
| quality_report | Tín hiệu cần rà soát, không phải phê duyệt |
| error.code, error.message | Chẩn đoán có cấu trúc |
| artifacts | Đường dẫn nội bộ; không trả nguyên đường dẫn lên frontend công khai |

Các schema được đóng gói trong schemas. JSON rubric giữ schema core hiện có; điểm là số nguyên đơn vị 1/100 điểm. Không chuyển thành số thực rồi làm tròn từng tiêu chí trước khi tính tổng.

## Xử lý trạng thái trong worker

- DRAFT_READY → DRAFT_PENDING_REVIEW trong DB; chưa tự bật cho kỳ phỏng vấn chính thức.
- NEEDS_REVIEW → NEEDS_AUTHOR_REVIEW; hiển thị nguyên nhân cho người soạn câu hỏi/đáp án.
- INVALID_INPUT → INPUT_ERROR; yêu cầu sửa dữ liệu.
- BUSY → giữ trong hàng đợi, chạy khi worker rảnh; không tạo worker song song hoặc work_dir mới để vượt khóa.
- ERROR → ghi lỗi vận hành, kiểm tra Ollama/package/disk; retry có kiểm soát sau khi xử lý.
- INTERRUPTED → đánh dấu dở dang và xem checkpoint trước khi retry.

Cùng question_id có thể có nhiều phiên bản đầu vào/rubric. DB không nên ghi đè bản đã duyệt chỉ bằng question_id. Dùng khóa phiên bản hoặc rubric_sha256 và một con trỏ tới phiên bản đang sử dụng.

## Nghiệm thu tích hợp tại dự án chính

- Gửi một câu đơn và một câu ghép từ backend; kiểm tra tiếng Việt, question_id và tổng điểm.
- Cùng request chạy lại: new_model_calls=0 và cùng job_id nếu môi trường/model không đổi.
- Thử dữ liệu trống, Ollama tắt, hai job đồng thời và tiến trình bị ngắt; không ghi lỗi thành rubric đã duyệt.
- Kiểm tra duyệt đúng hash và bộ chấm lấy đúng phiên bản rubric.
- Đo thời gian/queue thực tế trên máy đích. Gói không công bố mục tiêu dưới 5 giây hoặc kết quả thử tải đa người dùng.

Đây là danh sách kiểm tra tích hợp; các thao tác DB/queue của dự án chính chưa được thực hiện trong bản bàn giao này.
