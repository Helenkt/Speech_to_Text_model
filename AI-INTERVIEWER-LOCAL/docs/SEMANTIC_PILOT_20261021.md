# Thử nghiệm cải thiện bộ chấm ngữ nghĩa

Ngày: 21/10/2026. Kết luận: có cải thiện một phần, **chưa đạt để triển khai**.
Model đang chạy, frontend, ngân hàng câu hỏi và cơ sở dữ liệu không được thay thế.

## Đã thực hiện

- Fine-tune một ứng viên MiniLM 6 lớp, 106.995.075 tham số, cùng kiến trúc bản hiện tại.
- Đóng băng embeddings; huấn luyện encoder và classification head trên CPU.
- Đầu vào mới: câu hỏi + câu trả lời của sinh viên ở vế thứ nhất, một ý rubric ở vế thứ hai. Không đưa đáp án chuẩn vào phần lời sinh viên.
- Nhãn riêng: nêu đúng ý, chưa nêu ý, phủ định/sai ý. Không coi nhãn “không chắc chắn” là câu sai.
- Dùng trọng số tiêu chí gốc, tổng 10 điểm; không tự xuất bản rubric hay thay đổi trọng số.
- Thêm diễn đạt đời thường, câu thiếu ý, đảo quan hệ, phủ định, điều kiện, độ phức tạp và tự đính chính.
- Chỉ lấy kiến thức từ bốn tệp khóa học có sẵn trong `data/rubricguard_training`; không thêm kiến thức Internet.

## Cách kiểm tra

433 cặp để học, 102 cặp validation để chọn checkpoint và hiệu chỉnh confidence, 160 cặp test thuộc 64 câu trả lời trên 8 câu hỏi.
18 câu hỏi train, 8 validation và 8 test tách biệt; thêm 6 câu hỏi cách ly khỏi huấn luyện. Không trùng nguyên văn câu trả lời hay reference claim giữa các tập.
Chọn vòng học 4 bằng validation; dừng sau vòng 7, khoảng 148 giây. Không mở test trong quá trình huấn luyện.
Chạy thực tế cả hai bản ONNX INT8 trên CPU, 4 luồng, từng tiêu chí một.

**Giới hạn:** đây là dữ liệu tổng hợp và nhãn do agent soạn, chưa có giảng viên kiểm chứng độc lập. Bản cũ có thể từng thấy chủ đề câu hỏi nguồn. Các tỷ lệ dưới đây không phải độ chính xác chấm bài sinh viên thật, không phải STT/WER và không phải kết quả toàn bộ pipeline rules + LLM.

## Kết quả giữ riêng

| Chỉ số phân loại ý rubric | Bản đang dùng | Ứng viên |
| --- | ---: | ---: |
| Đúng cả ba loại | 98/160 (61,25%) | 117/160 (73,13%) |
| Macro-F1 | 0,580 | 0,680 |
| Nhận ra ý đúng | 45/65 (69,23%) | 55/65 (84,62%) |
| Câu sai bị gọi nhầm là đúng, khi ép chọn nhãn | 4/20 | 5/20 |
| Sai số điểm đề xuất trung bình /10, chưa áp dụng abstention | 1,734 | 1,531 |
| Thời gian trung vị / tiêu chí | 12,4 ms | 18,1 ms |
| P95 / tiêu chí | 17,5 ms | 24,4 ms |
| File INT8 | 102,4 MiB | 102,4 MiB |
| Working set tiến trình sau suy luận | 436,1 MiB | 438,0 MiB |

Theo môn, accuracy cũ → mới: AI 34,4% → 59,4%; DSA 60,4% → 81,3%; OOP 62,5% → 75,0%; DB **79,2% → 72,9%**. Không phải môn nào cũng tiến bộ.
Bootstrap ghép cặp theo 8 nhóm câu hỏi cho chênh lệch accuracy khoảng +1,1 đến +23,6 điểm phần trăm (95% mô tả); số nhóm nhỏ và dữ liệu tổng hợp nên không suy rộng cho người dùng thật.

## Vì sao chưa được dùng

- Vẫn có lỗi nguy hiểm: câu đảo WHERE/HAVING, hiểu sai Isolation, và câu không giám sát nhưng có nhãn vẫn bị head gọi là đúng.
- Có trường hợp sai với confidence 98,2%; confidence cao không bảo đảm nội dung đúng.
- Trên bộ diễn tập cũ, head ứng viên gọi nhầm cả 12/12 ý sai thành đúng, so với 8/12 của head cũ. Đây là hồi quy nghiêm trọng với tiêu chí dài. Không nhầm số này với pipeline production vốn còn có FactGuard và các bước kiểm chứng.
- Không có ngưỡng confidence nào trong lưới đã định đạt đồng thời ít nhất 20 ý validation được nhận và không quan sát lỗi. Vì thế ngưỡng ứng viên dùng sentinel `1.01` để **tắt tự chấp nhận**. Coverage bằng 0, không phải chứng minh chấm đúng 100%.
- Thiếu nhãn sinh viên thật do giảng viên duyệt, kiểm thử tiếng Anh và benchmark trên máy RAM 4/8GB.

Không thay model đang chạy. Không sao chép ứng viên vào `models/rubricguard-lite`: ứng viên còn có hợp đồng đầu vào khác runtime hiện tại.

## Tài nguyên và bước tiếp theo

Ứng viên không tăng số tham số hay dung lượng INT8; RAM của tiến trình đo được gần như bằng bản cũ. Có thêm ngữ cảnh nên suy luận tăng khoảng 5,7 ms/ý trên máy thử. Đây không phải cam kết tốc độ cho CPU máy yếu; cũng chưa đo cả STT và LLM cùng hoạt động.

Đã xuất `teacher_review_queue.json` gồm 69 cặp có ít nhất một head phân loại sai để rà soát nhãn và loại lỗi. Tệp này chỉ dùng đánh giá; không đưa lại vào train rồi tiếp tục gọi nó là test độc lập.
Lần tiếp theo cần dữ liệu có giảng viên gán nhãn và evidence theo ý rubric, đặc biệt tiêu chí dài, thiếu một vế, đảo vai trò, phủ định và tự sửa. Phải có tập kiểm thử mới chưa dùng để chọn cách sửa. Giữ model nhỏ cho sinh viên; chưa có bằng chứng cần tăng kích thước model.

## Tệp và tái lập

- `manifest.json`: nguồn, SHA256, phân chia dữ liệu và dấu vết các file production được bảo vệ.
- `history.json`, `checkpoint/`, `onnx/`: lịch sử, trọng số ứng viên và bản INT8 riêng.
- `evaluation_active.json`, `evaluation_candidate.json`: kết quả từng tiêu chí, từng môn và hồi quy cũ.
- `candidate_calibration.json`, `predeclared_gates.json`, `decision.json`: hiệu chỉnh và quyết định không triển khai.
- `tools/semantic_grading_pilot.py`: prepare → train → export bằng công cụ sẵn có → evaluate → summarize → verify. Công cụ từ chối ghi đè thí nghiệm và kết quả đã có.

Chạy từ thư mục gốc dự án; dùng tên thư mục đầu ra **mới** cho lần thử khác. Không chạy train lại vào thư mục kết quả này.

## Kiểm tra mã nguồn

13 test tập trung về dữ liệu, chống rò rỉ tập học/test, ngưỡng tin cậy và công cụ huấn luyện đã đạt.
Toàn bộ suite: 448 đạt, 1 lỗi khi kiểm tra mở cổng loopback PowerShell báo quyền socket. Chạy riêng lại test này đạt (0,62 giây); chưa đủ dữ liệu kết luận lỗi do port ngẫu nhiên hay môi trường. Không sửa launcher ngoài phạm vi thử nghiệm. Có cảnh báo deprecation Starlette/httpx sẵn có.

## Bản Đưa Lên Git

Đây là bản tóm tắt thí nghiệm local, không phải lần đo mới sau khi tải repository. Các checkpoint, trọng số và báo cáo suy luận đầy đủ trong phần tái lập ở trên không được commit. Bộ 28 câu diễn tập tổng hợp được tách thành `data/semantic_pilot_regression_cases_v1.json`, không kèm trace runtime hoặc thông tin hệ thống local. Không có model ứng viên nào được tự động thay vào production.
