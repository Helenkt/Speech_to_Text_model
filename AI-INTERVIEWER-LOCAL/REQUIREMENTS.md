# Cài đặt và chạy trên máy khác

Đây là hướng dẫn cài thủ công để thử bản mã nguồn từ GitHub. Đã có launcher
**CAI_DAT_VA_CHAY.bat** tự chuẩn bị môi trường/model rồi mở web; xem
[ONE_CLICK_SETUP.md](ONE_CLICK_SETUP.md) để biết điều kiện và giới hạn.
`CHAY_WEB.bat` cũ vẫn chỉ chạy backend, không tự cài thư viện/model.

## 1. Những gì cần có

| Thành phần | Cách chuẩn bị | Có trong Git? |
| --- | --- | --- |
| Windows 10/11 64-bit | Ollama hiện yêu cầu Windows 10 22H2 trở lên | Không |
| Python 64-bit | Cài từ [python.org](https://www.python.org/downloads/windows/), không dùng bản 32-bit | Không |
| Thư viện chạy ứng dụng | `requirements.txt` | Có danh sách; pip tải thư viện |
| Ollama | Cài từ [ollama.com/download/windows](https://ollama.com/download/windows), mở ứng dụng sau khi cài | Không |
| Qwen2.5 3B | `ollama pull qwen2.5:3b` | Không |
| Faster-Whisper | `python -m app.stt_setup` trong môi trường dự án | Có mã tải, không có trọng số |
| RubricGuard gốc | `tools/setup_rubricguard_lite.py` | Có mã tải, không có trọng số |
| RubricGuard đã fine-tune | Gói runtime do người quản lý dự án cung cấp riêng | Chưa có gói tải fine-tune trên Git |
| Ngân hàng câu hỏi, giao diện và backend | Nằm trong `AI-INTERVIEWER-LOCAL` | Có |
| Database và voice sinh viên | Ứng dụng tự tạo trên máy mới | Không, không sao chép dữ liệu cá nhân |

RAM 8 GB là cấu hình mục tiêu; RAM 4 GB có chế độ tiết kiệm nhưng chậm hơn. CPU có thể chạy STT INT8 mà không cần NVIDIA/CUDA. Không cài PyTorch, bộ huấn luyện hoặc model giảng viên chỉ để dùng luyện tập.

Các phiên bản chính được cố định trong requirements để giảm khác biệt giữa các lần cài. Đây chưa phải bộ lock có hash cho mọi thư viện phụ hoặc mọi hệ điều hành. Bằng chứng kiểm thử hiện có không bảo đảm WER/tốc độ/điểm chấm giống nhau trên mọi máy.

## 2. Tạo môi trường và cài thư viện

Giải nén ZIP, mở **PowerShell ngay trong thư mục `AI-INTERVIEWER-LOCAL`** chứa `main.py` và `requirements.txt`, không chạy ở thư mục cha của repository.

Python 3.11 là phiên bản đã kiểm thử. Nếu máy đã cài Python 3.11, chạy:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Không cần chạy `Activate.ps1`, nên không cần đổi ExecutionPolicy toàn máy. Nếu lệnh `py` không tìm thấy Python, kiểm tra `python --version` và dùng `python -m venv .venv` với đúng phiên bản đã cài. Không tự dùng một Python mới hơn chưa kiểm thử rồi kết luận model bị lỗi.

### Cấu hình riêng của máy

Ứng dụng dùng mặc định nếu chưa có `.env`. Khi cần cấu hình rõ, tạo file từ mẫu
mà không ghi đè cấu hình đang dùng:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Mặc định `EVALUATOR_MODE=auto`, `DEFER_GRADING_UNTIL_FINISH=true`,
`RUNTIME_WARMUP=true`, `INFERENCE_WORKER=true`. Model chỉ chuẩn bị sau khi bắt
đầu/khôi phục phiên; chấm cuối phiên. Các biến môi trường đã đặt trong cửa sổ
PowerShell được ưu tiên hơn `.env`. Sau khi sửa cấu hình, dừng rồi chạy lại backend.
Không đưa `.env` của máy sử dụng thật lên Git.

## 3. Cài Ollama và tải LLM

Sau khi cài Ollama bằng đường dẫn ở mục 1, mở Ollama từ Start Menu. Đóng/mở lại PowerShell nếu chưa nhận lệnh `ollama`.

```powershell
ollama --version
ollama pull qwen2.5:3b
ollama list
```

Kiểm tra dịch vụ:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Nếu chưa có dịch vụ, mở một cửa sổ PowerShell khác, chạy `ollama serve` và giữ cửa sổ đó mở. Nếu Ollama đã chạy từ Start Menu thì không chạy thêm `serve`, tránh lỗi trùng cổng.

Ollama là chương trình riêng, **không phải** thư viện có thể cài bằng `pip install -r requirements.txt`. Lệnh pull chỉ tải model, không fine-tune. Chưa tải hoặc chưa chạy Ollama thì web vẫn có thể mở, nhưng không được coi là đã sẵn sàng sửa transcript/chấm bằng Qwen.

## 4. Tải và kiểm tra Whisper

```powershell
.\.venv\Scripts\python.exe -m app.stt_setup
```

Lần đầu cần Internet. Chương trình tự chọn profile theo RAM/CPU/GPU và lưu trọng số ở `models/whisper`. Chờ thông báo `STT san sang` trước khi thử microphone. Việc nạp model khi bắt đầu phiên không thay cho bước tải trên máy mới.

CPU không cần cài thêm CUDA. Nếu muốn dùng NVIDIA, cần driver và thư viện CUDA/cuDNN tương thích theo [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper#gpu). Các DLL GPU của Ollama portable trên máy phát triển không được đưa lên Git và không tự xuất hiện sau khi cài requirements.

Để thử tương thích bằng CPU trước nếu máy mới thiếu DLL GPU:

```powershell
$env:WHISPER_DEVICE = "cpu"
$env:WHISPER_COMPUTE_TYPE = "int8"
.\.venv\Scripts\python.exe -m app.stt_setup
```

Giữ các biến đó trong cửa sổ dùng để chạy backend, hoặc ghi vào `.env` nếu muốn cố định cấu hình. Nếu báo thiếu Visual C++ Runtime, cài [Microsoft Visual C++ Redistributable x64](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist), sau đó thử lại.

## 5. Chuẩn bị Transformer chấm rubric

Máy mới chưa có model:

```powershell
.\.venv\Scripts\python.exe tools\setup_rubricguard_lite.py
```

Lệnh này tải **MiniLM gốc và lượng tử hóa**, không tải model fine-tune của dự án. Quality gate chưa được kiểm định cho model gốc; các ý chưa đủ chắc chắn sẽ qua bộ chấm phụ hoặc được ghi là chưa đủ cơ sở chấm.

Muốn thử đúng bản fine-tune trên máy phát triển, cần nhận nguyên thư mục runtime `models/rubricguard-lite` riêng: trọng số, tokenizer/config và các báo cáo/calibration tương ứng. Kiểm tra SHA256 theo `FINETUNE_REPORT_20261016.md`; không chép riêng file ONNX rồi bỏ metadata hoặc tự bật gate. Không chạy setup vào thư mục fine-tune đang dùng. Không tự huấn luyện hay thay model chỉ để mở ứng dụng.

Với bản local hiện tại, sao chép nguyên thư mục đó sang cùng vị trí trên máy thử. Các tệp runtime cần giữ cùng nhau:

```text
models/rubricguard-lite/
  model.int8.onnx
  config.json
  tokenizer.json
  tokenizer_config.json
  special_tokens_map.json
  sentencepiece.bpe.model
  training_summary.json
  runtime_evaluation.json
  calibration.json
  runtime_manifest.json
```

Không cần đưa checkpoint huấn luyện, `.train-venv`, database hoặc voice sinh viên sang máy thử. Không thêm trọng số nặng vào commit requirements này. Chuyển đủ tệp không thay thế việc kiểm thử chất lượng trên máy mới.

## 6. Chạy ứng dụng

Sau khi đã chuẩn bị Ollama/model, chạy backend trong PowerShell tại thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Giữ cửa sổ đó mở. Mở [http://127.0.0.1:8001](http://127.0.0.1:8001) bằng Chrome/Edge, cho phép microphone khi ứng dụng yêu cầu. Nhấn `Ctrl+C` để dừng backend. Nếu cổng 8001 đã dùng, thay bằng 8002 và mở đúng cổng đó; không tự tắt tiến trình khác.

Tùy chọn khác sau khi cài: `CHAY_WEB.bat` mở backend cổng **8000**, không tự cài Ollama/model. `start_local.ps1` là launcher portable cũ, không phải installer; với Ollama cài thông thường nên dùng lệnh uvicorn ở trên để tránh đổi đường dẫn cache sang `models/ollama`.

### Đăng nhập trên database mới

| Vai trò demo | Tên đăng nhập | Mật khẩu demo |
| --- | --- | --- |
| Giảng viên | `teacher` | `Teacher@123` |
| Sinh viên | `candidate01` | `Candidate@123` |

Đây là tài khoản dùng thử công khai trong `data/accounts_demo.csv`. Chỉ được tạo khi database chưa có người dùng và `AUTO_SEED_DEMO=true` (mặc định). Không ghi đè mật khẩu trên database cũ. Đổi mật khẩu/nhập tài khoản riêng trước khi sử dụng thực tế; không đưa danh sách tài khoản thật lên Git.

### Kiểm tra sẵn sàng

```powershell
$health = Invoke-RestMethod http://127.0.0.1:8001/api/health
$health.database
$health.speech_to_text
$health.ollama
$health.rubric_transformer
```

Với dữ liệu đi kèm và `AUTO_SEED_DEMO=true`, database mới có 1.800 câu hỏi và 3 tài khoản demo. Database cũ/import riêng có thể khác. Sau setup, Whisper cần `ready=true`; Ollama cần `running=true` và `model_available=true`. `rubric_transformer.installed=true` chỉ xác nhận có file, không chứng minh model đã đạt chất lượng tự chấm. Nếu dùng model gốc thì `production_ready=false` là đúng, không tự sửa thành true.

`speech_to_text.ready` dựa trên dấu kiểm tra setup của đúng cấu hình, không có
nghĩa model đang thường trú trong RAM. Trạng thái chuẩn bị theo phiên nằm ở
`runtime_readiness`. Health đọc trạng thái, không tự nạp tất cả model. Đổi profile
có thể cần chạy lại `app.stt_setup` cho đúng model/device/compute type.

Sau đó đăng nhập sinh viên, bắt đầu luyện tập, kiểm tra mic, ghi âm, xem transcript chỉ đọc, xác nhận từng câu và kết thúc để nhận báo cáo. Không cần Docker, Node.js, npm hoặc tải mô hình ngôn ngữ qua dịch vụ cloud để chạy bản này.

## 7. Phần tùy chọn cho giảng viên

Chỉ máy cần sinh đề bằng LLM mới tải thêm:

```powershell
ollama pull qwen3:8b
```

Chức năng giảng viên nhận dạng lại voice dùng `large-v3` và tải theo nhu cầu khi chạy chấm lại lần đầu, không nằm trong requirements. Lần đầu của chức năng đó vẫn cần Internet nếu chưa có trọng số. Qwen3 8B và Whisper large-v3 nặng hơn; không phải yêu cầu cài mặc định của máy sinh viên 4/8 GB, không nạp đồng thời mọi model chỉ vì mở web.

## 8. Kiểm thử và huấn luyện

Chỉ cần khi phát triển/kiểm tra phần mềm:

Cài thêm Node.js và kiểm tra `node --version` nếu muốn chạy đủ các test frontend.
Những test đó dùng DOM giả lập, không thay thế kiểm thử microphone hoặc giao diện
trong trình duyệt thật. Không cần npm cho bộ test hiện tại. Nếu thiếu Node, một số
test sẽ `skip`; không gọi đó là đã kiểm đủ frontend.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Huấn luyện là công việc riêng, cần môi trường `.train-venv` với Python 3.11 và `requirements-training.txt`. Không cài file training vào môi trường ứng dụng: tokenizer của bộ huấn luyện và runtime có ràng buộc khác nhau. Xem `RUBRICGUARD_LITE.md` trước khi fine-tune/xuất ONNX.

Test phần mềm đạt không chứng minh STT hoặc chấm bài đạt một tỷ lệ chính xác cụ thể. Cần kiểm thử audio có transcript chuẩn và câu trả lời được giảng viên duyệt riêng trên máy đích.

## 9. Lỗi thường gặp

| Hiện tượng | Kiểm tra / xử lí |
| --- | --- |
| `ERR_CONNECTION_REFUSED` | Backend chưa chạy hoặc đã dừng. Đọc lỗi ở PowerShell, giữ cửa sổ mở và dùng đúng cổng đang chạy. |
| `WinError 10048`, cổng 8001 đã dùng | Mở ứng dụng đã chạy hoặc đổi lệnh uvicorn sang `--port 8002`; không mở thêm hai backend vào cùng database để thử chữa lỗi cổng. |
| Không gọi được Ollama / chưa có model | Kiểm tra `/api/tags`, `ollama list` và tải `qwen2.5:3b`; không chỉ cài requirements. |
| Whisper chưa sẵn sàng, thiếu model/DLL | Chạy lại `app.stt_setup`, xem lỗi cụ thể; thử CPU INT8 theo mục 4 nếu thiếu DLL GPU. |
| Báo cáo “chưa xác minh”, điểm chưa chốt | Kiểm tra transcript, trạng thái chấm và bằng chứng rubric. Đây không tự động có nghĩa trả lời sai hoặc đã đạt 0 điểm; xem PRACTICE_GRADING.md. |
| Tải Git nhưng chấm khác máy phát triển | Setup tải Transformer baseline, không phải checkpoint fine-tune; xem mục 5. Cấu hình Whisper/Ollama và phần cứng cũng có thể khác. |

## 10. Cập nhật và sao lưu

Dừng backend trước khi sao lưu/đổi phiên bản. Giữ bản sao `data/ai_interviewer.db`
và toàn bộ thư mục `data/audio` cùng nhau, cùng `.env` và các đường dẫn storage
tùy chỉnh nếu có. Sao lưu chỉ database sẽ không giữ được voice cho bước nghe hoặc
nhận dạng lại. Giữ model và metadata đã kiểm định nếu cần tái lập runtime fine-tune.

Sau khi cập nhật mã, cài lại `requirements.txt` nếu danh sách thay đổi rồi chạy
backend bằng database hiện có. Ứng dụng có migration schema tự động; không xóa
database để nâng cấp. Sao lưu trước vì migration không phải công cụ khôi phục
điểm/voice bị mất. Không commit backup, database hoặc voice cá nhân.

Chức năng xóa trong ứng dụng có thể xóa cả bài làm và voice liên quan. Các file
JSON nằm ngoài `AI-INTERVIEWER-LOCAL/data` không tự được nhập vào database; dùng
trang nhập câu hỏi để kiểm tra và đưa thêm dữ liệu vào hệ thống.
