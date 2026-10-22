# Gói Transformer cho nhóm

Gói được xuất từ máy người dùng. Script chỉ đọc dự án, không cài thư viện,
không train, không sửa .env/database, không commit/push GitHub.

## 1. Các phần
- CODE.zip: core/ là module và công cụ; integration_reference/ là mã để SO SÁNH/GHÉP.
- MODEL.zip: giải nén vào thư mục gốc AI-INTERVIEWER-LOCAL để có models/context-demo_fixed_20261014_163341/.
- docs/: tài liệu gốc của phần Transformer.
- FILE_MANIFEST.json: danh sách và SHA-256 từng file khi đóng gói.

KHÔNG chép đè nguyên integration_reference/ vào dự án. Bản Transformer có thể
được làm trên nền cũ hơn GitHub của nhóm. Mọi khác biệt chưa chắc thuộc Transformer.
REVIEW_ONLY.patch chỉ phục vụ xem xét, không phải bản vá đã kiểm thử để áp dụng tự động.
Không xóa file của nhóm chỉ vì không có trong bản Transformer.

## 2. Ghép vào dự án (Python 3.11)
1. Tạo nhánh riêng/backup dự án nhóm; giải nén hai ZIP vào thư mục tạm.
2. Thêm các file trong core/ vào đúng đường dẫn của dự án. Nếu đã có file,
   so sánh trước. CONTEXT.env.example chỉ là mẫu, không thay thế .env.
3. Ghép thay đổi liên quan Transformer bằng cách so sánh team_zip/ với
   transformer_version/, ưu tiên app/config.py, app/main.py,
   app/services/evaluator.py, app/services/teacher_review.py. Rà soát thêm
   CHANGED_FILES.json cho phần lưu điểm, báo cáo hoặc giao diện liên quan.
4. Giải nén MODEL.zip vào gốc dự án để tạo models/context-demo_fixed_20261014_163341/.
5. Cài phụ thuộc trong .venv đang dùng của nhóm (CPU):

```powershell
.\.venv\Scripts\python.exe -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-context.txt
```

Máy đang dùng PyTorch CUDA cần giữ bản tương thích thay vì cài lại bản CPU.
Không tự thay phiên bản thư viện trong lúc bàn giao nếu chưa kiểm thử.

6. Bổ sung/cập nhật các khóa trong CONTEXT.env.example vào .env của từng máy.
   Giữ cấu hình khác của mỗi người; không commit .env cá nhân.
7. Kiểm tra checkpoint riêng:

```powershell
.\.venv\Scripts\python.exe -m scripts.context.check --model "models/context-demo_fixed_20261014_163341" --id CTX_OVERFIT --answer "Overfitting là khi mô hình học quá sát dữ liệu huấn luyện, kể cả nhiễu. Mô hình làm tốt trên train nhưng tổng quát hóa kém trên dữ liệu mới. Có thể giảm bằng regularization, early stopping hoặc bổ sung dữ liệu phù hợp."
```

8. Chạy backend theo README của nhóm, kiểm tra /api/health có context_grader.
   Health installed=true chỉ kiểm tra manifest; cần nộp một bài qua giao diện
   và xác nhận kết quả Transformer được lưu trong metadata/báo cáo.
   Chạy kiểm thử hồi quy hiện có của nhóm trước khi merge.

## 3. GitHub và checkpoint
Commit mã nguồn sau khi ghép và kiểm tra. Gửi MODEL.zip riêng cho nhóm;
không thêm cả ZIP hoặc trọng số model vào commit mã nguồn thông thường.
Nếu dùng Git LFS hoặc nơi lưu model riêng, nhóm thống nhất cách quản lý trước.
Không gửi .venv, .env cá nhân, database hoặc audio sinh viên.

## 4. Trạng thái bàn giao
Checkpoint đã suy luận được qua CLI, còn demo_only và dùng shadow.
Hai câu Overfitting chưa đủ đo độ chính xác. Còn cảnh báo tokenizer cần kiểm tra.
Không hạ ngưỡng chỉ để lấy nhãn met; chưa dùng để chốt điểm tự động.
Gói này là bộ bàn giao để GHÉP MÃ, không phải installer tự ghép được mọi bản backend.
