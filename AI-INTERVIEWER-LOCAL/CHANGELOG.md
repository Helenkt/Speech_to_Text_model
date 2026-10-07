# Changelog

## 1.8.0

- Thêm màn hình sinh câu hỏi Easy, Medium, Hard bằng Qwen3:8B từ nguồn nội bộ.
- Hiển thị điểm rubric, nguồn truy vết, đáp án và key points trước khi Giáo viên duyệt.
- Thêm hàng chờ chấm lại với voice gốc, transcript, điểm AI và điểm cuối của Giáo viên.
- Bổ sung kiểm tra microphone độc lập, mức tiếng ồn và chất lượng bản ghi.
- Nâng cấp báo cáo Giáo viên với đối chiếu STT gốc, bản xác minh và lịch sử điểm.
- Tối ưu giao diện responsive cho laptop và thiết bị di động.

## 1.7.0

- Thêm backend sinh câu hỏi bằng model local từ nguồn nội bộ đã duyệt.
- Chấm câu hỏi sinh mới bằng rubric 100 điểm và bắt buộc Giáo viên duyệt trước khi đưa vào ngân hàng.
- Lưu file voice gốc theo từng câu trả lời, kèm SHA-256, định dạng và dung lượng.
- Thêm API chỉ dành cho Giáo viên để nghe lại voice.
- Tách điểm AI, điểm Giáo viên và điểm cuối; giữ lịch sử mỗi lần chấm lại.
- Tự đưa bài thi có điểm thấp hoặc độ tin cậy thấp vào hàng chờ kiểm tra.
- Báo cáo và danh sách kết quả sử dụng điểm cuối sau khi Giáo viên chấm.

## 1.5.0

- Thêm nút **Xóa đợt** trong danh sách đợt Interview của Giáo viên.
- Thêm hộp xác nhận nêu rõ phạm vi dữ liệu bị xóa.
- Xóa toàn bộ lượt làm, câu trả lời, báo cáo và bản chụp câu hỏi liên quan trong cùng một giao dịch.
- Chỉ tài khoản Giáo viên có quyền xóa đợt Interview.

## 1.4.0

- Thêm nút **Xóa** cho từng kết quả Interview thật trong trang Giáo viên.
- Thêm nút **Xóa** cho từng lịch sử luyện tập của ứng viên.
- Thêm hộp xác nhận trước khi xóa và kiểm tra quyền ở backend.
- Ứng viên chỉ có thể xóa lịch sử luyện tập của chính mình.
- Khi xóa một phiên, toàn bộ câu trả lời liên quan cũng được xóa trong cùng giao dịch.

## 1.3.0

- Sửa Voice/STT: không còn khóa nút ghi âm chỉ vì chưa chạy setup thủ công.
- Tự tải và khởi tạo Faster-Whisper ở lần ghi âm đầu tiên; lưu trạng thái sẵn sàng sau khi nhận dạng thành công.
- Hiển thị hướng dẫn rõ khi trình duyệt chưa được cấp quyền microphone.
- Sửa nút **Làm mới** danh sách đợt Interview với trạng thái tải và thông báo hoàn tất.
- Thêm trang **Lịch sử luyện tập** riêng cho từng ứng viên, có điểm, tiến độ và báo cáo chi tiết.

## 1.2.0

- Thêm đăng nhập local và phân quyền Giáo viên/Ứng viên.
- Thêm import tài khoản từ Excel, CSV và JSON; mật khẩu được băm bằng scrypt.
- Giáo viên có thể tạo, mở/đóng đợt Interview thật và xem kết quả ứng viên.
- Ứng viên có luồng luyện tập và Interview thật riêng; mỗi mã đề chỉ có một lượt.
- Ẩn điểm và rubric trong Interview thật, chỉ Giáo viên xem báo cáo.
- Làm lại giao diện theo bốn mẫu và thêm file chạy trực tiếp `main.py`.

## 1.1.0

- Tinh gọn giao diện, chỉ giữ thiết lập phiên, phỏng vấn, dữ liệu và báo cáo.
- Đưa Faster-Whisper 1.2.1 vào `SETUP.bat` chính.
- Tự tải model `small` vào thư mục project và kiểm tra giải mã audio bằng CPU `int8`.
- Phân biệt rõ STT đã cài và STT thực sự sẵn sàng.
- Bổ sung hỗ trợ tải model qua SOCKS proxy.
- Báo lỗi rõ khi đoạn ghi âm không có giọng nói.
- Bổ sung test cho giao diện và toàn bộ luồng STT.

## 1.0.0

- Phiên bản local đầu tiên với FastAPI, SQLite, phỏng vấn thích ứng và import JSON.
