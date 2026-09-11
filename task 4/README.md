# Speech-to-Text Local

Mô-đun chuyển giọng nói thành văn bản bằng Faster Whisper. Toàn bộ quá trình nhận dạng chạy trên máy local; Internet chỉ cần trong lần đầu tải thư viện và model.

## Cấu hình thích ứng phần cứng

- `auto` chọn cấu hình theo CPU, RAM và khả năng CUDA của từng máy.
- Máy yếu: model `tiny`, CPU INT8.
- Máy phổ thông: model `base`, CPU INT8.
- Máy CPU mạnh hoặc có GPU phù hợp: model `small`.
- CUDA là tùy chọn; không có GPU hệ thống vẫn chạy hoàn toàn bằng CPU.
- Số luồng CPU được tự động chọn và giới hạn tối đa 8 để giữ máy phản hồi tốt.
- `beam_size=1` và VAD được bật để giảm độ trễ.
- Kết quả có transcript, ngôn ngữ, thời gian xử lý và RTF.

Giao diện có ba chế độ:

- `Nhanh`: Whisper Small, beam size 1.
- `Cân bằng`: Whisper Small, beam size 3.
- `Chính xác`: Whisper Medium, beam size 5.
- Có thể truyền từ khóa ưu tiên để tăng độ chính xác cho tên riêng và thuật ngữ môn học.

## Cấu trúc Frontend

Frontend nằm trong thư mục `web` và được chia theo trách nhiệm:

- `index.html`: cấu trúc ba màn hình Giới thiệu, Thông tin ứng viên và Phỏng vấn.
- `styles.css`: màu sắc, kiểu chữ và bố cục responsive.
- `router.js`: điều hướng theo URL và chặn truy cập màn hình phỏng vấn khi chưa có hồ sơ.
- `api-client.js`: kiểm tra `/health` và gửi âm thanh đến `/v1/audio/transcriptions`.
- `app.js`: trạng thái phiên, sự kiện giao diện, ghi âm và hiển thị transcript.

Các đường dẫn giao diện:

- `#/gioi-thieu`
- `#/thong-tin-ung-vien`
- `#/phong-van`

Kiểm tra cú pháp Frontend:

```powershell
cd .\web
npm run check
```

## Chuẩn bị

Máy cần Python 3.10 trở lên. Trong PowerShell:

```powershell
.\setup.ps1 -Model auto
```

Nếu Python chưa có trong `PATH`, truyền đường dẫn trực tiếp:

```powershell
.\setup.ps1 -Model auto -Python "C:\duong-dan\python.exe"
```

## Chuyển âm thanh thành văn bản

```powershell
.\run.ps1 -Audio ".\sample.wav" -Language vi
```

Xuất JSON để tích hợp với AI Interviewer:

```powershell
.\.venv\Scripts\python.exe .\transcribe.py .\sample.wav --language vi --json --output result.json
```

Để tự nhận dạng tiếng Việt hoặc tiếng Anh, dùng `--language auto`.

## Chạy REST API

Model được nạp một lần khi dịch vụ khởi động và tái sử dụng cho các yêu cầu sau:

```powershell
.\start_api.ps1 -Port 8000 -Model auto
```

Kiểm tra trạng thái:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Gửi file âm thanh:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/audio/transcriptions `
  -F "file=@sample.wav" `
  -F "language=vi" `
  -F "beam_size=1" `
  -F "model=small" `
  -F "hotwords=Faster Whisper, REST API"
```

Tài liệu API tương tác: `http://127.0.0.1:8000/api/docs`.

Kiểm tra tính toàn vẹn của model:

```powershell
.\.venv\Scripts\python.exe .\verify_model.py --model small
```

## Tối ưu tốc độ

- Mọi máy: giữ `--model auto --device auto` để hệ thống tự chọn.
- Faster Whisper trên Windows cần cuBLAS cho CUDA 12 và cuDNN 9 để chạy GPU.
- Chỉ dùng CPU: thêm `--device cpu --compute-type int8`.
- Đoạn phỏng vấn ngắn: giữ `--beam-size 1`.
- Ưu tiên tốc độ tuyệt đối: dùng `tiny`; cân bằng hơn: dùng `base` hoặc `small`.

## Tích hợp Python

```python
from stt_local import LocalWhisperEngine

engine = LocalWhisperEngine("models/small", device="auto")
result = engine.transcribe("answer.wav", language="vi")
print(result.text)
print(result.real_time_factor)
```
