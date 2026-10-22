# Báo cáo fine-tune RubricGuard Lite - 16/10/2026

Đây là báo cáo lịch sử của máy phát triển tại ngày ghi trên tiêu đề. Các thư mục
`models/` và báo cáo runtime được nhắc tới không đi kèm Git. Cài model gốc bằng
setup không tái tạo bản fine-tune hoặc tự bật quality gate. Số test bên dưới là
của thời điểm đó, không phải kết quả kiểm thử hiện tại trên máy mới.

## Kết quả

Đã huấn luyện thật MiniLM, xuất bản nén trọng số INT8 và tích hợp vào backend.
Bản đang dùng nằm tại `models/rubricguard-lite`; bản trước fine-tune được giữ tại
`models/rubricguard-baseline-before-ft-20261016`.

Model hỗ trợ đối chiếu câu trả lời với từng ý rubric. Đây là model chấm nội dung,
không phải model chuyển giọng nói thành văn bản. Faster-Whisper tiếp tục thực hiện STT.

## Dữ liệu và cách chia

- 364 cặp câu trả lời - mệnh đề, 40 câu hỏi, thuộc DSA, DB, OOP và AI.
- Chỉ dùng bốn JSON nội bộ trong `data/rubricguard_training`; không bổ sung kiến thức Internet.
- Train: 220 mẫu thuộc 24 câu hỏi. Validation: 72 mẫu thuộc 8 câu hỏi. Test: 72 mẫu thuộc 8 câu hỏi.
- Các câu trả lời và mệnh đề trùng được giữ chung nhóm trước khi chia.
- Train được bổ sung thành 666 mẫu: tiêu chí ngắn, câu khẳng định và câu phủ định từ mệnh đề trong train.
- Validation và test giữ dữ liệu gốc; không dùng mẫu bổ sung để báo cáo chất lượng.
- Chặn việc mệnh đề từ train xuất hiện trong validation/test, kể cả sau khi bổ sung tiêu chí ngắn.

SHA256 nguồn và danh sách câu hỏi của từng tập nằm trong
`models/rubricguard-finetuned-20261016/dataset_manifest.json`.
JSONL không được nạp lặp lại cùng JSON. Các mẫu hiện là synthetic, không phải bộ trả lời thực tế của sinh viên.

## Thiết lập huấn luyện

- Backbone: `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`, revision `0a71e92a985b6e1ad1828cf67ce9c459639c1dca`.
- 106.995.075 tham số tổng; 10.795.779 tham số được cập nhật. Bảng embedding được đóng băng để giảm RAM và hạn chế quá khớp.
- Nhãn: entailment, neutral, contradiction. Partial được Qwen hoặc các ý rubric nhỏ xử lý; không suy ra nửa điểm chỉ từ xác suất thấp.
- Loss có trọng số cân bằng nhãn; AdamW, gradient clipping, warmup và giảm learning rate.
- Input tối đa 192 token; dữ liệu bị cắt được đánh dấu cần kiểm tra phụ khi chạy thực tế.
- Seed: 20261016. Hai thí nghiệm cùng cách chia dữ liệu, chọn bằng validation macro-F1.

| Thí nghiệm | Dữ liệu train | Learning rate | Epoch tốt nhất | Validation macro-F1 |
|---|---:|---:|---:|---:|
| Có bổ sung tiêu chí ngắn và phủ định | 666 | 0,00003 | 6 | 0,8098 |
| Chỉ dữ liệu gốc | 220 | 0,00001 | 15 | 0,7512 |

Chọn thí nghiệm đầu bằng validation. Thí nghiệm đầu chạy 11 vòng và dừng sớm,
giữ checkpoint vòng 6. Thời gian huấn luyện và đánh giá của lần này khoảng 463 giây bằng CPU.

## Kiểm tra cuối trên câu hỏi chưa học

Các cột sau dùng cùng 72 mẫu test với mệnh đề đầy đủ.

| Chỉ số | Model gốc FP32 | Fine-tune FP32 | Fine-tune INT8 weights |
|---|---:|---:|---:|
| Accuracy | 61,11% | 77,78% | 76,39% |
| Macro-F1 | 0,5685 | 0,7568 | 0,7435 |
| Recall mâu thuẫn | 33,33% | 66,67% | 66,67% |
| Mâu thuẫn bị nhầm thành đúng | 6/15 | 3/15 | 3/15 |

Bản INT8 trùng 71/72 dự đoán với FP32 (98,61%). Khi thay mệnh đề đầy đủ bằng
tiêu chí ngắn trong cùng test, accuracy đạt 86,11%, macro-F1 0,8409; vẫn còn 4/15
mẫu mâu thuẫn bị nhầm thành đúng nếu bỏ qua ngưỡng tin cậy.

Những số liệu này là điểm của Transformer trên tập nhỏ, không phải độ chính xác của
toàn bộ hệ thống, của STT hoặc của mọi câu trả lời thực tế.

## Lượng tử hóa và máy yếu

Lượng tử hóa động toàn bộ các phép nhân làm validation accuracy tụt còn 43,06%.
Đối chiếu với ONNX FP32 xác nhận bước xuất model đúng, lỗi xuất hiện khi lượng tử hóa.
Bản được chọn dùng embedding INT8 và trọng số MatMul INT8 theo kênh, giữ activation FP32.
Các lựa chọn nén được so sánh trên validation, không chọn theo kết quả test.

Phép đo CPU một luồng trên máy hiện tại, không dùng GPU:

| Phép đo | Kết quả |
|---|---:|
| File trọng số | 102,39 MiB |
| Thư mục runtime, gồm tokenizer và metadata | Khoảng 123,6 MiB |
| Nạp session và tokenizer | Khoảng 0,48 giây |
| Trung vị một tiêu chí sau khi nạp | Khoảng 31 ms |
| P95 một tiêu chí | Khoảng 52 ms |
| Working set tiến trình benchmark | Khoảng 430,5 MiB |
| Working set cao nhất | Khoảng 446,5 MiB |

Đã tắt CPU memory arena để giảm lượng RAM giữ lại và đọc hash theo luồng thay vì
nạp thêm cả file trọng số vào RAM. RAM trên gồm Python/tokenizer/ONNX Runtime trong
tiến trình benchmark; chưa gồm Whisper, Ollama, trình duyệt và các ứng dụng khác.
Giới hạn một luồng trên máy hiện tại không thay thế phép đo trên một máy yếu thật.

## Chấm tự động có chọn lọc

Temperature được chọn bằng validation NLL, giá trị 2,3. Ngưỡng xác suất sau hiệu chỉnh
là 0,91, được chọn trên validation đầy đủ và tiêu chí ngắn; không chỉnh ngưỡng theo test.

- Validation: 18/144 lượt đối chiếu vượt ngưỡng, đúng nhãn 18/18.
- Test: 15/144 lượt đối chiếu vượt ngưỡng, đúng nhãn 15/15.
- 144 lượt là hai cách viết tiêu chí cho 72 mẫu, không phải 144 bài thi độc lập.
- Coverage 10,42% là tỷ lệ lượt đối chiếu vượt ngưỡng trên test, không phải tỷ lệ toàn bộ bài thi được tự động chấm.
- Không diễn giải ngưỡng 0,91 là cam kết nhận dạng đúng 91% hay kết quả 15/15 là cam kết đúng 100%.

Backend giữ kết quả của các ý vượt ngưỡng, chỉ gửi các ý còn lại cho Qwen. Nếu toàn bộ
ý đều đủ chắc chắn thì không gọi Qwen. Nếu Ollama không hoạt động, các ý chưa rõ vẫn
được đánh dấu cần kiểm tra. Các quy định chấm lại của giảng viên vẫn áp dụng.

Ba lỗi raw test như đảo vai trò BFS/DFS, hiểu sai 3NF và đổi WHERE/HAVING đều dưới
ngưỡng tự chốt, nên được gửi kiểm tra tiếp thay vì dùng trực tiếp làm điểm cuối.

Chế độ tự chấm hoàn toàn chưa đạt quality gate. Bản đang dùng chỉ được bật chế độ
chọn lọc cho tiếng Việt. Tiếng Anh tiếp tục chấm qua Qwen vì chưa có test tiếng Anh
sau fine-tune. Hash trọng số phải khớp báo cáo runtime và calibration trước khi bật gate.

## Tệp và tái lập

- Model đang hoạt động: `models/rubricguard-lite/model.int8.onnx`.
- SHA256: `8b91f9f94e042edafbc8dc044975eca493d50cd4d2c1964fec3dafbc13bcc8f3`.
- Checkpoint, lịch sử, tập chia và dự đoán: `models/rubricguard-finetuned-20261016`.
- Báo cáo runtime có số liệu chi tiết: `models/rubricguard-lite/runtime_evaluation.json`.
- Lệnh huấn luyện/xuất/kiểm định: xem `RUBRICGUARD_LITE.md`.
- Môi trường huấn luyện `.train-venv` và checkpoint không cần đưa sang máy sinh viên.
- `models/` được Git ignore; mã nguồn trên Git không tự chứa checkpoint fine-tune.

## Giới hạn và bước cải thiện tiếp

Dữ liệu chỉ có 40 câu hỏi và đều là synthetic. Tập test có 15 mẫu mâu thuẫn nên chưa
đủ để chứng minh tỷ lệ lỗi rất thấp trên thực tế. Cần thêm câu trả lời sinh viên đã được
giảng viên chấm, nhất là câu đảo quan hệ, đổi số/đơn vị, phủ định, trả lời một phần và
tiếng Anh. Dữ liệu mới phải được chia theo câu hỏi và giữ một test độc lập mới.

Fine-tune lần này cải thiện bộ chấm nội dung, không cải thiện trực tiếp WER hoặc
độ chính xác chuyển giọng nói thành văn bản. FactGuard hiện vẫn cần thiết cho số và so sánh.

## Kiểm thử tích hợp

- 109/109 kiểm thử toàn project đạt trong môi trường Python 3.12 riêng của lần huấn luyện.
- Có kiểm thử chống rò rỉ tập dữ liệu, giữ nhãn mâu thuẫn dù lặp đúng từ khóa, không tự cho nửa điểm vì thiếu tin cậy.
- Có kiểm thử input bị cắt, ngôn ngữ chưa kiểm định, calibration sai và trọng số không khớp báo cáo.
- Có kiểm thử chỉ gửi các ý chưa rõ cho Qwen và giữ kết quả các ý Transformer đủ tin cậy.
- Smoke test với trọng số thật: câu đủ tin cậy được chấm 100 và không gọi Qwen.
- Smoke test với trọng số thật và bộ chấm phụ giả lập: một lỗi dự đoán raw dưới ngưỡng được chuyển kiểm tra tiếp.
- Các test phần mềm và smoke test kiểm tra luồng chạy; không thay cho tập đánh giá độc lập về chất lượng chấm.
