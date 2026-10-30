# Rubric Engine V15 — Gói tích hợp

Ngày 30/10/2026. SDK 1.0.0, engine 1.5.0-task-source-scope, core 1.3.0.

Gói này nhận câu hỏi và đáp án chuẩn, tạo rubric cho bảy dạng DEFINITION, COMPARISON, EXPLANATION, PROCEDURE, ENUMERATION, APPLICATION, ANALYSIS. Câu ghép được xử lý theo engine V15 hiện có. Trọng số Qwen không được huấn luyện hoặc thay đổi.

## Gói gồm những gì?

- Wheel Python `rubric_generator_sdk-1.0.0-py3-none-any.whl`: SDK, engine và core dùng namespace riêng. Không cần thư mục Rubric_Builder_7 cũ để chạy sau khi cài.
- Thư viện phụ thuộc đã tải sẵn cho Windows 64-bit và CPython 3.11, gồm Pydantic 2.14.1. Cài bằng `--no-index`, không tải qua mạng.
- Mã nguồn trong source; ví dụ gọi Python và gọi qua tiến trình JSON trong examples.
- Input/response/rubric JSON Schema trong schemas.
- INSTALL.ps1, SMOKE_TEST.ps1, tài liệu tích hợp và kiểm thử trong tests.
- Nhật ký nguồn và mã băm: chỉ thay đường dẫn import của sáu mô-đun V15/core được đưa vào namespace SDK; giữ nguyên prompt, quy tắc phân loại và tạo tiêu chí trong các mô-đun đó.

Ollama và trọng số `qwen3:4b-instruct-2507-q4_K_M` là phụ thuộc riêng, không nằm trong ZIP. Trên máy hiện tại, sử dụng model đã tải. Khi chuyển sang máy khác, phải chuẩn bị Ollama và đúng model trên máy đó; ZIP này không tự cung cấp trọng số. Không cần chạy thêm ollama serve nếu dịch vụ đã hoạt động.

## Cài ở máy Windows hiện tại

Giải nén vào D:\UP để có D:\UP\RUBRIC_ENGINE_V15_PACKAGE. Từ PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\INSTALL.ps1' `
  -PythonPath 'D:\UP\Rubric_Builder_7_Thiet_ke_va_ma_tham_chieu\Rubric_Builder_7\.venv\Scripts\python.exe'
```

Script dùng Python 3.11 hiện có để tạo `.venv` riêng trong gói, cài wheel/dependency offline, chạy pip check và doctor --offline. Nó không cài đè môi trường của dự án chính. Kết thúc thành công có dòng SDK_READY. Lệnh cài không gọi model.

Chuyển máy hoặc đổi vị trí triển khai: mang ZIP sang và cài lại; không sao chép `.venv` cũ. Bộ wheel phụ thuộc đi kèm chỉ dành cho Windows x64/CPython 3.11. Linux hoặc phiên bản Python khác có thể cài wheel SDK cùng dependency tương ứng, nhưng không dùng wheel pydantic-core win_amd64 đi kèm. Bộ SDK đã được thử trên Python 3.12/Linux trong môi trường xây dựng; PowerShell/Windows thật cần chạy kiểm tra tại máy đích.

## Kiểm tra kết nối và sinh thử

```powershell
# Chỉ kiểm tra SDK và /api/tags của Ollama: 0 lượt sinh model.
powershell -NoProfile -ExecutionPolicy Bypass -File `
  'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\SMOKE_TEST.ps1'

# Sinh rubric cho examples/input.json, lưu vào runtime/jobs/<job_id>.
powershell -NoProfile -ExecutionPolicy Bypass -File `
  'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\SMOKE_TEST.ps1' -Generate
```

Doctor OK xác nhận package, một phép biên dịch rubric bằng code và model xuất hiện trong Ollama khi kiểm tra online. Nó không xác nhận chất lượng ngữ nghĩa hoặc tốc độ Qwen. Khi sinh thử, đường dẫn rubric_json/rubric_markdown nằm trong `artifacts` của JSON kết quả.

## Gọi bằng Python

Môi trường đang chạy đoạn mã phải được cài wheel SDK. Có thể dùng Python riêng của gói qua `examples/python_integration.py --work-dir ...`, hoặc cài wheel vào môi trường backend nếu dependency tương thích.

```python
from rubric_generator_sdk import RubricGenerator

builder = RubricGenerator(work_dir=r"D:\AI_INTERVIEWER_DATA\rubric_jobs")
result = builder.generate(
    question_id="INTERVIEW_001",
    question="Định nghĩa mã phiên đăng nhập.",
    reference_answer="Mã phiên đăng nhập là mã định danh tạm thời đại diện cho một phiên đăng nhập.",
)

if result["status"] == "DRAFT_READY":
    rubric = result["rubric"]
    # Lưu rubric cùng mã băm và trạng thái chờ người phụ trách duyệt.
else:
    print(result["status"], result["error"])
```

Hai trường bắt buộc là question/reference_answer. question_id nên do dự án chính cấp; nếu bỏ qua, SDK sinh mã ổn định từ đầu vào chuẩn hóa. Mặc định 1000 đơn vị = 10 điểm, mỗi điểm 100 đơn vị. Có thể truyền total_units và task_budgets_units, ví dụ {"T1":400,"T2":600} khi đã xác định đúng hai task T1/T2. Ngân sách không khớp task sẽ bị chặn, không tự chia lại.

Các lựa chọn lúc khởi tạo: model, base_url, timeout (30–1200 giây mỗi lượt, mặc định 420), num_ctx (2048–16384, mặc định 4096), expected_model_digest (tùy chọn khóa đúng bản trọng số). Đây là cấu hình server, không nhận từ người dùng cuối. Cấu hình CPU/think=false/temperature=0 và hạn mức token giữ như V15.

## Dùng trong dự án chính

Đọc INTEGRATION.md. Với backend có môi trường Python khác, dùng `examples/subprocess_adapter.py`: backend chỉ cần thư viện chuẩn và gọi Python riêng của SDK bằng stdin/stdout JSON. Không cần cài Pydantic 2 vào backend cũ hoặc sửa tên mô-đun của nó.

Giao diện generate là đồng bộ, có thể mất nhiều phút. Đặt nó trong worker/hàng đợi tạo rubric; không để người dùng chờ trực tiếp ở request HTTP hoặc chạy lại mỗi lần ứng viên trả lời. Tạo rubric ở bước chuẩn bị câu hỏi, duyệt rồi lưu để tái sử dụng khi chấm interview.

Một máy CPU ít RAM nên có một worker và một work_dir chung cho tất cả tiến trình SDK dùng cùng Ollama. Khi bận, SDK trả BUSY ngay. Khóa này chỉ điều phối các tiến trình SDK dùng cùng thư mục, không điều phối ứng dụng khác gọi Ollama, máy khác hoặc thư mục khác. Đây không phải hàng đợi phân tán hay bộ điều phối GPU.

## Kết quả và chạy tiếp

| status | Ý nghĩa | CLI exit code |
|---|---|---:|
| DRAFT_READY | Bản nháp qua cấu trúc; cần duyệt nội dung | 0 |
| INVALID_INPUT | Đầu vào sai hợp đồng; không gọi model | 2 |
| NEEDS_REVIEW | Nguồn/nội dung/hợp đồng sinh cần rà soát; rubric=null | 3 |
| ERROR | Lỗi package, kết nối, lưu trữ hoặc checkpoint | 4 |
| BUSY | Worker khác đang dùng cùng work_dir; chưa gọi model | 5 |
| INTERRUPTED | Bị ngắt; kiểm tra checkpoint trước khi tiếp tục | 130 |

Mọi kết quả giữ human_approved=false, production_ready=false. `rubric_sha256` dùng để gắn việc duyệt vào đúng bản nội dung. `validate_rubric_dict` chỉ kiểm tra cấu trúc, không phê duyệt. Chính sách người duyệt/DB của dự án chính phải lưu riêng; không đổi cờ trong kết quả gốc để giả lập phê duyệt.

Mỗi job dùng hash của input, cấu hình, model digest, phiên bản Pydantic và runtime SDK. Cùng các yếu tố đó thì dùng lại các bước thành công, không gọi lại model cho bước đã lưu. Thay nội dung/cấu hình/model tạo job mới, giữ job cũ. Không nhập checkpoint V15 cũ vào SDK vì ràng buộc package khác.

Khi ERROR/NEEDS_REVIEW, mặc định không tự retry. Sau khi xử lý nguyên nhân có thể dùng `generate_input(..., retry_failed=True)` hoặc CLI `--retry-failed`. Chỉ bước chưa hoàn thành mới gọi model; cờ không sửa nội dung sai trong bước đã lưu. Nếu tiến trình chết đột ngột, khóa worker của hệ điều hành được giải phóng; khóa job cũ chỉ được dọn khi đã kiểm tra checkpoint đúng và có retry rõ ràng. Không tự xóa khóa/chỉnh checkpoint.

work_dir phải là thư mục riêng, ban đầu rỗng hoặc đã thuộc SDK. Nó lưu câu hỏi, đáp án, phản hồi model và kết quả; đặt ngoài thư mục public/static của web. Bản rubric_draft.* và sdk_result.json có thể được xuất lại khi dùng cache; lưu chỉnh sửa/duyệt của nhóm vào DB hoặc thư mục riêng. Không xóa toàn bộ runtime để retry một ca.

## Đưa ZIP tải về vào kho

Sau khi cài thành công:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  'D:\UP\RUBRIC_ENGINE_V15_PACKAGE\ARCHIVE_DOWNLOAD.ps1'
```

Script chỉ sao chép ZIP tải về vào thư mục con mới trong D:\UP\Rubric_Builder_7_Thiet_ke_va_ma_tham_chieu\kho, kiểm tra hash, rồi xóa ZIP tại Downloads. Giữ gói đang chạy, model, bộ 30 mẫu, mọi kết quả và dự án cũ để đối chiếu.

## Giới hạn của bản đóng gói

Việc đóng gói tạo giao diện tích hợp, không làm tăng độ chính xác của Qwen. User đã báo chạy ổn; tại thời điểm đóng gói chưa có test_bundle.json của bộ 30 mẫu để tự xác minh. Không tuyên bố đã nghiệm thu 30/30 hoặc đủ chất lượng production. Chưa kết nối DB/routes/hàng đợi thật của AI Interviewer. Những giới hạn ngữ nghĩa của V15 vẫn còn, gồm phạm vi nguồn, phần điểm và trùng ý diễn đạt khác. Nội dung rubric dùng chấm chính thức cần người có trách nhiệm duyệt.

Tài liệu kỹ thuật dùng để xây gói: https://packaging.python.org/en/latest/tutorials/packaging-projects/ và https://docs.python.org/3.11/library/msvcrt.html. Chi tiết kiểm chứng gói nằm trong VALIDATION.json; chỉ số kiểm thử phần mềm không phải độ chính xác model.
