# Mẫu dữ liệu để đọc nhanh

Tất cả đều là ví dụ AI soạn, chưa có giảng viên duyệt.

## AI101: Machine learning là gì?

### AI_001_DRAFT_01 (natural_complete)

Thay vì người lập trình viết hết từng tình huống, mình cho máy xem dữ liệu để rút quy luật. Máy tận dụng kinh nghiệm đó nhằm làm một công việc tốt hơn.

- AI_001_R1.a1: `supported`
- AI_001_R2.a1: `supported`

### AI_001_DRAFT_02 (mixed_terminology)

ML learn patterns từ data thay vì hand-code từng rule; mục tiêu là improve task performance nhờ data hoặc experience.

- AI_001_R1.a1: `supported`
- AI_001_R2.a1: `supported`

### AI_001_DRAFT_03 (partial_first)

Em hiểu là để máy tự tìm quy luật từ các ví dụ dữ liệu, không viết sẵn tất cả các luật cho nó.

- AI_001_R1.a1: `supported`
- AI_001_R2.a1: `missing`

### AI_001_DRAFT_04 (partial_goal)

Mục tiêu của machine learning là dùng kinh nghiệm hay dữ liệu để làm một nhiệm vụ ngày càng tốt hơn.

- AI_001_R1.a1: `missing`
- AI_001_R2.a1: `supported`

## DB101: Khóa chính (primary key) là gì?

### DB_001_DRAFT_01 (natural_complete)

Khóa chính phân biệt từng dòng, không hai dòng trùng khóa và giá trị khóa không được thiếu. Mỗi bảng chỉ có tối đa một khóa chính, nhưng khóa đó có thể ghép từ mấy cột.

- DB_001_R1.a1: `supported`
- DB_001_R2.a1: `supported`
- DB_001_R3.a1: `supported`
- DB_001_R3.a2: `supported`

### DB_001_DRAFT_02 (mixed_terminology)

Primary key uniquely identifies một record và phải NOT NULL. Một table có tối đa một primary-key constraint; composite primary key có thể chứa nhiều columns.

- DB_001_R1.a1: `supported`
- DB_001_R2.a1: `supported`
- DB_001_R3.a1: `supported`
- DB_001_R3.a2: `supported`

### DB_001_DRAFT_03 (partial_first)

Đó là một mã không trùng để nhận ra từng bản ghi riêng biệt trong bảng.

- DB_001_R1.a1: `supported`
- DB_001_R2.a1: `missing`
- DB_001_R3.a1: `missing`
- DB_001_R3.a2: `missing`

### DB_001_DRAFT_04 (partial_nullability)

Em biết giá trị khóa chính bắt buộc không NULL; những đặc điểm còn lại em chưa nói được.

- DB_001_R1.a1: `missing`
- DB_001_R2.a1: `supported`
- DB_001_R3.a1: `missing`
- DB_001_R3.a2: `missing`

## DSA101: Stack và queue khác nhau như thế nào?

### DSA_001_DRAFT_01 (natural_complete)

Với ngăn xếp, món vừa bỏ lên sẽ được lấy xuống đầu tiên. Hàng đợi thì ai vào trước được lấy ra trước.

- DSA_001_R1.a1: `supported`
- DSA_001_R2.a1: `supported`

### DSA_001_DRAFT_02 (mixed_terminology)

Stack theo LIFO, nghĩa là last in first out. Queue theo FIFO, first in first out.

- DSA_001_R1.a1: `supported`
- DSA_001_R2.a1: `supported`

### DSA_001_DRAFT_03 (partial_first)

Em nhớ stack giống chồng khay, khay đặt lên cuối thì nhấc xuống trước. Queue em chưa giải thích được.

- DSA_001_R1.a1: `supported`
- DSA_001_R2.a1: `missing`

### DSA_001_DRAFT_04 (partial_last)

Về queue, phần tử nào xếp vào sớm nhất thì được lấy ra sớm nhất. Stack thì em quên rồi.

- DSA_001_R1.a1: `missing`
- DSA_001_R2.a1: `supported`

## OOP101: Tính đóng gói (encapsulation) trong OOP là gì?

### OOP_001_DRAFT_01 (natural_complete)

Mình để dữ liệu với các hàm xử lý nó chung trong lớp. Phần bên trong được giấu, người dùng bên ngoài muốn đọc sửa thì đi qua những hàm được công khai.

- OOP_001_R1.a1: `supported`
- OOP_001_R2.a1: `supported`
- OOP_001_R2.a2: `supported`

### OOP_001_DRAFT_02 (mixed_terminology)

Encapsulation gom data và methods vào class, hide internal state và expose public methods để kiểm soát access.

- OOP_001_R1.a1: `supported`
- OOP_001_R2.a1: `supported`
- OOP_001_R2.a2: `supported`

### OOP_001_DRAFT_03 (partial_first)

Em hiểu là thuộc tính và các phương thức thao tác lên thuộc tính được đặt trong cùng một lớp.

- OOP_001_R1.a1: `supported`
- OOP_001_R2.a1: `missing`
- OOP_001_R2.a2: `missing`

### OOP_001_DRAFT_04 (partial_hidden_state)

Ý em nhớ là che trạng thái bên trong đối tượng, không nói thêm về cách cung cấp truy cập.

- OOP_001_R1.a1: `missing`
- OOP_001_R2.a1: `supported`
- OOP_001_R2.a2: `missing`
