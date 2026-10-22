# Xử lý giọng nói có thể khôi phục, bản 1.13

## Đã triển khai

- Audio được lưu local trước khi chạy STT hoặc LLM. Xử lý thất bại không xóa bản ghi đã nhận.
- Tác vụ STT/hiệu chỉnh chạy trong một hàng đợi SQLite, không cần Redis/Celery hay thêm model.
- Mỗi lượt ghi có `request_key` UUID. Gửi lại cùng mã và cùng audio trả cùng tác vụ; đổi nội dung với mã cũ bị từ chối.
- Chỉ chủ phiên được tạo, đọc, hủy hoặc thử lại tác vụ. Tác vụ gắn với câu hỏi tại thời điểm nhận audio.
- Tác vụ bị lỗi kỹ thuật có thể xử lý lại chính file cũ, tối đa ba lần chạy. Lỗi chất lượng cần ghi lại, không lặp vô hạn cùng audio.
- Worker có lease/heartbeat. Tác vụ bị gián đoạn được chuyển sang lỗi có thể thử lại; không giữ trạng thái chạy vô hạn sau khi mất worker.
- Nếu transcript đã commit trước khi ứng dụng bị dừng, lần phục hồi dùng đúng văn bản đã lưu, không chạy STT lại để tạo văn bản khác.
- Hủy là yêu cầu hợp tác: chặng suy luận đang chạy có thể phải kết thúc trước khi hủy có hiệu lực. Khi đang lưu kết quả thì không hủy nữa.
- Chống nộp trùng bằng receipt lưu cùng giao dịch với câu trả lời. Retry sau khi mất phản hồi không chấm/lưu thêm một câu mới.

## Trạng thái và điểm

Luồng xử lý: `queued -> transcribing -> correcting -> saving -> completed`, hoặc `failed/cancelled`.

`transcript_status=processed` chỉ có nghĩa đã xử lý xong, không phải đã xác nhận đúng từng từ.
`transcript_status=needs_review` nghĩa còn bằng chứng chưa chắc chắn. `accuracy_percent=null`,
`confidence_is_accuracy=false`; không biến confidence thành độ chính xác phần trăm.

Khi transcript hoặc ý nghĩa chưa được xác minh, điểm là tạm: không tính vào tổng kết luyện tập,
không dùng để tăng/hạ độ khó hoặc kết luận điểm mạnh/yếu. Điểm thi chính thức vẫn chờ giảng viên xác nhận.
Giảng viên có thể tự chấm, dùng điểm AI hợp lệ và nghe voice nhiều lần. Không bắt buộc phát voice để được chấm.

Danh sách chấm và báo cáo dùng chung `review_readiness`. Cache chấm lại là
`teacher-review-v7-span-correction-evidence`; cache cũ phải chạy lại trước khi chốt bằng thao tác dùng điểm AI.

## STT và LLM

Giữ Faster-Whisper, các profile phần cứng, Transformer và Qwen hiện có. Không thay trọng số.
Đoạn không chắc chắn được nhận dạng lại kèm đoạn lân cận khi vùng cần xử lý đủ nhỏ;
giữ nguyên các đoạn ngoài vùng đó và phục hồi dấu thời gian toàn bản ghi. Nếu sự không chắc chắn
phủ rộng thì vẫn chạy lượt chính xác toàn bản ghi, không cắt mất ngữ cảnh chỉ để nhanh.
Nếu hai lượt khác nhau ở số hoặc phủ định, giữ cảnh báo và các phương án nhận dạng để đối chiếu.

Các kiểm tra sửa nghĩa/số/phủ định của LLM tiếp tục áp dụng. Bản STT trước LLM, bản sau hiệu chỉnh,
thay đổi và cảnh báo đều được lưu. Không cho sinh viên sửa văn bản hoặc gửi văn bản thay audio.

## Giao diện tối thiểu

- Hiển thị công đoạn hiện tại và thời gian đã chờ, không tạo phần trăm tiến độ giả.
- Lưu bản ghi chưa gửi trong IndexedDB khi trình duyệt cho phép. Server lưu bản ghi khi upload thành công.
- Khôi phục phiên/câu hỏi đang làm sau khi tải lại trang; dùng lại kết quả mic thành công của phiên.
- Khôi phục tác vụ từ server nếu không còn cache trình duyệt nhưng audio đã được server nhận.
- Có nút xử lý lại bản ghi và hủy yêu cầu. Vẫn cho ghi âm lại trước khi nộp, không cho sửa transcript.
- Hiển thị “Chờ xác minh” thay vì một điểm tạm dễ bị hiểu là điểm cuối.

Nếu trình duyệt không lưu được IndexedDB và audio chưa tới server thì việc đóng tab vẫn có thể làm mất
bản ghi chưa gửi. Lỗi ổ đĩa/quyền ghi cũng không thể được coi là đã lưu thành công.

## API

- `POST /api/speech/jobs`: multipart `file`, `session_id`, `request_key`; trả 202 sau khi đã lưu file và tác vụ.
- `GET /api/speech/jobs/{job_id}`: trạng thái/kết quả của chính người dùng.
- `GET /api/speech/jobs?session_id=...`: tác vụ mới nhất của câu hỏi đang làm.
- `POST /api/speech/jobs/{job_id}/retry`: thử lại lỗi kỹ thuật với cùng file.
- `POST /api/speech/jobs/{job_id}/cancel`: yêu cầu hủy, không xóa audio.
- `GET /api/interviews/{session_id}/resume`: khôi phục phiên còn hoạt động, không lộ đáp án.
- Endpoint `/api/speech/transcribe` cũ vẫn được giữ để tương thích.

Chạy một tiến trình Uvicorn như launcher hiện tại. Không tăng số worker/model chạy đồng thời trên máy ít RAM.

## Chưa hoàn thành mục tiêu chất lượng

Đây chưa phải STT streaming ngay trong lúc sinh viên nói: hiện vẫn upload sau khi dừng ghi.
Hạn chế chọn câu theo điểm của bản 1.13 đã được thay thế: phiên mới chuẩn bị đề
ngay từ đầu, xác nhận transcript rồi chuyển câu, chỉ chấm khi kết thúc.
Audio đã nhận hợp lệ trước hạn được tiếp tục xử lý sau hạn theo receipt của server;
không nhận audio mới sau hạn. Xem FUNCTIONAL_FIXES.md về chính sách đóng mềm.

Không fine-tune mới khi chưa có nhãn độc lập của giảng viên và tập kiểm tra tách biệt.
Chưa chứng nhận WER 8%/15%, độ chính xác 99%, khả năng tách giọng nói chồng lấn hoặc hiệu năng mọi máy yếu.
Kết quả đo cũ lưu local tại `reports/recovery_20261018/`, không đi kèm bản tải Git.
