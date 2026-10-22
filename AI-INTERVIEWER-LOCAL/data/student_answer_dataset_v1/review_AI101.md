# Bản đọc duyệt AI101

Nhãn và điểm đều là AI đề xuất; chưa có giảng viên duyệt.

## AI_001: Machine learning là gì?

Nhóm: `regression_only`. Nguồn mô tả cải thiện nhờ dữ liệu/kinh nghiệm. Draft hiểu là mục tiêu cải thiện tác vụ, không suy thành cứ thêm mọi loại dữ liệu là chất lượng luôn tăng.

- AI_001_R1.a1 (5.0 điểm dự thảo): Machine learning học quy luật từ dữ liệu thay vì viết thủ công từng luật.
- AI_001_R2.a1 (5.0 điểm dự thảo): Machine learning dùng dữ liệu hoặc kinh nghiệm để cải thiện khả năng thực hiện một tác vụ.

### AI_001_DRAFT_01 / natural_complete

Thay vì người lập trình viết hết từng tình huống, mình cho máy xem dữ liệu để rút quy luật. Máy tận dụng kinh nghiệm đó nhằm làm một công việc tốt hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `supported`. Bằng chứng: cho máy xem dữ liệu để rút quy luật
- AI_001_R2.a1: `supported`. Bằng chứng: tận dụng kinh nghiệm đó nhằm làm một công việc tốt hơn

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_02 / mixed_terminology

ML learn patterns từ data thay vì hand-code từng rule; mục tiêu là improve task performance nhờ data hoặc experience.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `supported`. Bằng chứng: learn patterns từ data thay vì hand-code từng rule
- AI_001_R2.a1: `supported`. Bằng chứng: improve task performance nhờ data hoặc experience

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_03 / partial_first

Em hiểu là để máy tự tìm quy luật từ các ví dụ dữ liệu, không viết sẵn tất cả các luật cho nó.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `supported`. Bằng chứng: tự tìm quy luật từ các ví dụ dữ liệu, không viết sẵn tất cả các luật
- AI_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_04 / partial_goal

Mục tiêu của machine learning là dùng kinh nghiệm hay dữ liệu để làm một nhiệm vụ ngày càng tốt hơn.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_001_R2.a1: `supported`. Bằng chứng: dùng kinh nghiệm hay dữ liệu để làm một nhiệm vụ ngày càng tốt hơn

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_05 / one_wrong_mechanism

ML chỉ là người viết toàn bộ luật if-else, máy không học quy luật từ dữ liệu. Nó vẫn hướng đến cải thiện khả năng thực hiện tác vụ nhờ kinh nghiệm.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `contradicted`. Bằng chứng: người viết toàn bộ luật if-else, máy không học quy luật từ dữ liệu
- AI_001_R2.a1: `supported`. Bằng chứng: cải thiện khả năng thực hiện tác vụ nhờ kinh nghiệm

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_06 / wrong_definition

Machine learning không học từ dữ liệu, chỉ chạy các luật người viết cố định. Dữ liệu và kinh nghiệm không có vai trò gì trong việc cải thiện tác vụ.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `contradicted`. Bằng chứng: không học từ dữ liệu, chỉ chạy các luật người viết cố định
- AI_001_R2.a1: `contradicted`. Bằng chứng: Dữ liệu và kinh nghiệm không có vai trò gì trong việc cải thiện tác vụ

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_07 / explicit_correction

Em nói chỉ có if-else là nhầm. ML tìm quy luật từ dữ liệu chứ không cần viết từng luật, rồi dùng kinh nghiệm để cải thiện việc thực hiện tác vụ.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `supported`. Bằng chứng: tìm quy luật từ dữ liệu chứ không cần viết từng luật
- AI_001_R2.a1: `supported`. Bằng chứng: dùng kinh nghiệm để cải thiện việc thực hiện tác vụ

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_08 / retract_correct_to_wrong

Em đã nói máy học quy luật từ dữ liệu nhưng rút lại. Em chốt ML không học từ dữ liệu, chỉ là viết sẵn toàn bộ luật thủ công.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `contradicted`. Bằng chứng: ML không học từ dữ liệu, chỉ là viết sẵn toàn bộ luật thủ công
- AI_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_09 / keywords_without_claim

Dữ liệu, kinh nghiệm, tác vụ và ML là các từ em nhớ, chưa nói được máy học gì hay cải thiện thế nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_001_DRAFT_10 / unresolved_conflict

ML tự học quy luật từ dữ liệu. ML không học quy luật mà chỉ dùng các luật viết sẵn. Em chưa chọn ý nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- AI_001_R1.a1: `needs_review`. Bằng chứng: ML tự học quy luật từ dữ liệu. ML không học quy luật mà chỉ dùng các luật viết sẵn. Em chưa chọn ý nào
- AI_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_002: Phân biệt học có giám sát và học không giám sát.

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_002_R1.a1 (5.0 điểm dự thảo): Học có giám sát dùng dữ liệu huấn luyện đã có nhãn đầu ra.
- AI_002_R2.a1 (2.5 điểm dự thảo): Học không giám sát dùng dữ liệu không có nhãn đầu ra.
- AI_002_R2.a2 (2.5 điểm dự thảo): Học không giám sát tìm cấu trúc ẩn, chẳng hạn các cụm, trong dữ liệu.

### AI_002_DRAFT_01 / natural_complete

Có giám sát thì ví dụ học đã đi kèm đáp án đúng. Không giám sát thì chưa gắn đáp án cho dữ liệu, máy tự tìm quy luật bên trong như chia những thứ giống nhau thành nhóm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `supported`. Bằng chứng: ví dụ học đã đi kèm đáp án đúng
- AI_002_R2.a1: `supported`. Bằng chứng: chưa gắn đáp án cho dữ liệu
- AI_002_R2.a2: `supported`. Bằng chứng: tự tìm quy luật bên trong như chia những thứ giống nhau thành nhóm

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_02 / mixed_terminology

Supervised train với labeled data. Unsupervised dùng unlabeled data để discover hidden structure hoặc clusters.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `supported`. Bằng chứng: Supervised train với labeled data
- AI_002_R2.a1: `supported`. Bằng chứng: Unsupervised dùng unlabeled data
- AI_002_R2.a2: `supported`. Bằng chứng: discover hidden structure hoặc clusters

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_03 / partial_first

Học có giám sát là khi mỗi mẫu huấn luyện có sẵn kết quả đích làm nhãn cho nó học.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `supported`. Bằng chứng: mỗi mẫu huấn luyện có sẵn kết quả đích làm nhãn
- AI_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_04 / partial_unsupervised

Không giám sát nhận các ví dụ chưa gắn nhãn đầu ra rồi tự tìm cấu trúc hay gom các nhóm tương tự.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a1: `supported`. Bằng chứng: các ví dụ chưa gắn nhãn đầu ra
- AI_002_R2.a2: `supported`. Bằng chứng: tự tìm cấu trúc hay gom các nhóm tương tự

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_05 / one_wrong_label_requirement

Có giám sát thì không dùng nhãn đầu ra. Không giám sát dùng dữ liệu chưa nhãn nhưng không tìm bất kỳ cấu trúc hay cụm nào trong dữ liệu.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `contradicted`. Bằng chứng: Có giám sát thì không dùng nhãn đầu ra
- AI_002_R2.a1: `supported`. Bằng chứng: Không giám sát dùng dữ liệu chưa nhãn
- AI_002_R2.a2: `contradicted`. Bằng chứng: không tìm bất kỳ cấu trúc hay cụm nào trong dữ liệu

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_06 / role_reversal

Theo em supervised bắt buộc không có nhãn, còn unsupervised bắt buộc có đáp án đích gán nhãn cho từng mẫu.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `contradicted`. Bằng chứng: supervised bắt buộc không có nhãn
- AI_002_R2.a1: `contradicted`. Bằng chứng: unsupervised bắt buộc có đáp án đích gán nhãn cho từng mẫu
- AI_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_07 / explicit_correction

Em vừa đảo nhãn, xin sửa. Supervised học trên mẫu có nhãn; unsupervised không có nhãn đầu ra và tự tìm cấu trúc như các cụm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `supported`. Bằng chứng: Supervised học trên mẫu có nhãn
- AI_002_R2.a1: `supported`. Bằng chứng: unsupervised không có nhãn đầu ra
- AI_002_R2.a2: `supported`. Bằng chứng: tự tìm cấu trúc như các cụm

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_08 / retract_correct_to_wrong

Em đã nói unsupervised không nhãn và tìm cấu trúc, nhưng rút lại. Em chốt nó bắt buộc có nhãn đích và không tìm cấu trúc ẩn hay phân cụm.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a1: `contradicted`. Bằng chứng: bắt buộc có nhãn đích
- AI_002_R2.a2: `contradicted`. Bằng chứng: không tìm cấu trúc ẩn hay phân cụm

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_09 / keywords_without_claim

Supervised, unsupervised, nhãn và cluster em chỉ nhớ các từ, chưa phân biệt loại nào dùng dữ liệu gì.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_002_DRAFT_10 / unresolved_conflict

Supervised học mẫu đã có nhãn. Supervised không dùng nhãn. Em chưa chọn được phát biểu cuối cùng.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- AI_002_R1.a1: `needs_review`. Bằng chứng: Supervised học mẫu đã có nhãn. Supervised không dùng nhãn. Em chưa chọn được phát biểu cuối cùng
- AI_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_003: Neural network (mạng nơ-ron) hoạt động như thế nào?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_003_R1.a1 (4.0 điểm dự thảo): Mạng nơ-ron tổ chức các nơ-ron thành lớp đầu vào, lớp ẩn và lớp đầu ra.
- AI_003_R2.a1 (4.0 điểm dự thảo): Trong huấn luyện, lan truyền ngược giúp điều chỉnh trọng số.
- AI_003_R3.a1 (2.0 điểm dự thảo): Hàm kích hoạt phi tuyến giúp mạng học quan hệ phức tạp.

### AI_003_DRAFT_01 / natural_complete

Các nơ-ron được xếp thành tầng nhận vào, tầng ẩn và tầng trả kết quả. Khi học, sai số truyền ngược để chỉnh các trọng số. Hàm kích hoạt không tuyến tính giúp học những liên hệ phức tạp.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `supported`. Bằng chứng: tầng nhận vào, tầng ẩn và tầng trả kết quả
- AI_003_R2.a1: `supported`. Bằng chứng: sai số truyền ngược để chỉnh các trọng số
- AI_003_R3.a1: `supported`. Bằng chứng: Hàm kích hoạt không tuyến tính giúp học những liên hệ phức tạp

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_02 / mixed_terminology

Network có input, hidden, output layers; backpropagation hỗ trợ update weights, và nonlinear activation giúp học complex relations.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `supported`. Bằng chứng: input, hidden, output layers
- AI_003_R2.a1: `supported`. Bằng chứng: backpropagation hỗ trợ update weights
- AI_003_R3.a1: `supported`. Bằng chứng: nonlinear activation giúp học complex relations

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_03 / partial_first

Các nơ-ron nối thành những lớp: đầu vào, lớp ẩn rồi đầu ra.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `supported`. Bằng chứng: lớp: đầu vào, lớp ẩn rồi đầu ra
- AI_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_04 / partial_training

Em biết lúc train có lan truyền ngược để điều chỉnh các trọng số trong mạng.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R2.a1: `supported`. Bằng chứng: lan truyền ngược để điều chỉnh các trọng số
- AI_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_05 / one_wrong_training

Mạng có tầng vào, ẩn và ra. Khi học thì trọng số giữ cố định, lan truyền ngược không điều chỉnh được gì. Activation phi tuyến giúp học quan hệ phức tạp.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `supported`. Bằng chứng: tầng vào, ẩn và ra
- AI_003_R2.a1: `contradicted`. Bằng chứng: trọng số giữ cố định, lan truyền ngược không điều chỉnh được gì
- AI_003_R3.a1: `supported`. Bằng chứng: Activation phi tuyến giúp học quan hệ phức tạp

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_06 / wrong_mechanism

Lan truyền ngược không tham gia điều chỉnh trọng số. Chỉ các hàm kích hoạt tuyến tính mới giúp học quan hệ phi tuyến phức tạp, hàm phi tuyến không giúp được.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R2.a1: `contradicted`. Bằng chứng: Lan truyền ngược không tham gia điều chỉnh trọng số
- AI_003_R3.a1: `contradicted`. Bằng chứng: hàm phi tuyến không giúp được

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_07 / explicit_correction

Em nói trọng số không đổi là nhầm. Mạng gồm các lớp vào, ẩn, ra; học có backprop chỉnh trọng số và dùng kích hoạt phi tuyến để biểu diễn quan hệ phức tạp.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `supported`. Bằng chứng: các lớp vào, ẩn, ra
- AI_003_R2.a1: `supported`. Bằng chứng: backprop chỉnh trọng số
- AI_003_R3.a1: `supported`. Bằng chứng: kích hoạt phi tuyến để biểu diễn quan hệ phức tạp

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_08 / retract_correct_to_wrong

Em đã nói backprop giúp chỉnh trọng số, nhưng em rút lại. Kết luận của em là lan truyền ngược không liên quan tới việc điều chỉnh trọng số khi học.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R2.a1: `contradicted`. Bằng chứng: lan truyền ngược không liên quan tới việc điều chỉnh trọng số khi học
- AI_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_09 / keywords_without_claim

Neuron, layer, weights, backprop, activation em đọc lại tên thôi, chưa trình bày cấu trúc hoặc vai trò.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_003_DRAFT_10 / unresolved_conflict

Lan truyền ngược giúp chỉnh trọng số. Lan truyền ngược không giúp chỉnh trọng số. Em chưa quyết định ý nào đúng.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- AI_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_003_R2.a1: `needs_review`. Bằng chứng: Lan truyền ngược giúp chỉnh trọng số. Lan truyền ngược không giúp chỉnh trọng số. Em chưa quyết định ý nào đúng
- AI_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_004: Gradient descent dùng để làm gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_004_R1.a1 (4.0 điểm dự thảo): Gradient descent nhằm tối thiểu hóa hàm mất mát.
- AI_004_R2.a1 (3.0 điểm dự thảo): Bước cập nhật tham số của gradient descent đi ngược hướng gradient.
- AI_004_R3.a1 (3.0 điểm dự thảo): Learning rate quyết định độ lớn bước cập nhật.

### AI_004_DRAFT_01 / natural_complete

Mục tiêu là kéo giá trị lỗi xuống thấp. Mỗi lần chỉnh tham số đi ngược chiều gradient, còn learning rate cho biết bước chỉnh dài hay ngắn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `supported`. Bằng chứng: kéo giá trị lỗi xuống thấp
- AI_004_R2.a1: `supported`. Bằng chứng: chỉnh tham số đi ngược chiều gradient
- AI_004_R3.a1: `supported`. Bằng chứng: learning rate cho biết bước chỉnh dài hay ngắn

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_02 / mixed_terminology

Gradient descent minimize loss, update parameters theo negative gradient và learning rate scale step size.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `supported`. Bằng chứng: minimize loss
- AI_004_R2.a1: `supported`. Bằng chứng: update parameters theo negative gradient
- AI_004_R3.a1: `supported`. Bằng chứng: learning rate scale step size

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_03 / partial_first

Nó là cách tìm tham số để giảm hàm mất mát, hướng tới giá trị nhỏ nhất.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `supported`. Bằng chứng: giảm hàm mất mát, hướng tới giá trị nhỏ nhất
- AI_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_04 / partial_update

Cập nhật ngược hướng gradient; độ lớn bước được điều khiển bởi learning rate.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R2.a1: `supported`. Bằng chứng: Cập nhật ngược hướng gradient
- AI_004_R3.a1: `supported`. Bằng chứng: độ lớn bước được điều khiển bởi learning rate

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_05 / one_wrong_direction

Nó giảm loss nhưng đi cùng chiều gradient, không đi ngược. Learning rate vẫn điều khiển độ lớn bước.

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `supported`. Bằng chứng: giảm loss
- AI_004_R2.a1: `contradicted`. Bằng chứng: đi cùng chiều gradient, không đi ngược
- AI_004_R3.a1: `supported`. Bằng chứng: Learning rate vẫn điều khiển độ lớn bước

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_06 / wrong_goal_and_update

Gradient descent nhằm làm loss lớn nhất. Tham số cập nhật cùng chiều gradient và learning rate không ảnh hưởng gì tới kích thước bước.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `contradicted`. Bằng chứng: nhằm làm loss lớn nhất
- AI_004_R2.a1: `contradicted`. Bằng chứng: cập nhật cùng chiều gradient
- AI_004_R3.a1: `contradicted`. Bằng chứng: learning rate không ảnh hưởng gì tới kích thước bước

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_07 / explicit_correction

Em nói đi cùng gradient là sai. Chốt lại giảm hàm mất mát, đi ngược gradient, learning rate quyết định độ dài bước cập nhật.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `supported`. Bằng chứng: giảm hàm mất mát
- AI_004_R2.a1: `supported`. Bằng chứng: đi ngược gradient
- AI_004_R3.a1: `supported`. Bằng chứng: learning rate quyết định độ dài bước cập nhật

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_08 / retract_correct_to_wrong

Em đã nói trừ theo gradient nhưng rút lại. Em chốt gradient descent phải cập nhật cùng chiều gradient, không phải chiều ngược.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R2.a1: `contradicted`. Bằng chứng: phải cập nhật cùng chiều gradient, không phải chiều ngược
- AI_004_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_09 / keywords_without_claim

Loss, gradient, learning rate và tham số em chỉ nhớ tên, chưa nêu chiều cập nhật hay vai trò.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_004_DRAFT_10 / unresolved_conflict

Gradient descent cập nhật ngược gradient. Gradient descent cập nhật cùng gradient. Em chưa quyết định chọn hướng nào.

Khoảng điểm đề xuất: 0.0–3.0/10. Không phải điểm đã duyệt.

- AI_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_004_R2.a1: `needs_review`. Bằng chứng: Gradient descent cập nhật ngược gradient. Gradient descent cập nhật cùng gradient. Em chưa quyết định chọn hướng nào
- AI_004_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_005: Vì sao cần chia dữ liệu thành tập train, validation và test?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_005_R1.a1 (3.0 điểm dự thảo): Tập train dùng để học tham số mô hình.
- AI_005_R2.a1 (4.0 điểm dự thảo): Tập validation dùng để chọn mô hình hoặc tinh chỉnh siêu tham số.
- AI_005_R3.a1 (3.0 điểm dự thảo): Tập test giữ riêng để đánh giá khách quan mô hình sau khi chốt lựa chọn.

### AI_005_DRAFT_01 / natural_complete

Phần train đưa vào cho mô hình học các tham số. Validation để so các cấu hình và chọn cái tốt. Test cất riêng đến khi đã chọn xong mới dùng báo chất lượng khách quan.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `supported`. Bằng chứng: train đưa vào cho mô hình học các tham số
- AI_005_R2.a1: `supported`. Bằng chứng: Validation để so các cấu hình và chọn cái tốt
- AI_005_R3.a1: `supported`. Bằng chứng: Test cất riêng đến khi đã chọn xong mới dùng báo chất lượng khách quan

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_02 / mixed_terminology

Training set fit weights; validation set select model và tune hyperparameters; test set held out cho final unbiased evaluation sau khi chốt model.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `supported`. Bằng chứng: Training set fit weights
- AI_005_R2.a1: `supported`. Bằng chứng: validation set select model và tune hyperparameters
- AI_005_R3.a1: `supported`. Bằng chứng: test set held out cho final unbiased evaluation sau khi chốt model

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_03 / partial_first

Em chỉ nêu được train là phần dữ liệu dùng để mô hình học tham số.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `supported`. Bằng chứng: train là phần dữ liệu dùng để mô hình học tham số
- AI_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_04 / partial_validation_test

Mình chọn cấu hình bằng validation. Sau khi chọn xong mới dùng test giữ riêng để đo chất lượng cuối.

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R2.a1: `supported`. Bằng chứng: chọn cấu hình bằng validation
- AI_005_R3.a1: `supported`. Bằng chứng: Sau khi chọn xong mới dùng test giữ riêng để đo chất lượng cuối

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_05 / one_wrong_test_usage

Train học trọng số, validation chọn siêu tham số, còn test cũng được dùng liên tục để chọn mô hình thay vì giữ riêng tới cuối.

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `supported`. Bằng chứng: Train học trọng số
- AI_005_R2.a1: `supported`. Bằng chứng: validation chọn siêu tham số
- AI_005_R3.a1: `contradicted`. Bằng chứng: test cũng được dùng liên tục để chọn mô hình thay vì giữ riêng tới cuối

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_06 / role_reversal

Validation chỉ dùng báo kết quả cuối, tuyệt đối không chọn cấu hình. Test mới dùng tune siêu tham số liên tục và không cần để riêng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R2.a1: `contradicted`. Bằng chứng: Validation chỉ dùng báo kết quả cuối, tuyệt đối không chọn cấu hình
- AI_005_R3.a1: `contradicted`. Bằng chứng: Test mới dùng tune siêu tham số liên tục và không cần để riêng

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_07 / explicit_correction

Em nhầm test với validation. Sửa lại train học tham số, validation chọn mô hình và cấu hình, test chỉ đánh giá khách quan sau khi đã chốt.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `supported`. Bằng chứng: train học tham số
- AI_005_R2.a1: `supported`. Bằng chứng: validation chọn mô hình và cấu hình
- AI_005_R3.a1: `supported`. Bằng chứng: test chỉ đánh giá khách quan sau khi đã chốt

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_08 / retract_correct_to_wrong

Em đã nói phải giữ test riêng đến cuối, nhưng rút lại. Em chốt cứ dùng test liên tục để chọn siêu tham số và model.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R3.a1: `contradicted`. Bằng chứng: dùng test liên tục để chọn siêu tham số và model

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_09 / keywords_without_claim

Train, validation, test và hyperparameters là mấy tên em nhớ, chưa nói được phần nào làm gì.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_005_DRAFT_10 / unresolved_conflict

Test chỉ dùng sau khi đã chốt mô hình. Test phải dùng nhiều lần để chọn mô hình. Em chưa biết nên giữ câu nào.

Khoảng điểm đề xuất: 0.0–3.0/10. Không phải điểm đã duyệt.

- AI_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_005_R3.a1: `needs_review`. Bằng chứng: Test chỉ dùng sau khi đã chốt mô hình. Test phải dùng nhiều lần để chọn mô hình. Em chưa biết nên giữ câu nào

Ghi chú người duyệt: ____________________

## AI_006: Deep learning khác machine learning truyền thống ở điểm nào?

Nhóm: `validation`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_006_R1.a1 (4.0 điểm dự thảo): Deep learning sử dụng mạng nơ-ron nhiều lớp sâu.
- AI_006_R2.a1 (4.0 điểm dự thảo): Deep learning học đặc trưng từ dữ liệu thô thay vì chỉ thiết kế thủ công.
- AI_006_R3.a1 (2.0 điểm dự thảo): Deep learning thường cần nhiều dữ liệu và sức mạnh tính toán.

### AI_006_DRAFT_01 / natural_complete

Nó dùng mạng nơ-ron có nhiều tầng sâu. Các đặc trưng được rút ra từ dữ liệu ban đầu chứ không phải con người tự viết hết. Việc học thường đòi nhiều dữ liệu và năng lực tính toán lớn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `supported`. Bằng chứng: mạng nơ-ron có nhiều tầng sâu
- AI_006_R2.a1: `supported`. Bằng chứng: đặc trưng được rút ra từ dữ liệu ban đầu chứ không phải con người tự viết hết
- AI_006_R3.a1: `supported`. Bằng chứng: thường đòi nhiều dữ liệu và năng lực tính toán lớn

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_02 / mixed_terminology

Deep learning dùng deep neural nets, learn features từ raw data, và thường cần large datasets cùng compute như GPU.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `supported`. Bằng chứng: dùng deep neural nets
- AI_006_R2.a1: `supported`. Bằng chứng: learn features từ raw data
- AI_006_R3.a1: `supported`. Bằng chứng: thường cần large datasets cùng compute như GPU

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_03 / partial_first

Đặc điểm em biết là dùng mạng nơ-ron nhiều lớp sâu.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `supported`. Bằng chứng: dùng mạng nơ-ron nhiều lớp sâu
- AI_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_04 / partial_features

Nó có thể tự học các đặc trưng trực tiếp từ dữ liệu thô, không phải thiết kế hết đặc trưng bằng tay.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R2.a1: `supported`. Bằng chứng: tự học các đặc trưng trực tiếp từ dữ liệu thô, không phải thiết kế hết đặc trưng bằng tay
- AI_006_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_05 / one_wrong_feature_source

Deep learning dùng mạng nhiều lớp, nhưng các đặc trưng bắt buộc do người thiết kế hết, mạng không học được từ dữ liệu thô. Nó thường cần nhiều dữ liệu và compute.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `supported`. Bằng chứng: dùng mạng nhiều lớp
- AI_006_R2.a1: `contradicted`. Bằng chứng: các đặc trưng bắt buộc do người thiết kế hết, mạng không học được từ dữ liệu thô
- AI_006_R3.a1: `supported`. Bằng chứng: thường cần nhiều dữ liệu và compute

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_06 / wrong_generalization

Deep learning không sử dụng mạng sâu. Nó không học đặc trưng từ dữ liệu thô, và trong mọi trường hợp không bao giờ cần nhiều dữ liệu hay sức tính toán.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `contradicted`. Bằng chứng: không sử dụng mạng sâu
- AI_006_R2.a1: `contradicted`. Bằng chứng: không học đặc trưng từ dữ liệu thô
- AI_006_R3.a1: `contradicted`. Bằng chứng: không bao giờ cần nhiều dữ liệu hay sức tính toán

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_07 / explicit_correction

Em nói phải làm hết đặc trưng bằng tay là sai. Deep learning dùng mạng nơ-ron sâu, học đặc trưng từ dữ liệu thô, thường cần dữ liệu và tính toán mạnh.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `supported`. Bằng chứng: dùng mạng nơ-ron sâu
- AI_006_R2.a1: `supported`. Bằng chứng: học đặc trưng từ dữ liệu thô
- AI_006_R3.a1: `supported`. Bằng chứng: thường cần dữ liệu và tính toán mạnh

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_08 / retract_correct_to_wrong

Em đã nói mô hình tự học đặc trưng nhưng rút lại. Em chốt deep learning chỉ dùng đặc trưng thiết kế tay và không thể học đặc trưng từ dữ liệu thô.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R2.a1: `contradicted`. Bằng chứng: chỉ dùng đặc trưng thiết kế tay và không thể học đặc trưng từ dữ liệu thô
- AI_006_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_09 / keywords_without_claim

Em nhớ deep, layer, feature, data, GPU nhưng chưa nối thành một đặc điểm của deep learning.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_006_DRAFT_10 / unresolved_conflict

Deep learning học đặc trưng từ dữ liệu thô. Deep learning không thể học đặc trưng từ dữ liệu thô. Em chưa kết luận được.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- AI_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_006_R2.a1: `needs_review`. Bằng chứng: Deep learning học đặc trưng từ dữ liệu thô. Deep learning không thể học đặc trưng từ dữ liệu thô. Em chưa kết luận được
- AI_006_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_007: Thuật toán tìm kiếm A* hoạt động ra sao?

Nhóm: `train`. Nguồn nêu heuristic admissible. Phạm vi bảo đảm tối ưu còn phụ thuộc biến thể A* và cách xử lý graph search; cần giảng viên xác nhận cách hiểu theo bài học, không coi draft là định lý cho mọi triển khai.

- AI_007_R1.a1 (5.0 điểm dự thảo): A* ưu tiên nút có f(n)=g(n)+h(n) nhỏ nhất.
- AI_007_R2.a1 (5.0 điểm dự thảo): Theo điều kiện tối ưu nêu trong nguồn, heuristic không đánh giá quá chi phí thực.

### AI_007_DRAFT_01 / natural_complete

Cộng chi phí đã đi với phần ước lượng còn lại, chọn nút có tổng nhỏ nhất. Ước lượng không được cao quá chi phí thật trong điều kiện bảo đảm tối ưu đang học.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `supported`. Bằng chứng: Cộng chi phí đã đi với phần ước lượng còn lại, chọn nút có tổng nhỏ nhất
- AI_007_R2.a1: `supported`. Bằng chứng: Ước lượng không được cao quá chi phí thật

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_02 / mixed_terminology

A-star expand node có minimum f=g+h. Heuristic admissible, tức không overestimate true cost, theo điều kiện tối ưu của bài.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `supported`. Bằng chứng: minimum f=g+h
- AI_007_R2.a1: `supported`. Bằng chứng: không overestimate true cost

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_03 / partial_first

A* so giá trị f bằng g cộng h, nút nào nhỏ nhất thì được chọn trước.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `supported`. Bằng chứng: f bằng g cộng h, nút nào nhỏ nhất thì được chọn trước
- AI_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_04 / partial_last

Em nhớ điều kiện của heuristic là không đánh giá chi phí cao hơn chi phí thật tới đích.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_007_R2.a1: `supported`. Bằng chứng: không đánh giá chi phí cao hơn chi phí thật tới đích

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_05 / one_wrong_priority

A* chọn tổng g+h lớn nhất chứ không nhỏ nhất. Heuristic vẫn không được vượt chi phí thật.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `contradicted`. Bằng chứng: chọn tổng g+h lớn nhất chứ không nhỏ nhất
- AI_007_R2.a1: `supported`. Bằng chứng: Heuristic vẫn không được vượt chi phí thật

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_06 / wrong_priority_and_condition

A* ưu tiên f=g+h lớn nhất. Muốn tối ưu thì heuristic bắt buộc đánh giá cao hơn chi phí thực.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `contradicted`. Bằng chứng: ưu tiên f=g+h lớn nhất
- AI_007_R2.a1: `contradicted`. Bằng chứng: heuristic bắt buộc đánh giá cao hơn chi phí thực

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_07 / explicit_correction

Em nhầm lớn nhất với nhỏ nhất. A* lấy nút có g+h nhỏ nhất, heuristic theo điều kiện đang học không được vượt chi phí thật.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `supported`. Bằng chứng: lấy nút có g+h nhỏ nhất
- AI_007_R2.a1: `supported`. Bằng chứng: không được vượt chi phí thật

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_08 / retract_correct_to_wrong

Em đã nói h không được đánh giá quá, nhưng rút lại. Em kết luận điều kiện tối ưu là h bắt buộc lớn hơn chi phí thực.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_007_R2.a1: `contradicted`. Bằng chứng: điều kiện tối ưu là h bắt buộc lớn hơn chi phí thực

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_09 / keywords_without_claim

A*, g, h, f và heuristic em chỉ nhớ tên, chưa nêu công thức chọn hoặc điều kiện của ước lượng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_007_DRAFT_10 / unresolved_conflict

A* lấy g+h nhỏ nhất. A* lấy g+h lớn nhất. Em chưa chọn được một ý làm kết luận.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- AI_007_R1.a1: `needs_review`. Bằng chứng: A* lấy g+h nhỏ nhất. A* lấy g+h lớn nhất. Em chưa chọn được một ý làm kết luận
- AI_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_008: Precision và recall khác nhau như thế nào?

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_008_R1.a1 (5.0 điểm dự thảo): Precision là số dự đoán dương đúng chia cho tổng số dự đoán dương.
- AI_008_R2.a1 (5.0 điểm dự thảo): Recall là số ca dương thật được tìm ra chia cho tổng số ca dương thật.

### AI_008_DRAFT_01 / natural_complete

Precision hỏi trong những ca máy báo dương thì bao nhiêu ca thực sự đúng. Recall hỏi trong toàn bộ ca thật sự dương, máy đã tìm được bao nhiêu.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `supported`. Bằng chứng: trong những ca máy báo dương thì bao nhiêu ca thực sự đúng
- AI_008_R2.a1: `supported`. Bằng chứng: trong toàn bộ ca thật sự dương, máy đã tìm được bao nhiêu

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_02 / mixed_terminology

Precision bằng TP/(TP+FP), mẫu số là predicted positives. Recall bằng TP/(TP+FN), mẫu số là actual positives.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `supported`. Bằng chứng: Precision bằng TP/(TP+FP), mẫu số là predicted positives
- AI_008_R2.a1: `supported`. Bằng chứng: Recall bằng TP/(TP+FN), mẫu số là actual positives

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_03 / partial_first

Precision lấy số dự đoán dương đúng chia cho tất cả những dự đoán dương của mô hình.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `supported`. Bằng chứng: số dự đoán dương đúng chia cho tất cả những dự đoán dương
- AI_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_04 / partial_last

Recall là phần ca dương thực tế đã được phát hiện trên tổng số ca dương thực tế.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_008_R2.a1: `supported`. Bằng chứng: ca dương thực tế đã được phát hiện trên tổng số ca dương thực tế

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_05 / one_wrong_denominator

Precision là TP trên TP cộng FN, tức dùng tổng dương thật làm mẫu số. Recall cũng TP trên TP cộng FN.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `contradicted`. Bằng chứng: Precision là TP trên TP cộng FN, tức dùng tổng dương thật làm mẫu số
- AI_008_R2.a1: `supported`. Bằng chứng: Recall cũng TP trên TP cộng FN

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_06 / role_reversal

Em gán precision cho TP/(TP+FN), recall cho TP/(TP+FP), chứ không phải ngược lại.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `contradicted`. Bằng chứng: precision cho TP/(TP+FN)
- AI_008_R2.a1: `contradicted`. Bằng chứng: recall cho TP/(TP+FP)

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_07 / explicit_correction

Em vừa đảo hai mẫu số. Sửa lại precision là TP/(TP+FP), trên tổng dự đoán dương; recall TP/(TP+FN), trên tổng dương thật.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `supported`. Bằng chứng: precision là TP/(TP+FP), trên tổng dự đoán dương
- AI_008_R2.a1: `supported`. Bằng chứng: recall TP/(TP+FN), trên tổng dương thật

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_08 / retract_correct_to_wrong

Em đã trả lời recall là TP/(TP+FN), nhưng xin rút lại. Em chốt recall lấy TP/(TP+FP), mẫu số là các dự đoán dương.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_008_R2.a1: `contradicted`. Bằng chứng: recall lấy TP/(TP+FP), mẫu số là các dự đoán dương

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_09 / keywords_without_claim

Precision, recall, TP, FP, FN em chỉ nhớ tên, chưa nói tử số hay mẫu số của tỷ lệ nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_008_DRAFT_10 / unresolved_conflict

Precision là TP/(TP+FP). Precision là TP/(TP+FN). Em chưa chọn công thức nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- AI_008_R1.a1: `needs_review`. Bằng chứng: Precision là TP/(TP+FP). Precision là TP/(TP+FN). Em chưa chọn công thức nào
- AI_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## AI_009: Reinforcement learning (học tăng cường) là gì?

Nhóm: `validation`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_009_R1.a1 (4.0 điểm dự thảo): Agent tương tác với môi trường bằng hành động và quan sát trạng thái.
- AI_009_R2.a1 (6.0 điểm dự thảo): Agent học chính sách nhằm tối đa hóa tổng phần thưởng tích lũy.

### AI_009_DRAFT_01 / natural_complete

Tác tử làm hành động trong môi trường rồi nhìn trạng thái nhận được. Nó học cách chọn hành động sao cho tổng thưởng thu được qua quá trình lớn nhất.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `supported`. Bằng chứng: làm hành động trong môi trường rồi nhìn trạng thái nhận được
- AI_009_R2.a1: `supported`. Bằng chứng: học cách chọn hành động sao cho tổng thưởng thu được qua quá trình lớn nhất

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_02 / mixed_terminology

Agent interacts với environment bằng actions và observed states; learn policy để maximize cumulative reward.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `supported`. Bằng chứng: interacts với environment bằng actions và observed states
- AI_009_R2.a1: `supported`. Bằng chứng: learn policy để maximize cumulative reward

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_03 / partial_first

Agent quan sát trạng thái môi trường và tác động lại bằng các hành động của nó.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `supported`. Bằng chứng: quan sát trạng thái môi trường và tác động lại bằng các hành động
- AI_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_04 / partial_last

Mục tiêu là học một chính sách để tổng phần thưởng tích lũy nhận được lớn nhất.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_009_R2.a1: `supported`. Bằng chứng: học một chính sách để tổng phần thưởng tích lũy nhận được lớn nhất

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_05 / one_wrong_objective

Agent có hành động và quan sát trạng thái môi trường, nhưng học chính sách để tổng thưởng tích lũy càng nhỏ càng tốt.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `supported`. Bằng chứng: có hành động và quan sát trạng thái môi trường
- AI_009_R2.a1: `contradicted`. Bằng chứng: tổng thưởng tích lũy càng nhỏ càng tốt

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_06 / wrong_interaction_and_goal

Agent không bao giờ tương tác hay quan sát môi trường. Nó học chính sách nhằm tối thiểu hóa tổng phần thưởng tích lũy.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `contradicted`. Bằng chứng: không bao giờ tương tác hay quan sát môi trường
- AI_009_R2.a1: `contradicted`. Bằng chứng: nhằm tối thiểu hóa tổng phần thưởng tích lũy

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_07 / explicit_correction

Em nhầm giảm thưởng với tăng thưởng. Agent tương tác môi trường bằng hành động và quan sát trạng thái; chính sách học được nhằm tối đa tổng thưởng tích lũy.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `supported`. Bằng chứng: tương tác môi trường bằng hành động và quan sát trạng thái
- AI_009_R2.a1: `supported`. Bằng chứng: nhằm tối đa tổng thưởng tích lũy

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_08 / retract_correct_to_wrong

Em đã nói tối đa thưởng nhưng rút lại. Em chốt học tăng cường tối thiểu hóa tổng thưởng tích lũy, không tối đa hóa.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_009_R2.a1: `contradicted`. Bằng chứng: tối thiểu hóa tổng thưởng tích lũy, không tối đa hóa

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_09 / keywords_without_claim

Em nhớ agent, environment, action, state, reward nhưng chưa diễn đạt quan hệ hay mục tiêu học.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_009_DRAFT_10 / unresolved_conflict

Agent tối đa hóa tổng thưởng. Agent tối thiểu hóa tổng thưởng. Em chưa xác định mục tiêu cuối cùng.

Khoảng điểm đề xuất: 0.0–6.0/10. Không phải điểm đã duyệt.

- AI_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_009_R2.a1: `needs_review`. Bằng chứng: Agent tối đa hóa tổng thưởng. Agent tối thiểu hóa tổng thưởng. Em chưa xác định mục tiêu cuối cùng

Ghi chú người duyệt: ____________________

## AI_010: Cơ chế self-attention trong Transformer làm gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- AI_010_R1.a1 (4.0 điểm dự thảo): Mỗi token xét mức độ liên quan với mọi token khác trong chuỗi.
- AI_010_R2.a1 (2.0 điểm dự thảo): Trọng số attention được tính từ query và key.
- AI_010_R2.a2 (2.0 điểm dự thảo): Attention dùng các trọng số để lấy tổng có trọng số của value.
- AI_010_R3.a1 (2.0 điểm dự thảo): Self-attention có thể xử lý song song toàn chuỗi, khác xử lý tuần tự của RNN.

### AI_010_DRAFT_01 / natural_complete

Mỗi từ nhìn mức liên quan tới các từ khác trong chuỗi. Từ query và key tính ra trọng số, rồi dùng trọng số ấy cộng các value lại. Các vị trí tính song song được, không phải lần lượt như RNN.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `supported`. Bằng chứng: Mỗi từ nhìn mức liên quan tới các từ khác trong chuỗi
- AI_010_R2.a1: `supported`. Bằng chứng: Từ query và key tính ra trọng số
- AI_010_R2.a2: `supported`. Bằng chứng: dùng trọng số ấy cộng các value lại
- AI_010_R3.a1: `supported`. Bằng chứng: Các vị trí tính song song được, không phải lần lượt như RNN

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_02 / mixed_terminology

Mỗi token attend tới mọi token; Q và K tạo attention weights, weights dùng cho weighted sum of V. Self-attention xử lý parallel, khác RNN sequential.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `supported`. Bằng chứng: Mỗi token attend tới mọi token
- AI_010_R2.a1: `supported`. Bằng chứng: Q và K tạo attention weights
- AI_010_R2.a2: `supported`. Bằng chứng: weighted sum of V
- AI_010_R3.a1: `supported`. Bằng chứng: xử lý parallel, khác RNN sequential

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_03 / partial_first

Một token có thể xét độ liên quan của nó với mọi token còn lại trong cùng chuỗi.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `supported`. Bằng chứng: xét độ liên quan của nó với mọi token còn lại trong cùng chuỗi
- AI_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_04 / partial_computation

Query với key tạo ra các trọng số, dùng chúng lấy tổng có trọng số của các value.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a1: `supported`. Bằng chứng: Query với key tạo ra các trọng số
- AI_010_R2.a2: `supported`. Bằng chứng: dùng chúng lấy tổng có trọng số của các value
- AI_010_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_05 / one_wrong_computation

Token xét mọi token trong chuỗi. Trọng số chỉ tính từ value, không dùng query hay key; sau đó tổng có trọng số của value được tính. Nó cho phép tính song song khác RNN.

Khoảng điểm đề xuất: 8.0–8.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `supported`. Bằng chứng: Token xét mọi token trong chuỗi
- AI_010_R2.a1: `contradicted`. Bằng chứng: Trọng số chỉ tính từ value, không dùng query hay key
- AI_010_R2.a2: `supported`. Bằng chứng: tổng có trọng số của value được tính
- AI_010_R3.a1: `supported`. Bằng chứng: cho phép tính song song khác RNN

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_06 / wrong_scope_and_parallelism

Self-attention không bao giờ nhìn token khác, chỉ được nhìn chính token đó. Nó bắt buộc tính lần lượt từng vị trí, không thể song song như RNN.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `contradicted`. Bằng chứng: không bao giờ nhìn token khác, chỉ được nhìn chính token đó
- AI_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R3.a1: `contradicted`. Bằng chứng: bắt buộc tính lần lượt từng vị trí, không thể song song

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_07 / explicit_correction

Em nói nó giống RNN chạy tuần tự là sai. Token xét các token khác; trọng số ra từ query với key để cộng có trọng số các value. Tính được song song toàn chuỗi, khác RNN tuần tự.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `supported`. Bằng chứng: Token xét các token khác
- AI_010_R2.a1: `supported`. Bằng chứng: trọng số ra từ query với key
- AI_010_R2.a2: `supported`. Bằng chứng: cộng có trọng số các value
- AI_010_R3.a1: `supported`. Bằng chứng: Tính được song song toàn chuỗi, khác RNN tuần tự

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_08 / retract_correct_to_wrong

Em đã nói self-attention xử lý song song nhưng xin rút lại. Em chốt nó buộc chạy tuần tự từng token và không có khả năng xử lý song song toàn chuỗi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R3.a1: `contradicted`. Bằng chứng: buộc chạy tuần tự từng token và không có khả năng xử lý song song toàn chuỗi

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_09 / keywords_without_claim

Token, query, key, value, attention, parallel em chỉ đọc thuật ngữ, chưa giải thích cách tính hay cách xử lý.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### AI_010_DRAFT_10 / unresolved_conflict

Self-attention tính song song toàn chuỗi. Self-attention không thể tính song song toàn chuỗi. Em chưa kết luận được.

Khoảng điểm đề xuất: 0.0–2.0/10. Không phải điểm đã duyệt.

- AI_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- AI_010_R3.a1: `needs_review`. Bằng chứng: Self-attention tính song song toàn chuỗi. Self-attention không thể tính song song toàn chuỗi. Em chưa kết luận được

Ghi chú người duyệt: ____________________
