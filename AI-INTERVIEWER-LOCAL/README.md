# AI Interview Local

Demo hệ thống AI Interview chạy trực tiếp trên laptop bằng FastAPI, SQLite và giao diện web local. Hệ thống có hai vai trò riêng:

| Vai trò | Chức năng |
|---|---|
| Giáo viên | Import tài khoản, quản lý bộ câu hỏi, mở/đóng đợt Interview thật và xem kết quả. |
| Ứng viên | Luyện tập, xem lại lịch sử hoặc làm Interview thật bằng mã đề do Giáo viên cung cấp. |

> Hai ngân hàng câu hỏi VI/EN hiện là dữ liệu demo chưa được giảng viên kiểm định. Điểm số chỉ dùng để thử luồng hệ thống.

Ngân hàng hiện có `1.800` câu song ngữ thuộc 4 môn: Nhập môn Trí tuệ nhân tạo,
Các hệ cơ sở dữ liệu, Cấu trúc dữ liệu và giải thuật, và Lập trình hướng đối tượng.

## 1. Cài thư viện và chạy trong VS Code

Yêu cầu: Windows 10/11, VS Code và Python 3.11.

Mở thư mục này trong VS Code, chọn **Terminal → New Terminal**, sau đó chạy lần lượt:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Mở <http://127.0.0.1:8000>. Nhấn `Ctrl+C` trong Terminal để dừng. Khi chạy bằng
`start_local.ps1`, ứng dụng dùng <http://127.0.0.1:8001>.

Từ lần chạy sau chỉ cần:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

Bạn cũng có thể nhấn `F5` trong VS Code và chọn **AI Interview Local**.

## 2. Tài khoản cục bộ

Ở lần chạy đầu, hệ thống tạo dữ liệu khởi tạo trong cơ sở dữ liệu cục bộ. Không công khai mật khẩu sử dụng thực tế trên GitHub. Sau khi khởi động, hãy dùng thông tin do người quản trị cung cấp và mở trang **Tài khoản** để nhập danh sách người dùng.

## 3. File tài khoản

Hệ thống nhận `.xlsx`, `.csv` và `.json`. Có thể tải mẫu trực tiếp trong trang **Tài khoản** hoặc dùng các file trong thư mục `data`:

- `account_template.csv`
- `account_template.json`

Các cột:

| Cột | Bắt buộc | Nội dung |
|---|---|---|
| `username` | Có | Tên đăng nhập duy nhất, không có khoảng trắng. |
| `password` | Có với tài khoản mới | Tối thiểu 6 ký tự. Để trống khi cập nhật nếu muốn giữ mật khẩu cũ. |
| `full_name` | Có | Họ và tên hiển thị. |
| `role` | Có | `teacher` hoặc `candidate`. |
| `email` | Không | Email liên hệ. |
| `student_id` | Không | Mã sinh viên/mã ứng viên. |
| `active` | Không | `true/false` hoặc `1/0`; mặc định là `true`. |

Hệ thống cũng hiểu tên cột tiếng Việt như `ten_dang_nhap`, `mat_khau`, `ho_ten`, `vai_tro`, `ma_sinh_vien` và vai trò `giao_vien`, `ung_vien`.

Mật khẩu gốc chỉ nằm trong file do bạn quản lý. Sau khi import, SQLite chỉ lưu mật khẩu đã băm bằng `scrypt`.

## 4. Cách demo

### Giáo viên

1. Đăng nhập bằng tài khoản Giáo viên.
2. Import bộ câu hỏi JSON hoặc dùng sẵn hai bộ demo.
3. Nhập tên đợt, chọn môn, số câu, thời gian, hình thức trả lời và mã đề.
4. Bấm **Tạo và mở đợt Interview**.
5. Gửi mã đề cho ứng viên.
6. Mở trang **Kết quả** để xem báo cáo chi tiết.
7. Có thể xóa từng kết quả không còn cần thiết; thao tác này xóa cả câu trả lời đã lưu.
8. Có thể bấm **Xóa đợt** tại danh sách đợt Interview; thao tác này xóa cả lượt làm, câu trả lời và báo cáo thuộc đợt đó.

### Ứng viên luyện tập

1. Đăng nhập bằng tài khoản Ứng viên.
2. Chọn **Luyện tập**.
3. Chọn ngôn ngữ, môn, số câu và độ khó ban đầu.
4. Trả lời từng câu; hệ thống hiển thị điểm và góp ý ngay.
5. Xem báo cáo cuối phiên.
6. Mở **Lịch sử** để xem lại điểm và báo cáo của các buổi trước.
7. Có thể xóa từng buổi luyện tập của chính mình bằng nút **Xóa**.

### Ứng viên làm Interview thật

1. Chọn **Interview thật**.
2. Nhập mã đề do Giáo viên cung cấp.
3. Chỉ có thể bắt đầu khi đợt kiểm tra đang mở và đúng thời gian.
4. Mỗi tài khoản có một lượt cho mỗi mã đề.
5. Trong lúc làm, hệ thống không hiện điểm hay đáp án; chỉ Giáo viên xem báo cáo.

## 5. Voice / STT và LLM local

Tất cả thư viện Voice/STT đã có trong `requirements.txt`. Trong buổi luyện tập hoặc đợt Interview cho phép Voice, bấm **Ghi âm**, cấp quyền microphone cho Chrome/Edge rồi nói câu trả lời.

Ở lần sử dụng đầu tiên, hệ thống tự chọn cấu hình Faster-Whisper theo máy và lưu model trong `models/whisper`: `medium/CUDA float16` cho máy có GPU, `medium/CPU INT8` cho CPU đủ mạnh, hoặc `small/CPU INT8` cho máy yếu. Cấu hình GPU medium được chọn từ kết quả đo thực tế vì ổn định hơn `large-v3` trên bộ âm thanh hiện có. Lần đầu cần Internet và có thể mất vài phút; các lần sau chạy offline. Nếu muốn tải model trước khi demo, có thể chạy:

```powershell
python -m app.stt_setup
```

Trước khi ghi, trình duyệt đo tiếng nền trong 1,5 giây và bật khử nhiễu, khử vọng
cùng tự động cân bằng âm lượng. Ứng viên có thể chọn đúng microphone ngay trên màn
phỏng vấn; lựa chọn được ghi nhớ trên máy. Hệ thống chỉ chặn trước khi ghi khi âm thanh
quá lớn hoặc bị vỡ tiếng. Sau nhận dạng, hệ thống tính điểm chất lượng từ độ tin cậy
của Whisper, tỷ lệ từ không chắc chắn, tỷ lệ im lặng và tiếng nền. Bản ghi có nội dung
nhưng độ tin cậy thấp vẫn được chuyển qua Qwen để xem xét vùng nghi ngờ; báo cáo sẽ
đánh dấu câu đó để Giáo viên đối chiếu. Chỉ bản ghi không có lời nói, quá ngắn hoặc có
dấu hiệu lặp bất thường mới buộc phải ghi lại. Bộ kiểm tra từ chối bản sửa ngoài vùng
nghi ngờ hoặc làm đổi phủ định, số liệu, mức chắc chắn hay quá nhiều từ. Chế độ Voice
dùng mã bản ghi phía server nên ứng viên không thể sửa văn bản rồi gửi thay cho âm thanh.

Nếu trình duyệt chặn microphone, bấm biểu tượng ổ khóa cạnh địa chỉ `127.0.0.1` và chọn cho phép microphone.

### LLM sửa transcript

Dự án dùng `Qwen2.5 3B Q4_K_M` qua Ollama portable để sửa lỗi ASR sau
Faster-Whisper. Model chỉ nhận câu hỏi hiện tại và danh sách thuật ngữ đã duyệt;
không nhận đáp án tham chiếu. Server chỉ áp dụng từng cặp thay thế gần âm đã vượt qua
bộ kiểm tra an toàn, đồng thời giữ cả transcript gốc, bản sửa và danh sách thay đổi.

Sau khi cài Ollama trên máy mới, tải model đúng phiên bản trước khi chạy ứng dụng:

```powershell
ollama pull qwen2.5:3b
ollama pull qwen3:8b
```

Kiểm tra model đã có trên máy:

```powershell
ollama list
```

Lệnh pull chỉ cần chạy một lần khi máy đang có Internet. Sau khi tải xong, Ollama và
`qwen2.5:3b` có thể chạy hoàn toàn local.

`qwen2.5:3b` tiếp tục làm nhiệm vụ sửa transcript và chấm rubric. `qwen3:8b`
được dùng riêng để sinh câu hỏi có cấu trúc vì tác vụ này cần khả năng tuân thủ schema
và lập luận tốt hơn. Có thể đổi model bằng biến `QUESTION_GENERATION_MODEL`.

Luồng xử lý:

```text
Ghi âm -> Faster-Whisper + hotwords -> transcript + độ tin cậy từng từ
        -> Qwen đề xuất lỗi trong vùng nghi ngờ
        -> kiểm tra vùng sửa/thuật ngữ/phủ định/số liệu/mức độ chắc chắn
        -> transcript đã xác minh -> chấm rubric
```

Khởi động cả Ollama portable và ứng dụng trên cổng 8001:

```powershell
.\start_local.ps1
```

Kiểm thử đầu-cuối trên 7 file tiếng Việt, 299 từ tham chiếu, cho WER `6,02%`,
không có mẫu nào bị Qwen sửa tệ hơn. Thời gian STT trung bình trên RTX 4060 là
`2,41 giây/file`; Qwen sau khi được nạp mất khoảng `0,32 giây`. Báo cáo chi tiết
nằm tại `test_audio/end_to_end_pipeline_evaluation.json`.

Bộ chấm mặc định thử Ollama `qwen2.5:3b`; nếu Ollama chưa chạy, hệ thống tự chuyển sang bộ chấm rubric local. Vì vậy Ollama không bắt buộc để demo.

Điểm không được lấy trực tiếp từ con số do LLM sinh. Qwen phân loại từng ý rubric
thành `met`, `partial`, `missing` hoặc `contradicted`; server tính điểm theo trọng số
cố định. Mỗi ý lưu cả lý do và trích dẫn bằng chứng; server loại bỏ trích dẫn không có
trong câu trả lời và đánh dấu kết quả có độ tin cậy thấp để Giáo viên kiểm tra. Câu trả
lời không biết, phủ định toàn bộ nội dung hoặc cố thao túng điểm được chặn trước khi gọi
model. Khi câu trả lời dưới 80 điểm, câu tiếp theo ưu tiên cùng khái niệm để kiểm tra lại;
khi đạt từ 80 điểm, hệ thống tăng độ khó và mở rộng sang nội dung khác. Bộ kiểm định gồm
32 trường hợp đúng/sai/đối kháng trên 4 môn và 2 ngôn ngữ nằm tại
`test_audio/grading_quality_evaluation.json`.

## 6. Dữ liệu câu hỏi

Giáo viên có hai lựa chọn:

- **Thêm mới / cập nhật:** câu cùng `language + id` được cập nhật, câu khác được giữ lại.
- **Thay dữ liệu cùng ngôn ngữ:** thay các câu thuộc ngôn ngữ có trong file.

Hệ thống kiểm tra toàn bộ file trước khi ghi. Nếu có một câu sai cấu trúc, toàn bộ lần import bị hủy.
Mỗi ngôn ngữ hiện có 900 câu, chia đều 300 câu cho từng mức Easy, Medium và Hard.

### Rubric sinh câu hỏi bằng LLM

Quy tắc kiểm định câu hỏi do LLM sinh nằm trong
`data/question_generation_rubric.json`; bản giải thích để đọc và trình bày nằm trong
`QUESTION_GENERATION_RUBRIC.md`. Model chỉ được nhận các câu nguồn đã duyệt, không
được bổ sung kiến thức Internet. Backend kiểm tra nguồn, cấu trúc, độ trùng và bằng
chứng độ khó trước khi cho phép sử dụng câu hỏi.

Độ khó không được xác định chỉ bằng độ dài câu. Rubric đo mức Bloom, số khái niệm,
số bước suy luận, số ràng buộc, thời lượng trả lời và số key points. Câu luyện tập cần
đạt tối thiểu 85/100 và không vi phạm điều kiện bắt buộc; câu dùng trong Interview
thật luôn cần Giáo viên duyệt.

Luồng backend dành cho Giáo viên:

```text
Chọn môn + ngôn ngữ + số câu theo từng độ khó
→ Qwen3 sinh câu chỉ từ các câu nguồn nội bộ
→ backend kiểm tra rubric, nguồn và độ trùng
→ lưu ở trạng thái chờ duyệt
→ Giáo viên duyệt hoặc từ chối
→ câu đã duyệt mới được đưa vào ngân hàng
```

Các API chính:

- `POST /api/teacher/questions/generate`: sinh câu hỏi Dễ, Trung bình và Khó.
- `GET /api/teacher/questions/generated`: xem danh sách câu đang chờ duyệt.
- `PATCH /api/teacher/questions/generated/{id}`: duyệt hoặc từ chối câu hỏi.

### Voice và Giáo viên chấm lại

Mỗi câu trả lời bằng giọng nói lưu file voice gốc trong `data/audio`, kèm SHA-256,
transcript ban đầu, transcript đã xác minh và độ tin cậy. Thư mục voice được loại khỏi
Git để không công khai dữ liệu cá nhân của sinh viên.

Điểm AI là điểm tạm thời. Trong kỳ thi chính thức, câu có điểm dưới
`TEACHER_REVIEW_SCORE_THRESHOLD` hoặc có cảnh báo STT được đưa vào hàng chờ. Giáo viên
có quyền nghe voice, đối chiếu transcript và nhập điểm mới. Báo cáo dùng điểm Giáo viên
làm điểm cuối, đồng thời vẫn giữ điểm AI và lịch sử thay đổi để kiểm tra.

- `GET /api/teacher/reviews`: hàng chờ cần chấm lại.
- `GET /api/teacher/transcriptions/{id}/audio`: nghe hoặc tải voice gốc.
- `PATCH /api/teacher/answers/{id}/review`: nhập điểm và nhận xét của Giáo viên.
- `GET /api/teacher/answers/{id}/reviews`: xem lịch sử chấm lại.

## 7. Cấu trúc chính

| Vị trí | Chức năng |
|---|---|
| `main.py` | File chạy ứng dụng từ Terminal. |
| `app/main.py` | API, đăng nhập và phân quyền. |
| `app/services/account_importer.py` | Đọc tài khoản Excel/CSV/JSON. |
| `app/services/exam_service.py` | Quản lý đợt Interview thật. |
| `app/services/interview_engine.py` | Chọn câu hỏi thích ứng và tạo báo cáo. |
| `app/services/evaluator.py` | Chấm bằng Ollama hoặc rubric local. |
| `app/services/question_generation_rubric.py` | Tạo prompt và kiểm định câu hỏi do LLM sinh. |
| `app/services/question_generator.py` | Sinh, lưu và duyệt câu hỏi từ model local. |
| `app/services/teacher_review.py` | Hàng chờ, voice và điểm Giáo viên chấm lại. |
| `app/services/speech_to_text.py` | Chuyển Voice thành văn bản. |
| `app/static/` | Giao diện web. |
| `data/` | Dữ liệu mẫu và SQLite khi chạy. |

API docs: <http://127.0.0.1:8000/docs>

## 8. Kiểm thử

```powershell
python -m pytest -q
```

Database local nằm tại `data/ai_interviewer.db`. Server chỉ lắng nghe `127.0.0.1`, nên mặc định chỉ laptop đang chạy ứng dụng truy cập được.

> Lưu ý: mọi thao tác xóa là vĩnh viễn. Khi Giáo viên xóa một kết quả Interview thật, ứng viên có thể làm lại mã đề nếu đợt vẫn mở. Khi Giáo viên xóa cả đợt Interview, mã đề cùng toàn bộ lượt làm, câu trả lời và báo cáo liên quan cũng bị xóa.
