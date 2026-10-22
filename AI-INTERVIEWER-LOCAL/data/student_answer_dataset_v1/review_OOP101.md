# Bản đọc duyệt OOP101

Nhãn và điểm đều là AI đề xuất; chưa có giảng viên duyệt.

## OOP_001: Tính đóng gói (encapsulation) trong OOP là gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_001_R1.a1 (5.0 điểm dự thảo): Đóng gói gom dữ liệu và phương thức xử lý dữ liệu trong cùng một lớp.
- OOP_001_R2.a1 (2.5 điểm dự thảo): Đóng gói che giấu trạng thái nội bộ của đối tượng.
- OOP_001_R2.a2 (2.5 điểm dự thảo): Truy cập trạng thái được kiểm soát qua các phương thức công khai.

### OOP_001_DRAFT_01 / natural_complete

Mình để dữ liệu với các hàm xử lý nó chung trong lớp. Phần bên trong được giấu, người dùng bên ngoài muốn đọc sửa thì đi qua những hàm được công khai.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `supported`. Bằng chứng: dữ liệu với các hàm xử lý nó chung trong lớp
- OOP_001_R2.a1: `supported`. Bằng chứng: Phần bên trong được giấu
- OOP_001_R2.a2: `supported`. Bằng chứng: đọc sửa thì đi qua những hàm được công khai

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_02 / mixed_terminology

Encapsulation gom data và methods vào class, hide internal state và expose public methods để kiểm soát access.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `supported`. Bằng chứng: gom data và methods vào class
- OOP_001_R2.a1: `supported`. Bằng chứng: hide internal state
- OOP_001_R2.a2: `supported`. Bằng chứng: expose public methods để kiểm soát access

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_03 / partial_first

Em hiểu là thuộc tính và các phương thức thao tác lên thuộc tính được đặt trong cùng một lớp.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `supported`. Bằng chứng: thuộc tính và các phương thức thao tác lên thuộc tính được đặt trong cùng một lớp
- OOP_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_04 / partial_hidden_state

Ý em nhớ là che trạng thái bên trong đối tượng, không nói thêm về cách cung cấp truy cập.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a1: `supported`. Bằng chứng: che trạng thái bên trong đối tượng
- OOP_001_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_05 / one_wrong_property

Dữ liệu và phương thức ở cùng lớp, nhưng trạng thái nội bộ không được che giấu. Việc truy cập được kiểm soát bằng các phương thức public.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `supported`. Bằng chứng: Dữ liệu và phương thức ở cùng lớp
- OOP_001_R2.a1: `contradicted`. Bằng chứng: trạng thái nội bộ không được che giấu
- OOP_001_R2.a2: `supported`. Bằng chứng: truy cập được kiểm soát bằng các phương thức public

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_06 / wrong_encapsulation

Đóng gói là tách dữ liệu khỏi lớp chứa phương thức, mở công khai toàn bộ trạng thái, để bên ngoài sửa trực tiếp tùy ý chứ không thông qua phương thức kiểm soát.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `contradicted`. Bằng chứng: tách dữ liệu khỏi lớp chứa phương thức
- OOP_001_R2.a1: `contradicted`. Bằng chứng: mở công khai toàn bộ trạng thái
- OOP_001_R2.a2: `contradicted`. Bằng chứng: sửa trực tiếp tùy ý chứ không thông qua phương thức kiểm soát

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_07 / explicit_correction

Em vừa bảo mở hết biến là nhầm. Đóng gói gom dữ liệu và hàm trong lớp, giấu trạng thái nội bộ và cho truy cập qua các hàm công khai có kiểm soát.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `supported`. Bằng chứng: gom dữ liệu và hàm trong lớp
- OOP_001_R2.a1: `supported`. Bằng chứng: giấu trạng thái nội bộ
- OOP_001_R2.a2: `supported`. Bằng chứng: truy cập qua các hàm công khai có kiểm soát

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_08 / retract_correct_to_wrong

Em đã nói giấu trạng thái là đúng, nhưng em xin rút lại. Em chốt đóng gói bắt buộc không che giấu trạng thái nội bộ.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a1: `contradicted`. Bằng chứng: đóng gói bắt buộc không che giấu trạng thái nội bộ
- OOP_001_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_09 / keywords_without_claim

Class, data, method, public, private là các từ em nhớ, chưa diễn đạt nội dung của đóng gói.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_001_DRAFT_10 / unresolved_conflict

Đóng gói che trạng thái bên trong. Đóng gói không che trạng thái bên trong. Em chưa chốt một ý.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- OOP_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_001_R2.a1: `needs_review`. Bằng chứng: Đóng gói che trạng thái bên trong. Đóng gói không che trạng thái bên trong. Em chưa chốt một ý
- OOP_001_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_002: Tính kế thừa (inheritance) dùng để làm gì?

Nhóm: `regression_only`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_002_R1.a1 (5.0 điểm dự thảo): Lớp con thừa hưởng thuộc tính và phương thức của lớp cha.
- OOP_002_R2.a1 (2.5 điểm dự thảo): Kế thừa giúp tái sử dụng mã.
- OOP_002_R2.a2 (2.5 điểm dự thảo): Lớp con có thể mở rộng hoặc ghi đè hành vi.

### OOP_002_DRAFT_01 / natural_complete

Lớp con nhận lại những thuộc tính và hàm mà lớp cha đã có. Như vậy dùng lại phần mã có sẵn, rồi lớp con thêm việc riêng hoặc làm lại cách chạy một hàm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `supported`. Bằng chứng: Lớp con nhận lại những thuộc tính và hàm mà lớp cha đã có
- OOP_002_R2.a1: `supported`. Bằng chứng: dùng lại phần mã có sẵn
- OOP_002_R2.a2: `supported`. Bằng chứng: lớp con thêm việc riêng hoặc làm lại cách chạy một hàm

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_02 / mixed_terminology

Subclass inherits fields và methods từ superclass, giúp code reuse và có thể extend hoặc override behavior.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `supported`. Bằng chứng: Subclass inherits fields và methods từ superclass
- OOP_002_R2.a1: `supported`. Bằng chứng: giúp code reuse
- OOP_002_R2.a2: `supported`. Bằng chứng: có thể extend hoặc override behavior

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_03 / partial_inheritance

Con dùng lại thuộc tính và phương thức cha đã có, nên không phải viết trùng phần mã ấy. Em chưa nói việc thay đổi hành vi.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `supported`. Bằng chứng: Con dùng lại thuộc tính và phương thức cha đã có
- OOP_002_R2.a1: `supported`. Bằng chứng: không phải viết trùng phần mã ấy
- OOP_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_04 / partial_extension

Lớp con được thêm hành vi mới hoặc ghi đè cách làm của phương thức đã thừa hưởng.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a2: `supported`. Bằng chứng: Lớp con được thêm hành vi mới hoặc ghi đè cách làm

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_05 / role_reversal

Lớp cha lấy thuộc tính và phương thức từ lớp con. Kế thừa giúp dùng lại mã; lớp con vẫn có thể thêm hoặc ghi đè hành vi.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `contradicted`. Bằng chứng: Lớp cha lấy thuộc tính và phương thức từ lớp con
- OOP_002_R2.a1: `supported`. Bằng chứng: giúp dùng lại mã
- OOP_002_R2.a2: `supported`. Bằng chứng: lớp con vẫn có thể thêm hoặc ghi đè hành vi

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_06 / wrong_permission

Lớp con dùng lại thuộc tính phương thức của cha và tái sử dụng mã, nhưng bị cấm hoàn toàn việc bổ sung hay ghi đè hành vi.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `supported`. Bằng chứng: Lớp con dùng lại thuộc tính phương thức của cha
- OOP_002_R2.a1: `supported`. Bằng chứng: tái sử dụng mã
- OOP_002_R2.a2: `contradicted`. Bằng chứng: bị cấm hoàn toàn việc bổ sung hay ghi đè hành vi

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_07 / explicit_correction

Em đảo chiều kế thừa là sai. Con thừa hưởng thuộc tính phương thức từ cha, dùng lại mã và có thể thêm hành vi hoặc ghi đè.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `supported`. Bằng chứng: Con thừa hưởng thuộc tính phương thức từ cha
- OOP_002_R2.a1: `supported`. Bằng chứng: dùng lại mã
- OOP_002_R2.a2: `supported`. Bằng chứng: có thể thêm hành vi hoặc ghi đè

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_08 / retract_correct_to_wrong

Em đã nói con có thể ghi đè hoặc thêm hành vi, nhưng rút lại. Em chốt con không được thêm bất cứ hành vi nào và cũng không được ghi đè.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a2: `contradicted`. Bằng chứng: con không được thêm bất cứ hành vi nào và cũng không được ghi đè

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_09 / keywords_without_claim

Cha, con, thuộc tính, phương thức và override em mới nhớ tên, chưa khẳng định chiều nhận hay quyền sửa hành vi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_002_DRAFT_10 / unresolved_conflict

Con thừa hưởng thuộc tính và phương thức của cha. Cha thừa hưởng thuộc tính và phương thức của con. Em chưa chọn chiều nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- OOP_002_R1.a1: `needs_review`. Bằng chứng: Con thừa hưởng thuộc tính và phương thức của cha. Cha thừa hưởng thuộc tính và phương thức của con. Em chưa chọn chiều nào
- OOP_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_002_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_003: Tính đa hình (polymorphism) là gì?

Nhóm: `test`. Hai tiêu chí liên quan chặt. Giảng viên cần cho phép diễn đạt hàm ý tương đương; không trừ điểm chỉ vì thiếu nguyên văn từ dynamic dispatch hoặc runtime.

- OOP_003_R1.a1 (6.0 điểm dự thảo): Cùng lời gọi phương thức có thể có hành vi khác nhau tùy kiểu thực của đối tượng.
- OOP_003_R2.a1 (4.0 điểm dự thảo): Dynamic dispatch chọn phương thức lúc chạy theo kiểu thực của đối tượng.

### OOP_003_DRAFT_01 / natural_complete

Cùng gọi một hàm nhưng đối tượng thực là loại nào thì chạy cách làm của loại đó. Lúc chương trình chạy mới chọn theo loại thật của đối tượng.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `supported`. Bằng chứng: Cùng gọi một hàm nhưng đối tượng thực là loại nào thì chạy cách làm của loại đó
- OOP_003_R2.a1: `supported`. Bằng chứng: Lúc chương trình chạy mới chọn theo loại thật của đối tượng

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_02 / mixed_terminology

Một method call có behavior khác theo actual object type; dynamic dispatch resolve method ở runtime dựa trên actual type đó.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `supported`. Bằng chứng: method call có behavior khác theo actual object type
- OOP_003_R2.a1: `supported`. Bằng chứng: dynamic dispatch resolve method ở runtime dựa trên actual type đó

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_03 / concise_equivalent

Khi chạy, cùng lời gọi đó được gửi tới cách cài đặt của đúng kiểu đối tượng thực tế nên các kiểu có thể thực hiện khác nhau.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `supported`. Bằng chứng: cùng lời gọi đó được gửi tới cách cài đặt của đúng kiểu đối tượng thực tế nên các kiểu có thể thực hiện khác nhau
- OOP_003_R2.a1: `supported`. Bằng chứng: Khi chạy, cùng lời gọi đó được gửi tới cách cài đặt của đúng kiểu đối tượng thực tế

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_04 / partial_dispatch

Em chỉ nêu bước chọn phương thức: khi chạy thì chọn bằng kiểu thực của đối tượng, chưa giải thích phần nhiều hành vi.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_003_R2.a1: `supported`. Bằng chứng: khi chạy thì chọn bằng kiểu thực của đối tượng

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_05 / one_wrong_dispatch

Cùng lời gọi có hành vi khác theo kiểu đối tượng thực. Nhưng dynamic dispatch chỉ quyết định ở compile-time bằng kiểu biến khai báo, không dùng kiểu thực lúc chạy.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `supported`. Bằng chứng: Cùng lời gọi có hành vi khác theo kiểu đối tượng thực
- OOP_003_R2.a1: `contradicted`. Bằng chứng: chỉ quyết định ở compile-time bằng kiểu biến khai báo, không dùng kiểu thực lúc chạy

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_06 / wrong_polymorphism

Đa hình buộc mọi kiểu đối tượng chạy y hệt nhau cho cùng lời gọi. Dynamic dispatch không chọn lúc chạy mà chỉ dùng kiểu khai báo lúc biên dịch.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `contradicted`. Bằng chứng: buộc mọi kiểu đối tượng chạy y hệt nhau cho cùng lời gọi
- OOP_003_R2.a1: `contradicted`. Bằng chứng: không chọn lúc chạy mà chỉ dùng kiểu khai báo lúc biên dịch

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_07 / explicit_correction

Em rút lại ý chọn theo kiểu khai báo lúc biên dịch. Đúng là chọn lúc chạy theo kiểu thực; cùng lời gọi có thể có cách thực hiện khác nhau theo kiểu thực ấy.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `supported`. Bằng chứng: cùng lời gọi có thể có cách thực hiện khác nhau theo kiểu thực ấy
- OOP_003_R2.a1: `supported`. Bằng chứng: chọn lúc chạy theo kiểu thực

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_08 / retract_correct_to_wrong

Em đã nói chọn lúc chạy nhưng xin rút lại. Em chốt dynamic dispatch chỉ chọn lúc biên dịch bằng kiểu khai báo, không chọn theo đối tượng thực khi chạy.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_003_R2.a1: `contradicted`. Bằng chứng: dynamic dispatch chỉ chọn lúc biên dịch bằng kiểu khai báo, không chọn theo đối tượng thực khi chạy

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_09 / keywords_without_claim

Em mới nhớ đa hình, method, type, dynamic dispatch là các thuật ngữ, chưa trình bày cơ chế của chúng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_003_DRAFT_10 / unresolved_conflict

Dynamic dispatch chọn theo kiểu thực lúc chạy. Dynamic dispatch chỉ chọn theo kiểu khai báo lúc biên dịch. Em chưa biết lấy ý nào làm kết luận.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- OOP_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_003_R2.a1: `needs_review`. Bằng chứng: Dynamic dispatch chọn theo kiểu thực lúc chạy. Dynamic dispatch chỉ chọn theo kiểu khai báo lúc biên dịch. Em chưa biết lấy ý nào làm kết luận

Ghi chú người duyệt: ____________________

## OOP_004: Phân biệt lớp trừu tượng (abstract class) và interface.

Nhóm: `validation`. Định nghĩa interface khác nhau theo ngôn ngữ; draft chỉ dùng phần hợp đồng hành vi và đa interface trong nguồn, không gán nhãn các hạn chế ngoài nguồn.

- OOP_004_R1.a1 (2.5 điểm dự thảo): Lớp trừu tượng có thể giữ trạng thái.
- OOP_004_R1.a2 (2.5 điểm dự thảo): Lớp trừu tượng có thể có cả phương thức trừu tượng và phương thức đã cài đặt.
- OOP_004_R2.a1 (2.5 điểm dự thảo): Interface quy định hợp đồng hành vi mà lớp thực hiện.
- OOP_004_R2.a2 (2.5 điểm dự thảo): Một lớp có thể cài đặt nhiều interface.

### OOP_004_DRAFT_01 / natural_complete

Lớp trừu tượng giữ được trạng thái, có hàm chưa có thân và hàm đã viết sẵn. Interface giống hợp đồng phải làm những hành vi nào; một lớp có thể nhận thực hiện nhiều hợp đồng như vậy.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `supported`. Bằng chứng: Lớp trừu tượng giữ được trạng thái
- OOP_004_R1.a2: `supported`. Bằng chứng: có hàm chưa có thân và hàm đã viết sẵn
- OOP_004_R2.a1: `supported`. Bằng chứng: hợp đồng phải làm những hành vi nào
- OOP_004_R2.a2: `supported`. Bằng chứng: một lớp có thể nhận thực hiện nhiều hợp đồng

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_02 / mixed_terminology

Abstract class có state, abstract methods lẫn implemented methods. Interface là behavior contract; class implement nhiều interfaces được.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `supported`. Bằng chứng: Abstract class có state
- OOP_004_R1.a2: `supported`. Bằng chứng: abstract methods lẫn implemented methods
- OOP_004_R2.a1: `supported`. Bằng chứng: Interface là behavior contract
- OOP_004_R2.a2: `supported`. Bằng chứng: class implement nhiều interfaces được

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_03 / partial_abstract_class

Abstract class có dữ liệu trạng thái và có thể chứa cả hàm trừu tượng lẫn hàm đã cài đặt.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `supported`. Bằng chứng: có dữ liệu trạng thái
- OOP_004_R1.a2: `supported`. Bằng chứng: cả hàm trừu tượng lẫn hàm đã cài đặt
- OOP_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_04 / partial_interface

Interface nêu hợp đồng hành vi cần thực hiện; một lớp thực hiện được nhiều interface.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a1: `supported`. Bằng chứng: nêu hợp đồng hành vi cần thực hiện
- OOP_004_R2.a2: `supported`. Bằng chứng: một lớp thực hiện được nhiều interface

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_05 / one_wrong_capability

Abstract class không thể giữ trạng thái, nhưng có cả hàm trừu tượng và hàm đã cài đặt. Interface là hợp đồng hành vi và một lớp có thể cài đặt nhiều interface.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `contradicted`. Bằng chứng: Abstract class không thể giữ trạng thái
- OOP_004_R1.a2: `supported`. Bằng chứng: có cả hàm trừu tượng và hàm đã cài đặt
- OOP_004_R2.a1: `supported`. Bằng chứng: Interface là hợp đồng hành vi
- OOP_004_R2.a2: `supported`. Bằng chứng: một lớp có thể cài đặt nhiều interface

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_06 / wrong_restrictions

Abstract class bị cấm có trạng thái và bị cấm có phương thức đã cài đặt. Một lớp tuyệt đối không được thực hiện nhiều interface.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `contradicted`. Bằng chứng: bị cấm có trạng thái
- OOP_004_R1.a2: `contradicted`. Bằng chứng: bị cấm có phương thức đã cài đặt
- OOP_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a2: `contradicted`. Bằng chứng: tuyệt đối không được thực hiện nhiều interface

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_07 / explicit_correction

Em nói abstract class không có state là nhầm. Nó giữ state, có hàm abstract cùng hàm có thân; interface quy định hợp đồng hành vi và một class có thể implement nhiều interface.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `supported`. Bằng chứng: Nó giữ state
- OOP_004_R1.a2: `supported`. Bằng chứng: có hàm abstract cùng hàm có thân
- OOP_004_R2.a1: `supported`. Bằng chứng: interface quy định hợp đồng hành vi
- OOP_004_R2.a2: `supported`. Bằng chứng: một class có thể implement nhiều interface

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_08 / retract_correct_to_wrong

Em đã nói class được thực hiện nhiều interface, nhưng em rút lại. Kết luận của em là class chỉ được đúng một interface, không thể có nhiều.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a2: `contradicted`. Bằng chứng: class chỉ được đúng một interface, không thể có nhiều

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_09 / keywords_without_claim

Abstract, interface, state, method và implement em chỉ đọc từ, chưa nêu đặc điểm hoặc khả năng nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_004_DRAFT_10 / unresolved_conflict

Abstract class có thể giữ state. Abstract class không thể giữ state. Em chưa có ý cuối cùng.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- OOP_004_R1.a1: `needs_review`. Bằng chứng: Abstract class có thể giữ state. Abstract class không thể giữ state. Em chưa có ý cuối cùng
- OOP_004_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_005: Constructor là gì và dùng để làm gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_005_R1.a1 (5.0 điểm dự thảo): Constructor là phương thức đặc biệt được gọi khi tạo đối tượng.
- OOP_005_R2.a1 (5.0 điểm dự thảo): Constructor khởi tạo giá trị ban đầu cho các thuộc tính.

### OOP_005_DRAFT_01 / natural_complete

Lúc đối tượng được tạo ra thì hàm khởi tạo đặc biệt chạy, để đặt các thuộc tính vào giá trị ban đầu.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `supported`. Bằng chứng: Lúc đối tượng được tạo ra thì hàm khởi tạo đặc biệt chạy
- OOP_005_R2.a1: `supported`. Bằng chứng: đặt các thuộc tính vào giá trị ban đầu

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_02 / mixed_terminology

Constructor là special method called khi create object; nó initialize các fields cho instance mới.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `supported`. Bằng chứng: special method called khi create object
- OOP_005_R2.a1: `supported`. Bằng chứng: initialize các fields cho instance mới

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_03 / partial_first

Constructor được gọi ở thời điểm tạo một đối tượng mới.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `supported`. Bằng chứng: được gọi ở thời điểm tạo một đối tượng mới
- OOP_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_04 / partial_last

Nhiệm vụ em biết là gán các giá trị khởi đầu cho thuộc tính của đối tượng.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_005_R2.a1: `supported`. Bằng chứng: gán các giá trị khởi đầu cho thuộc tính của đối tượng

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_05 / wrong_lifecycle

Constructor chỉ được gọi lúc hủy đối tượng chứ không lúc tạo; nó gán giá trị ban đầu cho các thuộc tính.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `contradicted`. Bằng chứng: chỉ được gọi lúc hủy đối tượng chứ không lúc tạo
- OOP_005_R2.a1: `supported`. Bằng chứng: gán giá trị ban đầu cho các thuộc tính

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_06 / wrong_purpose

Constructor được gọi khi tạo object, nhưng tuyệt đối không khởi tạo được giá trị của bất kỳ thuộc tính nào.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `supported`. Bằng chứng: được gọi khi tạo object
- OOP_005_R2.a1: `contradicted`. Bằng chứng: tuyệt đối không khởi tạo được giá trị của bất kỳ thuộc tính nào

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_07 / explicit_correction

Em vừa nhầm với hàm hủy. Constructor chạy khi tạo mới đối tượng và khởi gán các thuộc tính cho nó.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `supported`. Bằng chứng: Constructor chạy khi tạo mới đối tượng
- OOP_005_R2.a1: `supported`. Bằng chứng: khởi gán các thuộc tính cho nó

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_08 / retract_correct_to_wrong

Em đã nói constructor chạy khi tạo, nhưng rút lại. Em kết luận nó chỉ chạy khi hủy chứ không chạy khi tạo đối tượng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `contradicted`. Bằng chứng: chỉ chạy khi hủy chứ không chạy khi tạo đối tượng
- OOP_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_09 / keywords_without_claim

Em nhớ constructor, object và khởi tạo là các từ của bài, chưa giải thích lúc gọi hoặc việc nó làm.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_005_DRAFT_10 / unresolved_conflict

Constructor được gọi khi tạo. Constructor chỉ được gọi khi hủy chứ không khi tạo. Em chưa chọn phát biểu nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- OOP_005_R1.a1: `needs_review`. Bằng chứng: Constructor được gọi khi tạo. Constructor chỉ được gọi khi hủy chứ không khi tạo. Em chưa chọn phát biểu nào
- OOP_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_006: Overloading và overriding khác nhau ra sao?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_006_R1.a1 (5.0 điểm dự thảo): Overloading là các phương thức cùng tên, khác danh sách tham số trong cùng lớp.
- OOP_006_R2.a1 (5.0 điểm dự thảo): Overriding là lớp con định nghĩa lại phương thức cha với cùng chữ ký.

### OOP_006_DRAFT_01 / natural_complete

Nạp chồng là trong lớp có nhiều hàm trùng tên nhưng bộ tham số khác nhau. Ghi đè thì con viết lại hàm của cha mà chữ ký vẫn như cũ.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `supported`. Bằng chứng: trong lớp có nhiều hàm trùng tên nhưng bộ tham số khác nhau
- OOP_006_R2.a1: `supported`. Bằng chứng: con viết lại hàm của cha mà chữ ký vẫn như cũ

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_02 / mixed_terminology

Overload: same method name, different parameter lists trong class. Override: subclass redefine superclass method cùng signature.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `supported`. Bằng chứng: same method name, different parameter lists trong class
- OOP_006_R2.a1: `supported`. Bằng chứng: subclass redefine superclass method cùng signature

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_03 / partial_first

Overloading cho các phương thức trong cùng lớp giữ một tên nhưng đổi danh sách tham số.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `supported`. Bằng chứng: trong cùng lớp giữ một tên nhưng đổi danh sách tham số
- OOP_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_04 / partial_last

Overriding là lớp con viết lại cách thực hiện của phương thức lớp cha, giữ nguyên chữ ký.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_006_R2.a1: `supported`. Bằng chứng: lớp con viết lại cách thực hiện của phương thức lớp cha, giữ nguyên chữ ký

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_05 / one_wrong_signature

Overloading cùng tên khác tham số trong lớp. Overriding bắt buộc thay danh sách tham số, không được giữ cùng chữ ký của cha.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `supported`. Bằng chứng: Overloading cùng tên khác tham số trong lớp
- OOP_006_R2.a1: `contradicted`. Bằng chứng: Overriding bắt buộc thay danh sách tham số, không được giữ cùng chữ ký của cha

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_06 / role_reversal

Overloading là con ghi lại hàm cha cùng chữ ký. Overriding mới là các hàm cùng lớp cùng tên nhưng khác tham số.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `contradicted`. Bằng chứng: Overloading là con ghi lại hàm cha cùng chữ ký
- OOP_006_R2.a1: `contradicted`. Bằng chứng: Overriding mới là các hàm cùng lớp cùng tên nhưng khác tham số

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_07 / explicit_correction

Em vừa đảo overload và override. Sửa lại overload cùng tên khác bộ tham số trong một lớp; override là con viết lại hàm cha nhưng giữ chữ ký.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `supported`. Bằng chứng: overload cùng tên khác bộ tham số trong một lớp
- OOP_006_R2.a1: `supported`. Bằng chứng: override là con viết lại hàm cha nhưng giữ chữ ký

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_08 / retract_correct_to_wrong

Em đã nói override giữ chữ ký nhưng xin rút lại. Em chốt override phải khác danh sách tham số với phương thức cha.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_006_R2.a1: `contradicted`. Bằng chứng: override phải khác danh sách tham số với phương thức cha

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_09 / keywords_without_claim

Em thuộc overload, override, signature và tham số nhưng chưa gắn ý nghĩa với từng thuật ngữ.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_006_DRAFT_10 / unresolved_conflict

Override giữ chữ ký phương thức cha. Override buộc đổi chữ ký phương thức cha. Em đang phân vân giữa hai câu.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- OOP_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_006_R2.a1: `needs_review`. Bằng chứng: Override giữ chữ ký phương thức cha. Override buộc đổi chữ ký phương thức cha. Em đang phân vân giữa hai câu

Ghi chú người duyệt: ____________________

## OOP_007: Lớp (class) và đối tượng (object) khác nhau thế nào?

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_007_R1.a1 (5.0 điểm dự thảo): Lớp là khuôn mẫu định nghĩa thuộc tính và hành vi.
- OOP_007_R2.a1 (2.5 điểm dự thảo): Đối tượng là một thể hiện cụ thể của lớp.
- OOP_007_R2.a2 (2.5 điểm dự thảo): Đối tượng có trạng thái riêng.

### OOP_007_DRAFT_01 / natural_complete

Lớp như bản vẽ mô tả có những dữ liệu và việc gì làm được. Đối tượng là một cái cụ thể tạo theo bản vẽ, giữ các giá trị của riêng cái đó.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `supported`. Bằng chứng: bản vẽ mô tả có những dữ liệu và việc gì làm được
- OOP_007_R2.a1: `supported`. Bằng chứng: một cái cụ thể tạo theo bản vẽ
- OOP_007_R2.a2: `supported`. Bằng chứng: giữ các giá trị của riêng cái đó

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_02 / mixed_terminology

Class là blueprint của attributes và behavior; object là concrete instance của class với own state.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `supported`. Bằng chứng: blueprint của attributes và behavior
- OOP_007_R2.a1: `supported`. Bằng chứng: concrete instance của class
- OOP_007_R2.a2: `supported`. Bằng chứng: với own state

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_03 / partial_first

Lớp là bản mẫu ghi những thuộc tính và phương thức mà các đối tượng sẽ có.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `supported`. Bằng chứng: bản mẫu ghi những thuộc tính và phương thức
- OOP_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_04 / partial_object

Object là một thể hiện cụ thể của class, mỗi object có những giá trị trạng thái của riêng mình.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a1: `supported`. Bằng chứng: một thể hiện cụ thể của class
- OOP_007_R2.a2: `supported`. Bằng chứng: mỗi object có những giá trị trạng thái của riêng mình

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_05 / one_wrong_identity

Class là instance cụ thể chứ không phải bản thiết kế. Object là thể hiện cụ thể của class và có trạng thái riêng.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `contradicted`. Bằng chứng: Class là instance cụ thể chứ không phải bản thiết kế
- OOP_007_R2.a1: `supported`. Bằng chứng: Object là thể hiện cụ thể của class
- OOP_007_R2.a2: `supported`. Bằng chứng: có trạng thái riêng

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_06 / reversed_identity

Object là bản mẫu định nghĩa các thuộc tính hành vi để tạo ra class. Class mới là một instance cụ thể, không phải bản thiết kế.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `contradicted`. Bằng chứng: Class mới là một instance cụ thể, không phải bản thiết kế
- OOP_007_R2.a1: `contradicted`. Bằng chứng: Object là bản mẫu định nghĩa các thuộc tính hành vi để tạo ra class
- OOP_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_07 / explicit_correction

Em đã đảo lớp với đối tượng, xin sửa. Class là mẫu định nghĩa thuộc tính hành vi; object là một thể hiện cụ thể theo mẫu đó và có trạng thái riêng.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `supported`. Bằng chứng: Class là mẫu định nghĩa thuộc tính hành vi
- OOP_007_R2.a1: `supported`. Bằng chứng: object là một thể hiện cụ thể theo mẫu đó
- OOP_007_R2.a2: `supported`. Bằng chứng: có trạng thái riêng

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_08 / retract_correct_to_wrong

Em đã nói các object có trạng thái riêng nhưng rút lại. Em chốt không object nào có trạng thái riêng, tất cả đều bắt buộc dùng chung một trạng thái.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a2: `contradicted`. Bằng chứng: không object nào có trạng thái riêng, tất cả đều bắt buộc dùng chung một trạng thái

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_09 / keywords_without_claim

Class, object, blueprint và state em chỉ nhớ từ, chưa nêu quan hệ giữa chúng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_007_DRAFT_10 / unresolved_conflict

Object là một thể hiện của class. Object không phải thể hiện của class mà là mẫu tạo ra class. Em chưa biết kết luận nào.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- OOP_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_007_R2.a1: `needs_review`. Bằng chứng: Object là một thể hiện của class. Object không phải thể hiện của class mà là mẫu tạo ra class. Em chưa biết kết luận nào
- OOP_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_008: Khi nào nên dùng composition thay vì inheritance?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_008_R1.a1 (2.5 điểm dự thảo): Composition biểu diễn quan hệ has-a.
- OOP_008_R1.a2 (2.5 điểm dự thảo): Inheritance biểu diễn quan hệ is-a.
- OOP_008_R2.a1 (2.5 điểm dự thảo): Composition thường ít ràng buộc chặt hơn kế thừa.
- OOP_008_R2.a2 (2.5 điểm dự thảo): Composition thường linh hoạt hơn khi thay đổi hành vi.

### OOP_008_DRAFT_01 / natural_complete

Composition là một đối tượng có một thành phần, kế thừa là một loại của lớp cha. Ghép thành phần thường bớt buộc chặt hơn, và thay thành phần để đổi hành vi linh hoạt hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `supported`. Bằng chứng: Composition là một đối tượng có một thành phần
- OOP_008_R1.a2: `supported`. Bằng chứng: kế thừa là một loại của lớp cha
- OOP_008_R2.a1: `supported`. Bằng chứng: thường bớt buộc chặt hơn
- OOP_008_R2.a2: `supported`. Bằng chứng: đổi hành vi linh hoạt hơn

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_02 / mixed_terminology

Composition là has-a; inheritance là is-a. Composition thường less tightly coupled và flexible hơn khi change behavior.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `supported`. Bằng chứng: Composition là has-a
- OOP_008_R1.a2: `supported`. Bằng chứng: inheritance là is-a
- OOP_008_R2.a1: `supported`. Bằng chứng: less tightly coupled
- OOP_008_R2.a2: `supported`. Bằng chứng: flexible hơn khi change behavior

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_03 / partial_relations

Composition nói quan hệ có-một; inheritance là quan hệ là-một. Phần ưu nhược em chưa rõ.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `supported`. Bằng chứng: Composition nói quan hệ có-một
- OOP_008_R1.a2: `supported`. Bằng chứng: inheritance là quan hệ là-một
- OOP_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_04 / partial_tradeoff

Dùng composition thường giảm liên kết chặt và dễ thay đổi hành vi bằng thay thành phần.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a1: `supported`. Bằng chứng: thường giảm liên kết chặt
- OOP_008_R2.a2: `supported`. Bằng chứng: dễ thay đổi hành vi bằng thay thành phần

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_05 / one_wrong_relation

Composition là is-a chứ không has-a; inheritance cũng is-a. Ghép thành phần thường ít ràng buộc và linh hoạt hơn khi đổi hành vi.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `contradicted`. Bằng chứng: Composition là is-a chứ không has-a
- OOP_008_R1.a2: `supported`. Bằng chứng: inheritance cũng is-a
- OOP_008_R2.a1: `supported`. Bằng chứng: thường ít ràng buộc
- OOP_008_R2.a2: `supported`. Bằng chứng: linh hoạt hơn khi đổi hành vi

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_06 / reversed_relations

Em gán composition cho is-a, còn inheritance cho has-a, chứ không phải ngược lại.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `contradicted`. Bằng chứng: composition cho is-a
- OOP_008_R1.a2: `contradicted`. Bằng chứng: inheritance cho has-a
- OOP_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_07 / explicit_correction

Em vừa đảo hai quan hệ, sửa lại composition là has-a và inheritance là is-a. Composition ít buộc chặt hơn và linh hoạt hơn khi cần thay hành vi.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `supported`. Bằng chứng: composition là has-a
- OOP_008_R1.a2: `supported`. Bằng chứng: inheritance là is-a
- OOP_008_R2.a1: `supported`. Bằng chứng: ít buộc chặt hơn
- OOP_008_R2.a2: `supported`. Bằng chứng: linh hoạt hơn khi cần thay hành vi

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_08 / retract_correct_to_wrong

Em đã nói composition ít coupling và linh hoạt hơn, nhưng rút lại. Em chốt composition luôn buộc chặt hơn kế thừa và tuyệt đối kém linh hoạt hơn khi đổi hành vi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a1: `contradicted`. Bằng chứng: luôn buộc chặt hơn kế thừa
- OOP_008_R2.a2: `contradicted`. Bằng chứng: tuyệt đối kém linh hoạt hơn khi đổi hành vi

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_09 / keywords_without_claim

Has-a, is-a, coupling và composition là các từ em nhớ thôi, chưa phát biểu quan hệ hay ưu điểm.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_008_DRAFT_10 / unresolved_conflict

Composition là has-a. Composition không phải has-a mà là is-a. Em chưa lựa chọn một trong hai.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- OOP_008_R1.a1: `needs_review`. Bằng chứng: Composition là has-a. Composition không phải has-a mà là is-a. Em chưa lựa chọn một trong hai
- OOP_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## OOP_009: Nguyên lý Single Responsibility (SRP) nói gì?

Nhóm: `validation`. Hai tiêu chí nguồn gần tương đương về ngữ nghĩa. Draft gán supported cho cả hai khi lời đáp diễn đạt đầy đủ nguyên tắc bằng một trong hai cách; giảng viên nên cân nhắc gộp để tránh chấm trùng ý.

- OOP_009_R1.a1 (5.0 điểm dự thảo): Theo SRP, mỗi lớp chỉ nên có một trách nhiệm.
- OOP_009_R2.a1 (5.0 điểm dự thảo): Theo SRP, mỗi lớp chỉ nên có một lý do thay đổi để dễ bảo trì.

### OOP_009_DRAFT_01 / natural_complete

Một lớp nên tập trung làm một nhiệm vụ thôi. Khi đó chỉ có một lý do khiến mình phải sửa nó, giúp bảo trì dễ hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `supported`. Bằng chứng: Một lớp nên tập trung làm một nhiệm vụ thôi
- OOP_009_R2.a1: `supported`. Bằng chứng: chỉ có một lý do khiến mình phải sửa nó, giúp bảo trì dễ hơn

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_02 / mixed_terminology

Single Responsibility: class có single responsibility và single reason to change để dễ maintain.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `supported`. Bằng chứng: class có single responsibility
- OOP_009_R2.a1: `supported`. Bằng chứng: single reason to change để dễ maintain

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_03 / concise_equivalent

Đừng nhét các nhiệm vụ độc lập vào cùng lớp; mỗi lớp chỉ chịu một trách nhiệm, nhờ đó dễ bảo trì.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `supported`. Bằng chứng: mỗi lớp chỉ chịu một trách nhiệm
- OOP_009_R2.a1: `supported`. Bằng chứng: mỗi lớp chỉ chịu một trách nhiệm, nhờ đó dễ bảo trì

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_04 / concise_reason_to_change

Em hiểu mỗi class chỉ nên có một lý do thay đổi, tức tập trung vào một trách nhiệm để dễ bảo trì.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `supported`. Bằng chứng: tập trung vào một trách nhiệm
- OOP_009_R2.a1: `supported`. Bằng chứng: một lý do thay đổi, tức tập trung vào một trách nhiệm để dễ bảo trì

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_05 / wrong_principle

SRP khuyến khích gom nhiều trách nhiệm độc lập vào một lớp và để lớp có càng nhiều lý do thay đổi càng tốt.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `contradicted`. Bằng chứng: gom nhiều trách nhiệm độc lập vào một lớp
- OOP_009_R2.a1: `contradicted`. Bằng chứng: càng nhiều lý do thay đổi càng tốt

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_06 / benefit_only

Em chỉ nhớ nó có lợi cho bảo trì, còn nguyên tắc phân chia trách nhiệm và lý do thay đổi thì em chưa nêu được.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_07 / explicit_correction

Em rút lại việc gom nhiều nhiệm vụ. Theo SRP, mỗi lớp chỉ một trách nhiệm, một lý do thay đổi, để công việc bảo trì dễ hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `supported`. Bằng chứng: mỗi lớp chỉ một trách nhiệm
- OOP_009_R2.a1: `supported`. Bằng chứng: một lý do thay đổi, để công việc bảo trì dễ hơn

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_08 / retract_correct_to_wrong

Em đã nói một trách nhiệm, một lý do sửa, nhưng xin rút lại. Em chốt SRP bắt lớp có nhiều nhiệm vụ độc lập và nhiều lý do thay đổi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `contradicted`. Bằng chứng: SRP bắt lớp có nhiều nhiệm vụ độc lập
- OOP_009_R2.a1: `contradicted`. Bằng chứng: nhiều lý do thay đổi

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_09 / keywords_without_claim

SRP, trách nhiệm, thay đổi và bảo trì em nhớ tên nhưng chưa đưa ra yêu cầu nào cho một lớp.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_009_DRAFT_10 / unresolved_conflict

SRP yêu cầu một trách nhiệm và một lý do đổi. SRP yêu cầu nhiều trách nhiệm độc lập và nhiều lý do đổi. Em không chọn được phát biểu nào.

Khoảng điểm đề xuất: 0.0–10.0/10. Không phải điểm đã duyệt.

- OOP_009_R1.a1: `needs_review`. Bằng chứng: SRP yêu cầu một trách nhiệm và một lý do đổi. SRP yêu cầu nhiều trách nhiệm độc lập và nhiều lý do đổi. Em không chọn được phát biểu nào
- OOP_009_R2.a1: `needs_review`. Bằng chứng: SRP yêu cầu một trách nhiệm và một lý do đổi. SRP yêu cầu nhiều trách nhiệm độc lập và nhiều lý do đổi. Em không chọn được phát biểu nào

Ghi chú người duyệt: ____________________

## OOP_010: Thành viên static trong một lớp có đặc điểm gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- OOP_010_R1.a1 (5.0 điểm dự thảo): Thành viên static thuộc về lớp chứ không thuộc riêng từng đối tượng.
- OOP_010_R2.a1 (2.5 điểm dự thảo): Các đối tượng dùng chung thành viên static.
- OOP_010_R2.a2 (2.5 điểm dự thảo): Có thể truy cập thành viên static qua tên lớp mà không cần tạo đối tượng.

### OOP_010_DRAFT_01 / natural_complete

Static gắn với lớp chứ không gắn riêng một object. Các object dùng chung nó, và mình gọi qua tên lớp được ngay cả khi chưa tạo object nào.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `supported`. Bằng chứng: gắn với lớp chứ không gắn riêng một object
- OOP_010_R2.a1: `supported`. Bằng chứng: Các object dùng chung nó
- OOP_010_R2.a2: `supported`. Bằng chứng: gọi qua tên lớp được ngay cả khi chưa tạo object nào

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_02 / mixed_terminology

Static là class-level member, shared giữa các instances và access bằng class name không cần new instance.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `supported`. Bằng chứng: class-level member
- OOP_010_R2.a1: `supported`. Bằng chứng: shared giữa các instances
- OOP_010_R2.a2: `supported`. Bằng chứng: access bằng class name không cần new instance

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_03 / partial_first

Em biết static thuộc về class thay vì thuộc riêng mỗi instance, chưa nêu thêm cách dùng.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `supported`. Bằng chứng: thuộc về class thay vì thuộc riêng mỗi instance
- OOP_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_04 / partial_access

Ta có thể gọi thành viên static bằng tên lớp dù chưa tạo đối tượng.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a2: `supported`. Bằng chứng: gọi thành viên static bằng tên lớp dù chưa tạo đối tượng

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_05 / one_wrong_sharing

Static thuộc lớp nhưng mỗi object có bản static riêng, không chia sẻ. Vẫn truy cập qua tên lớp được mà không cần new.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `supported`. Bằng chứng: Static thuộc lớp
- OOP_010_R2.a1: `contradicted`. Bằng chứng: mỗi object có bản static riêng, không chia sẻ
- OOP_010_R2.a2: `supported`. Bằng chứng: truy cập qua tên lớp được mà không cần new

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_06 / wrong_ownership

Static chỉ thuộc từng object, mỗi object có bản riêng. Bắt buộc new một object rồi mới truy cập được, không gọi bằng tên lớp được.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `contradicted`. Bằng chứng: Static chỉ thuộc từng object
- OOP_010_R2.a1: `contradicted`. Bằng chứng: mỗi object có bản riêng
- OOP_010_R2.a2: `contradicted`. Bằng chứng: Bắt buộc new một object rồi mới truy cập được, không gọi bằng tên lớp được

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_07 / explicit_correction

Em nói static có bản riêng cho mỗi object là nhầm. Nó thuộc lớp, các object chia sẻ một bản, và gọi bằng tên lớp không cần tạo đối tượng.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `supported`. Bằng chứng: Nó thuộc lớp
- OOP_010_R2.a1: `supported`. Bằng chứng: các object chia sẻ một bản
- OOP_010_R2.a2: `supported`. Bằng chứng: gọi bằng tên lớp không cần tạo đối tượng

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_08 / retract_correct_to_wrong

Em đã nói không cần tạo object, nhưng xin rút lại. Em chốt muốn truy cập static luôn phải new object, không được chỉ dùng tên lớp.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a2: `contradicted`. Bằng chứng: muốn truy cập static luôn phải new object, không được chỉ dùng tên lớp

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_09 / keywords_without_claim

Static, class, instance và shared em chỉ nhớ từ, chưa nêu static thuộc ai hay cách truy cập.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### OOP_010_DRAFT_10 / unresolved_conflict

Các object dùng chung static. Mỗi object có một bản static riêng, không dùng chung. Em chưa chốt ý nào.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- OOP_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- OOP_010_R2.a1: `needs_review`. Bằng chứng: Các object dùng chung static. Mỗi object có một bản static riêng, không dùng chung. Em chưa chốt ý nào
- OOP_010_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________
