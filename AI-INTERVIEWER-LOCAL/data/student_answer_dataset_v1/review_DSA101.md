# Bản đọc duyệt DSA101

Nhãn và điểm đều là AI đề xuất; chưa có giảng viên duyệt.

## DSA_001: Stack và queue khác nhau như thế nào?

Nhóm: `regression_only`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_001_R1.a1 (5.0 điểm dự thảo): Stack lấy phần tử được đưa vào sau cùng ra trước.
- DSA_001_R2.a1 (5.0 điểm dự thảo): Queue lấy phần tử được đưa vào trước ra trước.

### DSA_001_DRAFT_01 / natural_complete

Với ngăn xếp, món vừa bỏ lên sẽ được lấy xuống đầu tiên. Hàng đợi thì ai vào trước được lấy ra trước.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `supported`. Bằng chứng: món vừa bỏ lên sẽ được lấy xuống đầu tiên
- DSA_001_R2.a1: `supported`. Bằng chứng: ai vào trước được lấy ra trước

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_02 / mixed_terminology

Stack theo LIFO, nghĩa là last in first out. Queue theo FIFO, first in first out.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `supported`. Bằng chứng: Stack theo LIFO, nghĩa là last in first out
- DSA_001_R2.a1: `supported`. Bằng chứng: Queue theo FIFO, first in first out

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_03 / partial_first

Em nhớ stack giống chồng khay, khay đặt lên cuối thì nhấc xuống trước. Queue em chưa giải thích được.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `supported`. Bằng chứng: khay đặt lên cuối thì nhấc xuống trước
- DSA_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_04 / partial_last

Về queue, phần tử nào xếp vào sớm nhất thì được lấy ra sớm nhất. Stack thì em quên rồi.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_001_R2.a1: `supported`. Bằng chứng: phần tử nào xếp vào sớm nhất thì được lấy ra sớm nhất

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_05 / one_wrong_relation

Stack lấy cái thêm đầu tiên ra trước; queue cũng lấy cái thêm đầu tiên ra trước.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `contradicted`. Bằng chứng: Stack lấy cái thêm đầu tiên ra trước
- DSA_001_R2.a1: `supported`. Bằng chứng: queue cũng lấy cái thêm đầu tiên ra trước

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_06 / role_reversal

Em nghĩ stack vào trước ra trước, còn queue mới vào sau ra trước.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `contradicted`. Bằng chứng: stack vào trước ra trước
- DSA_001_R2.a1: `contradicted`. Bằng chứng: queue mới vào sau ra trước

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_07 / explicit_correction

Lúc nãy em đảo hai cái. Em sửa lại: stack vào sau ra trước, queue vào trước ra trước.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `supported`. Bằng chứng: Em sửa lại: stack vào sau ra trước
- DSA_001_R2.a1: `supported`. Bằng chứng: queue vào trước ra trước

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_08 / retract_correct_to_wrong

Ban đầu em nói stack vào sau ra trước và queue vào trước ra trước. Em rút lại và chốt ngược lại: stack vào trước ra trước, queue vào sau ra trước.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `contradicted`. Bằng chứng: Em rút lại và chốt ngược lại: stack vào trước ra trước
- DSA_001_R2.a1: `contradicted`. Bằng chứng: queue vào sau ra trước

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_09 / keywords_without_claim

Stack, queue, LIFO, FIFO là các từ em nhớ, nhưng em chưa biết từ nào đi với cách lấy phần tử nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_001_DRAFT_10 / unresolved_conflict

Stack lấy phần tử mới nhất trước. Stack cũng lấy phần tử cũ nhất trước. Em chưa chọn được ý nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- DSA_001_R1.a1: `needs_review`. Bằng chứng: Stack lấy phần tử mới nhất trước. Stack cũng lấy phần tử cũ nhất trước. Em chưa chọn được ý nào
- DSA_001_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_002: Ký hiệu Big-O biểu diễn điều gì?

Nhóm: `regression_only`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_002_R1.a1 (6.0 điểm dự thảo): Big-O mô tả cận trên của mức tăng chi phí thời gian hoặc bộ nhớ theo kích thước đầu vào.
- DSA_002_R2.a1 (4.0 điểm dự thảo): Trong phân tích Big-O có thể bỏ qua hệ số hằng và số hạng bậc thấp.

### DSA_002_DRAFT_01 / natural_complete

Nó cho biết mức chi phí tăng không vượt quá bậc nào khi đầu vào lớn lên. Mình chỉ giữ bậc chi phối, không giữ hệ số hằng và các bậc nhỏ hơn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `supported`. Bằng chứng: mức chi phí tăng không vượt quá bậc nào khi đầu vào lớn lên
- DSA_002_R2.a1: `supported`. Bằng chứng: chỉ giữ bậc chi phối, không giữ hệ số hằng và các bậc nhỏ hơn

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_02 / mixed_terminology

Big-O là asymptotic upper bound cho time hoặc space khi n tăng. Phân tích này bỏ constant factors và lower-order terms.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `supported`. Bằng chứng: asymptotic upper bound cho time hoặc space khi n tăng
- DSA_002_R2.a1: `supported`. Bằng chứng: bỏ constant factors và lower-order terms

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_03 / partial_first

Theo em nó là giới hạn trên cho tốc độ tăng chi phí khi số phần tử đầu vào tăng lên.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `supported`. Bằng chứng: giới hạn trên cho tốc độ tăng chi phí khi số phần tử đầu vào tăng lên
- DSA_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_04 / partial_last

Khi viết Big-O, em bỏ các hệ số hằng và số hạng bậc thấp. Phần định nghĩa em chưa nhớ.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_002_R2.a1: `supported`. Bằng chứng: bỏ các hệ số hằng và số hạng bậc thấp

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_05 / one_wrong_relation

Big-O cho cận dưới, không phải cận trên của chi phí theo n. Hệ số hằng và bậc thấp thì bỏ đi.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `contradicted`. Bằng chứng: Big-O cho cận dưới, không phải cận trên của chi phí theo n
- DSA_002_R2.a1: `supported`. Bằng chứng: Hệ số hằng và bậc thấp thì bỏ đi

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_06 / wrong_quantities

Big-O chỉ là số giây chính xác cho một lần chạy, không mô tả mức tăng theo đầu vào. Khi phân tích phải giữ nguyên mọi hệ số hằng và mọi bậc thấp.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `contradicted`. Bằng chứng: chỉ là số giây chính xác cho một lần chạy, không mô tả mức tăng theo đầu vào
- DSA_002_R2.a1: `contradicted`. Bằng chứng: phải giữ nguyên mọi hệ số hằng và mọi bậc thấp

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_07 / explicit_correction

Em nhầm chữ dưới với trên. Đúng phải là cận trên của mức tăng chi phí theo kích thước đầu vào; các hệ số hằng và số hạng thấp có thể bỏ.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `supported`. Bằng chứng: cận trên của mức tăng chi phí theo kích thước đầu vào
- DSA_002_R2.a1: `supported`. Bằng chứng: các hệ số hằng và số hạng thấp có thể bỏ

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_08 / retract_correct_to_wrong

Em đã nói Big-O là cận trên theo n, nhưng em rút lại. Kết luận của em là nó chỉ mô tả cận dưới theo kích thước đầu vào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `contradicted`. Bằng chứng: Kết luận của em là nó chỉ mô tả cận dưới theo kích thước đầu vào
- DSA_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_09 / keywords_without_claim

Em nhớ có n, hệ số, cận và thời gian, nhưng chưa phát biểu định nghĩa hay quy tắc bỏ số hạng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_002_DRAFT_10 / unresolved_conflict

Big-O là cận trên theo n. Big-O là cận dưới theo n. Em đang phân vân giữa hai ý này.

Khoảng điểm đề xuất: 0.0–6.0/10. Không phải điểm đã duyệt.

- DSA_002_R1.a1: `needs_review`. Bằng chứng: Big-O là cận trên theo n. Big-O là cận dưới theo n. Em đang phân vân giữa hai ý này
- DSA_002_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_003: Binary search hoạt động thế nào và độ phức tạp ra sao?

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_003_R1.a1 (3.0 điểm dự thảo): Tìm kiếm nhị phân cần dữ liệu đã sắp xếp.
- DSA_003_R2.a1 (2.0 điểm dự thảo): Tìm kiếm nhị phân so sánh giá trị cần tìm với phần tử giữa khoảng tìm kiếm.
- DSA_003_R2.a2 (2.0 điểm dự thảo): Sau mỗi bước tìm kiếm nhị phân, loại bỏ một nửa khoảng tìm kiếm.
- DSA_003_R3.a1 (3.0 điểm dự thảo): Thời gian tìm kiếm nhị phân có độ phức tạp O(log n).

### DSA_003_DRAFT_01 / natural_complete

Dãy phải được xếp thứ tự. Em đối chiếu số cần tìm với số ở giữa, giữ nửa có thể chứa nó rồi lặp lại. Thời gian tăng theo log n.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `supported`. Bằng chứng: Dãy phải được xếp thứ tự
- DSA_003_R2.a1: `supported`. Bằng chứng: đối chiếu số cần tìm với số ở giữa
- DSA_003_R2.a2: `supported`. Bằng chứng: giữ nửa có thể chứa nó rồi lặp lại
- DSA_003_R3.a1: `supported`. Bằng chứng: Thời gian tăng theo log n

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_02 / mixed_terminology

Binary search dùng sorted data, compare target với middle, discard một nửa search range mỗi bước và có time complexity O(log n).

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `supported`. Bằng chứng: dùng sorted data
- DSA_003_R2.a1: `supported`. Bằng chứng: compare target với middle
- DSA_003_R2.a2: `supported`. Bằng chứng: discard một nửa search range mỗi bước
- DSA_003_R3.a1: `supported`. Bằng chứng: time complexity O(log n)

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_03 / partial_first

Điều kiện em biết là các phần tử đã có thứ tự từ trước, còn cách thu hẹp và độ phức tạp thì em chưa rõ.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `supported`. Bằng chứng: các phần tử đã có thứ tự từ trước
- DSA_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_04 / partial_mechanism

So giá trị cần tìm với phần tử chính giữa; dựa vào kết quả mà bỏ đi một nửa vùng đang xét.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a1: `supported`. Bằng chứng: So giá trị cần tìm với phần tử chính giữa
- DSA_003_R2.a2: `supported`. Bằng chứng: bỏ đi một nửa vùng đang xét
- DSA_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_05 / wrong_precondition

Không cần sắp xếp, dãy lộn xộn vẫn luôn tìm nhị phân đúng. Cứ so ô giữa, bỏ nửa khoảng và thời gian O(log n).

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `contradicted`. Bằng chứng: Không cần sắp xếp, dãy lộn xộn vẫn luôn tìm nhị phân đúng
- DSA_003_R2.a1: `supported`. Bằng chứng: so ô giữa
- DSA_003_R2.a2: `supported`. Bằng chứng: bỏ nửa khoảng
- DSA_003_R3.a1: `supported`. Bằng chứng: thời gian O(log n)

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_06 / wrong_quantity

Mỗi bước chỉ bỏ một phần tử chứ không bỏ một nửa. Độ phức tạp là O(n), không phải O(log n).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a2: `contradicted`. Bằng chứng: chỉ bỏ một phần tử chứ không bỏ một nửa
- DSA_003_R3.a1: `contradicted`. Bằng chứng: Độ phức tạp là O(n), không phải O(log n)

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_07 / explicit_correction

Em nói không cần thứ tự là sai. Phải sắp xếp trước, so với phần tử giữa rồi bỏ nửa vùng tìm. Kết quả độ phức tạp em chốt là O(log n).

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `supported`. Bằng chứng: Phải sắp xếp trước
- DSA_003_R2.a1: `supported`. Bằng chứng: so với phần tử giữa
- DSA_003_R2.a2: `supported`. Bằng chứng: bỏ nửa vùng tìm
- DSA_003_R3.a1: `supported`. Bằng chứng: độ phức tạp em chốt là O(log n)

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_08 / retract_correct_to_wrong

Em đã trả lời O(log n), nhưng xin rút lại. Em chốt thời gian của binary search là O(n) thay vì O(log n).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R3.a1: `contradicted`. Bằng chứng: Em chốt thời gian của binary search là O(n) thay vì O(log n)

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_09 / keywords_without_claim

Các từ sorted, middle, nửa và log n em chỉ nhớ tên; em chưa giải thích được chúng liên quan thế nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_003_DRAFT_10 / unresolved_conflict

Binary search cần dãy đã sắp xếp. Nó cũng không cần dãy đã sắp xếp. Em không biết chọn mệnh đề nào.

Khoảng điểm đề xuất: 0.0–3.0/10. Không phải điểm đã duyệt.

- DSA_003_R1.a1: `needs_review`. Bằng chứng: Binary search cần dãy đã sắp xếp. Nó cũng không cần dãy đã sắp xếp. Em không biết chọn mệnh đề nào
- DSA_003_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_003_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_004: So sánh mảng và danh sách liên kết.

Nhóm: `train`. Chi phí sửa linked list giả định đã có các liên kết cần thiết, kể cả nút trước khi cần. Giảng viên cần xác nhận điều kiện này trước khi duyệt.

- DSA_004_R1.a1 (5.0 điểm dự thảo): Mảng cho phép truy cập theo chỉ số trong O(1).
- DSA_004_R2.a1 (2.5 điểm dự thảo): Danh sách liên kết chèn hoặc xóa tại vị trí đã có các liên kết cần thiết trong O(1).
- DSA_004_R2.a2 (2.5 điểm dự thảo): Truy cập danh sách liên kết theo chỉ số tốn O(n).

### DSA_004_DRAFT_01 / natural_complete

Mảng có index là đọc ngay, thời gian hằng. Danh sách nối nếu đã nắm nút và liên kết cần sửa thì thêm bớt mất thời gian hằng, nhưng tìm ô thứ i phải đi dọc danh sách nên tuyến tính.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `supported`. Bằng chứng: Mảng có index là đọc ngay, thời gian hằng
- DSA_004_R2.a1: `supported`. Bằng chứng: nếu đã nắm nút và liên kết cần sửa thì thêm bớt mất thời gian hằng
- DSA_004_R2.a2: `supported`. Bằng chứng: tìm ô thứ i phải đi dọc danh sách nên tuyến tính

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_02 / mixed_terminology

Array random access theo index là O(1). Linked list insert/delete là O(1) khi đã có các links cần thiết; indexed access của list là O(n).

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `supported`. Bằng chứng: Array random access theo index là O(1)
- DSA_004_R2.a1: `supported`. Bằng chứng: insert/delete là O(1) khi đã có các links cần thiết
- DSA_004_R2.a2: `supported`. Bằng chứng: indexed access của list là O(n)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_03 / partial_first

Em chỉ nhớ lấy mảng theo chỉ số tốn thời gian không đổi, không phải duyệt từng ô.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `supported`. Bằng chứng: lấy mảng theo chỉ số tốn thời gian không đổi
- DSA_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_04 / partial_last

Danh sách liên kết muốn lấy phần tử thứ k phải lần qua các nút, độ phức tạp O(n).

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a2: `supported`. Bằng chứng: lần qua các nút, độ phức tạp O(n)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_05 / one_wrong_cost

Đọc mảng theo chỉ số O(1). Với linked list, dù có sẵn mọi liên kết cần thiết thì chèn xóa vẫn bắt buộc O(n); đọc theo index cũng O(n).

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `supported`. Bằng chứng: Đọc mảng theo chỉ số O(1)
- DSA_004_R2.a1: `contradicted`. Bằng chứng: dù có sẵn mọi liên kết cần thiết thì chèn xóa vẫn bắt buộc O(n)
- DSA_004_R2.a2: `supported`. Bằng chứng: đọc theo index cũng O(n)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_06 / reversed_costs

Mảng đọc index phải O(n). Danh sách nối chèn xóa dù có đủ liên kết vẫn O(n), còn truy cập index bất kỳ là O(1).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `contradicted`. Bằng chứng: Mảng đọc index phải O(n)
- DSA_004_R2.a1: `contradicted`. Bằng chứng: chèn xóa dù có đủ liên kết vẫn O(n)
- DSA_004_R2.a2: `contradicted`. Bằng chứng: truy cập index bất kỳ là O(1)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_07 / explicit_correction

Em sửa các chi phí vừa nói: mảng truy cập index O(1); linked list có đủ liên kết thì sửa O(1), còn đọc theo chỉ số O(n).

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `supported`. Bằng chứng: mảng truy cập index O(1)
- DSA_004_R2.a1: `supported`. Bằng chứng: linked list có đủ liên kết thì sửa O(1)
- DSA_004_R2.a2: `supported`. Bằng chứng: đọc theo chỉ số O(n)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_08 / retract_correct_to_wrong

Em đã nói đọc linked list theo index là O(n), nhưng rút lại. Em chốt nó đọc mọi index trong O(1).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a2: `contradicted`. Bằng chứng: Em chốt nó đọc mọi index trong O(1)

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_09 / keywords_without_claim

Array, linked list, O(1), O(n), em nhớ những ký hiệu đó nhưng chưa gán được cho thao tác nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_004_DRAFT_10 / ambiguous_condition

Linked list chèn xóa O(1), nhưng em không rõ đã có con trỏ tới vị trí hay còn phải tìm vị trí đó.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DSA_004_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_004_R2.a1: `needs_review`. Bằng chứng: Linked list chèn xóa O(1), nhưng em không rõ đã có con trỏ tới vị trí hay còn phải tìm vị trí đó
- DSA_004_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_005: Hash table xử lý va chạm (collision) như thế nào?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_005_R1.a1 (4.0 điểm dự thảo): Hàm băm ánh xạ một khóa sang chỉ số trong bảng.
- DSA_005_R2.a1 (6.0 điểm dự thảo): Có thể xử lý va chạm bằng chaining hoặc open addressing.

### DSA_005_DRAFT_01 / natural_complete

Lấy khóa cho qua hàm băm để biết ô cần vào. Nếu nhiều khóa cùng ô thì có thể nối chúng thành chuỗi tại ô đó hoặc dò sang ô còn chỗ.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `supported`. Bằng chứng: khóa cho qua hàm băm để biết ô cần vào
- DSA_005_R2.a1: `supported`. Bằng chứng: nối chúng thành chuỗi tại ô đó hoặc dò sang ô còn chỗ

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_02 / mixed_terminology

Hash function map key sang bucket index. Collision xử lý bằng chaining hoặc open addressing.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `supported`. Bằng chứng: map key sang bucket index
- DSA_005_R2.a1: `supported`. Bằng chứng: Collision xử lý bằng chaining hoặc open addressing

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_03 / partial_first

Hàm hash lấy khóa làm đầu vào rồi tính ra chỉ số ô trong bảng.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `supported`. Bằng chứng: lấy khóa làm đầu vào rồi tính ra chỉ số ô trong bảng
- DSA_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_04 / valid_alternative

Em chọn chaining: giữ các khóa trùng ô trong chuỗi tại bucket đó. Hàm hash làm gì em chưa nêu được.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_005_R2.a1: `supported`. Bằng chứng: giữ các khóa trùng ô trong chuỗi tại bucket đó

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_05 / one_wrong_relation

Hash nhận vị trí ô rồi trả ngược ra khóa gốc, không phải nhận khóa ra vị trí. Va chạm thì dùng open addressing.

Khoảng điểm đề xuất: 6.0–6.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `contradicted`. Bằng chứng: nhận vị trí ô rồi trả ngược ra khóa gốc, không phải nhận khóa ra vị trí
- DSA_005_R2.a1: `supported`. Bằng chứng: Va chạm thì dùng open addressing

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_06 / wrong_resolution

Hàm băm từ khóa ra chỉ số. Khi hai khóa trùng ô thì phải vứt cả hai đi, chaining và open addressing đều không xử lý được.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `supported`. Bằng chứng: Hàm băm từ khóa ra chỉ số
- DSA_005_R2.a1: `contradicted`. Bằng chứng: phải vứt cả hai đi, chaining và open addressing đều không xử lý được

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_07 / explicit_correction

Em nói xóa khóa khi trùng ô là sai. Đúng là hash biến khóa thành chỉ số, và collision xử lý được bằng nối chuỗi hoặc dò ô khác.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `supported`. Bằng chứng: hash biến khóa thành chỉ số
- DSA_005_R2.a1: `supported`. Bằng chứng: collision xử lý được bằng nối chuỗi hoặc dò ô khác

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_08 / retract_correct_to_wrong

Ban đầu em chọn chaining để xử lý collision; em rút lại. Em chốt chaining không thể xử lý va chạm và open addressing cũng không.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_005_R2.a1: `contradicted`. Bằng chứng: chaining không thể xử lý va chạm và open addressing cũng không

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_09 / keywords_without_claim

Hash, key, bucket, collision, chaining là mấy từ em nhớ nhưng chưa giải thích quan hệ hay cách xử lý.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_005_DRAFT_10 / unresolved_conflict

Hàm băm chuyển khóa thành vị trí. Hàm băm chuyển vị trí thành khóa gốc. Em đang giữ cả hai ý mà chưa chốt.

Khoảng điểm đề xuất: 0.0–4.0/10. Không phải điểm đã duyệt.

- DSA_005_R1.a1: `needs_review`. Bằng chứng: Hàm băm chuyển khóa thành vị trí. Hàm băm chuyển vị trí thành khóa gốc. Em đang giữ cả hai ý mà chưa chốt
- DSA_005_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_006: Cây nhị phân tìm kiếm (BST) có tính chất gì?

Nhóm: `validation`. Nguồn dùng khóa phân biệt và bất đẳng thức nghiêm ngặt; không suy rộng cho chính sách khóa trùng của mọi biến thể BST.

- DSA_006_R1.a1 (3.0 điểm dự thảo): Mọi khóa ở cây con trái nhỏ hơn khóa nút đang xét.
- DSA_006_R1.a2 (3.0 điểm dự thảo): Mọi khóa ở cây con phải lớn hơn khóa nút đang xét.
- DSA_006_R2.a1 (4.0 điểm dự thảo): Duyệt inorder BST cho thứ tự khóa tăng dần.

### DSA_006_DRAFT_01 / natural_complete

Ở mỗi nút, tất cả giá trị nhánh trái bé hơn nó, tất cả giá trị nhánh phải lớn hơn nó. Đi theo inorder sẽ được dãy từ bé tới lớn.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `supported`. Bằng chứng: tất cả giá trị nhánh trái bé hơn nó
- DSA_006_R1.a2: `supported`. Bằng chứng: tất cả giá trị nhánh phải lớn hơn nó
- DSA_006_R2.a1: `supported`. Bằng chứng: Đi theo inorder sẽ được dãy từ bé tới lớn

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_02 / mixed_terminology

Với từng node: all left keys nhỏ hơn node, all right keys lớn hơn node. Inorder traversal trả ra ascending order.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `supported`. Bằng chứng: all left keys nhỏ hơn node
- DSA_006_R1.a2: `supported`. Bằng chứng: all right keys lớn hơn node
- DSA_006_R2.a1: `supported`. Bằng chứng: Inorder traversal trả ra ascending order

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_03 / partial_first

Tính chất em nhớ là mọi khóa trong cây con trái đều nhỏ hơn khóa tại nút đó.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `supported`. Bằng chứng: mọi khóa trong cây con trái đều nhỏ hơn khóa tại nút đó
- DSA_006_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_04 / partial_last

Inorder của cây tìm kiếm nhị phân cho các khóa theo chiều tăng dần.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R2.a1: `supported`. Bằng chứng: Inorder của cây tìm kiếm nhị phân cho các khóa theo chiều tăng dần

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_05 / one_wrong_relation

Nhánh trái phải lớn hơn nút gốc, nhánh phải cũng lớn hơn nút gốc. Inorder vẫn cho thứ tự tăng dần.

Khoảng điểm đề xuất: 7.0–7.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `contradicted`. Bằng chứng: Nhánh trái phải lớn hơn nút gốc
- DSA_006_R1.a2: `supported`. Bằng chứng: nhánh phải cũng lớn hơn nút gốc
- DSA_006_R2.a1: `supported`. Bằng chứng: Inorder vẫn cho thứ tự tăng dần

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_06 / reversed_order

Cả cây con trái lớn hơn nút, cây con phải nhỏ hơn nút. Inorder BST cho dãy giảm dần chứ không tăng.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `contradicted`. Bằng chứng: cây con trái lớn hơn nút
- DSA_006_R1.a2: `contradicted`. Bằng chứng: cây con phải nhỏ hơn nút
- DSA_006_R2.a1: `contradicted`. Bằng chứng: Inorder BST cho dãy giảm dần chứ không tăng

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_07 / explicit_correction

Em vừa nói đảo trái phải, xin sửa: toàn bộ trái nhỏ hơn nút, toàn bộ phải lớn hơn nút, duyệt inorder tăng dần.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `supported`. Bằng chứng: toàn bộ trái nhỏ hơn nút
- DSA_006_R1.a2: `supported`. Bằng chứng: toàn bộ phải lớn hơn nút
- DSA_006_R2.a1: `supported`. Bằng chứng: duyệt inorder tăng dần

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_08 / retract_correct_to_wrong

Em đã nói inorder tăng dần nhưng xin rút lại. Kết luận em chọn là inorder của BST cho các khóa giảm dần.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R2.a1: `contradicted`. Bằng chứng: inorder của BST cho các khóa giảm dần

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_09 / keywords_without_claim

Em nhớ có trái, phải, nút gốc và inorder, nhưng chưa nêu được bất đẳng thức hay thứ tự duyệt.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_006_DRAFT_10 / unresolved_conflict

Mọi khóa bên trái nhỏ hơn gốc. Mọi khóa bên trái lớn hơn gốc. Em không xác định được câu nào đúng.

Khoảng điểm đề xuất: 0.0–3.0/10. Không phải điểm đã duyệt.

- DSA_006_R1.a1: `needs_review`. Bằng chứng: Mọi khóa bên trái nhỏ hơn gốc. Mọi khóa bên trái lớn hơn gốc. Em không xác định được câu nào đúng
- DSA_006_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_006_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_007: Quick sort hoạt động thế nào và độ phức tạp ra sao?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_007_R1.a1 (2.5 điểm dự thảo): Quicksort phân hoạch các phần tử theo pivot thành phía nhỏ hơn và phía lớn hơn.
- DSA_007_R1.a2 (2.5 điểm dự thảo): Quicksort đệ quy sắp xếp hai phần sau phân hoạch.
- DSA_007_R2.a1 (2.5 điểm dự thảo): Thời gian trung bình của quicksort là O(n log n).
- DSA_007_R2.a2 (2.5 điểm dự thảo): Thời gian xấu nhất của quicksort là O(n^2).

### DSA_007_DRAFT_01 / natural_complete

Chọn chốt để chia các số nhỏ và lớn hơn chốt sang hai phía, rồi làm đệ quy ở hai phần. Trung bình mất n log n, còn trường hợp tệ nhất là n bình phương.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `supported`. Bằng chứng: chia các số nhỏ và lớn hơn chốt sang hai phía
- DSA_007_R1.a2: `supported`. Bằng chứng: làm đệ quy ở hai phần
- DSA_007_R2.a1: `supported`. Bằng chứng: Trung bình mất n log n
- DSA_007_R2.a2: `supported`. Bằng chứng: tệ nhất là n bình phương

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_02 / mixed_terminology

Partition theo pivot thành hai vùng nhỏ/lớn rồi recursively sort hai vùng. Average O(n log n), worst-case O(n^2).

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `supported`. Bằng chứng: Partition theo pivot thành hai vùng nhỏ/lớn
- DSA_007_R1.a2: `supported`. Bằng chứng: recursively sort hai vùng
- DSA_007_R2.a1: `supported`. Bằng chứng: Average O(n log n)
- DSA_007_R2.a2: `supported`. Bằng chứng: worst-case O(n^2)

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_03 / partial_first

Em biết bước chia dữ liệu theo một chốt: nhỏ hơn qua một bên, lớn hơn qua bên kia. Các bước sau em chưa nhớ.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `supported`. Bằng chứng: nhỏ hơn qua một bên, lớn hơn qua bên kia
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_04 / partial_costs

Thời gian trung bình của quicksort là O(n log n); trường hợp xấu nhất O(n^2).

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `supported`. Bằng chứng: trung bình của quicksort là O(n log n)
- DSA_007_R2.a2: `supported`. Bằng chứng: trường hợp xấu nhất O(n^2)

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_05 / wrong_recursion

Nó phân hoạch nhỏ lớn theo pivot nhưng sau đó không bao giờ sắp tiếp hai phần bằng đệ quy. Trung bình O(n log n), xấu nhất O(n^2).

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `supported`. Bằng chứng: phân hoạch nhỏ lớn theo pivot
- DSA_007_R1.a2: `contradicted`. Bằng chứng: không bao giờ sắp tiếp hai phần bằng đệ quy
- DSA_007_R2.a1: `supported`. Bằng chứng: Trung bình O(n log n)
- DSA_007_R2.a2: `supported`. Bằng chứng: xấu nhất O(n^2)

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_06 / reversed_costs

Em cho rằng trung bình là O(n^2), còn trường hợp xấu nhất lại chỉ O(n log n).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `contradicted`. Bằng chứng: trung bình là O(n^2)
- DSA_007_R2.a2: `contradicted`. Bằng chứng: trường hợp xấu nhất lại chỉ O(n log n)

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_07 / explicit_correction

Em nhầm hai độ phức tạp, sửa lại: trung bình n log n, xấu nhất n bình phương. Cách làm là phân vùng bé lớn theo pivot rồi đệ quy sắp cả hai phần.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `supported`. Bằng chứng: phân vùng bé lớn theo pivot
- DSA_007_R1.a2: `supported`. Bằng chứng: đệ quy sắp cả hai phần
- DSA_007_R2.a1: `supported`. Bằng chứng: trung bình n log n
- DSA_007_R2.a2: `supported`. Bằng chứng: xấu nhất n bình phương

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_08 / retract_correct_to_wrong

Em đã nói worst-case n bình phương, nhưng rút lại. Em chọn worst-case của quicksort là O(n log n), không phải O(n^2).

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a2: `contradicted`. Bằng chứng: worst-case của quicksort là O(n log n), không phải O(n^2)

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_09 / keywords_without_claim

Em chỉ nhớ pivot, recursion, n log n và n bình phương, chưa biết chúng mô tả bước hay trường hợp nào.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_007_DRAFT_10 / unresolved_conflict

Trung bình quicksort là O(n log n). Trung bình quicksort là O(n^2). Em chưa chốt được một trong hai.

Khoảng điểm đề xuất: 0.0–2.5/10. Không phải điểm đã duyệt.

- DSA_007_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_007_R2.a1: `needs_review`. Bằng chứng: Trung bình quicksort là O(n log n). Trung bình quicksort là O(n^2). Em chưa chốt được một trong hai
- DSA_007_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_008: BFS và DFS khác nhau ở điểm nào?

Nhóm: `test`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_008_R1.a1 (2.0 điểm dự thảo): BFS duyệt các đỉnh theo từng tầng.
- DSA_008_R1.a2 (2.0 điểm dự thảo): BFS dùng hàng đợi.
- DSA_008_R2.a1 (1.5 điểm dự thảo): DFS đi sâu hết một nhánh trước khi quay lại.
- DSA_008_R2.a2 (1.5 điểm dự thảo): DFS dùng ngăn xếp hoặc đệ quy.
- DSA_008_R3.a1 (3.0 điểm dự thảo): BFS tìm đường đi ít cạnh nhất trên đồ thị không trọng số.

### DSA_008_DRAFT_01 / natural_complete

Duyệt rộng đi lần lượt từng lớp đỉnh và dùng hàng đợi. Duyệt sâu đi hết một nhánh rồi quay lại, dùng ngăn xếp hay gọi đệ quy. Đồ thị không trọng số thì BFS tìm đường qua ít cạnh nhất.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `supported`. Bằng chứng: Duyệt rộng đi lần lượt từng lớp đỉnh
- DSA_008_R1.a2: `supported`. Bằng chứng: dùng hàng đợi
- DSA_008_R2.a1: `supported`. Bằng chứng: Duyệt sâu đi hết một nhánh rồi quay lại
- DSA_008_R2.a2: `supported`. Bằng chứng: dùng ngăn xếp hay gọi đệ quy
- DSA_008_R3.a1: `supported`. Bằng chứng: Đồ thị không trọng số thì BFS tìm đường qua ít cạnh nhất

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_02 / mixed_terminology

BFS level-order bằng queue. DFS depth-first bằng stack hoặc recursion. BFS cho minimum edge path ở unweighted graph.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `supported`. Bằng chứng: BFS level-order
- DSA_008_R1.a2: `supported`. Bằng chứng: BFS level-order bằng queue
- DSA_008_R2.a1: `supported`. Bằng chứng: DFS depth-first
- DSA_008_R2.a2: `supported`. Bằng chứng: DFS depth-first bằng stack hoặc recursion
- DSA_008_R3.a1: `supported`. Bằng chứng: minimum edge path ở unweighted graph

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_03 / partial_bfs

BFS mở rộng từng tầng và dùng queue; phần DFS với ứng dụng tìm đường em chưa biết.

Khoảng điểm đề xuất: 4.0–4.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `supported`. Bằng chứng: BFS mở rộng từng tầng
- DSA_008_R1.a2: `supported`. Bằng chứng: dùng queue
- DSA_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_04 / partial_dfs

DFS cứ đi sâu dọc nhánh đang xét cho tới hết, rồi quay lui bằng stack hoặc đệ quy.

Khoảng điểm đề xuất: 3.0–3.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a1: `supported`. Bằng chứng: đi sâu dọc nhánh đang xét cho tới hết
- DSA_008_R2.a2: `supported`. Bằng chứng: quay lui bằng stack hoặc đệ quy
- DSA_008_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_05 / wrong_data_structure

BFS đi theo tầng nhưng chỉ dùng stack, không dùng queue. DFS đi sâu bằng đệ quy. BFS tìm ít cạnh nhất khi đồ thị không trọng số.

Khoảng điểm đề xuất: 8.0–8.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `supported`. Bằng chứng: BFS đi theo tầng
- DSA_008_R1.a2: `contradicted`. Bằng chứng: chỉ dùng stack, không dùng queue
- DSA_008_R2.a1: `supported`. Bằng chứng: DFS đi sâu
- DSA_008_R2.a2: `supported`. Bằng chứng: DFS đi sâu bằng đệ quy
- DSA_008_R3.a1: `supported`. Bằng chứng: BFS tìm ít cạnh nhất khi đồ thị không trọng số

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_06 / role_reversal

BFS đi sâu hết nhánh nhờ stack, không đi theo tầng hay queue. DFS chỉ đi theo tầng bằng queue, không đi sâu bằng stack hoặc đệ quy.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `contradicted`. Bằng chứng: BFS đi sâu hết nhánh nhờ stack, không đi theo tầng
- DSA_008_R1.a2: `contradicted`. Bằng chứng: không đi theo tầng hay queue
- DSA_008_R2.a1: `contradicted`. Bằng chứng: DFS chỉ đi theo tầng bằng queue, không đi sâu
- DSA_008_R2.a2: `contradicted`. Bằng chứng: không đi sâu bằng stack hoặc đệ quy
- DSA_008_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_07 / explicit_correction

Em đảo BFS với DFS, xin sửa: BFS đi từng tầng bằng hàng đợi, DFS đi hết nhánh bằng ngăn xếp hoặc đệ quy. Khi các cạnh không có trọng số thì BFS tìm ít cạnh nhất.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `supported`. Bằng chứng: BFS đi từng tầng
- DSA_008_R1.a2: `supported`. Bằng chứng: BFS đi từng tầng bằng hàng đợi
- DSA_008_R2.a1: `supported`. Bằng chứng: DFS đi hết nhánh
- DSA_008_R2.a2: `supported`. Bằng chứng: DFS đi hết nhánh bằng ngăn xếp hoặc đệ quy
- DSA_008_R3.a1: `supported`. Bằng chứng: Khi các cạnh không có trọng số thì BFS tìm ít cạnh nhất

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_08 / retract_correct_to_wrong

Em đã nói BFS tìm ít cạnh nhất trên đồ thị không trọng số. Em rút lại và chốt BFS không bảo đảm ít cạnh nhất ngay cả trên đồ thị không trọng số.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R3.a1: `contradicted`. Bằng chứng: BFS không bảo đảm ít cạnh nhất ngay cả trên đồ thị không trọng số

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_09 / keywords_without_claim

BFS, DFS, tầng, nhánh, queue, stack em chỉ đọc lại tên, chưa mô tả cách duyệt hay tính chất đường đi.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_008_DRAFT_10 / unresolved_conflict

BFS dùng queue. BFS không dùng queue mà chỉ dùng stack. Em chưa quyết định cách nói nào.

Khoảng điểm đề xuất: 0.0–2.0/10. Không phải điểm đã duyệt.

- DSA_008_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R1.a2: `needs_review`. Bằng chứng: BFS dùng queue. BFS không dùng queue mà chỉ dùng stack. Em chưa quyết định cách nói nào
- DSA_008_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R2.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_008_R3.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

## DSA_009: Thuật toán Dijkstra giải bài toán gì và có điều kiện nào?

Nhóm: `validation`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_009_R1.a1 (5.0 điểm dự thảo): Dijkstra tìm đường đi ngắn nhất từ một nguồn tới các đỉnh khác.
- DSA_009_R2.a1 (5.0 điểm dự thảo): Điều kiện áp dụng Dijkstra là các trọng số cạnh không âm.

### DSA_009_DRAFT_01 / natural_complete

Chọn một đỉnh làm điểm xuất phát rồi tìm đường ngắn nhất từ nó tới các đỉnh còn lại. Điều kiện là không có cạnh mang trọng số âm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `supported`. Bằng chứng: đường ngắn nhất từ nó tới các đỉnh còn lại
- DSA_009_R2.a1: `supported`. Bằng chứng: không có cạnh mang trọng số âm

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_02 / mixed_terminology

Dijkstra giải single-source shortest paths với edge weights lớn hơn hoặc bằng zero.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `supported`. Bằng chứng: single-source shortest paths
- DSA_009_R2.a1: `supported`. Bằng chứng: edge weights lớn hơn hoặc bằng zero

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_03 / partial_first

Nó tìm các đường đi ngắn nhất bắt đầu từ một đỉnh nguồn, em chưa nhớ điều kiện trọng số.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `supported`. Bằng chứng: đường đi ngắn nhất bắt đầu từ một đỉnh nguồn
- DSA_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_04 / partial_last

Các trọng số cạnh phải lớn hơn hoặc bằng 0. Em chưa trình bày bài toán nó giải.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_009_R2.a1: `supported`. Bằng chứng: Các trọng số cạnh phải lớn hơn hoặc bằng 0

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_05 / wrong_goal

Dijkstra tìm đường dài nhất từ nguồn đến các đỉnh khác; trọng số cạnh thì không âm.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `contradicted`. Bằng chứng: tìm đường dài nhất từ nguồn đến các đỉnh khác
- DSA_009_R2.a1: `supported`. Bằng chứng: trọng số cạnh thì không âm

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_06 / wrong_precondition

Nó tìm đường ngắn nhất từ một nguồn và được bảo đảm đúng với mọi cạnh âm, không cần điều kiện không âm.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `supported`. Bằng chứng: tìm đường ngắn nhất từ một nguồn
- DSA_009_R2.a1: `contradicted`. Bằng chứng: được bảo đảm đúng với mọi cạnh âm, không cần điều kiện không âm

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_07 / explicit_correction

Em vừa cho phép cạnh âm là nhầm. Chốt lại Dijkstra tìm đường ngắn nhất từ một nguồn, áp dụng khi mọi cạnh không âm.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `supported`. Bằng chứng: tìm đường ngắn nhất từ một nguồn
- DSA_009_R2.a1: `supported`. Bằng chứng: áp dụng khi mọi cạnh không âm

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_08 / retract_correct_to_wrong

Em đã nêu phải không âm nhưng xin rút lại. Em cho rằng Dijkstra luôn đúng với cả trọng số âm tùy ý.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_009_R2.a1: `contradicted`. Bằng chứng: Dijkstra luôn đúng với cả trọng số âm tùy ý

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_09 / keywords_without_claim

Em nhớ nguồn, đường đi, trọng số và Dijkstra, chưa mô tả mục tiêu hay điều kiện.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_009_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_009_DRAFT_10 / unresolved_conflict

Dijkstra bắt buộc trọng số không âm. Dijkstra không cần điều kiện không âm. Em chưa chọn được ý nào.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- DSA_009_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_009_R2.a1: `needs_review`. Bằng chứng: Dijkstra bắt buộc trọng số không âm. Dijkstra không cần điều kiện không âm. Em chưa chọn được ý nào

Ghi chú người duyệt: ____________________

## DSA_010: Quy hoạch động (dynamic programming) là gì?

Nhóm: `train`. Giảng viên cần xác nhận diễn giải và trọng số trước khi duyệt.

- DSA_010_R1.a1 (2.5 điểm dự thảo): Quy hoạch động áp dụng cho các bài toán con gối nhau.
- DSA_010_R1.a2 (2.5 điểm dự thảo): Bài toán dùng quy hoạch động có cấu trúc con tối ưu.
- DSA_010_R2.a1 (5.0 điểm dự thảo): Quy hoạch động lưu kết quả bài toán con để tránh tính lại.

### DSA_010_DRAFT_01 / natural_complete

Các phần việc con gặp đi gặp lại, lời giải tốt nhất ghép được từ các lời giải con tốt nhất. Tính xong phần nào thì giữ đáp số phần đó để khỏi tính lại.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `supported`. Bằng chứng: Các phần việc con gặp đi gặp lại
- DSA_010_R1.a2: `supported`. Bằng chứng: lời giải tốt nhất ghép được từ các lời giải con tốt nhất
- DSA_010_R2.a1: `supported`. Bằng chứng: giữ đáp số phần đó để khỏi tính lại

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_02 / mixed_terminology

DP cần overlapping subproblems và optimal substructure. Dùng memoization hoặc bảng để reuse kết quả, không solve lại cùng subproblem.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `supported`. Bằng chứng: overlapping subproblems
- DSA_010_R1.a2: `supported`. Bằng chứng: optimal substructure
- DSA_010_R2.a1: `supported`. Bằng chứng: reuse kết quả, không solve lại cùng subproblem

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_03 / partial_first

Em nhớ là các bài toán con có phần trùng lặp, nhiều lần gặp lại cùng một bài toán con.

Khoảng điểm đề xuất: 2.5–2.5/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `supported`. Bằng chứng: nhiều lần gặp lại cùng một bài toán con
- DSA_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_04 / partial_last

Đã giải bài toán con thì ghi kết quả lại, lần sau tra lại thay vì tính mới.

Khoảng điểm đề xuất: 5.0–5.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R2.a1: `supported`. Bằng chứng: ghi kết quả lại, lần sau tra lại thay vì tính mới

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_05 / one_wrong_condition

Các bài toán con phải hoàn toàn không lặp lại. Có cấu trúc con tối ưu và kết quả con được lưu để tái dùng.

Khoảng điểm đề xuất: 7.5–7.5/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `contradicted`. Bằng chứng: Các bài toán con phải hoàn toàn không lặp lại
- DSA_010_R1.a2: `supported`. Bằng chứng: Có cấu trúc con tối ưu
- DSA_010_R2.a1: `supported`. Bằng chứng: kết quả con được lưu để tái dùng

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_06 / wrong_conditions_and_cache

DP chỉ dùng khi các bài toán con độc lập không trùng và không có cấu trúc con tối ưu. Mọi kết quả con phải xóa để lần sau tính lại từ đầu.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `contradicted`. Bằng chứng: các bài toán con độc lập không trùng
- DSA_010_R1.a2: `contradicted`. Bằng chứng: không có cấu trúc con tối ưu
- DSA_010_R2.a1: `contradicted`. Bằng chứng: kết quả con phải xóa để lần sau tính lại từ đầu

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_07 / explicit_correction

Em nhầm việc bỏ kết quả. DP giữ kết quả để không tính lại, dùng khi bài toán con gối nhau và có cấu trúc con tối ưu.

Khoảng điểm đề xuất: 10.0–10.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `supported`. Bằng chứng: bài toán con gối nhau
- DSA_010_R1.a2: `supported`. Bằng chứng: có cấu trúc con tối ưu
- DSA_010_R2.a1: `supported`. Bằng chứng: giữ kết quả để không tính lại

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_08 / retract_correct_to_wrong

Em đã nói lưu kết quả con nhưng rút lại. Theo kết luận mới của em, DP không lưu mà bắt buộc tính lại mỗi lần gặp.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R2.a1: `contradicted`. Bằng chứng: DP không lưu mà bắt buộc tính lại mỗi lần gặp

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_09 / keywords_without_claim

Em nhớ từ memo, tối ưu, bài toán con, còn các điều kiện và cách tái dùng thì em chưa diễn đạt được.

Khoảng điểm đề xuất: 0.0–0.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R2.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.

Ghi chú người duyệt: ____________________

### DSA_010_DRAFT_10 / unresolved_conflict

DP lưu đáp số con để dùng lại. DP không lưu đáp số con và phải tính lại. Em giữ cả hai phát biểu, chưa chốt.

Khoảng điểm đề xuất: 0.0–5.0/10. Không phải điểm đã duyệt.

- DSA_010_R1.a1: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R1.a2: `missing`. Bằng chứng: Không trích dẫn vì chưa nêu ý.
- DSA_010_R2.a1: `needs_review`. Bằng chứng: DP lưu đáp số con để dùng lại. DP không lưu đáp số con và phải tính lại. Em giữ cả hai phát biểu, chưa chốt

Ghi chú người duyệt: ____________________
