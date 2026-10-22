# Rà soát tài liệu ngày 22/10/2026

Phạm vi: README, hướng dẫn cài đặt, tài liệu backend/rubric, báo cáo thử nghiệm
và hướng dẫn dữ liệu trong repository. Đối chiếu với mã nguồn, kiểm tra liên kết
Markdown nội bộ và schema manifest benchmark. Không thay backend/frontend,
trọng số, nhãn, dữ liệu câu hỏi hoặc cơ sở dữ liệu.

## Những mô tả đã sửa

| Nội dung cũ | Mô tả đúng của bản hiện tại |
| --- | --- |
| Chọn câu sau dựa trên điểm câu trước | Phiên mới mặc định lưu đề từ đầu, chấm cuối phiên; luồng cũ giữ để tương thích |
| Cài thư viện là có cùng model fine-tune | Trọng số không nằm trên Git; setup RubricGuard tải baseline, không tự có quality gate của bản fine-tune |
| Nguồn sinh câu hỏi đều đã được duyệt | Bộ chọn nguồn hiện lọc active/learning/môn/ngôn ngữ, chưa lọc bắt buộc verification_status |
| Điểm rubric cao chứng minh đáp án đúng | Điểm là kiểm tra quy tắc; semantic_review_required vẫn true, cần giảng viên duyệt bản nháp |
| Có lượt model độc lập kiểm chứng câu hỏi | Chưa có lượt kiểm chứng ngữ nghĩa độc lập trong bộ sinh hiện tại |
| WER/tốc độ cũ là kết quả có thể tái lập từ Git | Audio và báo cáo gốc không được commit; không chứng nhận máy yếu hoặc mọi giọng nói |
| File mẫu benchmark ở test_audio nhưng không tồn tại | Bổ sung mẫu schema trong data, không kèm audio hoặc giả làm kết quả thực nghiệm |
| Kiểm tra mic 1,5 giây mỗi câu | Kiểm tra một lần thành công theo phiên, bước đo nền 2 giây và bước ghi thử |
| start_local là installer cho mọi máy | Launcher portable cũ, không tự cài; hướng dẫn chính dùng venv + uvicorn sau setup |
| DeepFilterNet/pyannote có tên trong health nghĩa là đang xử lý | Phát hiện thư viện/policy không chứng minh pipeline đã gọi engine |
| Cache chấm mạnh v6 | Mã hiện tại dùng teacher-review-v7-span-correction-evidence |
| Đường dẫn C:\\Users\\Admin của máy phát triển | Lệnh chạy tương đối từ thư mục dự án; URL thống nhất với cổng trong lệnh |

Báo cáo ngày 16/10 và 21/10 được giữ như hồ sơ lịch sử, không viết lại số liệu
thí nghiệm thành kết quả mới. Changelog vẫn giữ hành vi theo từng phiên bản,
kèm cảnh báo các chính sách đã bị thay thế.

## Giới hạn còn lại, chưa sửa mã trong đợt này

- Chưa có bảo đảm mọi nguồn sinh câu hỏi đã qua giảng viên duyệt. Cần cơ chế lọc
  và quản lý duyệt nguồn nếu dùng yêu cầu này làm điều kiện bắt buộc.
- Kiểm tra cấu trúc và trích dẫn không đủ chứng minh tính đúng đắn ngữ nghĩa của
  câu hỏi/đáp án hoặc độ khó thực tế. Cần đánh giá nội dung độc lập.
- Chưa có bằng chứng đạt WER 8%/15% trên máy RAM 4/8 GB và tập audio sinh viên
  đại diện. Cần audio được phép sử dụng, transcript người nghe xác minh và phép đo thực.
- Bản tải Git không chứa trọng số fine-tune, audio, database và báo cáo runtime
  local; không được giới thiệu là tải về tự có cùng chất lượng model của máy phát triển.
- Bộ câu trả lời tổng hợp có nhãn dự thảo, không thay thế nhãn sinh viên thật
  đã được kiểm chứng. Test phần mềm đạt không chứng minh AI chấm đúng.

Hướng dẫn hiện hành: [README](../README.md), [cài đặt máy mới](../REQUIREMENTS.md),
[rubric sinh câu hỏi](../QUESTION_GENERATION_RUBRIC.md).

## Kiểm thử lần rà soát

- 3 test mới đạt: liên kết Markdown nội bộ, schema benchmark song ngữ và phiên bản cache trong hướng dẫn.
- Toàn bộ suite: 471 test đạt trong 80,06 giây, dùng Python 3.11 và thư viện runtime/dev đã cài từ requirements.
- Lượt đầu có 16 lỗi WinError 5 khi đổi tên audio trong thư mục Temp của sandbox;
  chạy lại với `--basetemp` trong workspace thì toàn bộ đạt. Không thay mã lưu audio
  để che lỗi môi trường.
- `git diff --check` không phát hiện lỗi whitespace. Không đo lại STT/LLM thực
  hoặc chứng nhận độ chính xác AI trong lần rà soát tài liệu này.
