# Nâng cấp chấm ngữ cảnh bằng Transformer

Gói này bổ sung mã fine-tune, suy luận, benchmark và tích hợp vào đúng bản
`AI-INTERVIEWER-LOCAL` bạn cung cấp. Không kèm trọng số mô hình đã huấn luyện trên
dữ liệu sinh viên, không có cam kết độ chính xác. Đọc tệp này trước khi chạy train.

## 1. Thay đổi cụ thể

- Bỏ cơ chế tự nâng thành `met` khi thấy nguyên văn key point trong câu trả lời.
  Sinh viên có thể đang trích dẫn để bác bỏ, nhắc lại một quan điểm sai hoặc tự mâu thuẫn.
- Không chấm 0 toàn câu chỉ vì chứa cụm “không biết”/“I don't know”. Câu như
  “Em không biết tên tiếng Anh nhưng mô hình ghi nhớ cả nhiễu...” được đưa cho model đọc.
- Các phủ định toàn cục cần phân tích ngữ cảnh được chuyển cho model. Bộ chấm quy tắc
  chỉ có thể đưa ra điểm thử và đánh dấu cần duyệt.
- LLM phải trả bằng chứng nguyên văn. Ý đúng/đúng một phần/mâu thuẫn mà thiếu bằng
  chứng hợp lệ bị đổi thành `uncertain`; không được tự động nhận điểm.
- Transformer là **cross-encoder phân loại từng tiêu chí**, không dùng cosine similarity
  để kết luận kiến thức đúng. Đầu vào gồm câu hỏi + tiêu chí + đáp án chuẩn ở chuỗi
  thứ nhất, toàn bộ câu trả lời sinh viên ở chuỗi thứ hai.
- Năm nhãn: `met`, `partial`, `missing`, `contradicted`, `uncertain`.
- Giữ cách chia điểm hiện tại: mỗi key point có trọng số bằng nhau, hệ số lần lượt
  1 / 0.5 / 0 / 0 / 0. Chưa bổ sung trình soạn rubric có trọng số riêng trên giao diện.
- Mọi tiêu chí được xét; không dùng top-k bỏ bớt những ý sinh viên chưa trả lời.
- Không cắt âm thầm câu dài hơn giới hạn model. Trường hợp này chuyển sang cần giáo viên duyệt,
  vì cuối câu có thể chứa phủ định hay đính chính làm đổi nghĩa toàn câu.
- Model được nạp lại khi khởi động tiến trình, tái sử dụng giữa các câu; suy luận
  Transformer được tuần tự hóa trong mỗi tiến trình để hạn chế RAM. Đây chưa phải Redis Queue.
- Bằng chứng và kết quả Transformer được lưu chung trong `assessment_json` có sẵn.
  Bài thi thật cần duyệt giữ `final_score = NULL` đến khi giáo viên chốt.

LLM hiện tại vốn đã là Transformer. Module mới là một bộ phân loại chuyên biệt
được fine-tune trên quan hệ giữa câu trả lời và rubric; tên kiến trúc không tự bảo đảm hiểu đúng.

## 2. Model nền và cách học

Mặc định khởi tạo từ `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, một model đa ngôn ngữ
đã học NLI. Thay đầu phân loại ba nhãn NLI bằng đầu năm nhãn rubric và fine-tune
có giám sát. Thông báo “classifier weights newly initialized” ở lần train đầu là bình thường.
Không sử dụng trực tiếp đầu mới khởi tạo để chấm bài.

Huấn luyện dùng PyTorch và Transformers, FP32, AdamW, cân bằng lớp, tích lũy gradient,
chọn checkpoint bằng macro-F1 trên validation và dừng sớm nếu không cải thiện hai epoch.
Test không được đọc trong bước chọn checkpoint. Có thể đổi base model bằng `--base-model`.

Embedding như BGE-M3 có thể hỗ trợ truy hồi khi ngân hàng rất lớn, nhưng độ giống
ngữ nghĩa cao không phân biệt chắc chắn hai câu trái nghĩa. Gói này không thêm BGE-M3
để tránh nạp thêm model khi chưa cần truy hồi; mọi tiêu chí vẫn được chấm.

Nguồn kỹ thuật:
- https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
- https://huggingface.co/docs/transformers/en/tasks/sequence_classification

## 3. Dữ liệu và lỗi đã phát hiện

Trong ZIP cũ có 364 dòng gán nhãn của 40 câu hỏi, tất cả ghi `data_origin=synthetic`.
Chữ `approved` trong tệp cũ không chứng minh giảng viên đã kiểm định kiến thức.
Không được dùng số dòng này để tuyên bố đạt chất lượng trên sinh viên thật.

Cách chia cũ lệch nhãn nghiêm trọng:

| Split cũ | supported | missing | contradicted | uncertain |
|---|---:|---:|---:|---:|
| train | 139 | 43 | 0 | 0 |
| val | 0 | 18 | 73 | 0 |
| test | 0 | 51 | 0 | 40 |

Ngoài ra, chưa có `partial`. Huấn luyện đúng split cũ sẽ không học được đầy đủ nhãn.

Đã thêm 72 dòng **synthetic/draft** của 3 câu hỏi, 24 câu trả lời trong
`data/context/context_cases.draft.jsonl`. Bao gồm keyword đúng nhưng kết luận sai,
trích dẫn ý sai để bác bỏ, đính chính, không biết tên nhưng hiểu bản chất, thiếu ý,
đúng một phần và chưa rõ ý. Đây là nhãn đề xuất, không phải kết quả model hay điểm GV thật.

`prepare` kiểm tra nhãn, điểm, bằng chứng, trùng lặp rồi chia lại theo toàn bộ nhóm
câu hỏi đã chuẩn hóa. Cùng câu hỏi và mọi câu trả lời/tiêu chí của nó chỉ thuộc một split.
Không dùng trường split cũ. Kiểm tra câu trả lời giống nhau không lọt sang nhiều split.
Khi có paraphrase của câu hỏi hay mẫu sinh tương tự, nhóm cần gộp chúng trước khi chia;
chuẩn hóa văn bản không tự phát hiện tất cả paraphrase.

Với seed 42 và dữ liệu đi kèm:
- Train: 316 dòng / 31 câu hỏi; chỉ 4 dòng `partial`.
- Validation: 64 dòng / 6 câu hỏi; 2 dòng `partial`.
- Test: 56 dòng / 6 câu hỏi; chưa có `partial`.

Đây chỉ là dữ liệu để chạy thử pipeline. Chưa thể kết luận chất lượng nhãn partial,
tiếng Anh, Việt–Anh xen kẽ hay bản STT lỗi từ bộ này. Cần bổ sung mẫu thật và cân bằng
các nhãn trong từng split; giữ nguyên test độc lập sau khi thống nhất thiết kế đánh giá.

## 4. Cài và chạy nhanh trên Windows

Giải nén gói mới sang thư mục riêng. Mở **AI-INTERVIEWER-LOCAL** trong VS Code.
Terminal phải đứng trong thư mục có `main.py`, `requirements.txt`, `setup_context.ps1`.

Chạy toàn bộ cài đặt + chuẩn bị dữ liệu + train thử + benchmark:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_context.ps1 -TrainDemo
```

Script mặc định CPU để tương thích. Cần Python 3.11 và Internet khi cài thư viện,
tải model nền. Huấn luyện toàn model trên CPU có thể lâu; không có cam kết số phút.
Không vừa train vừa phục vụ kỳ thi. Nếu dùng GPU, cài đúng PyTorch CUDA theo máy trước,
rồi thêm `-Device cuda`; script không tự cấu hình driver hay CUDA.

Mỗi lần train tạo thư mục model/dataset mới theo thời gian. Chỉ khi train và benchmark
hoàn thành, script sao lưu `.env` rồi bật `CONTEXT_MODE=shadow` và ghi đường dẫn model mới.
Nếu lỗi thì dừng, không tự bật model chưa hoàn thành. Script không sửa database hiện có.

Chạy ứng dụng:

```powershell
.\.venv\Scripts\python.exe main.py
```

Mở http://127.0.0.1:8000. Ollama cần chạy và có `qwen2.5:3b` nếu muốn đối chiếu LLM thật.
Nếu LLM không sẵn sàng, app ghi rõ bộ chấm quy tắc dự phòng và yêu cầu giáo viên kiểm tra.
`qwen3:8b` vẫn chỉ dùng cho sinh câu hỏi theo cấu hình dự án cũ.
Tài khoản demo khi database mới: `teacher / Teacher@123`, `candidate01 / Candidate@123`.
Các bước Whisper/microphone giữ như README gốc, có thể chạy `python -m app.stt_setup`.

Để giữ lịch sử hiện tại khi chuyển sang bản mới, dừng ứng dụng cũ và sao lưu trước,
rồi sao chép `data/ai_interviewer.db`, thư mục `data/audio/`, `models/whisper/` và `.env`
từ bản cũ sang cùng vị trí ở bản mới trước khi khởi động. Không sao chép `.venv`.
Nếu `.env` cũ được chép sau khi train, cần bổ sung lại các dòng CONTEXT theo model đã tạo.

## 5. Chạy từng bước để kiểm soát

```powershell
# Nếu đã có .venv và thư viện app:
.\.venv\Scripts\python.exe -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-context.txt

.\.venv\Scripts\python.exe -m scripts.context.prepare --demo
.\.venv\Scripts\python.exe -m scripts.context.train --demo --device cpu
.\.venv\Scripts\python.exe -m scripts.context.evaluate
```

Lệnh mặc định lưu model vào `models/context-grader`. Output train phải là thư mục mới.
Nếu đã chạy trước đó, chọn `--output models/context-grader-v2` và chỉ đúng model khi evaluate.
Để thử nhanh đầu phân loại có thể thêm `--freeze-encoder --epochs 1`; cách này
không đại diện cho chất lượng fine-tune toàn model. `--max-steps` chỉ dành cho smoke test.

Sau đó sửa `.env`:

```dotenv
CONTEXT_MODE=shadow
CONTEXT_MODEL_PATH=models/context-grader
CONTEXT_DEVICE=cpu
CONTEXT_THRESHOLD=0.85
CONTEXT_MARGIN=0.20
```

Khởi động lại app. `GET /api/health` có `context_grader` cho biết cấu hình và có manifest hay chưa;
việc có manifest chưa chứng minh model nạp thành công. Lỗi thực tế được ghi ở kết quả chấm/log.

## 6. Các chế độ tích hợp

| Chế độ | Hành vi |
|---|---|
| off | LLM như hiện tại với các sửa lỗi kiểm tra bằng chứng; không cần torch/Transformers |
| shadow | Giữ điểm LLM, thêm dự đoán Transformer theo tiêu chí, đánh dấu bất đồng/chưa rõ để GV duyệt |
| hybrid | Chỉ ghi nhận tiêu chí khi hai model thống nhất và LLM có bằng chứng hợp lệ; còn lại là uncertain |

Trong hybrid, điểm của uncertain được tính 0 để tạo **điểm đề xuất phần đã xác minh**;
đây không phải điểm trượt cuối cùng. Bài thi thật có cảnh báo giữ `final_score=NULL`.
Model học từ dữ liệu demo luôn yêu cầu GV duyệt, kể cả khi hai model đồng ý.

Mặc định mã app tắt module cho đến khi người quản trị cấu hình. Script train-demo bật shadow.
Chưa nên bật hybrid để chốt điểm tự động: hai model có thể cùng sai. Trước hết cần
kiểm định với ít nhất hai người chấm độc lập và giải quyết bất đồng nhãn.

`CONTEXT_THRESHOLD=0.85` và margin 0.20 chỉ là giá trị khởi đầu thử nghiệm, không có nghĩa
“chấm đúng 85%”. Chọn/hiệu chỉnh ngưỡng trên validation theo tỷ lệ cho điểm nhầm và mức
chuyển giáo viên; không chỉnh theo test rồi tiếp tục gọi test là độc lập.

## 7. Kiểm tra trực tiếp ba tình huống

Giáo viên có thể import `data/context/questions_context_demo.json` vào ngân hàng câu hỏi.
Các câu thuộc môn **Kiểm thử ngữ cảnh**. Dữ liệu JSONL training không nhập qua giao diện bộ đề.

Hoặc dùng CLI với model được train từng bước ở thư mục mặc định:

```powershell
.\.venv\Scripts\python.exe -m scripts.context.check --id CTX_OVERFIT --answer 'Overfitting là học quá sát dữ liệu train nên tổng quát hóa tốt hơn trên dữ liệu mới.' --with-llm

.\.venv\Scripts\python.exe -m scripts.context.check --id CTX_BINARY --answer 'Nhận định mảng không cần sắp xếp là sai. Cần mảng có thứ tự, so sánh ở giữa rồi chọn nửa phù hợp. Tìm kiếm mất O(log n).' --with-llm

.\.venv\Scripts\python.exe -m scripts.context.check --id CTX_HTTPS --answer 'Em không biết tên TLS đầy đủ, nhưng nó mã hóa dữ liệu truyền và xác thực tên miền bằng chứng chỉ; website vẫn có thể lừa đảo.' --with-llm
```

Nếu dùng script train-demo theo thời gian, thêm `--model models/context-demo_YYYYMMDD_HHMMSS`
theo đúng `CONTEXT_MODEL_PATH` trong `.env`. CLI không ghi điểm vào database.
Đối chiếu nhãn đề xuất trong tệp draft; không mặc định model chắc chắn vượt qua cả ba tình huống.

## 8. Dữ liệu thật để model học ngữ cảnh của môn học

Thu thập câu trả lời thật theo từng câu hỏi, bao gồm đúng diễn đạt khác, phủ định,
so sánh, điều kiện đúng/sai, số liệu, tự sửa ý, code-switching và STT sai. Giáo viên
gán nhãn từng tiêu chí kèm dẫn chứng, thay vì chỉ cho điểm tổng.

Xuất những bài đã được GV xem lại để tạo tệp **nháp**:

```powershell
.\.venv\Scripts\python.exe -m scripts.context.export_reviews
```

File `data/context/human_annotation.draft.jsonl` không chứa username/tên sinh viên,
nhưng nội dung câu trả lời vẫn có thể chứa thông tin cá nhân. Quản lý như dữ liệu bài thi.
Mã chỉ đọc database, không làm thay đổi điểm. Không suy ra nhãn từng ý từ điểm tổng.
Các gợi ý AI nằm ở trường riêng, không được tự dùng làm nhãn chuẩn.

Giáo viên sửa `relation_label`, `coverage_level`, `teacher_points`, `evidence_quote`:
- `supported/full`: điểm tối đa; `supported/partial`: nửa số điểm.
- `missing`, `contradicted`, `uncertain`: 0 điểm đề xuất; uncertain cần giải quyết khi có thể.
- Với ý có nội dung phải có dẫn chứng nguyên văn trong câu trả lời.
- Chỉ đặt `reviewer_status=approved` sau khi con người duyệt từng dòng.
- Không đổi dữ liệu synthetic thành human chỉ để vượt qua kiểm tra.

Sau khi đủ mẫu thật của ít nhất 10 nhóm câu hỏi và đủ 5 nhãn trong train:

```powershell
.\.venv\Scripts\python.exe -m scripts.context.prepare --input data/context/human_approved.jsonl --output data/context/human_prepared
.\.venv\Scripts\python.exe -m scripts.context.train --data data/context/human_prepared --output models/context-human-v1 --device cpu
.\.venv\Scripts\python.exe -m scripts.context.evaluate --data data/context/human_prepared --model models/context-human-v1 --output data/context/human_test_report.json --compare-llm
```

Chất lượng phụ thuộc quy mô/đa dạng dữ liệu, chuẩn rubric và tính nhất quán người chấm;
không thể hứa số mẫu cố định hay một vòng train sẽ đạt độ chính xác mong muốn.
Model không tự học từ mỗi lần sinh viên trả lời. Cần xuất, duyệt, train offline,
đánh giá holdout, rồi đổi đường dẫn model và khởi động lại app có kiểm soát.

## 9. Benchmark phải đọc gì?

`evaluate` ghi accuracy, macro-F1, confusion matrix, support từng nhãn, tỷ lệ
`met` nhầm trên `missing/contradicted`, MAE điểm 0–100, coverage và MAE ở phần
không abstain, cùng P50/P95. Thời gian gồm suy luận đầu tiên, không gồm nạp model.

MAE thấp ở vài câu được chấp nhận mà coverage rất thấp không có nghĩa model đã tốt.
Test chưa có partial thì chưa thể báo chất lượng partial. Cần tập con đối kháng
độc lập có nhãn loại lỗi và giữ riêng dữ liệu STT/môn/ngôn ngữ khi đánh giá mở rộng.

`--compare-llm` gọi LLM hiện có trên cùng câu trả lời và quy đổi cùng trọng số để so sánh.
Lỗi Ollama được liệt kê, không thay âm thầm bằng rule. Nếu thiếu kết quả LLM, không
so sánh trực tiếp MAE hai tập có số mẫu khác nhau. Benchmark chưa mô phỏng tải nhiều SV.

## 10. Kiểm thử và giới hạn gói nâng cấp

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Kiểm thử hồi quy xác minh xử lý ngữ cảnh, kiểm tra bằng chứng, chế độ shadow/hybrid,
fallback, chia dữ liệu và luồng API hiện tại. Smoke test huấn luyện/lưu/nạp/evaluate
trong môi trường phát triển dùng model BERT ngẫu nhiên rất nhỏ; đó là kiểm tra kỹ thuật,
không chứng minh chất lượng mDeBERTa hay độ chính xác chấm bài. Không kèm model smoke này.

Đây là tích hợp vào bản local được gửi. Chưa chuyển toàn hệ thống sang server,
chưa triển khai Redis/PostgreSQL, batch 2 câu, scheduler hay model chấm lại mới.
Khi tách server, đặt module này ở worker chấm; phía sinh viên chỉ STT theo kiến trúc nhóm.
