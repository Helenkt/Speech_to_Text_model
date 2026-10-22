# AI Interview Local

Demo hệ thống AI Interview chạy trực tiếp trên laptop bằng FastAPI, SQLite và giao diện web local. Hệ thống có hai vai trò riêng:

| Vai trò | Chức năng |
|---|---|
| Giáo viên | Import tài khoản, quản lý bộ câu hỏi, mở/đóng đợt Interview thật và xem kết quả. |
| Ứng viên | Luyện tập, xem lại lịch sử hoặc làm Interview thật bằng mã đề do Giáo viên cung cấp. |

> Hai ngân hàng câu hỏi VI/EN hiện là dữ liệu demo chưa được giảng viên kiểm định. Điểm số chỉ dùng để thử luồng hệ thống.

Ngân hàng hiện có `1.800` câu song ngữ thuộc 4 môn: Nhập môn Trí tuệ nhân tạo,
Các hệ cơ sở dữ liệu, Cấu trúc dữ liệu và giải thuật, và Lập trình hướng đối tượng.

## 1. Cài đặt và chạy

Hướng dẫn đầy đủ cho máy mới, gồm Python, Ollama, Whisper, Transformer và tài khoản demo:
**[REQUIREMENTS.md](REQUIREMENTS.md)**. Bản này vẫn cài thủ công, chưa có bộ tự cài một lần bấm.

Yêu cầu đã kiểm thử: Windows 64-bit và Python 3.11. VS Code không bắt buộc.
Mở PowerShell trong thư mục `AI-INTERVIEWER-LOCAL`, sau đó chạy:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Tiếp tục cài/mở Ollama, tải model và kiểm tra STT theo `REQUIREMENTS.md`.
Sau khi đã chuẩn bị, chạy:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Mở <http://127.0.0.1:8001>. Nhấn `Ctrl+C` trong Terminal để dừng.
`python main.py`, F5 hoặc `CHAY_WEB.bat` vẫn dùng cổng 8000; không phải trình tự cài model.
Không cần kích hoạt môi trường bằng `Activate.ps1` nếu dùng đường dẫn Python như trên.

## 2. Tài khoản cục bộ

Ở lần chạy đầu, hệ thống tạo dữ liệu khởi tạo trong cơ sở dữ liệu cục bộ. Tài khoản demo công khai nằm trong `data/accounts_demo.csv` và được mô tả ở `REQUIREMENTS.md`; chỉ tự tạo khi database chưa có người dùng. Không công khai mật khẩu sử dụng thực tế trên GitHub. Sau khi khởi động, mở trang **Tài khoản** để nhập danh sách người dùng riêng.

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
3. Nhập tên đợt, chọn môn, số câu, thời gian và mã đề. Giao diện ứng viên dùng ghi âm, không nhập câu trả lời bằng chữ.
4. Bấm **Tạo và mở đợt Interview**.
5. Gửi mã đề cho ứng viên.
6. Mở trang **Kết quả** để xem báo cáo chi tiết.
7. Có thể xóa từng kết quả không còn cần thiết; thao tác này xóa cả câu trả lời đã lưu.
8. Có thể bấm **Xóa đợt** tại danh sách đợt Interview; thao tác này xóa cả lượt làm, câu trả lời và báo cáo thuộc đợt đó.

### Ứng viên luyện tập

1. Đăng nhập bằng tài khoản Ứng viên.
2. Chọn **Luyện tập**.
3. Chọn ngôn ngữ, môn, số câu và độ khó ban đầu.
4. Bấm Bắt đầu để chuẩn bị STT/VAD ở nền; ghi âm, xem transcript và xác nhận từng câu.
5. Kết thúc phiên để AI tự chấm theo rubric, trả điểm và báo cáo; không cần giảng viên duyệt luyện tập.
6. Mở **Lịch sử** để xem lại điểm và báo cáo của các buổi trước.
7. Có thể xóa từng buổi luyện tập của chính mình bằng nút **Xóa**.

### Ứng viên làm Interview thật

1. Chọn **Interview thật**.
2. Nhập mã đề do Giáo viên cung cấp.
3. Chỉ có thể bắt đầu khi đợt kiểm tra đang mở và đúng thời gian.
4. Mỗi tài khoản có một lượt cho mỗi mã đề.
5. Trong lúc làm, hệ thống không hiện điểm hay đáp án; chỉ Giáo viên xem báo cáo.

## 5. Voice / STT và LLM local

Các thư viện runtime Voice/STT nằm trong `requirements.txt`; trọng số model, Ollama và thư viện GPU cần chuẩn bị riêng theo [REQUIREMENTS.md](REQUIREMENTS.md). Bấm **Ghi âm**, cấp quyền microphone cho Chrome/Edge rồi nói câu trả lời.

Hệ thống tự chọn cấu hình Faster-Whisper theo tài nguyên và lưu model trong `models/whisper`: `medium/CUDA float16` khi GPU tương thích và đủ tài nguyên, `medium/CPU INT8` cho CPU đủ mạnh, hoặc `small/CPU INT8` cho máy yếu. Đây là lựa chọn cân bằng tài nguyên, không chứng minh medium chính xác hơn large-v3. Lần tải đầu cần Internet; sau khi tải đủ model có thể chạy offline. Nếu muốn tải model trước khi demo, chạy:

```powershell
.\.venv\Scripts\python.exe -m app.stt_setup
```

Kiểm tra mic thành công được tái sử dụng trong cùng phiên; không đo lại trước mỗi câu.
Bài kiểm tra có bước giữ im lặng 2 giây để đo nền và bước ghi thử giọng nói.
Trình duyệt yêu cầu khử nhiễu, khử vọng và tự động cân bằng âm lượng; mức hỗ trợ tùy thiết bị.
Ứng viên có thể chọn đúng microphone ngay trên màn
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

Dự án dùng `qwen2.5:3b` qua Ollama để sửa lỗi ASR sau
Faster-Whisper. Model chỉ nhận câu hỏi hiện tại và danh sách thuật ngữ đã duyệt;
không nhận đáp án tham chiếu. Server chỉ áp dụng từng cặp thay thế gần âm đã vượt qua
bộ kiểm tra an toàn, đồng thời giữ cả transcript gốc, bản sửa và danh sách thay đổi.

Sau khi cài Ollama trên máy mới, tải model đúng phiên bản trước khi chạy ứng dụng:

```powershell
ollama pull qwen2.5:3b
```

Chỉ máy giảng viên cần sinh đề mới tải thêm `ollama pull qwen3:8b`; không bắt máy sinh viên tải model này.

Kiểm tra model đã có trên máy:

```powershell
ollama list
```

### Transformer chấm theo rubric

Backend có thêm `RubricGuard Lite`: `FactGuard` kiểm tra số, đơn vị, phủ định và
quan hệ so sánh; MiniLM Transformer ONNX INT8 đối chiếu từng ý trong câu trả lời
với rubric. Model chỉ được tự chốt khi vượt quality gate. Nếu chưa đủ tin cậy, hệ
thống tự chuyển sang Qwen. Chỉ bài thi chính thức có luồng giảng viên chấm lại;
luyện tập thiếu bằng chứng được ghi rõ là chưa đủ cơ sở chấm, không tự gán điểm 0.

Tải model Transformer cho máy mới:

```powershell
.\.venv\Scripts\python.exe tools\setup_rubricguard_lite.py
```

Model INT8 khoảng 102 MB và được nạp khi chấm lần đầu, không chạy trong lúc ghi âm
hay chuyển giọng nói thành văn bản. Xem chi tiết tại [RUBRICGUARD_LITE.md](RUBRICGUARD_LITE.md).

Bản trên máy phát triển từng được fine-tune ngày 16/10/2026; trọng số đó không có trên Git.
Chỉ runtime có đủ trọng số và metadata kiểm định hợp lệ mới bật chế độ chọn lọc tương ứng.
Máy mới chạy lệnh setup ở trên nhận model gốc, không phải checkpoint fine-tune và không
tự có cùng quality gate như máy phát triển. Xem kết quả thực nghiệm và cách tái lập tại
[FINETUNE_REPORT_20261016.md](FINETUNE_REPORT_20261016.md).

Lệnh pull chỉ cần chạy một lần khi máy đang có Internet. Sau khi tải xong, Ollama và
`qwen2.5:3b` có thể chạy hoàn toàn local.

`qwen2.5:3b` tiếp tục làm nhiệm vụ sửa transcript và chấm rubric. `qwen3:8b`
được dùng riêng để sinh câu hỏi có cấu trúc vì tác vụ này cần khả năng tuân thủ schema
và lập luận tốt hơn. Có thể đổi model bằng biến `QUESTION_GENERATION_MODEL`.

Luồng xử lý:

```text
Bắt đầu -> chuẩn bị và lưu toàn bộ câu hỏi/rubric/độ khó của phiên
Trong phiên: ghi âm từng câu -> STT -> sửa transcript có kiểm soát (LLM khi cần)
             -> lưu voice/transcript tạm -> sinh viên xem lại, không sửa chữ
             -> ghi âm lại hoặc xác nhận -> khóa bản đang xem -> câu tiếp theo
Kết thúc -> hàng đợi chấm -> giải phóng STT -> chấm đúng bản đã xác nhận
         -> tổng hợp báo cáo; điểm thi voice vẫn cần quyết định của giảng viên
```

Luồng mới mặc định bật qua `DEFER_GRADING_UNTIL_FINISH=true` và chỉ áp dụng khi
tạo phiên mới. Phiên cũ giữ nguyên cách xử lý, không chấm lại lịch sử. STT xử lý
từng bản ghi và tái sử dụng worker khi ngân sách bộ nhớ cho phép, không ghép voice của nhiều câu thành một
câu trả lời. Câu hỏi do LLM sinh vẫn qua luồng chuẩn bị/duyệt hiện có trước khi thi.
Từ bản 1.16.1, sửa transcript diễn ra trước xác nhận; bước chấm cuối không sửa
text thêm lần nữa. Bản tạm được giữ trên đĩa local, không giữ toàn bộ audio trong
RAM. Các lần ghi lại không tự trở thành câu trả lời; chỉ bản đã xác nhận được chấm.

`GET /api/interviews/{id}/draft` phục hồi preview hiện tại, fingerprint,
`can_confirm` và `can_record`. `POST /api/interviews/{id}/transcriptions/{tid}/confirm`
nhận JSON chỉ gồm `preview_sha256`, không nhận text sinh viên sửa. Server khóa
voice/transcript trong cùng transaction với việc chuyển câu; bản cũ bị thay thế,
voice mất hoặc fingerprint sai sẽ không được xác nhận. `/answer` giữ tương thích
như một alias xác nhận, luôn dùng transcript server chứ không dùng text client.

API `GET /api/interviews/{id}/grading` trả trạng thái/progress/report_ready;
`POST /api/interviews/{id}/grading/retry` thử lại lỗi kỹ thuật, tối đa ba lượt tổng.
Báo cáo ứng viên/giảng viên có thêm trường `grading`. Từ bản 1.17.0, giao diện đã
nối luồng này: xem transcript chỉ đọc, ghi âm lại hoặc xác nhận để chuyển thẳng
sang câu tiếp theo, không hiện điểm giữa các câu ở phiên mới. Cuối phiên hiển
thị tiến độ chấm rồi tự mở nội dung báo cáo; lỗi kỹ thuật có nút thử tiếp trong
giới hạn backend. Tải lại trang có thể khôi phục bản tạm từ server hoặc tiếp tục
theo dõi báo cáo đã nộp. Thi chính thức chỉ báo trạng thái cho sinh viên, không
hiện điểm riêng của giảng viên. Phiên cũ vẫn dùng luồng chấm từng câu.

Từ backend 1.18.0, mở web, đăng nhập hoặc đọc trạng thái không nạp sẵn model AI.
API Bắt đầu luyện tập/Interview mới khởi động chuẩn bị STT/VAD ở nền; mở lại phiên
đang làm cũng chuẩn bị lại nếu model chưa sẵn sàng. Bộ câu hỏi trả về ngay để
sinh viên đọc/kiểm tra mic trong lúc model chuẩn bị. Worker đã nạp được tái sử dụng,
không tạo lượt nạp trùng. LLM sửa transcript và chấm chỉ nạp khi thực sự cần.
`RUNTIME_WARMUP=false` tắt bước chuẩn bị theo phiên, không tắt nhận dạng theo nhu cầu.
Tác vụ chấm đã nộp từ trước vẫn được hàng đợi khôi phục khi backend khởi động;
đây là tiếp tục yêu cầu đã lưu, không phải nạp trước model cho một phiên chưa bắt đầu.

Luyện tập có `grading_owner=ai`, không vào hàng chờ giáo viên và không cho giảng viên
ghi đè điểm qua API chấm lại. Điểm thiếu bằng chứng có `final_score=null`,
`score_status=insufficient_evidence` và không được tính vào điểm trung bình.
Điểm 0 chỉ là kết quả chính thức khi AI đã đối chiếu được rubric, không phải do lỗi
kỹ thuật/voice không rõ. Không chỉnh lại transcript đã xác nhận trong bước chấm.

Launcher tùy chọn khi đã có Ollama portable trong project và đã cài môi trường:

```powershell
.\start_local.ps1
```

Script chọn cổng trống; dùng đúng URL được in ra. Đây không phải bộ tự cài model.
Với Ollama cài thông thường, ưu tiên lệnh uvicorn ở mục 1 để tránh đổi cache model.

Bộ chấm kết hợp kiểm tra quy tắc, Transformer và Ollama `qwen2.5:3b` tùy bằng chứng.
Có thể mở web khi Ollama chưa chạy, nhưng không có sửa transcript bằng Qwen và các ý
không đủ bằng chứng có thể chưa chấm được; không coi đây là bản AI đầy đủ.

Điểm không được lấy trực tiếp từ con số do LLM sinh. Qwen phân loại từng ý rubric
thành `met`, `partial`, `missing` hoặc `contradicted`; server tính điểm theo trọng số
cố định. Mỗi ý lưu cả lý do và trích dẫn bằng chứng; server loại bỏ trích dẫn không có
trong câu trả lời và đánh dấu kết quả có độ tin cậy thấp để Giáo viên kiểm tra. Câu trả
lời không biết, phủ định toàn bộ nội dung hoặc cố thao túng điểm được chặn trước khi gọi
model. Phiên mới mặc định chuẩn bị toàn bộ câu hỏi và độ khó trước khi bắt đầu,
không dùng điểm câu trước để chọn câu sau. Luồng thích ứng cũ chỉ còn để tương thích
khi không dùng chiến lược chấm cuối phiên; không phải hành vi mặc định.

## 6. Dữ liệu câu hỏi

Giáo viên có hai lựa chọn:

- **Thêm mới / cập nhật:** câu cùng `language + id` được cập nhật, câu khác được giữ lại.
- **Thay dữ liệu cùng ngôn ngữ:** thay các câu thuộc ngôn ngữ có trong file.

Hệ thống kiểm tra toàn bộ file trước khi ghi. Nếu có một câu sai cấu trúc, toàn bộ lần import bị hủy.
Mỗi ngôn ngữ hiện có 900 câu, chia đều 300 câu cho từng mức Easy, Medium và Hard.

### Rubric sinh câu hỏi bằng LLM

Quy tắc kiểm định câu hỏi do LLM sinh nằm trong
`data/question_generation_rubric.json`; bản giải thích để đọc và trình bày nằm trong
`QUESTION_GENERATION_RUBRIC.md`. Prompt giới hạn model vào nguồn nội bộ, không bổ sung
kiến thức Internet. Backend kiểm tra ID nguồn, trích dẫn, cấu trúc, độ trùng và khai báo
độ khó. Hiện bộ chọn nguồn lọc `active` và `bank_scope=learning`, chưa bắt buộc
`verification_status` đã duyệt. Vì vậy không được mô tả tất cả nguồn là đã được giảng viên
kiểm định. Trích dẫn khớp và điểm quy tắc cao không chứng minh đáp án đúng về ngữ nghĩa.

Mỗi câu sinh mới còn được backend gắn `source_provenance` gồm UID/ID câu nguồn,
tên file, SHA-256 file, trạng thái duyệt và trích đoạn tham chiếu. Model phải trả
`evidence_quote` khớp nguyên văn đáp án hoặc key point nguồn; nếu không khớp, câu
bị từ chối. `generation_provenance` lưu model, thời điểm sinh và SHA-256 prompt để
có thể tái kiểm tra mà không phải công khai toàn bộ prompt.

Độ khó không được xác định chỉ bằng độ dài câu. Rubric đo mức Bloom, số khái niệm,
số bước suy luận, số ràng buộc, thời lượng trả lời và số key points. Câu luyện tập cần
đạt tối thiểu 85/100 và không vi phạm điều kiện bắt buộc để nhận nhãn `practice_eligible`.
Đây không phải tự xuất bản: luồng sinh hiện lưu bản nháp, giảng viên duyệt trước khi
đưa vào ngân hàng, kể cả câu đủ điều kiện luyện tập. Chưa có lượt LLM độc lập chứng
nhận tính đúng đắn của câu hỏi.

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

Quy trình dưới đây chỉ áp dụng cho kiểm tra Interview chính thức, không áp dụng luyện tập.
Điểm AI ban đầu là điểm tạm thời. Khi Giáo viên mở một câu trong phần chấm lại,
backend dùng Faster-Whisper `large-v3` chạy Beam 5 trên voice gốc, sửa an toàn các vùng
không chắc chắn rồi chấm lại theo cùng rubric. Giao diện giữ song song text cũ và text
do model mạnh chuyển lại. Kết quả được lưu để không chạy lại model khi mở lần sau.

Điểm từ model mạnh luôn là điểm đề xuất. Khi kết quả đã xác minh và đạt ngưỡng
`TEACHER_REVIEW_SCORE_THRESHOLD`, Giáo viên có thể dùng điểm này hoặc tự nhập điểm
và nhận xét. Nếu model mạnh chấm lại vẫn dưới ngưỡng, bắt buộc giảng viên tự chấm;
API từ chối thao tác dùng nguyên điểm AI. Việc nghe
voice là tùy chọn, có thể phát lại không giới hạn và không khóa thao tác chấm. Chỉ sau
quyết định của Giáo viên, điểm mới được ghi vào `final_score`; mọi lần đổi điểm đều có
lịch sử riêng.

Kết quả model mạnh dùng cache có phiên bản theo STT, LLM và rubric. Cùng một câu trả
lời không bị xử lý trùng khi có nhiều yêu cầu đồng thời. `REVIEW_MODEL_CACHE_POLICY`
cho phép tự giữ model trên máy đủ RAM/VRAM và tự giải phóng trên máy yếu.

- `GET /api/teacher/reviews`: hàng chờ cần chấm lại.
- `POST /api/teacher/answers/{id}/ai-review`: chạy hoặc lấy lại kết quả `large-v3` đã lưu.
- `GET /api/teacher/transcriptions/{id}/audio`: nghe hoặc tải voice gốc.
- `PATCH /api/teacher/answers/{id}/review`: nhập điểm và nhận xét của Giáo viên.
- `GET /api/teacher/answers/{id}/reviews`: xem lịch sử chấm lại.

### Adaptive VAD và chuẩn WER

Hệ thống chọn cấu hình Silero VAD theo mức tiếng nền đo được thay vì dùng một
ngưỡng cố định. Bốn profile `quiet`, `moderate`, `noisy`, `very_noisy` điều chỉnh
ngưỡng speech, thời gian im lặng, thời lượng speech tối thiểu và padding. Profile
đã dùng được lưu trong metadata transcript.

Kiểm tra microphone được gắn với đúng `session_id` đang thi. Backend tự đo tiếng nền
từ audio; số đo phía trình duyệt chỉ dùng để đối chiếu. Phiên luyện tập bị bỏ quên được
tự đóng sau `ACTIVE_SESSION_TTL_HOURS`, còn phiên thi thật tự đóng khi đợt thi hết hạn.

Chuẩn chấp nhận STT:

- Audio sạch: `WER <= 8%`.
- Audio có tiếng nền: `WER <= 15%`.
- Không được làm mất hoặc thay đổi số liệu, phủ định và thuật ngữ được đánh dấu.

Đây là tiêu chí benchmark, không phải con số ước lượng trên giao diện. Đặt các
file voice có transcript chuẩn theo [mẫu manifest](data/stt_benchmark_manifest.example.json).
Mẫu chỉ minh họa schema, không kèm audio và không phải kết quả đo. Thay đường dẫn,
reference và thuật ngữ bằng dữ liệu đã được người nghe xác minh; cần cả clean/noisy
cho từng ngôn ngữ được đánh giá. Sau đó chạy từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m app.stt_benchmark data/stt_benchmark_manifest.example.json `
  --output data/stt_benchmark_report.json
```

Lệnh trả exit code `0` khi clean/noisy tổng và theo từng ngôn ngữ có trong manifest
đạt WER, tổng lỗi quan trọng bằng 0. CLI không bắt buộc có cả VI lẫn EN; muốn tuyên
bố song ngữ phải cung cấp đủ cả hai. Báo cáo lưu WER, CER và lỗi từng mẫu. WER được
tính theo token cách nhau bởi khoảng trắng sau chuẩn hóa, không phải phần trăm
độ chính xác ngữ nghĩa hoặc độ chính xác cho từng bản ghi trực tiếp.

Repository không kèm audio hay báo cáo gốc của các phép đo STT cũ, nên không thể
xác nhận lại các số WER/tốc độ đó chỉ từ bản tải Git. Các ngưỡng trên là mục tiêu,
chưa phải chứng nhận đạt trên máy RAM 4/8 GB hoặc mọi giọng sinh viên. Benchmark
này gọi STT, không đo toàn bộ luồng sửa bằng Qwen, xác nhận và chấm điểm.

### Tự nhận diện cấu hình máy

Khi chọn profile/chuẩn bị suy luận, backend đọc số luồng CPU, tổng RAM, RAM còn trống, mức sử dụng RAM,
CUDA, số GPU và VRAM rồi tự chọn profile:

| Profile | Model chính | Chính sách |
|---|---|---|
| Tiết kiệm | `small/cpu/int8` | Một model, ghi lại khi audio khó |
| Cân bằng | `medium/cpu/int8` | VAD và giải mã theo tài nguyên; không cam kết có engine khử nhiễu ngoài |
| Hiệu năng | `medium/cuda/float16` | Xử lý nặng theo nhu cầu, không giữ song song model |
| Độ chính xác cao | `medium/cuda/float16` | Giải mã thích ứng: lượt nhanh trước, Beam 5 khi độ tin cậy thấp |

RAM vật lý khoảng 8 GB trở xuống luôn thuộc luồng tiết kiệm tài nguyên, kể cả
khi còn nhiều RAM trống. Nếu máy 8 GB có CUDA/VRAM phù hợp, vẫn giữ medium trên
GPU thay vì hạ model không cần thiết. CPU dùng small INT8. RAM 4 GB có ngân sách
CPU/batch nhỏ hơn và đóng worker suy luận ở bước chuyển STT sang LLM để trả bộ
nhớ native cho hệ điều hành. Máy lớn hơn nhưng RAM còn trống dưới 4 GB cũng nạp
model theo giai đoạn. Kiểm tra RAM được cập nhật ở mỗi lần chuyển công đoạn.

Whisper/Transformer/LLM được giới hạn luồng CPU; LLM dùng batch nhỏ hơn nhưng
không cắt context/rubric hoặc giảm ngân sách output để làm nhanh. Với preview,
chỉ gọi LLM nếu cần sửa; máy ít RAM giải phóng LLM sau preview. Do yêu cầu xem
bản sửa trước xác nhận, có thể phải đổi model STT/LLM giữa các câu; không còn
cam kết giữ STT trong bộ nhớ suốt phiên khi đã gọi LLM. Model sinh câu
hỏi không chạy song song với STT/chấm. Large-v3 và Qwen3:8b vẫn là tác vụ nặng
theo yêu cầu, chưa được chứng nhận chạy thuận tiện trên máy 4/8 GB.

Các chính sách tài nguyên được kiểm thử mô phỏng; chưa phải benchmark tốc độ,
RAM đỉnh hoặc WER trên máy yếu thật. RAM 8 GB là cấu hình mục tiêu, 4 GB là mục
tiêu hỗ trợ chậm hơn, không phải bảo đảm mọi CPU/ổ đĩa đều đáp ứng.

`GET /api/health` trả cả phần cứng, profile, tính năng thực sự có sẵn và chính sách
bộ nhớ. DeepFilterNet hoặc pyannote chỉ được báo là có khi thư viện tương ứng đã
cài; phát hiện thư viện không chứng minh đã gọi engine xử lý. Pipeline hiện không
có lời gọi DeepFilterNet/pyannote để khử nhiễu hoặc tách người nói; không coi các
trường policy/engine trong health là bằng chứng đã xử lý bằng chúng. Có thể đặt `RUNTIME_PROFILE`
trong `.env`, nhưng profile cần GPU vẫn tự hạ xuống CPU nếu CUDA không tồn tại.

## 7. Cấu trúc chính

| Vị trí | Chức năng |
|---|---|
| `main.py` | File chạy ứng dụng từ Terminal. |
| `app/main.py` | API, đăng nhập và phân quyền. |
| `app/services/account_importer.py` | Đọc tài khoản Excel/CSV/JSON. |
| `app/services/exam_service.py` | Quản lý đợt Interview thật. |
| `app/services/interview_engine.py` | Chuẩn bị đề cố định cho phiên mới, giữ tương thích phiên cũ và tạo báo cáo. |
| `app/services/evaluator.py` | Chấm bằng Ollama hoặc rubric local. |
| `app/services/question_generation_rubric.py` | Tạo prompt và kiểm định câu hỏi do LLM sinh. |
| `app/services/question_generator.py` | Sinh, lưu và duyệt câu hỏi từ model local. |
| `app/services/teacher_review.py` | Hàng chờ, voice và điểm Giáo viên chấm lại. |
| `app/services/speech_to_text.py` | Chuyển Voice thành văn bản. |
| `app/static/` | Giao diện web. |
| `data/` | Dữ liệu mẫu và SQLite khi chạy. |

API docs theo lệnh mục 1: <http://127.0.0.1:8001/docs>. Nếu launcher chọn cổng khác, thay bằng đúng cổng đang chạy.

## 8. Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Database local nằm tại `data/ai_interviewer.db`. Server chỉ lắng nghe `127.0.0.1`, nên mặc định chỉ laptop đang chạy ứng dụng truy cập được.

> Lưu ý: mọi thao tác xóa là vĩnh viễn. Khi Giáo viên xóa một kết quả Interview thật, ứng viên có thể làm lại mã đề nếu đợt vẫn mở. Khi Giáo viên xóa cả đợt Interview, mã đề cùng toàn bộ lượt làm, câu trả lời và báo cáo liên quan cũng bị xóa.
