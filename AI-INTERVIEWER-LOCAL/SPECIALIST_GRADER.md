# Bộ chấm chuyên biệt không dùng LLM

## Trạng thái

Backend có bộ chấm ứng viên `SpecialistGrader` và công cụ chạy đối chiếu offline.
Khi chấm, bộ này gọi trực tiếp Transformer NLI ONNX INT8, không gọi Qwen/Ollama,
không tải Internet và không huấn luyện. Chưa thay bộ chấm hiện tại, chưa nối
frontend, chưa thay trọng số và không ghi điểm vào database.

Đây không phải một model mới đã được huấn luyện thành công. Nó là đường chạy
chuyên biệt để đo khả năng dùng checkpoint có sẵn thay cho LLM. Chỉ thêm một
đường chạy độc lập không làm trọng số cũ chính xác hơn.

Đã chạy thử model thật; xem [kết quả và lý do chưa thay Qwen](docs/SPECIALIST_PILOT_20261026.md).

## Luồng

```text
Checkpoint INT8 có sẵn -> manifest SHA-256 khóa model/tokenizer/config
                                         |
Transcript đã xác nhận + câu hỏi + rubric |
                 |                       |
           kiểm tra đầu vào              |
                 |                       |
    quy tắc đóng về dữ kiện/quan hệ       |
                 |                       |
       ý chưa kết luận -> NLI <-----------+
                 |
     đề xuất từng ý + bằng chứng nguyên văn
                 |
   tính đề xuất theo trọng số / khoảng điểm còn chưa rõ
                 |
       báo cáo shadow, không sửa điểm thật
```

Model nhận cặp `(lời sinh viên, mệnh đề rubric)`, đúng hợp đồng của checkpoint
MiniLM đang hỗ trợ. Câu hỏi được dùng trong kiểm tra quy tắc và truy vết; không
tự chèn câu hỏi/đáp án vào lời sinh viên đưa cho NLI. Checkpoint khai báo định
dạng question-answer khác sẽ bị từ chối; cần adapter và kiểm định riêng.

- `entailment`: đề xuất đúng ý; `contradiction`: đề xuất mâu thuẫn.
- `neutral`: chưa đủ bằng chứng, **không tự biến thành missing/sai hoặc nửa điểm**.
- Input bị cắt, phạm vi tự sửa/phủ định phức tạp hoặc quy tắc phát hiện hai ý trái
  nhau không bị ép thành điểm chắc chắn.
- Model không tự sinh trọng số hay điểm tổng. Backend dùng trọng số gốc; rubric
  atomic có snapshot được kiểm tra hash/khớp tiêu chí bằng hàm dùng chung.
- Bằng chứng là đoạn nguyên văn hoặc toàn transcript đã đưa vào model. Nhãn
  `full_transcript_model_input_not_verified_support` không khẳng định model đã
  chứng minh chính xác đoạn nào hỗ trợ ý rubric.
- `proposed_score` chỉ có khi mọi ý đều có đề xuất kết luận. Khoảng
  `rule_resolved_score_interval` giữ phần chưa rõ, không coi đó là điểm cuối.
- `final_score=null`, `production_ready=false`, `changes_final_grade=false` luôn
  đúng ở phiên bản shadow này. Không tự sửa những cờ đó để triển khai.

## Chạy thử

Từ thư mục `AI-INTERVIEWER-LOCAL`, sau khi cài runtime theo REQUIREMENTS.md và có
model INT8. Setup RubricGuard thông thường tải baseline, không phải bản fine-tune.
Nếu thư mục chỉ có model.onnx FP32, cần chuẩn bị bản INT8 trước; công cụ này không
tự lượng tử hóa hoặc tải thêm model.

Mỗi lần thử dùng đường dẫn đầu ra mới. Không chạy lại với tên file đã tồn tại.

```powershell
.\.venv\Scripts\python.exe tools\specialist_grading.py freeze `
  --model-dir models\rubricguard-lite `
  --output data\specialist_runs\run01\candidate.json

.\.venv\Scripts\python.exe tools\specialist_grading.py prepare-regression `
  --output data\specialist_runs\run01\regression.json

.\.venv\Scripts\python.exe tools\specialist_grading.py run `
  --model-dir models\rubricguard-lite `
  --manifest data\specialist_runs\run01\candidate.json `
  --dataset data\specialist_runs\run01\regression.json `
  --output data\specialist_runs\run01\report.json
```

`freeze` chỉ ghi manifest, không sao chép/sửa model. Khi di chuyển sang máy khác,
cần đủ model.int8.onnx, tokenizer.json và config.json đúng hash của manifest.
Thay trọng số/tokenizer/config thì phải tạo candidate mới. Manifest không phải
chữ ký của giảng viên hay bằng chứng chất lượng.

`prepare-regression` chuyển 28 ví dụ synthetic đã biết sang schema thử nghiệm.
Nhãn dự thảo nằm riêng, không được đưa vào đầu vào model. Đây là regression đã
biết, không phải blind test mới và không dùng để chứng nhận độ chính xác.

Đối chiếu thêm bộ chấm hiện tại bằng `--compare-current transformer` và nếu cần
`--current-model-dir <thư mục model hiện tại>`. Hai giai đoạn chạy lần lượt, giải
phóng session trước khi đổi model. `--compare-current auto` là tùy chọn tường
minh duy nhất cho phép nhánh so sánh gọi Qwen; bản specialist vẫn không gọi LLM.

## Dữ liệu độc lập

Lệnh `run` cũng nhận corpus `grading-corpus-v1` xuất từ công cụ nhãn giảng viên.
Hash transcript/rubric được đối chiếu. Nhãn bất đồng hoặc không độc lập bị loại
khỏi phép đo theo bộ kiểm tra chất lượng hiện có. Bộ chấm chỉ nhận question và
answer; nhãn/người chấm/điểm kỳ vọng không vào suy luận.

Trong diagnostic cũ, unresolved có thể góp 0 vào phép tính sai số kỹ thuật;
đó không phải điểm cuối của sinh viên. Không diễn giải MAE đó thành điểm thật.
Không có thao tác huấn luyện hoặc tự bật release trong công cụ này.

Trước khi thay Qwen cần chốt tập giảng viên chấm độc lập, tách câu hỏi/sinh viên
khỏi tập phát triển, bao phủ bốn môn và VI/EN. Chốt ngưỡng trên validation rồi
đóng băng trước khi mở blind test. Đề xuất tiêu chí nghiệm thu để giảng viên
thống nhất, **chưa phải kết quả đã đạt**:

- Macro-F1 từng ý tối thiểu 0,80; recall mâu thuẫn tối thiểu 0,90.
- Không quá 2% ý sai được cho đúng; báo số lượng mẫu và khoảng bất định.
- Theo dõi câu đúng bị mất điểm, sai số điểm theo rubric và riêng từng môn/ngôn ngữ.
- Có mục tiêu độ phủ tự chấm, ví dụ ít nhất 70% bài đủ bằng chứng, để tránh một
  model từ chối gần hết vẫn được quảng cáo là chính xác. Mục tiêu cần kiểm chứng,
  không hạ ngưỡng an toàn chỉ để đạt độ phủ.
- Đo độ trễ và RAM đỉnh trên máy 8 GB thật; 4 GB là cấu hình hỗ trợ chậm hơn.

Fine-tune chỉ làm offline khi có nhóm lỗi rõ và nhãn phù hợp. Không train trên
máy sinh viên, không train mỗi câu trả lời và không dùng cùng regression đã nhìn
để vừa chỉnh model vừa công bố độ chính xác độc lập.

## Tài nguyên và quyền riêng tư

Tái sử dụng ONNX session, CPU theo chính sách tài nguyên sẵn có, mỗi lượt một ý
rubric để tránh batch padding lớn. Không nạp Whisper hoặc model sinh đề. Đây
là thiết kế tiết kiệm tài nguyên, chưa phải cam kết tốc độ trên mọi CPU.

Báo cáo có thể chứa transcript/bằng chứng cá nhân. `data/specialist_runs/` và
`reports/` bị Git ignore. Không đưa báo cáo sinh viên thật lên Git, không đổi
nhãn AI dự thảo thành nhãn đã duyệt. Mã chạy không mở database bài thi.
