# RubricGuard Lite

Các số liệu fine-tune và chế độ chọn lọc bên dưới mô tả artifact trên máy phát triển
ngày 16/10/2026, không tự có trong bản tải Git. Lệnh setup chỉ tải baseline; cần đủ
artifact và metadata hợp lệ mới có chế độ chọn lọc tương ứng. Xem REQUIREMENTS.md.

RubricGuard Lite là bộ chấm lai chạy local, được đặt sau bước Speech-to-Text và sửa
bản chép lời. Bộ chấm không thay đổi nội dung giọng nói và không chạy trong lúc thu âm.

## Luồng xử lý

1. `FactGuard` kiểm tra số, đơn vị, người/vật và quan hệ hơn, kém, bằng.
2. MiniLM Transformer ONNX INT8 đối chiếu từng ý trong câu trả lời với từng tiêu chí rubric.
3. Model trả ba xác suất: `entailment`, `neutral`, `contradiction`.
4. Các ý vượt ngưỡng tin cậy đã kiểm định được chấm bằng Transformer; Qwen chỉ nhận các ý chưa rõ.
5. Bài dưới ngưỡng điểm vẫn được đưa vào hàng chờ để giảng viên chấm lại.

## Vì sao dùng kiến trúc này

- Model INT8 khoảng 102 MB, phù hợp hơn model mDeBERTa FP32 khoảng 1,1 GB.
- Bản fine-tune nén trọng số: khoảng 31 ms/tiêu chí, P95 khoảng 52 ms khi giới hạn một luồng CPU trên máy thử.
- Luật số học chặn lỗi nguy hiểm mà mô hình ngôn ngữ thường xử lý không ổn định.
- Qwen chỉ xử lý ca khó, giảm thời gian chấm so với gọi LLM cho mọi câu.

## Bản fine-tune hiện tại

Đã fine-tune trên 364 mẫu tiếng Việt nội bộ, chia theo câu hỏi thành train/validation/test.
Checkpoint được chọn ở vòng 6. Bản đang dùng nằm tại `models/rubricguard-lite`.

| Phép đo trên 72 mẫu test chưa học | Gốc FP32 | Fine-tune FP32 | Fine-tune INT8 weights |
|---|---:|---:|---:|
| Accuracy, mệnh đề đầy đủ | 61,11% | 77,78% | 76,39% |
| Macro-F1 | 0,5685 | 0,7568 | 0,7435 |
| Recall mâu thuẫn | 33,33% | 66,67% | 66,67% |

Accuracy khi dùng tiêu chí ngắn đạt 86,11%, là một phép đo riêng với cách viết đầu vào khác.
Kết quả này không phải tỷ lệ tự động chấm toàn bộ bài thi. Xem [báo cáo fine-tune](FINETUNE_REPORT_20261016.md).

## Cài model gốc khi chưa có bản fine-tune

```powershell
.\.venv\Scripts\python.exe tools\setup_rubricguard_lite.py
```

Lệnh trên tải model gốc, không tải checkpoint fine-tune của project.
Model gốc được ghim tại revision `0a71e92a985b6e1ad1828cf67ce9c459639c1dca`.
Thư mục `models/` không được đưa lên Git để tránh repository quá lớn.

## Quality gate

Chế độ tự chấm không giới hạn chỉ được bật khi đánh giá bản runtime xác nhận đồng thời:

- Validation và test macro-F1 từ `0.80`, recall mâu thuẫn từ `0.90`.
- Tỷ lệ nhầm câu mâu thuẫn thành đúng trên test không quá `0.02`.

Chế độ chọn lọc hiện được bật riêng cho tiếng Việt: temperature `2.3`, ngưỡng xác suất
sau hiệu chỉnh `0.91`. Ngưỡng được chọn trên validation; test kiểm tra riêng đạt 15/15
lượt vượt ngưỡng đúng nhãn (15/144 lượt đối chiếu mệnh đề đầy đủ và tiêu chí ngắn).
Đây là mẫu nhỏ, chưa chứng minh độ chính xác trên dữ liệu thực tế. Các ý khác qua Qwen tự động.

Backend kiểm tra hash trọng số và báo cáo runtime trước khi cho dùng quality gate.
Tiếng Anh chưa có kiểm định sau fine-tune, nên tiếp tục được chấm qua Qwen.

## Huấn luyện lại

```powershell
py -3.11 -m venv .train-venv
.\.train-venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.train-venv\Scripts\python.exe tools\finetune_rubricguard.py --data-dir data\rubricguard_training --output-dir models\rubricguard-new --epochs 16 --batch-size 12 --threads 4
.\.train-venv\Scripts\python.exe tools\export_rubricguard_onnx.py --checkpoint models\rubricguard-new --output-dir models\rubricguard-new-int8
.\.train-venv\Scripts\python.exe tools\benchmark_rubricguard.py --checkpoint models\rubricguard-new --model-dir models\rubricguard-new-int8 --threads 1
```

Dùng `tools/finetune_rubricguard.py` cho pipeline có chia tập độc lập và kiểm định INT8.
Không tự thay model đang dùng chỉ vì train loss thấp; so sánh báo cáo runtime và giữ bản cũ.
