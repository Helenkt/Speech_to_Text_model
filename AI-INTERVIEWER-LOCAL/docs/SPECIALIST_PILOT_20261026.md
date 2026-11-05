# Thử bộ chấm chuyên biệt ngày 26/10/2026

## Phạm vi đã làm

- Thêm bộ chấm NLI INT8 gọi trực tiếp model, không gọi LLM và không huấn luyện.
- Khóa trọng số, tokenizer, config và định dạng đầu vào bằng manifest SHA-256.
- Tái sử dụng ONNX session, batch một ý rubric mỗi lượt; giải phóng trước khi đổi model.
- Tính đề xuất theo trọng số; neutral, input bị cắt và phạm vi khẳng định phức tạp
  không bị tự chuyển thành câu sai hoặc nửa điểm.
- Có công cụ chuẩn bị regression, chạy model và đối chiếu nhánh bộ chấm cũ.
- Không thay frontend, model đang phục vụ, điểm thật hoặc database bài thi.

Đây là dùng pretrained có sẵn qua đường chạy chuyên biệt, không phải công bố một
checkpoint mới đã học tốt cách chấm bài. Không chạy thêm fine-tune trong lần này.

## Chạy model thật

Dùng bản baseline MiniLM trước fine-tune có sẵn local, model.int8.onnx khoảng
102,36 MiB. Nhánh đối chiếu dùng evaluator hiện tại ở chế độ `transformer` với
checkpoint local đang hoạt động. Không bật `auto` nên **không phải** đối chiếu
đầy đủ với hệ thống Qwen hoặc toàn bộ STT đến chấm bài.

Tập thử là 28 câu trả lời tổng hợp đã biết, 56 ý rubric từ bốn môn. Nhãn dự thảo
không có kiểm chứng độc lập của giảng viên. Câu hỏi/tiêu chí chủ yếu tiếng Việt,
có một lời đáp tiếng Anh, không thay thế một tập kiểm thử tiếng Anh riêng.

| Phép đo bộ chấm chuyên biệt | Kết quả |
| --- | ---: |
| Câu trả lời / ý rubric | 28 / 56 |
| Ý được quy tắc đóng kết luận | 21 |
| Ý vẫn chưa đủ kiểm định để chốt bằng model | 35 |
| Câu có đề xuất điểm đầy đủ, chưa phải điểm cuối | 12 / 28 |
| Số cặp thực sự đưa qua NLI | 34 |
| Câu đầu có gọi model, gồm nạp lần đầu | 14.112 ms |
| Trung vị câu có gọi model sau lần đầu | 29,74 ms |
| Trung vị tất cả câu, gồm câu chỉ dùng quy tắc | 24,51 ms |
| P95 tất cả câu trên tập nhỏ này | 41,24 ms |

Các câu ngắn trong bộ thử có hai ý mỗi câu; thời gian trên không bao gồm STT,
Qwen, chuẩn bị đề, ghi âm hay mạng. Không suy ra mọi bài dài đều chấm trong 30 ms.
P95 của 28 mẫu không phản ánh tốt trường hợp nạp lạnh; vì vậy tách lần nạp đầu
14,1 giây, không giấu nó trong trung vị. Chưa đo RAM đỉnh hoặc CPU máy RAM 4/8 GB thật.

## Kết luận chất lượng

Chỉ 29/56 đề xuất trùng nhãn dự thảo, có tính cả unresolved; con số này không
phải accuracy trên sinh viên thật. Không được diễn giải 12/28 đề xuất đầy đủ
thành 12 bài đã được tự động chấm đúng hoặc đạt quality gate.

Có một ý mà nhãn dự thảo là sai nhưng NLI đề xuất đúng: lời đáp nói một lớp chỉ
tạo được một đối tượng, đối chiếu tiêu chí một lớp có thể tạo nhiều đối tượng.
Đường chạy mới giữ ý này ở `status=unresolved`, không ghi điểm thật. Không thêm
quy tắc chỉ để sửa ví dụ này rồi tiếp tục gọi cùng tập là test độc lập.

**Chưa thay Qwen.** Model pretrained nhanh khi đã nạp, nhưng vẫn thiếu độ phủ và
khả năng phân biệt diễn đạt gần đúng/sai quan hệ. Tắt Qwen ngay sẽ làm nhiều bài
chưa chấm được hoặc chốt sai nếu bỏ lớp an toàn. Cần dữ liệu giảng viên kiểm
chứng và tập giữ riêng trước khi chọn checkpoint/ngưỡng hoặc fine-tune có mục tiêu.

## Kiểm thử và tái lập

Toàn bộ suite đạt 504/504 test trong 85,55 giây. Trong đó có 33 test mới cho bộ
chấm/manifest/công cụ. Test phần mềm không chứng minh model chấm đúng về ngữ nghĩa.

Xem [hướng dẫn](../SPECIALIST_GRADER.md). Báo cáo đầy đủ và manifest lưu local,
không commit trọng số hoặc transcript vào báo cáo tóm tắt này. `data/specialist_runs/`
bị ignore; không công khai báo cáo khi dùng lời đáp sinh viên thật.

Vướng loopback Windows lúc chạy đối chiếu ban đầu được xử lý bằng cấp quyền môi
trường rồi chạy lại, không sửa thuật toán để bỏ qua lỗi đó. Bản so sánh cuối chạy
hoàn tất cả hai giai đoạn. Luồng phục vụ ứng dụng hiện tại vẫn giữ nguyên.
