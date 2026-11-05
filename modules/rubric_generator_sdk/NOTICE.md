# Nguồn và phạm vi bản bàn giao

SDK đóng gói mã Rubric Generator V15 và core 1.3.0 của dự án này. Sáu mô-đun gốc giữ nguyên logic; chỉ đổi import sang namespace rubric_generator_sdk. SDK thêm giao diện, lưu trữ, khóa worker và CLI. _provenance.json ghi hash nguồn và hash sau đóng gói.

Wheel chạy không kèm model weights, Ollama binary, dữ liệu runtime của người dùng hoặc bộ rubric đã được người chấm phê duyệt. Thư mục tests trong ZIP giữ một đoạn phản hồi V1 của ví dụ Stack/Queue để tái hiện lỗi cũ; nó không được cài vào runtime hoặc gửi vào prompt. Các phản hồi giả lập dùng kiểm tra phần mềm không phải human gold hoặc dự đoán Qwen thật.

Wheel phụ thuộc trong wheelhouse được tải nguyên bản để cài offline Windows x64/CPython 3.11; mỗi wheel giữ thông tin giấy phép/metadata của nhà phát hành bên trong. Gói này không cấp lại giấy phép cho Ollama hoặc Qwen và không phân phối trọng số của chúng.

Wheel SDK không được xuất bản lên PyPI hoặc gửi lên repository của nhóm. Chỉ tạo bản bàn giao để người dùng tích hợp.
