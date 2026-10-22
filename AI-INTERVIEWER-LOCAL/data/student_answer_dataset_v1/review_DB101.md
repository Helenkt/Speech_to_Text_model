# Bản đọc duyệt DB101

Nhãn và điểm đều là AI đề xuất; chưa có giảng viên duyệt.

## DB_001: Khóa chính (primary key) là gì?

Nhóm: `regression_only`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DB_001_R1.a1 (5.0 điểm dự thảo): Khóa chính định danh duy nhất mỗi bản ghi.
- DB_001_R2.a1 (3.0 điểm dự thảo): Giá trị khóa chính không được NULL.
- DB_001_R3.a1 (1.0 điểm dự thảo): Mỗi bảng có tối đa một ràng buộc khóa chính.
- DB_001_R3.a2 (1.0 điểm dự thảo): Một khóa chính có thể gồm nhiều cột.

### DB_001_DRAFT_01 / natural_complete

Khóa chính phân biệt từng dòng, không hai dòng trùng khóa và giá trị khóa không được thiếu. Mỗi bảng chỉ có tối đa một khóa chính, nhưng khóa đó có thể ghép từ mấy cột.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `supported`. Bằng chứng: phân biệt từng dòng, không hai dòng trùng khóa
- DB_001_R2.a1: `supported`. Bằng chứng: giá trị khóa không được thiếu
- DB_001_R3.a1: `supported`. Bằng chứng: Mỗi bảng chỉ có tối đa một khóa chính
- DB_001_R3.a2: `supported`. Bằng chứng: khóa đó có thể ghép từ mấy cột

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_02 / mixed_terminology

Primary key uniquely identifies một record và phải NOT NULL. Một table có tối đa một primary-key constraint; composite primary key có thể chứa nhiều columns.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `supported`. Bằng chứng: uniquely identifies một record
- DB_001_R2.a1: `supported`. Bằng chứng: phải NOT NULL
- DB_001_R3.a1: `supported`. Bằng chứng: tối đa một primary-key constraint
- DB_001_R3.a2: `supported`. Bằng chứng: composite primary key có thể chứa nhiều columns

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_03 / partial_first

Đó là một mã không trùng để nhận ra từng bản ghi riêng biệt trong bảng.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `supported`. Bằng chứng: một mã không trùng để nhận ra từng bản ghi riêng biệt
- DB_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_04 / partial_nullability

Em biết giá trị khóa chính bắt buộc không NULL; những đặc điểm còn lại em chưa nói được.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R2.a1: `supported`. Bằng chứng: giá trị khóa chính bắt buộc không NULL
- DB_001_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_05 / one_wrong_condition

Nó xác định duy nhất dòng nhưng được phép NULL. Mỗi bảng chỉ một khóa chính, và khóa có thể gồm nhiều cột.

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `supported`. Bằng chứng: xác định duy nhất dòng
- DB_001_R2.a1: `contradicted`. Bằng chứng: được phép NULL
- DB_001_R3.a1: `supported`. Bằng chứng: Mỗi bảng chỉ một khóa chính
- DB_001_R3.a2: `supported`. Bằng chứng: khóa có thể gồm nhiều cột

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_06 / multiple_misconceptions

Các dòng được trùng giá trị khóa chính, được NULL. Một bảng có nhiều khóa chính độc lập, và mỗi khóa chính chỉ được gồm đúng một cột.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `contradicted`. Bằng chứng: Các dòng được trùng giá trị khóa chính
- DB_001_R2.a1: `contradicted`. Bằng chứng: được NULL
- DB_001_R3.a1: `contradicted`. Bằng chứng: Một bảng có nhiều khóa chính độc lập
- DB_001_R3.a2: `contradicted`. Bằng chứng: chỉ được gồm đúng một cột

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_07 / explicit_correction

Em nói được NULL là nhầm. Khóa chính không NULL và nhận diện duy nhất từng dòng. Bảng chỉ có một khóa chính, nhưng có thể dùng nhiều cột chung trong khóa đó.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `supported`. Bằng chứng: nhận diện duy nhất từng dòng
- DB_001_R2.a1: `supported`. Bằng chứng: Khóa chính không NULL
- DB_001_R3.a1: `supported`. Bằng chứng: Bảng chỉ có một khóa chính
- DB_001_R3.a2: `supported`. Bằng chứng: có thể dùng nhiều cột chung trong khóa đó

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_08 / retract_correct_to_wrong

Em đã nói khóa chính không được NULL, nhưng em rút lại. Em chốt khóa chính được phép NULL.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R2.a1: `contradicted`. Bằng chứng: Em chốt khóa chính được phép NULL
- DB_001_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_09 / keywords_without_claim

Khóa chính, unique, NULL và cột là các từ em nhớ, em chưa nối chúng thành một phát biểu về khóa chính.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_001_DRAFT_10 / unresolved_conflict

Khóa chính không NULL. Khóa chính được NULL. Em chưa biết nên giữ câu nào.

Khoảng điểm đề xuất: 0.0–3.0/10. Không phải điểm đã duyệt.

- DB_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R2.a1: `needs_review`. Bằng chứng: Khóa chính không NULL. Khóa chính được NULL. Em chưa biết nên giữ câu nào
- DB_001_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_001_R3.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_002: Khóa ngoại (foreign key) dùng để làm gì?

Nhóm: `train`. Nguồn nói bảng khác; bản draft chỉ giữ yêu cầu tham chiếu khóa chính/duy nhất, không tạo nhãn phủ định khóa ngoại tự tham chiếu. Giảng viên cần duyệt phạm vi và các trường hợp NULL.

- DB_002_R1.a1 (5.0 điểm dự thảo): Khóa ngoại tham chiếu khóa chính hoặc khóa duy nhất của bảng được tham chiếu.
- DB_002_R2.a1 (5.0 điểm dự thảo): Giá trị tham chiếu của khóa ngoại phải có bản ghi đích tương ứng, tránh tham chiếu mồ côi.

### DB_002_DRAFT_01 / natural_complete

Khóa ngoại trỏ tới khóa chính hoặc khóa duy nhất ở bảng đích. Mã đã đem tham chiếu phải tìm thấy dòng tương ứng, không được trỏ vào một dòng không tồn tại.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `supported`. Bằng chứng: trỏ tới khóa chính hoặc khóa duy nhất ở bảng đích
- DB_002_R2.a1: `supported`. Bằng chứng: không được trỏ vào một dòng không tồn tại

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_02 / mixed_terminology

Foreign key references primary key hoặc unique key và bảo đảm referential integrity, nghĩa là không lưu mã tham chiếu mồ côi.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `supported`. Bằng chứng: references primary key hoặc unique key
- DB_002_R2.a1: `supported`. Bằng chứng: không lưu mã tham chiếu mồ côi

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_03 / partial_first

Foreign key dẫn đến một primary key hoặc một unique key ở bảng được tham chiếu.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `supported`. Bằng chứng: dẫn đến một primary key hoặc một unique key
- DB_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_04 / partial_last

Nếu lưu một mã để tham chiếu thì phải có dòng mang mã đó ở bảng đích, không được mã mồ côi.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_002_R2.a1: `supported`. Bằng chứng: phải có dòng mang mã đó ở bảng đích, không được mã mồ côi

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_05 / one_wrong_relation

Khóa ngoại chỉ được trỏ cột không duy nhất, tuyệt đối không trỏ khóa chính hay unique. Nó vẫn ngăn dữ liệu tham chiếu mồ côi.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `contradicted`. Bằng chứng: tuyệt đối không trỏ khóa chính hay unique
- DB_002_R2.a1: `supported`. Bằng chứng: ngăn dữ liệu tham chiếu mồ côi

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_06 / wrong_integrity

Khóa ngoại trỏ primary key hoặc unique key, nhưng mọi mã không tồn tại ở bảng đích đều luôn được chấp nhận, không có ràng buộc tham chiếu.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `supported`. Bằng chứng: trỏ primary key hoặc unique key
- DB_002_R2.a1: `contradicted`. Bằng chứng: mọi mã không tồn tại ở bảng đích đều luôn được chấp nhận

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_07 / explicit_correction

Em vừa nói mã không tồn tại cũng được là sai. Khóa ngoại tham chiếu primary key hoặc unique và không cho trỏ đến bản ghi đích không tồn tại.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `supported`. Bằng chứng: tham chiếu primary key hoặc unique
- DB_002_R2.a1: `supported`. Bằng chứng: không cho trỏ đến bản ghi đích không tồn tại

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_08 / retract_correct_to_wrong

Em đã nói ngăn mã mồ côi nhưng xin rút lại. Em kết luận khóa ngoại cho phép tham chiếu tới mọi bản ghi không tồn tại mà không vi phạm gì.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_002_R2.a1: `contradicted`. Bằng chứng: cho phép tham chiếu tới mọi bản ghi không tồn tại mà không vi phạm gì

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_09 / keywords_without_claim

Em chỉ nhớ foreign key, unique và integrity; chưa diễn đạt cột được trỏ đến hay ràng buộc của nó.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_002_DRAFT_10 / unresolved_conflict

Khóa ngoại ngăn mã trỏ mồ côi. Khóa ngoại không ngăn mã trỏ mồ côi. Em đang phân vân, chưa có kết luận.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- DB_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_002_R2.a1: `needs_review`. Bằng chứng: Khóa ngoại ngăn mã trỏ mồ côi. Khóa ngoại không ngăn mã trỏ mồ côi. Em đang phân vân, chưa có kết luận

Ghi chú người duyệt: ____________________

## DB_003: Chuẩn hóa cơ sở dữ liệu nhằm mục đích gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DB_003_R1.a1 (4.0 điểm dự thảo): Chuẩn hóa giảm dư thừa hoặc lưu trùng dữ liệu.
- DB_003_R2.a1 (4.0 điểm dự thảo): Chuẩn hóa giúp tránh dị thường khi chèn, xóa hoặc cập nhật.
- DB_003_R3.a1 (2.0 điểm dự thảo): Việc tách bảng khi chuẩn hóa dựa trên phụ thuộc hàm.

### DB_003_DRAFT_01 / natural_complete

Mình tách bảng theo các quan hệ phụ thuộc hàm để khỏi ghi đi ghi lại cùng một dữ liệu. Nhờ vậy tránh bất thường khi thêm, xóa hoặc sửa thông tin.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `supported`. Bằng chứng: khỏi ghi đi ghi lại cùng một dữ liệu
- DB_003_R2.a1: `supported`. Bằng chứng: tránh bất thường khi thêm, xóa hoặc sửa thông tin
- DB_003_R3.a1: `supported`. Bằng chứng: tách bảng theo các quan hệ phụ thuộc hàm

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_02 / mixed_terminology

Normalization giảm redundancy, tránh insert/delete/update anomalies và dùng functional dependencies để phân rã bảng.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `supported`. Bằng chứng: giảm redundancy
- DB_003_R2.a1: `supported`. Bằng chứng: tránh insert/delete/update anomalies
- DB_003_R3.a1: `supported`. Bằng chứng: dùng functional dependencies để phân rã bảng

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_03 / partial_first

Em hiểu mục đích là hạn chế một thông tin bị lưu lặp ở nhiều chỗ.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `supported`. Bằng chứng: hạn chế một thông tin bị lưu lặp ở nhiều chỗ
- DB_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_04 / partial_last

Các phụ thuộc hàm là căn cứ để quyết định phân rã một quan hệ thành các bảng.

Khoảng điểm đề xuất: 2.0–2.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R3.a1: `supported`. Bằng chứng: Các phụ thuộc hàm là căn cứ để quyết định phân rã

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_05 / one_wrong_goal

Chuẩn hóa nhằm làm dữ liệu lưu trùng nhiều hơn. Nó tránh dị thường thêm xóa sửa và dựa vào phụ thuộc hàm để tách bảng.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `contradicted`. Bằng chứng: nhằm làm dữ liệu lưu trùng nhiều hơn
- DB_003_R2.a1: `supported`. Bằng chứng: tránh dị thường thêm xóa sửa
- DB_003_R3.a1: `supported`. Bằng chứng: dựa vào phụ thuộc hàm để tách bảng

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_06 / wrong_process

Nó giảm dư thừa nhưng cố ý tạo thêm các dị thường thêm xóa sửa. Tách bảng hoàn toàn tùy hứng, không dựa trên phụ thuộc hàm.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `supported`. Bằng chứng: giảm dư thừa
- DB_003_R2.a1: `contradicted`. Bằng chứng: cố ý tạo thêm các dị thường thêm xóa sửa
- DB_003_R3.a1: `contradicted`. Bằng chứng: không dựa trên phụ thuộc hàm

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_07 / explicit_correction

Em rút lại ý tăng lưu trùng. Chuẩn hóa giảm dư thừa và tránh dị thường chèn xóa cập nhật; việc phân rã dựa vào phụ thuộc hàm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `supported`. Bằng chứng: giảm dư thừa
- DB_003_R2.a1: `supported`. Bằng chứng: tránh dị thường chèn xóa cập nhật
- DB_003_R3.a1: `supported`. Bằng chứng: việc phân rã dựa vào phụ thuộc hàm

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_08 / retract_correct_to_wrong

Em đã bảo chuẩn hóa giảm dữ liệu trùng, nhưng không giữ ý đó nữa. Em chọn mục tiêu của chuẩn hóa là tăng dữ liệu trùng lặp.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `contradicted`. Bằng chứng: mục tiêu của chuẩn hóa là tăng dữ liệu trùng lặp
- DB_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_09 / keywords_without_claim

Em thuộc các từ chuẩn hóa, dư thừa, dị thường, phụ thuộc hàm nhưng chưa nêu mục đích hay cách tách bảng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_003_DRAFT_10 / unresolved_conflict

Chuẩn hóa giảm lưu trùng. Chuẩn hóa tăng lưu trùng. Em không phân biệt được hai phát biểu này.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- DB_003_R1.a1: `needs_review`. Bằng chứng: Chuẩn hóa giảm lưu trùng. Chuẩn hóa tăng lưu trùng. Em không phân biệt được hai phát biểu này
- DB_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_004: Điều kiện của dạng chuẩn 3 (3NF) là gì?

Nhóm: `validation`. Nguồn trình bày 3NF theo cách nhập môn giản lược. Cần giảng viên xác nhận phạm vi của thuộc tính không khóa và phụ thuộc bắc cầu; chưa coi draft là định nghĩa hình thức tổng quát.

- DB_004_R1.a1 (4.0 điểm dự thảo): Theo phạm vi nhập môn của nguồn, quan hệ đạt 3NF phải đạt 2NF trước.
- DB_004_R2.a1 (6.0 điểm dự thảo): Theo phạm vi nhập môn của nguồn, thuộc tính không khóa không phụ thuộc bắc cầu vào khóa chính.

### DB_004_DRAFT_01 / natural_complete

Em học rằng để lên dạng chuẩn ba thì trước hết quan hệ phải ở dạng chuẩn hai, rồi không còn thuộc tính không khóa phụ thuộc qua trung gian vào khóa chính.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `supported`. Bằng chứng: trước hết quan hệ phải ở dạng chuẩn hai
- DB_004_R2.a1: `supported`. Bằng chứng: không còn thuộc tính không khóa phụ thuộc qua trung gian vào khóa chính

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_02 / mixed_terminology

Điều kiện đang học là 2NF trước, và loại transitive dependency từ primary key tới non-key attributes để đạt 3NF.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `supported`. Bằng chứng: 2NF trước
- DB_004_R2.a1: `supported`. Bằng chứng: loại transitive dependency từ primary key tới non-key attributes

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_03 / partial_first

Điều kiện em nhớ chắc là trước khi đạt 3NF, quan hệ đã phải đạt 2NF.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `supported`. Bằng chứng: trước khi đạt 3NF, quan hệ đã phải đạt 2NF
- DB_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_04 / partial_last

Em chỉ nhớ loại phụ thuộc bắc cầu của thuộc tính không khóa vào khóa chính.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_004_R2.a1: `supported`. Bằng chứng: loại phụ thuộc bắc cầu của thuộc tính không khóa vào khóa chính

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_05 / one_wrong_precondition

Đạt 3NF không cần đạt 2NF trước. Điều kiện còn lại là thuộc tính không khóa không phụ thuộc bắc cầu vào khóa chính.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `contradicted`. Bằng chứng: Đạt 3NF không cần đạt 2NF trước
- DB_004_R2.a1: `supported`. Bằng chứng: thuộc tính không khóa không phụ thuộc bắc cầu vào khóa chính

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_06 / wrong_conditions

Quan hệ đạt 3NF mà chưa đạt 2NF vẫn đúng; đồng thời phải giữ phụ thuộc bắc cầu của thuộc tính không khóa vào khóa chính.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `contradicted`. Bằng chứng: đạt 3NF mà chưa đạt 2NF vẫn đúng
- DB_004_R2.a1: `contradicted`. Bằng chứng: phải giữ phụ thuộc bắc cầu của thuộc tính không khóa vào khóa chính

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_07 / explicit_correction

Em nói bỏ qua 2NF là sai. Phải đạt 2NF trước và không để thuộc tính không khóa phụ thuộc bắc cầu vào khóa chính.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `supported`. Bằng chứng: Phải đạt 2NF trước
- DB_004_R2.a1: `supported`. Bằng chứng: không để thuộc tính không khóa phụ thuộc bắc cầu vào khóa chính

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_08 / retract_correct_to_wrong

Em đã nói loại phụ thuộc bắc cầu nhưng rút lại. Em cho rằng 3NF bắt buộc tồn tại phụ thuộc bắc cầu từ khóa chính tới thuộc tính không khóa.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_004_R2.a1: `contradicted`. Bằng chứng: 3NF bắt buộc tồn tại phụ thuộc bắc cầu từ khóa chính tới thuộc tính không khóa

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_09 / keywords_without_claim

Em nhớ 2NF, 3NF, khóa và bắc cầu nhưng chưa trình bày quan hệ giữa chúng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_004_DRAFT_10 / unresolved_conflict

3NF cần đạt 2NF. 3NF không cần đạt 2NF. Em chưa quyết định phát biểu nào.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- DB_004_R1.a1: `needs_review`. Bằng chứng: 3NF cần đạt 2NF. 3NF không cần đạt 2NF. Em chưa quyết định phát biểu nào
- DB_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_005: Giải thích các tính chất ACID của giao dịch.

Nhóm: `test`. Nguồn diễn giải isolation ở mức nhập môn; cần giảng viên xác nhận mức cô lập và không suy rộng thành mọi mức isolation đều serializable.

- DB_005_R1.a1 (3.0 điểm dự thảo): Atomicity yêu cầu giao dịch thực hiện toàn bộ hoặc không thực hiện gì.
- DB_005_R2.a1 (3.0 điểm dự thảo): Consistency giữ cơ sở dữ liệu từ trạng thái hợp lệ sang trạng thái hợp lệ.
- DB_005_R3.a1 (2.0 điểm dự thảo): Theo phạm vi nguồn, Isolation cô lập các giao dịch đồng thời, tránh ảnh hưởng lẫn nhau.
- DB_005_R4.a1 (2.0 điểm dự thảo): Durability giữ thay đổi đã commit bền vững kể cả khi hệ thống lỗi.

### DB_005_DRAFT_01 / natural_complete

Nguyên tử là xong hết hoặc bỏ hết. Nhất quán giữ dữ liệu hợp lệ trước và sau. Cô lập để các giao dịch cùng lúc không can thiệp nhau. Bền vững giữ phần đã chốt ngay cả khi hệ thống gặp sự cố.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `supported`. Bằng chứng: xong hết hoặc bỏ hết
- DB_005_R2.a1: `supported`. Bằng chứng: giữ dữ liệu hợp lệ trước và sau
- DB_005_R3.a1: `supported`. Bằng chứng: các giao dịch cùng lúc không can thiệp nhau
- DB_005_R4.a1: `supported`. Bằng chứng: giữ phần đã chốt ngay cả khi hệ thống gặp sự cố

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_02 / mixed_terminology

Atomicity all-or-nothing; Consistency valid state sang valid state; Isolation tách ảnh hưởng giữa concurrent transactions; Durability giữ committed data sau system failure.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `supported`. Bằng chứng: Atomicity all-or-nothing
- DB_005_R2.a1: `supported`. Bằng chứng: Consistency valid state sang valid state
- DB_005_R3.a1: `supported`. Bằng chứng: Isolation tách ảnh hưởng giữa concurrent transactions
- DB_005_R4.a1: `supported`. Bằng chứng: Durability giữ committed data sau system failure

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_03 / partial_first

Em biết tính nguyên tử có nghĩa là cả giao dịch cùng thành công hoặc coi như không thực hiện phần nào.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `supported`. Bằng chứng: cả giao dịch cùng thành công hoặc coi như không thực hiện phần nào
- DB_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R4.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_04 / partial_last

Phần đã commit phải được giữ bền, kể cả hệ thống gặp lỗi sau đó.

Khoảng điểm đề xuất: 2.0–2.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R4.a1: `supported`. Bằng chứng: Phần đã commit phải được giữ bền, kể cả hệ thống gặp lỗi sau đó

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_05 / one_wrong_property

Atomicity là toàn bộ hoặc không gì; Consistency giữ trạng thái hợp lệ. Isolation cho phép các giao dịch đồng thời can thiệp tùy ý vào nhau. Durability giữ dữ liệu commit cả khi có sự cố.

Khoảng điểm đề xuất: 8.0–8.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `supported`. Bằng chứng: Atomicity là toàn bộ hoặc không gì
- DB_005_R2.a1: `supported`. Bằng chứng: Consistency giữ trạng thái hợp lệ
- DB_005_R3.a1: `contradicted`. Bằng chứng: Isolation cho phép các giao dịch đồng thời can thiệp tùy ý vào nhau
- DB_005_R4.a1: `supported`. Bằng chứng: Durability giữ dữ liệu commit cả khi có sự cố

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_06 / wrong_properties

Atomicity cho chốt nửa giao dịch. Consistency cho phá ràng buộc hợp lệ. Isolation không hề cô lập các giao dịch. Durability xóa dữ liệu đã commit mỗi khi hệ thống lỗi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `contradicted`. Bằng chứng: Atomicity cho chốt nửa giao dịch
- DB_005_R2.a1: `contradicted`. Bằng chứng: Consistency cho phá ràng buộc hợp lệ
- DB_005_R3.a1: `contradicted`. Bằng chứng: Isolation không hề cô lập các giao dịch
- DB_005_R4.a1: `contradicted`. Bằng chứng: Durability xóa dữ liệu đã commit mỗi khi hệ thống lỗi

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_07 / explicit_correction

Em sửa các tính chất: A là làm hết hoặc hủy hết; C giữ dữ liệu hợp lệ; I cô lập giao dịch chạy cùng lúc; D giữ thay đổi commit bền vững khi máy bị lỗi.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `supported`. Bằng chứng: A là làm hết hoặc hủy hết
- DB_005_R2.a1: `supported`. Bằng chứng: C giữ dữ liệu hợp lệ
- DB_005_R3.a1: `supported`. Bằng chứng: I cô lập giao dịch chạy cùng lúc
- DB_005_R4.a1: `supported`. Bằng chứng: D giữ thay đổi commit bền vững khi máy bị lỗi

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_08 / retract_correct_to_wrong

Em đã trả lời dữ liệu commit vẫn còn khi lỗi. Em rút lại: Durability nghĩa là dữ liệu đã commit phải mất khi hệ thống hỏng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R4.a1: `contradicted`. Bằng chứng: Durability nghĩa là dữ liệu đã commit phải mất khi hệ thống hỏng

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_09 / keywords_without_claim

Atomicity, Consistency, Isolation, Durability em đọc được tên thôi, chưa giải thích ý nghĩa.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R4.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_005_DRAFT_10 / unresolved_conflict

Isolation ngăn giao dịch đồng thời ảnh hưởng nhau. Isolation cho giao dịch đồng thời ảnh hưởng nhau tùy ý. Em chưa có kết luận.

Khoảng điểm đề xuất: 0.0–2.0/10. Không phải điểm đã duyệt.

- DB_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_005_R3.a1: `needs_review`. Bằng chứng: Isolation ngăn giao dịch đồng thời ảnh hưởng nhau. Isolation cho giao dịch đồng thời ảnh hưởng nhau tùy ý. Em chưa có kết luận
- DB_005_R4.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_006: Index trong cơ sở dữ liệu có lợi và hại gì?

Nhóm: `train`. Tác động hiệu năng phụ thuộc workload; giữ cách nói thường/tăng chi phí, không biến thành quy luật tuyệt đối cho mọi truy vấn và thao tác ghi.

- DB_006_R1.a1 (5.0 điểm dự thảo): Index giúp tăng tốc truy vấn đọc hoặc tìm kiếm phù hợp.
- DB_006_R2.a1 (2.5 điểm dự thảo): Index cần thêm không gian lưu trữ.
- DB_006_R2.a2 (2.5 điểm dự thảo): Duy trì index làm tăng chi phí thao tác ghi.

### DB_006_DRAFT_01 / natural_complete

Có chỉ mục phù hợp thì tra và đọc dữ liệu nhanh hơn. Đổi lại phải dành chỗ cất chỉ mục và khi ghi còn phải sửa nó, nên việc ghi có thêm chi phí.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `supported`. Bằng chứng: tra và đọc dữ liệu nhanh hơn
- DB_006_R2.a1: `supported`. Bằng chứng: phải dành chỗ cất chỉ mục
- DB_006_R2.a2: `supported`. Bằng chứng: việc ghi có thêm chi phí

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_02 / mixed_terminology

Index tăng tốc read/lookup phù hợp, tốn thêm storage và thêm maintenance cost cho insert/update/delete.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `supported`. Bằng chứng: tăng tốc read/lookup phù hợp
- DB_006_R2.a1: `supported`. Bằng chứng: tốn thêm storage
- DB_006_R2.a2: `supported`. Bằng chứng: thêm maintenance cost cho insert/update/delete

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_03 / partial_first

Em biết mục đích thường là làm việc tìm kiếm và đọc bản ghi nhanh hơn.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `supported`. Bằng chứng: làm việc tìm kiếm và đọc bản ghi nhanh hơn
- DB_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_04 / partial_costs

Chỉ mục cần chỗ lưu riêng, các lần ghi còn phải cập nhật chỉ mục nên tốn thêm công.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a1: `supported`. Bằng chứng: cần chỗ lưu riêng
- DB_006_R2.a2: `supported`. Bằng chứng: các lần ghi còn phải cập nhật chỉ mục nên tốn thêm công

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_05 / one_wrong_cost

Index giúp đọc nhanh, hoàn toàn không chiếm chỗ lưu nào, nhưng phải cập nhật khi ghi nên tăng chi phí ghi.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `supported`. Bằng chứng: Index giúp đọc nhanh
- DB_006_R2.a1: `contradicted`. Bằng chứng: hoàn toàn không chiếm chỗ lưu nào
- DB_006_R2.a2: `supported`. Bằng chứng: tăng chi phí ghi

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_06 / wrong_tradeoff

Index không thể tăng tốc bất cứ lần tìm kiếm nào, không cần không gian lưu trữ, và không bao giờ làm phát sinh chi phí khi ghi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `contradicted`. Bằng chứng: không thể tăng tốc bất cứ lần tìm kiếm nào
- DB_006_R2.a1: `contradicted`. Bằng chứng: không cần không gian lưu trữ
- DB_006_R2.a2: `contradicted`. Bằng chứng: không bao giờ làm phát sinh chi phí khi ghi

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_07 / explicit_correction

Em rút lại ý không tốn tài nguyên. Index hỗ trợ tra cứu nhanh hơn, chiếm thêm chỗ và tăng chi phí ghi do phải duy trì chỉ mục.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `supported`. Bằng chứng: hỗ trợ tra cứu nhanh hơn
- DB_006_R2.a1: `supported`. Bằng chứng: chiếm thêm chỗ
- DB_006_R2.a2: `supported`. Bằng chứng: tăng chi phí ghi do phải duy trì chỉ mục

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_08 / retract_correct_to_wrong

Em đã nói ghi tốn thêm công vì index; em rút lại. Kết luận em chọn là duy trì index không bao giờ tăng chi phí ghi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a2: `contradicted`. Bằng chứng: duy trì index không bao giờ tăng chi phí ghi

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_09 / keywords_without_claim

Read, write, index, storage em chỉ nhớ từ, chưa nói được cái nào nhanh hơn hay tốn thêm gì.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_006_DRAFT_10 / unresolved_conflict

Index cần thêm chỗ lưu. Index không cần thêm chỗ lưu. Em không biết nên giữ phát biểu nào.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DB_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_006_R2.a1: `needs_review`. Bằng chứng: Index cần thêm chỗ lưu. Index không cần thêm chỗ lưu. Em không biết nên giữ phát biểu nào
- DB_006_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_007: GROUP BY và HAVING khác nhau như thế nào?

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DB_007_R1.a1 (5.0 điểm dự thảo): GROUP BY gom các dòng theo giá trị cột để tính hàm tổng hợp.
- DB_007_R2.a1 (2.5 điểm dự thảo): HAVING lọc các nhóm sau khi gom nhóm.
- DB_007_R2.a2 (2.5 điểm dự thảo): WHERE lọc các dòng trước khi gom nhóm.

### DB_007_DRAFT_01 / natural_complete

Group by gom các dòng cùng giá trị để tính tổng hợp. Having sàng các nhóm đã gom xong, còn where sàng từng dòng từ trước lúc gom.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `supported`. Bằng chứng: gom các dòng cùng giá trị để tính tổng hợp
- DB_007_R2.a1: `supported`. Bằng chứng: Having sàng các nhóm đã gom xong
- DB_007_R2.a2: `supported`. Bằng chứng: where sàng từng dòng từ trước lúc gom

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_02 / mixed_terminology

GROUP BY group rows theo cột cho aggregate. HAVING filter groups sau grouping, WHERE filter rows trước grouping.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `supported`. Bằng chứng: group rows theo cột cho aggregate
- DB_007_R2.a1: `supported`. Bằng chứng: HAVING filter groups sau grouping
- DB_007_R2.a2: `supported`. Bằng chứng: WHERE filter rows trước grouping

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_03 / partial_first

Em biết GROUP BY gom các dòng dựa trên cột để dùng hàm tính tổng hợp.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `supported`. Bằng chứng: gom các dòng dựa trên cột để dùng hàm tính tổng hợp
- DB_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_04 / partial_filters

HAVING áp điều kiện lên nhóm đã tạo; WHERE áp điều kiện lên dòng trước khi tạo nhóm.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a1: `supported`. Bằng chứng: HAVING áp điều kiện lên nhóm đã tạo
- DB_007_R2.a2: `supported`. Bằng chứng: WHERE áp điều kiện lên dòng trước khi tạo nhóm

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_05 / one_wrong_stage

GROUP BY gom dòng cho hàm tổng hợp. HAVING lọc dòng trước khi gom, WHERE cũng lọc dòng trước khi gom.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `supported`. Bằng chứng: GROUP BY gom dòng cho hàm tổng hợp
- DB_007_R2.a1: `contradicted`. Bằng chứng: HAVING lọc dòng trước khi gom
- DB_007_R2.a2: `supported`. Bằng chứng: WHERE cũng lọc dòng trước khi gom

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_06 / role_reversal

Em cho rằng WHERE lọc các nhóm sau khi gom, còn HAVING lọc bản ghi trước khi gom.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a1: `contradicted`. Bằng chứng: HAVING lọc bản ghi trước khi gom
- DB_007_R2.a2: `contradicted`. Bằng chứng: WHERE lọc các nhóm sau khi gom

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_07 / explicit_correction

Em đã nói ngược WHERE với HAVING. Sửa lại GROUP BY gom dòng để tổng hợp; WHERE lọc dòng trước, HAVING lọc nhóm sau khi gom.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `supported`. Bằng chứng: GROUP BY gom dòng để tổng hợp
- DB_007_R2.a1: `supported`. Bằng chứng: HAVING lọc nhóm sau khi gom
- DB_007_R2.a2: `supported`. Bằng chứng: WHERE lọc dòng trước

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_08 / retract_correct_to_wrong

Em đã nói WHERE trước, HAVING sau, nhưng rút lại. Em chốt WHERE lọc nhóm sau grouping và HAVING lọc dòng trước grouping.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a1: `contradicted`. Bằng chứng: HAVING lọc dòng trước grouping
- DB_007_R2.a2: `contradicted`. Bằng chứng: WHERE lọc nhóm sau grouping

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_09 / keywords_without_claim

Em nhớ tên GROUP BY, HAVING, WHERE, SUM nhưng chưa nêu chức năng hoặc thứ tự áp dụng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_007_DRAFT_10 / unresolved_conflict

HAVING lọc nhóm sau gom. HAVING lọc dòng trước gom. Em chưa chọn câu nào là ý cuối.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DB_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_007_R2.a1: `needs_review`. Bằng chứng: HAVING lọc nhóm sau gom. HAVING lọc dòng trước gom. Em chưa chọn câu nào là ý cuối
- DB_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_008: Transaction rollback và commit khác nhau ra sao?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DB_008_R1.a1 (5.0 điểm dự thảo): COMMIT xác nhận và lưu bền vững các thay đổi của giao dịch.
- DB_008_R2.a1 (5.0 điểm dự thảo): ROLLBACK hủy thay đổi chưa commit và khôi phục trạng thái trước đó.

### DB_008_DRAFT_01 / natural_complete

Commit là chốt các thay đổi để giữ lại lâu dài. Rollback thì bỏ phần chưa chốt, đưa dữ liệu về tình trạng trước đó.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `supported`. Bằng chứng: chốt các thay đổi để giữ lại lâu dài
- DB_008_R2.a1: `supported`. Bằng chứng: bỏ phần chưa chốt, đưa dữ liệu về tình trạng trước đó

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_02 / mixed_terminology

COMMIT persist các transaction changes. ROLLBACK undo uncommitted changes để restore previous state.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `supported`. Bằng chứng: COMMIT persist các transaction changes
- DB_008_R2.a1: `supported`. Bằng chứng: ROLLBACK undo uncommitted changes để restore previous state

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_03 / partial_first

Commit xác nhận các thay đổi của giao dịch và lưu chúng bền vững.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `supported`. Bằng chứng: Commit xác nhận các thay đổi của giao dịch và lưu chúng bền vững
- DB_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_04 / partial_last

Rollback quay về trạng thái trước bằng cách bỏ các thay đổi chưa commit.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_008_R2.a1: `supported`. Bằng chứng: quay về trạng thái trước bằng cách bỏ các thay đổi chưa commit

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_05 / one_wrong_operation

COMMIT hủy mọi thay đổi thay vì lưu lại; ROLLBACK bỏ phần chưa commit để trả lại trạng thái cũ.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `contradicted`. Bằng chứng: COMMIT hủy mọi thay đổi thay vì lưu lại
- DB_008_R2.a1: `supported`. Bằng chứng: ROLLBACK bỏ phần chưa commit để trả lại trạng thái cũ

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_06 / role_reversal

COMMIT là lệnh hủy thay đổi chưa chốt. ROLLBACK mới xác nhận và lưu lâu dài các thay đổi chưa chốt.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `contradicted`. Bằng chứng: COMMIT là lệnh hủy thay đổi chưa chốt
- DB_008_R2.a1: `contradicted`. Bằng chứng: ROLLBACK mới xác nhận và lưu lâu dài các thay đổi chưa chốt

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_07 / explicit_correction

Em nhầm hai lệnh. Đúng ra COMMIT lưu và xác nhận thay đổi; ROLLBACK mới hủy phần chưa commit để quay lại trạng thái trước.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `supported`. Bằng chứng: COMMIT lưu và xác nhận thay đổi
- DB_008_R2.a1: `supported`. Bằng chứng: ROLLBACK mới hủy phần chưa commit để quay lại trạng thái trước

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_08 / retract_correct_to_wrong

Em đã bảo rollback hủy thay đổi, nhưng rút lại. Em kết luận rollback lưu bền vững các thay đổi chưa commit chứ không khôi phục trạng thái cũ.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_008_R2.a1: `contradicted`. Bằng chứng: rollback lưu bền vững các thay đổi chưa commit chứ không khôi phục trạng thái cũ

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_09 / keywords_without_claim

Commit, rollback và transaction em nhớ tên nhưng chưa gán chức năng nào cho từng lệnh.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_008_DRAFT_10 / unresolved_conflict

COMMIT giữ các thay đổi. COMMIT hủy các thay đổi. Em chưa biết ý nào là kết luận.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- DB_008_R1.a1: `needs_review`. Bằng chứng: COMMIT giữ các thay đổi. COMMIT hủy các thay đổi. Em chưa biết ý nào là kết luận
- DB_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_009: So sánh cơ sở dữ liệu quan hệ (SQL) và NoSQL.

Nhóm: `validation`. So sánh SQL/NoSQL là khái quát nhập môn trong nguồn, không phải thuộc tính tuyệt đối của mọi hệ quản trị. Giảng viên cần duyệt trước khi dùng các ví dụ tổng quát này.

- DB_009_R1.a1 (2.5 điểm dự thảo): Trong phạm vi so sánh của nguồn, dữ liệu quan hệ tổ chức thành bảng theo lược đồ xác định.
- DB_009_R1.a2 (2.5 điểm dự thảo): Cơ sở dữ liệu quan hệ hỗ trợ JOIN.
- DB_009_R2.a1 (2.5 điểm dự thảo): NoSQL thường có lược đồ linh hoạt.
- DB_009_R2.a2 (2.5 điểm dự thảo): NoSQL thường thuận lợi cho mở rộng theo chiều ngang.

### DB_009_DRAFT_01 / natural_complete

Theo phần em học, cơ sở dữ liệu quan hệ dùng bảng với lược đồ định sẵn và có phép nối. NoSQL thường linh hoạt về lược đồ hơn và dễ mở rộng bằng thêm máy hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `supported`. Bằng chứng: dùng bảng với lược đồ định sẵn
- DB_009_R1.a2: `supported`. Bằng chứng: có phép nối
- DB_009_R2.a1: `supported`. Bằng chứng: thường linh hoạt về lược đồ hơn
- DB_009_R2.a2: `supported`. Bằng chứng: dễ mở rộng bằng thêm máy hơn

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_02 / mixed_terminology

SQL relational data theo tables với defined schema và support JOIN. NoSQL thường flexible schema, thuận horizontal scaling.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `supported`. Bằng chứng: theo tables với defined schema
- DB_009_R1.a2: `supported`. Bằng chứng: support JOIN
- DB_009_R2.a1: `supported`. Bằng chứng: thường flexible schema
- DB_009_R2.a2: `supported`. Bằng chứng: thuận horizontal scaling

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_03 / partial_first

Em nhớ dữ liệu quan hệ được tổ chức thành các bảng theo một lược đồ xác định.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `supported`. Bằng chứng: tổ chức thành các bảng theo một lược đồ xác định
- DB_009_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_04 / partial_nosql

NoSQL thường cho cấu trúc dữ liệu linh hoạt và có thể thuận lợi khi tăng số máy để mở rộng.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a1: `supported`. Bằng chứng: thường cho cấu trúc dữ liệu linh hoạt
- DB_009_R2.a2: `supported`. Bằng chứng: thuận lợi khi tăng số máy để mở rộng

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_05 / one_wrong_capability

Dữ liệu quan hệ dùng bảng có schema, nhưng không hỗ trợ JOIN. NoSQL thường linh hoạt schema và dễ scale ngang.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `supported`. Bằng chứng: dùng bảng có schema
- DB_009_R1.a2: `contradicted`. Bằng chứng: không hỗ trợ JOIN
- DB_009_R2.a1: `supported`. Bằng chứng: thường linh hoạt schema
- DB_009_R2.a2: `supported`. Bằng chứng: dễ scale ngang

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_06 / wrong_generalization

Hệ quan hệ không dùng bảng hay lược đồ và cấm JOIN. Mọi NoSQL bắt buộc lược đồ cố định, không thể mở rộng bằng thêm máy.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `contradicted`. Bằng chứng: không dùng bảng hay lược đồ
- DB_009_R1.a2: `contradicted`. Bằng chứng: cấm JOIN
- DB_009_R2.a1: `contradicted`. Bằng chứng: Mọi NoSQL bắt buộc lược đồ cố định
- DB_009_R2.a2: `contradicted`. Bằng chứng: không thể mở rộng bằng thêm máy

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_07 / explicit_correction

Em sửa lại phần so sánh: quan hệ lưu bảng theo schema và dùng JOIN; NoSQL thường schema linh hoạt, thuận tăng số máy để scale ngang.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `supported`. Bằng chứng: quan hệ lưu bảng theo schema
- DB_009_R1.a2: `supported`. Bằng chứng: dùng JOIN
- DB_009_R2.a1: `supported`. Bằng chứng: NoSQL thường schema linh hoạt
- DB_009_R2.a2: `supported`. Bằng chứng: thuận tăng số máy để scale ngang

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_08 / retract_correct_to_wrong

Em đã bảo cơ sở dữ liệu quan hệ hỗ trợ JOIN nhưng xin rút lại. Em chốt hệ quan hệ không có phép JOIN.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R1.a2: `contradicted`. Bằng chứng: hệ quan hệ không có phép JOIN
- DB_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_09 / keywords_without_claim

SQL, NoSQL, schema, JOIN và scale em chỉ nhớ từ, chưa nêu đặc điểm bên nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_009_DRAFT_10 / unresolved_conflict

Hệ quan hệ hỗ trợ JOIN. Hệ quan hệ không hỗ trợ JOIN. Em chưa kết luận được.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DB_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R1.a2: `needs_review`. Bằng chứng: Hệ quan hệ hỗ trợ JOIN. Hệ quan hệ không hỗ trợ JOIN. Em chưa kết luận được
- DB_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_009_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DB_010: Mô hình thực thể - liên kết (ER) gồm những thành phần nào?

Nhóm: `regression_only`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DB_010_R1.a1 (2.5 điểm dự thảo): Mô hình ER biểu diễn các thực thể.
- DB_010_R1.a2 (2.5 điểm dự thảo): Thực thể trong ER có các thuộc tính.
- DB_010_R2.a1 (2.5 điểm dự thảo): Các mối liên kết nối các thực thể.
- DB_010_R2.a2 (2.5 điểm dự thảo): Lực lượng liên kết có thể là 1-1, 1-n hoặc n-n.

### DB_010_DRAFT_01 / natural_complete

ER có các thực thể và đặc điểm hay thuộc tính của chúng. Giữa các thực thể có quan hệ liên kết; số lượng tham gia có thể một-một, một-nhiều hoặc nhiều-nhiều.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: ER có các thực thể
- DB_010_R1.a2: `supported`. Bằng chứng: đặc điểm hay thuộc tính của chúng
- DB_010_R2.a1: `supported`. Bằng chứng: Giữa các thực thể có quan hệ liên kết
- DB_010_R2.a2: `supported`. Bằng chứng: một-một, một-nhiều hoặc nhiều-nhiều

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_02 / mixed_terminology

ER gồm entities với attributes, relationships nối entities, và cardinality 1:1, 1:N hoặc N:N.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: ER gồm entities
- DB_010_R1.a2: `supported`. Bằng chứng: với attributes
- DB_010_R2.a1: `supported`. Bằng chứng: relationships nối entities
- DB_010_R2.a2: `supported`. Bằng chứng: cardinality 1:1, 1:N hoặc N:N

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_03 / partial_entities

Em nhớ mô hình có các thực thể kèm thuộc tính mô tả chúng, phần liên kết chưa nhớ.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: có các thực thể
- DB_010_R1.a2: `supported`. Bằng chứng: kèm thuộc tính mô tả chúng
- DB_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_04 / partial_relations

Có liên kết giữa các thực thể với lực lượng một-một, một-nhiều hoặc nhiều-nhiều.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: Có liên kết giữa các thực thể
- DB_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a1: `supported`. Bằng chứng: liên kết giữa các thực thể
- DB_010_R2.a2: `supported`. Bằng chứng: lực lượng một-một, một-nhiều hoặc nhiều-nhiều

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_05 / one_wrong_component

ER có thực thể nhưng thực thể không có thuộc tính. Các liên kết nối thực thể với lực lượng 1-1, 1-n hay n-n.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: ER có thực thể
- DB_010_R1.a2: `contradicted`. Bằng chứng: thực thể không có thuộc tính
- DB_010_R2.a1: `supported`. Bằng chứng: Các liên kết nối thực thể
- DB_010_R2.a2: `supported`. Bằng chứng: lực lượng 1-1, 1-n hay n-n

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_06 / wrong_structure

ER không biểu diễn thực thể, không có thuộc tính và không nối thực thể bằng liên kết. Nó cũng không có lực lượng 1-1, 1-n hay n-n.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `contradicted`. Bằng chứng: ER không biểu diễn thực thể
- DB_010_R1.a2: `contradicted`. Bằng chứng: không có thuộc tính
- DB_010_R2.a1: `contradicted`. Bằng chứng: không nối thực thể bằng liên kết
- DB_010_R2.a2: `contradicted`. Bằng chứng: không có lực lượng 1-1, 1-n hay n-n

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_07 / explicit_correction

Em đã nói ER chỉ có thực thể là thiếu. Sửa lại nó có thực thể, có thuộc tính của thực thể, có liên kết giữa thực thể và lực lượng 1-1, 1-n hoặc n-n.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `supported`. Bằng chứng: nó có thực thể
- DB_010_R1.a2: `supported`. Bằng chứng: có thuộc tính của thực thể
- DB_010_R2.a1: `supported`. Bằng chứng: có liên kết giữa thực thể
- DB_010_R2.a2: `supported`. Bằng chứng: lực lượng 1-1, 1-n hoặc n-n

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_08 / retract_correct_to_wrong

Em đã liệt kê 1-1, 1-n, n-n nhưng xin rút lại. Em chốt lực lượng liên kết trong ER không thể là bất kỳ dạng nào trong ba dạng đó.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a2: `contradicted`. Bằng chứng: lực lượng liên kết trong ER không thể là bất kỳ dạng nào trong ba dạng đó

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_09 / keywords_without_claim

Entity, attribute, relationship và cardinality em chỉ đọc lại các từ đó, chưa phát biểu cấu trúc của ER.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DB_010_DRAFT_10 / unresolved_conflict

Thực thể có thuộc tính. Thực thể không có thuộc tính. Em chưa biết nên giữ khẳng định nào.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DB_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R1.a2: `needs_review`. Bằng chứng: Thực thể có thuộc tính. Thực thể không có thuộc tính. Em chưa biết nên giữ khẳng định nào
- DB_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DB_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________
