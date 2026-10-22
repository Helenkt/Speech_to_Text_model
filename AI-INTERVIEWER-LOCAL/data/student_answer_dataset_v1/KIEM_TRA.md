# Kết quả kiểm tra bộ dữ liệu

Ngày: 22/10/2026.

- 4 môn, mỗi môn 10 câu hỏi và 100 câu trả lời; tổng 400 câu trả lời.
- 1.160 cặp câu trả lời–ý rubric: 532 supported, 408 missing, 179 contradicted, 41 needs_review.
- 180 câu trả lời train, 80 validation, 80 test phát triển và 60 regression-only. Không xáo trộn câu hỏi đã giữ riêng ở thử nghiệm trước.
- Mọi bằng chứng đều là đoạn trích có vị trí chính xác trong lời đáp; missing không có bằng chứng giả.
- Tổng điểm ý con giữ nguyên từng tiêu chí cha và tổng 10 điểm mỗi câu hỏi.
- Không có nhãn đã được người duyệt xác nhận trong bundle gốc; chưa có file dữ liệu học đã duyệt.
- SHA256 xác nhận các file nguồn, ngân hàng câu hỏi, frontend và model production được bảo vệ không đổi trong quá trình tạo bundle.
- 30 test công cụ dữ liệu và các test huấn luyện liên quan đạt; có một cảnh báo deprecation Starlette/httpx sẵn có. Không chạy lại toàn bộ ứng dụng vì không sửa runtime hay frontend.

**Phạm vi xác nhận:** tính hợp lệ cấu trúc, trích dẫn, điểm, phân chia và cơ chế duyệt. Kiểm tra tự động không chứng minh rằng 1.160 nhãn AI đều đúng về ngữ nghĩa. Bộ này không được dùng để huấn luyện hoặc tự thay model trong lần tạo dữ liệu này.
