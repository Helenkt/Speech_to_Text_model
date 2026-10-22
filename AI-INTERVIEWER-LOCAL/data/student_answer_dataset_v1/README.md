# Bộ câu trả lời sinh viên mẫu v1

Ngày: 22/10/2026. Đây là **bộ dữ liệu tổng hợp do AI soạn, nhãn dự thảo cần duyệt**, không phải câu trả lời đã thu từ 400 sinh viên.

## Quy mô và nguồn

- Bốn môn AI101, DB101, DSA101 và OOP101.
- Mỗi môn 10 câu hỏi, mỗi câu hỏi 10 câu trả lời: tổng 400 câu trả lời.
- Nội dung lấy từ bốn tệp hiện có trong `data/rubricguard_training`. Có truy vết câu hỏi, tiêu chí gốc và SHA256 nguồn.
- Tiếng Việt tự nhiên và cách nói xen thuật ngữ Anh. Chưa phải bộ tiếng Anh độc lập, chưa kiểm chứng giọng nói hoặc lỗi STT.
- Không thêm tài liệu hoặc kiến thức từ Internet, không dùng thông tin sinh viên thật.

## Các tệp chính

| Tệp | Nội dung |
| --- | --- |
| `AI101.json`, `DB101.json`, `DSA101.json`, `OOP101.json` | Câu hỏi, rubric dự thảo, câu trả lời, nhãn từng ý, bằng chứng và ô duyệt |
| `draft_pairs_NOT_TRAINING.jsonl` | Mỗi dòng là một cặp câu trả lời–ý rubric, chỉ để kiểm tra, không tự dùng huấn luyện |
| `review_AI101.md`, `review_DB101.md`, `review_DSA101.md`, `review_OOP101.md` | Bản đọc toàn bộ câu trả lời và nhãn để người duyệt xem thuận tiện |
| `MAU_DOC_NHANH.md` | Một số ví dụ đầu tiên để hiểu cấu trúc |
| `HUONG_DAN_GAN_NHAN.md` | Định nghĩa nhãn, cách xử lý hàm ý, tự sửa, mâu thuẫn và cách duyệt |
| `manifest.json` | Nguồn, số lượng, phân chia nhóm và giới hạn sử dụng |
| `validation_report.json` | Kiểm tra cấu trúc, trích dẫn, trọng số và nguồn; không chứng minh nhãn đúng về ngữ nghĩa |

## Một ví dụ dữ liệu chứa gì

Mỗi câu hỏi có nguyên văn nguồn và `source_criteria` để đối chiếu. `rubric_draft` tách tiêu chí dài thành ý nhỏ. Tổng điểm các ý con giữ nguyên điểm tiêu chí cha; tổng mỗi câu vẫn 10. Chia đều điểm trong từng tiêu chí cha chỉ là **đề xuất**, không phải phân bổ đã được giảng viên duyệt.

Mỗi câu trả lời có nhãn đề xuất theo từng ý:

- `supported`: trình bày đúng ý bằng cách diễn đạt tương đương.
- `missing`: chưa trình bày ý đó, không đồng nghĩa với nói sai.
- `contradicted`: phát biểu sai/ngược ý, quan hệ hoặc điều kiện.
- `needs_review`: mâu thuẫn chưa giải quyết hoặc thiếu điều kiện để kết luận. Đây là trạng thái cần duyệt, **không phải nhãn thứ tư đưa vào model ba lớp**.

Bằng chứng trích nguyên văn từ câu trả lời, có offset ký tự. `proposed_score_range` chỉ minh họa điểm theo nhãn dự thảo; `teacher_points` vẫn `null`. Không có điểm đã được giảng viên xác nhận.

## Phân chia dữ liệu

Giữ nguyên nhóm câu hỏi từ thử nghiệm trước: 18 train, 8 validation, 8 test, 6 regression-only. Tương ứng 180/80/80/60 câu trả lời. Không đưa câu hỏi test, validation hoặc regression-only vào train.

**Đây là holdout phát triển, không phải benchmark độc lập mới:** các chủ đề đã xuất hiện trong quá trình thử nghiệm cũ; nhãn mới cũng do AI soạn. Duyệt nhãn không làm bộ này trở thành dữ liệu sinh viên thật hoặc tự tạo ra bằng chứng đạt 95–99%.

Không dùng `style`, nhãn đề xuất, bằng chứng, điểm hoặc ghi chú chấm làm đầu vào dự đoán. Đầu vào model chỉ gồm câu hỏi, câu trả lời và ý rubric cần kiểm tra. Không chèn đáp án chuẩn vào phần lời sinh viên.

## Quy trình sử dụng

1. Giảng viên xem và xác nhận rubric, phạm vi nguồn và phân bổ điểm.
2. Xem từng câu trả lời, sửa nhãn/evidence/lý do khi cần. Các ô `reviewed_*` ban đầu đều trống.
3. Chỉ những câu trả lời đã duyệt đầy đủ mọi ý và có rubric được duyệt mới được xuất; câu còn mơ hồ tiếp tục giữ lại.
4. Xuất train/validation/test riêng, không xáo trộn lại nhóm câu hỏi. Regression-only không được xuất để học.
5. Huấn luyện một ứng viên riêng rồi kiểm tra lỗi câu sai bị cho đúng, nhận diện ý đúng, độ phủ tự chấm và độ trễ. Không tự thay model đang chạy.

Từ thư mục gốc dự án, có thể kiểm tra bằng:

```powershell
.\.test-venv\Scripts\python.exe tools\student_answer_dataset.py validate
```

Lệnh validate kiểm tra dữ liệu và nguồn, không yêu cầu tải trọng số model. Có thể dùng `python` của môi trường đã cài thay cho đường dẫn `.test-venv`. Chỉ thêm `--verify-production` trên đúng máy có các model và file gốc muốn kiểm tra; hash audit local không phải phụ thuộc để dùng bộ dữ liệu trên máy mới.

Sau khi có duyệt thực sự, xuất sang một thư mục mới:

```powershell
.\.test-venv\Scripts\python.exe tools\student_answer_dataset.py export-reviewed --output data\student_answer_reviewed_v1
```

Lệnh xuất hiện tại sẽ từ chối vì chưa có duyệt. Không đổi hàng loạt trạng thái thành approved chỉ để chạy huấn luyện. Các trường người duyệt ở bộ file offline chỉ là metadata, không thay thế phân quyền/chữ ký duyệt trong ứng dụng.

## Giới hạn quan trọng

Các diễn đạt nguồn về linked list, BST, 3NF, isolation, SQL/NoSQL, SRP, dynamic dispatch và A* có điều kiện hoặc có thể giản lược/trùng ý. Ghi chú đi kèm từng câu hỏi để giảng viên xác nhận trước khi dùng làm nhãn chuẩn.

Không có thay đổi frontend, model production, bộ đề được công bố hoặc dữ liệu phiên làm bài. Chưa huấn luyện model bằng bộ này. Bộ dữ liệu chưa được bộ chấm nào sử dụng để tự xác nhận chất lượng cho chính nó.
