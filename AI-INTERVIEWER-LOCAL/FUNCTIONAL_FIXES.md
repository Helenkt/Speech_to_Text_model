# Bản sửa chức năng 1.14.0

## Kết Quả Chấm

`app/services/grade_state.py` thống nhất cách xác định điểm tạm và nguồn kết quả dùng cho báo cáo/lịch sử. Điểm chưa xác minh không tham gia điểm trung bình; không chuyển thành 0. Trạng thái thiếu/hỏng assessment hoặc thiếu đối chiếu từng ý ở dữ liệu cũ được giữ là chưa xác minh.

Khi giáo viên chấm, transaction lưu cùng lúc:

- Điểm cuối và nhận xét giáo viên.
- `interview_answers.final_decision_json`: bản kết quả đang được chấp nhận.
- Một dòng mới trong `answer_reviews`, kèm `decision_json` giữ nguồn chấm, transcript được dùng, rubric hash và assessment của lần quyết định đó.

Nguồn chấm mới là `strong_ai` hoặc `teacher_manual`. AI chấm lại sau đó không thay đổi snapshot đã được giáo viên chấp nhận. Nếu giáo viên chỉ nhập điểm tổng, không tự gán các tiêu chí đạt/thiếu. Lịch sử chấm vẫn được thêm mới mỗi lần giáo viên chấm.

Với điểm giáo viên đã chấm trước bản này nhưng chưa có snapshot, giữ nguyên điểm và nhận xét, dùng nguồn `legacy_teacher`; không đoán giáo viên đã dựa vào lần AI nào để tạo breakdown giả.

Migration `grade-state-v2` chỉ chuẩn hóa trạng thái của kết quả chưa được giáo viên xác nhận. Nó không gọi lại model và không tự sửa điểm giáo viên. SQLite có hàm `grade_is_provisional` dùng cùng quy tắc với báo cáo Python.

## Audio

`app/services/audio_lifecycle.py` dùng bảng `audio_deletions` làm danh sách dọn file có thể phục hồi sau restart:

1. Kiểm tra quyền và ghi danh sách file phải xóa trong cùng transaction xóa dữ liệu.
2. Sau commit, thử xóa các file thuộc đúng storage root và không còn tham chiếu.
3. File bị khóa được lưu trạng thái chờ, backoff tối đa 300 giây. Worker kiểm tra dọn file tối đa mỗi 5 giây, từng đợt nhỏ; nếu đang STT thì việc dọn tiếp tục sau lượt đó.
4. Đường dẫn không an toàn bị chặn, không thực hiện xóa ngoài storage.

Các API xóa có thêm `audio_cleanup_pending` và `audio_cleanup_complete`. Giao diện thông báo đang dọn nếu còn file chưa xóa xong. Mọi luồng xóa buổi luyện tập, bài làm thật và cả đợt thi đều dùng storage root trong cấu hình, kể cả thư mục tùy chỉnh.

API trạng thái speech job không phụ thuộc file audio còn hay mất. Nếu file mất, trả `audio_saved=false`, `audio_status=missing`, `audio_warning=audio_missing` cùng transcript đã lưu. Không thử STT lại khi file không còn; giáo viên vẫn được xem transcript và chấm theo quyền hiện có.

Phạm vi xóa là file gắn với dữ liệu đang được yêu cầu xóa. Bản sửa không tự động quét/xóa các file mồ côi đã có từ trước hoặc các bản sao lưu riêng.

## Hạn Thi

`app/services/exam_policy.py` áp dụng quy tắc dựa trên thời gian của server:

- Chỉ nhận bản ghi mới khi đợt thi đang mở và còn hạn.
- Kiểm tra lại sau khi ghi xong file, trước khi commit speech job. Client không được tự đặt `accepted_at`.
- Receipt được lưu trong `speech_jobs.context_json.admission`, gắn với kỳ thi, phiên, người dùng và câu hỏi.
- Bản ghi đã được nhận hợp lệ trước hạn được nhận dạng, thử lại kỹ thuật đúng file cũ và nộp hết câu đó sau khi đợt thi đóng/hết giờ. Không cho nộp audio mới sau hạn.
- Sau khi lưu câu trả lời cuối cùng được phép xử lý, kết thúc phiên bằng `exam_closed_after_recording`, không cấp câu tiếp theo.
- Có thể phục hồi receipt và bản ghi sau restart. Session có bản ghi hợp lệ đang chờ không bị quá trình expire đóng mất trước khi hoàn thành.

Đây là chính sách đóng mềm: `closed` ngăn lượt mới nhưng không hủy lượt đã nhận. Việc hủy khẩn cấp mọi lượt đang làm chưa phải một trạng thái riêng trong ứng dụng hiện tại.

Bản ghi legacy không có receipt vẫn được dùng khi kỳ thi còn mở. Nếu đã đóng, không tự suy đoán giờ upload từ giờ client để cho qua hạn.

## Giao Diện

- Có nhóm và nhãn riêng `unresolved`/“Chưa xác minh”; status không nhận biết không mặc định thành “Thiếu”.
- Khi chấm theo strong AI đã được chấp nhận, báo cáo ghi rõ transcript dùng để chấm; kết quả gốc vẫn được giữ để đối chiếu.
- Không hiện confidence của model cũ như confidence của kết quả giáo viên chấm.
- Không mở quyền sửa transcript cho sinh viên, không thay đổi quy tắc kiểm tra mic một lần hay quyền nghe lại/chấm lại của giáo viên.

## Kiểm Thử Và Khởi Động

Kết quả xác minh cũ lưu local ở `reports/fixes_20261018/REPORT.md`, không đi kèm Git. Không thay trọng số Whisper, Qwen hoặc RubricGuard; không công bố cải thiện WER từ bản sửa chức năng này.

Sau khi cài theo REQUIREMENTS.md, mở PowerShell trong thư mục AI-INTERVIEWER-LOCAL.
Dừng server cũ bằng Ctrl+C trong cửa sổ đang chạy, rồi khởi động lại:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Mở http://127.0.0.1:8001. Nếu cổng bận, chọn cổng khác trong lệnh và URL; không dừng
tiến trình không rõ nguồn gốc. Launcher portable start_local.ps1 có cơ chế chọn cổng
trống riêng, nhưng không phải trình tự cài đặt cho máy mới.
