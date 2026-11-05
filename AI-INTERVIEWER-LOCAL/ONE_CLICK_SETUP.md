# Cài đặt và chạy bằng một lần bấm

Trong thư mục `AI-INTERVIEWER-LOCAL`, bấm đúp **CAI_DAT_VA_CHAY.bat**. Không cần mở
VS Code hoặc tự gõ từng lệnh cài model. Giữ cửa sổ đang chạy; đóng ứng dụng bằng
Ctrl+C. Launcher mở trình duyệt sau khi backend trả health thành công.

## Lần đầu

1. Tìm Python 3.11 x64. Nếu thiếu, dùng WinGet cài `Python.Python.3.11` cho tài khoản hiện tại.
2. Tạo `.venv`, cài `requirements.txt`, kiểm tra dependency. Không cài thư viện training/dev.
3. Tạo `.env` từ mẫu nếu chưa có; không ghi đè `.env` đã tồn tại.
4. Tìm Ollama đang chạy. Nếu chưa có, dùng executable đã cài/portable, hoặc cài `Ollama.Ollama` bằng WinGet rồi khởi động dịch vụ ẩn. Tải model `OLLAMA_MODEL` đang cấu hình; mặc định `qwen2.5:3b`.
5. Tải/kiểm Whisper theo profile máy bằng công cụ STT có sẵn; lần đầu có nạp thử. Chuẩn bị Transformer baseline nếu chưa có. Model đã có được giữ nguyên, kể cả metadata fine-tune.
6. Chạy backend ở 127.0.0.1:8001 và mở web. Đăng nhập bằng tài khoản đã có, hoặc tài khoản demo trên database mới theo REQUIREMENTS.md.

Lần đầu cần Internet và nhiều GB dung lượng trống cho Python, thư viện và trọng
số. Thời gian phụ thuộc mạng và máy; không có cam kết hoàn tất trong vài phút.
Các lệnh WinGet chấp nhận điều khoản package/source để cài không cần nhập từng
bước. Không tự nâng quyền quản trị hoặc đổi ExecutionPolicy toàn máy.

Nếu Windows thiếu WinGet/App Installer hoặc bị chính sách trường chặn cài phần
mềm, launcher báo rõ phần thiếu. Cài Python 3.11 x64 và Ollama từ nguồn chính
thức theo REQUIREMENTS.md, rồi bấm lại. Đây là launcher từ mã nguồn, chưa phải
bộ cài `.exe` độc lập hay gói offline đủ trọng số.

## Những lần sau

Vẫn bấm **CAI_DAT_VA_CHAY.bat**. Launcher dùng dấu cài đặt theo SHA-256 của
requirements, kiểm dependency/import, tái sử dụng model/dịch vụ đã có và mở web.
Không huấn luyện hoặc tự tải lại toàn bộ model mỗi lần mở. STT chỉ kiểm setup
marker ở bước này, không nạp trước vào RAM nếu đã setup; ứng dụng tiếp tục nạp
khi Bắt đầu/khôi phục phiên theo chính sách hiện có. File model bị mất/hỏng có thể
cần chạy lại setup STT theo REQUIREMENTS.md.

Launcher có khóa ngăn bấm trùng. Nếu cổng 8001 đã dùng thì báo lỗi, không tắt
tiến trình khác hoặc tự mở thêm backend vào cùng database. Dừng backend cũ trước.
Nếu cổng đó thuộc ứng dụng khác, có thể chọn 8002 bằng lệnh bên dưới.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -Port 8002
```

Chỉ cài, chưa mở web:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -SetupOnly
```

Kiểm tra cài đặt và khởi động backend thật, xác minh HTML/JavaScript qua HTTP rồi
tự dừng các tiến trình do lượt thử tạo (không mở trình duyệt):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -VerifyStartup -Port 8093
```

Kết quả thành công lưu ở `.runtime/launcher-startup-check.json`. Chế độ này vẫn
cài phần thiếu như launcher thường; không chạy cùng `-SetupOnly`. Đây không phải
test độ chính xác nhận dạng hoặc chấm bài.

Cài lại thư viện runtime khi cần sửa môi trường, giữ nguyên dữ liệu/model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -Repair
```

Nếu `.venv` hiện có không phải Python 3.11 x64, launcher dừng và không xóa nó.
Kỹ thuật viên cần giữ lại môi trường cũ, tạo `.venv` phù hợp theo REQUIREMENTS.md.

## Model và dữ liệu được giữ

- Không xóa database, voice, tài khoản, ngân hàng câu hỏi hoặc kết quả chấm.
- Không ghi đè cấu hình riêng, không thay HOME/USERPROFILE hoặc cache Ollama toàn máy.
- Với Ollama portable tại `tools/ollama/ollama.exe`, chỉ đặt `OLLAMA_MODELS=models/ollama` cho tiến trình mới do launcher tạo nếu chưa có biến này. Dịch vụ đang chạy được dùng nguyên trạng.
- Chỉ quản lí Ollama HTTP loopback. URL remote/có credential cần cài/chạy thủ công; launcher không tự cài/tải model lên máy khác.
- Transformer đã có được giữ nguyên. Thư mục chứa model nhưng thiếu file sẽ bị dừng để tránh ghi đè fine-tune. Model mới được tải vào thư mục tạm, đổi tên sau khi setup thành công; tải/quantize dở không được công bố như file hoàn chỉnh.
- Không tải Qwen3:8b hoặc large-v3 ở mặc định; đây vẫn là tác vụ tùy chọn của giảng viên. Không thay thuật toán STT/chấm hoặc quality gate.
- Khi dừng launcher, chỉ dừng backend/dịch vụ Ollama mà chính lượt launcher này tạo. Không dừng dịch vụ Ollama đã chạy từ trước. Installer Ollama có thể tự mở tray service; đó là dịch vụ cài đặt thông thường, không bị launcher đóng.

Log Ollama do launcher tạo nằm ở `.runtime/ollama-launcher.log`; lỗi pip/WinGet và
backend hiện ngay trong cửa sổ. Không tắt máy giữa lúc tải; nếu lỗi, xem dòng lỗi
trước khi thử lại. Các artifact runtime bị loại khỏi Git.

## Phạm vi kiểm chứng

Đã kiểm parser PowerShell và test tự động các nhánh giữ cấu hình/model, cài lại
dependency, lỗi tải/quantize, Ollama sẵn có và cổng bận. Download/cài phần mềm dùng
giả lập trong test; chưa chạy cài sạch đầy đủ trên một máy Windows mới hoặc VM.
Không tự cài lại Python/Ollama trên máy đang dùng chỉ để thử installer.

Lượt kiểm ngày 05/11/2026: **994 test qua trong 123,78 giây**, gồm 20 test mới
cho launcher/tải model; hai cảnh báo deprecation từ môi trường TestClient.
Kiểm tra cú pháp PowerShell không có lỗi; câu lệnh nhận diện Python x64 cũng
được thử bằng Windows PowerShell. Đây không phải kết quả cài mới WinGet/Ollama
thật hoặc phép đo tốc độ STT.

Tài liệu nguồn: [WinGet install của Microsoft](https://learn.microsoft.com/en-us/windows/package-manager/winget/install),
[Python Windows](https://www.python.org/downloads/windows/),
[Ollama Windows](https://ollama.com/download/windows).

Đã chạy thêm cài thư viện thật và kiểm tra HTTP hai lần trên máy phát triển;
chi tiết, thời gian và giới hạn ở [báo cáo kiểm tra local](docs/INSTALLER_LOCAL_CHECK_20261105.md).
