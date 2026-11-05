# Điểm luyện tập theo từng phần

## Luồng xử lý

1. Bắt đầu phiên và dùng bộ câu hỏi/độ khó đã chuẩn bị.
2. Ghi âm → STT → sửa transcript có kiểm soát → xem bản chép lời.
3. Sinh viên có thể ghi âm lại trước khi xác nhận. Không nhập sửa transcript trực tiếp.
4. Xác nhận để lưu và sang câu tiếp theo; chưa chấm giữa phiên.
5. Kết thúc → backend chấm từng câu bằng pipeline hiện có → báo cáo từng tiêu chí,
   từng câu, từng môn, từng nhóm năng lực và cả phiên.

Luyện tập do AI chấm, không chuyển sang hàng chờ giảng viên. Nếu AI vẫn chưa đủ
cơ sở kết luận, giữ kết quả chưa chốt thay vì bịa điểm. Interview kiểm tra thật vẫn
giữ quy trình giảng viên và lịch sử quyết định hiện có.

## API và thang điểm

`GET /api/interviews/{session_id}/report` giữ các trường cũ ở thang 100.
Chỉ báo cáo luyện tập có thêm:

- `answers[].evaluation.score_breakdown`: điểm tiêu chí và điểm câu, thang 10.
- `summary.practice_grading.session`: điểm toàn phiên, thang 10.
- `summary.practice_grading.subjects`: điểm theo môn.
- `summary.practice_grading.competencies`: điểm nhóm năng lực trong từng môn.

Frontend hiển thị một điểm chính `/10` cùng số câu đã xác minh. Khi còn câu chưa
chốt thì không trình bày trung bình của phần đã chấm thành điểm toàn phiên.
Phần “Điểm theo môn và năng lực” lấy trực tiếp điểm môn và năng lực từ
`summary.practice_grading`, thang 10. Trong chi tiết từng câu, giao diện lấy
`evaluation.score_breakdown` để hiện điểm tối đa theo trọng số, điểm đã xác minh
và tiêu chí chưa chốt. Tiêu chí chưa xác minh không hiển thị thành 0 điểm.
Các trường API thang 100 vẫn tương thích, nhưng các ô tổng và phần trăm trùng lặp
được ẩn trong report luyện tập. Chế độ kiểm tra vẫn dùng báo cáo và quyết định
của giảng viên.
Phần hàng đợi bổ sung cột `retry_after` bằng migration tự động,
không đổi điểm, transcript hay voice đã lưu. Các trường báo cáo được tính từ
rubric và kết quả đã lưu, không gọi thêm Whisper/Transformer/Ollama để mở báo cáo.

## Cách tính

Điểm tối đa của một tiêu chí = `10 × trọng số tiêu chí / tổng trọng số câu`.
Đạt tiêu chí nhận đủ phần điểm; xác minh là thiếu/sai nhận 0 phần điểm đó. Rubric
atomic không tự chia đôi điểm. Kết quả `partial` của rubric legacy được giữ đúng
chính sách cũ, không tự đổi nhãn lịch sử hay trọng số.

Ví dụ trọng số 4, 3, 3:

| Kết quả ba tiêu chí | Điểm câu | Điểm chắc chắn | Khoảng có thể đạt |
|---|---:|---:|---:|
| Đạt, đạt, sai đã xác minh | 7/10 | 7 | 7–7 |
| Đạt, đạt, chưa xác minh | Chưa chốt (`null`) | 7 | 7–10 |

Tiêu chí chưa xác minh có `earned_points: null`, không phải 0 hay 0,5. Không bỏ
tiêu chí đó khỏi mẫu số để biến 7 thành 10. Khoảng điểm là khoảng theo rubric,
không phải khoảng tin cậy thống kê hay phần trăm độ chính xác.

Các trường chính của `score_breakdown`:

- `score`: điểm chính thức thang 10, hoặc `null` nếu chưa đủ điều kiện.
- `confirmed_points`, `possible_score_interval`: điểm đã xác nhận và khoảng điểm.
- `criteria[]`: nội dung tiêu chí, trọng số, điểm tối đa, trạng thái và điểm đạt.
- `resolved_criterion_count`, `unresolved_criterion_count`: số tiêu chí đã/chưa rõ.
- `status`: `pending`, `insufficient_evidence`, `final`, `invalid_rubric`, `score_mismatch`.

Chỉ chốt khi phiên kết thúc, chấm xong, transcript đủ điều kiện, đủ kết quả tiêu
chí và điểm đã lưu khớp trọng số rubric. Dữ liệu không hợp lệ/điểm không khớp bị
giữ lại để kiểm tra, không tự ghi đè bài làm hay tính điểm chính thức.
Điều kiện chốt điểm được dùng chung cho báo cáo và lịch sử luyện tập; trường điểm
cũ cũng bị giữ `null` nếu breakdown phát hiện rubric không hợp lệ/điểm không khớp.
Điểm tổng giảng viên đã chốt được bảo toàn, không tự suy diễn điểm từng tiêu chí.

Điểm nhóm/môn/phiên là trung bình đều theo câu, giữ chính sách tổng hợp cũ. Nếu
còn câu chưa chốt thì `score` tổng cũng là `null`; `scored_only_average` chỉ là
trung bình các câu đã chốt, không phải điểm toàn phiên. Phạm vi tổng hợp là các
câu đã trả lời (`scope: answered_questions`), không tự gán câu chưa trả lời là 0.
Để tương thích API cũ, trường `summary.average_score` và `average_score` trong lịch sử
vẫn là trung bình các câu đã chốt; điểm toàn phiên đầy đủ nằm trong
`summary.practice_grading.session.score` và chưa chốt khi còn câu chưa xác minh.
Lịch sử bổ sung `final_score` (thang 100), `score_status`, `scored_answer_count`,
`unscored_answer_count` và `scored_only_average`. Chỉ dùng `final_score` làm điểm
toàn bài; không hiển thị trung bình của phần đã chấm như điểm cuối.

## Lỗi kỹ thuật và thử lại

Timeout, lỗi kết nối/đầu ra model và bộ xác minh không chạy được không được xem là
chấm thành công. Câu lỗi giữ `grading_pending=1`; câu đã chốt không bị chấm lại.
Hàng đợi tự thử lại sau khoảng 5 giây rồi 15 giây, tối đa 3 lượt xử lý toàn phiên.
Đây là thời gian nghỉ giữa lượt, không phải cam kết tổng thời gian chấm bài.
Hết lượt chuyển `failed`, giữ voice/transcript và báo chưa có điểm cuối cho câu lỗi.

Các trường bổ sung của API trạng thái chấm: `retry_at`, `can_retry`,
`report_available`. `report_ready` chỉ đúng khi hàng đợi hoàn tất và không còn
câu lỗi đang chờ. Kết quả chưa đủ bằng chứng ngữ nghĩa vẫn có thể có báo cáo,
nhưng không có điểm cuối; không tự thử đi thử lại như lỗi kỹ thuật.
Khi `report_available=true`, giao diện vẫn cho xem các câu đã xử lý, kể cả khi
`report_ready=false`; cảnh báo gián đoạn và giới hạn thử lại vẫn được giữ nguyên.

Khi khởi động lại, backend sửa trạng thái các công việc cũ bị báo hoàn thành dù
còn lỗi kỹ thuật, không đặt lại bộ đếm lượt và không đụng điểm giảng viên đã chốt.

## Xác minh ngữ nghĩa

FactGuard chỉ chốt theo luật khi các phát biểu trong câu trả lời đã được phân
tích đầy đủ. Điều kiện này không phụ thuộc danh sách từ nối như “nghĩa là” hay
“nói đơn giản”. Nếu còn mệnh đề chưa phân tích được, tiêu chí chuyển cho
Transformer/LLM cùng toàn bộ câu trả lời; luật khớp câu đầu không được chốt thay.
Các quan hệ độc lập đã phân tích được vẫn được chấm riêng theo rubric. Việc nói
lớp con có thể thêm hành vi không tự chứng minh cả quyền ghi đè phương thức.
Đường khớp chủ ngữ/vị ngữ và so sánh số cũng không được bỏ qua phần giải thích.
Phát biểu rõ nhưng tự mâu thuẫn vẫn giữ trạng thái chưa chốt.
Luật này không học thêm kiến thức và không thay đổi trọng số model.
Cache đề xuất AI cho giảng viên được đổi phiên bản; quyết định giảng viên đã
xác nhận và điểm lịch sử không bị tự ghi lại. Bài cũ đáng ngờ cần đánh giá lại
riêng, không xem việc cập nhật mã là đã sửa điểm cũ.

`neutral` của Transformer được giữ là `unresolved`, không tự biến thành thiếu ý
hoặc sai. Bộ xác minh NLI đang cài phải báo rõ checkpoint/ngôn ngữ đủ điều kiện
chấp nhận và input không bị cắt trước khi xác nhận bằng chứng của Qwen; xác suất
cao không tự vượt qua kiểm định. Nếu không cài bộ xác minh thì nhánh Ollama-only
cũ vẫn hoạt động theo hợp đồng bằng chứng của nó, không được coi là đã có NLI
xác minh độc lập. Đây vẫn là một giới hạn cần đánh giá bằng dữ liệu thật.

## Phạm vi và giới hạn

- Báo cáo và lịch sử trên desktop đã kết nối trạng thái điểm đầy đủ/một phần.
- Không tải model mới, không train lại, không tăng kích thước checkpoint.
- Specialist INT8 vẫn chỉ chạy thử đối chiếu (`shadow_only`), không thay điểm thật.
- Pipeline chấm hiện tại vẫn dùng luật/Transformer và Qwen cho phần chưa chắc;
  chưa có bằng chứng đủ để bỏ Qwen hoặc cam kết chấm đúng 100%.
- Phát hiện câu tự rút lại/đính chính sẽ buộc kiểm tra phạm vi ý nghĩa. Trường hợp
  này có thể tốn thêm thời gian xác minh, không được bỏ kiểm tra để lấy tốc độ.
- Bộ test câu trả lời tổng hợp không thay thế dữ liệu thi thật được giảng viên
  gán nhãn độc lập. Chưa chứng nhận độ chính xác hay tốc độ trên máy RAM 4/8 GB thật.

## Vòng đời báo cáo luyện tập

Chỉ phản hồi của yêu cầu xem báo cáo mới nhất, đúng người dùng và đúng màn hình
lịch sử được phép hiển thị. Đóng báo cáo, đổi màn hình hoặc bắt đầu đăng xuất
sẽ vô hiệu hóa phản hồi cũ, kể cả khi mạng trả về muộn. Cơ chế này dùng số thứ tự
yêu cầu trong giao diện, không thay quyền truy cập API hay dữ liệu bài làm.

Bản sửa không tự chấm lại các điểm lịch sử. Một số câu trước đây được chốt bằng
luật sẽ cần bộ chấm ngữ nghĩa; nếu bộ chấm chưa xác minh được thì vẫn giữ điểm
chưa chốt. Không dùng điểm giả để che lỗi hoặc cam kết model chấm đúng mọi bài.

## Phản hồi học tập và luyện lại

- `answers[].evaluation.learning_feedback`: nhận xét dựa trên từng tiêu chí đã
  lưu, bằng chứng trích nguyên văn từ transcript được dùng chấm, nguồn và việc
  cần làm tiếp. Không dùng `missing_points` để đánh đồng thiếu, sai và chưa xác minh.
- `summary.learning_feedback`: điểm mạnh và phần cần bổ sung trong phiên này.
  Cùng một tiêu chí có câu đúng và câu sai được ghi là chưa nhất quán, không kết
  luận sinh viên đã nắm chắc toàn môn. Lỗi kỹ thuật/ghi âm không tạo điểm yếu kiến thức.
- `POST /api/interviews/{session_id}/practice-again` với `{"answer_id": 123}`:
  tạo một phiên voice mới từ câu cần luyện lại trong ngân hàng learning đang hoạt
  động. Bỏ `answer_id` để chọn các câu đủ điều kiện trong phiên. API chỉ nhận
  phiên luyện tập đã kết thúc của chính sinh viên; câu trong đề kiểm tra không
  được dùng qua đường này. Toàn bộ câu được chốt trước lúc bắt đầu, chấm cuối phiên.
- Lỗi bộ chấm hướng tới xử lý bài đã lưu. Ghi âm chưa chắc hoặc chưa xác minh
  ý nghĩa cho phép luyện lại trong phiên mới; không sửa transcript của bài cũ.
- Rubric đã có hợp đồng atomic, trọng số, nguồn và snapshot. Có thể tách PUSH/POP
  thành tiêu chí riêng bằng bản rubric mới đã duyệt; report dùng đúng phiên bản
  của từng bài. Không tự tách câu ghép hoặc đổi điểm lịch sử bằng quy tắc đoán.

Phần phản hồi là phép chiếu dữ liệu chấm đã có, không gọi thêm model và không
thay đổi kết luận chấm. Sinh viên không thấy phần trăm tin cậy nội bộ như thể đó
là tỷ lệ chính xác đã được kiểm định. Báo cáo vẫn phụ thuộc chất lượng bộ chấm;
chưa xác minh được phải giữ nguyên trạng thái chưa chốt.

## Bảo vệ report và nguồn luyện lại (1.18.5)

- Report khi kết thúc phiên và khi khôi phục bài đã lưu kiểm tra lại người dùng,
  phiên và trạng thái yêu cầu sau các bước chờ. Đóng report, đổi màn hình hoặc
  đăng xuất vô hiệu hóa phản hồi cũ; phản hồi đó không được bắt đầu watcher mới.
- Năm đề xuất luyện đầu tiên được ưu tiên; các mục còn lại nằm trong phần mở
  rộng có nút luyện riêng, thay vì bị loại khỏi giao diện.
- Câu lấy từ ngân hàng lưu thêm `learning_source_sha256` trước khi áp dụng rubric
  đã duyệt. Luyện lại kiểm tra bản nguồn trong cùng giao dịch chọn đề, gồm môn,
  chủ đề, năng lực, độ khó, câu hỏi, đáp án và ý chính. Thay tên file nguồn không
  làm đổi chữ ký. Bản 1.18.5 từng gộp khoảng trắng; bản 1.18.6 dùng chữ ký v2 giữ
  nguyên bố cục câu hỏi, đáp án và ý chính, chỉ thống nhất CRLF/CR thành LF.
- Bài cũ chưa có chữ ký dùng nội dung snapshot; snapshot atomic cũ dùng
  fingerprint nguồn trong hợp đồng. Khi nguồn không khớp, API báo câu gốc đã
  cập nhật và yêu cầu bắt đầu lượt mới; không âm thầm đổi mục tiêu luyện tập.
  Cách kiểm tra này thận trọng: sửa câu chữ ngoài khoảng trắng cũng có thể cần
  lượt mới. Rubric mới đã duyệt vẫn được áp dụng nếu bản nguồn còn khớp.
- API report chiếu lại quote và vị trí trích dẫn theo đúng transcript dùng chấm;
  frontend kiểm tra lại ở cả nhận xét lẫn chi tiết, kể cả transcript mạnh đã được
  giảng viên chấp nhận. Không có transcript đối chiếu thì không khẳng định quote
  là bằng chứng. Dữ liệu và quyết định chấm gốc không bị ghi đè.

## Xác thực và nguồn cũ (1.18.6)

- Mã thế hệ xác thực được tăng khi bắt đầu đăng nhập/đăng xuất hoặc xóa trạng
  thái đăng nhập. API chỉ xử lý tác động của 401 khi cả thế hệ và người dùng còn
  khớp. Khởi tạo kiểm tra lại sau response lẫn sau khi đọc JSON. Login/logout cũ
  không được cập nhật trạng thái hay biểu mẫu của lượt mới.
- Các phiên mới lưu `learning_source_version=practice-source-v2`. Code trong
  question/reference_answer/key_points giữ thụt dòng, ngắt dòng và khoảng trắng.
- Với phiên dùng hash cũ chưa có nhãn phiên bản, kiểm tra thêm nội dung và mọi
  metadata đã lưu; hash v1 không đủ để bỏ qua thay đổi bố cục. Snapshot atomic
  cũ vẫn đối chiếu fingerprint gốc để ràng buộc ý chính trước khi chiếu rubric.
- Không sửa thuật toán question_fingerprint của hợp đồng đã xuất bản, không
  chuyển đổi hay ghi đè dữ liệu phiên cũ. Phiên bản chữ ký không nhận biết bị từ
  chối thay vì tự coi tương đương. Nhánh atomic cũ có thể cần mở lượt mới khi tên
  file nguồn đổi, vì fingerprint gốc còn gắn với tên file; chữ ký v2 không có phụ
  thuộc này.

## Vòng đời thao tác và hợp đồng rubric (1.18.7)

- Tải lịch sử gắn với thế hệ xác thực và số thứ tự yêu cầu. Chỉ lượt mới nhất
  được thay dữ liệu và kết thúc trạng thái loading. Đăng xuất xóa nội dung bảng;
  đăng nhập lại cùng tài khoản cũng không khôi phục response cũ.
- Bắt đầu luyện tập và thi dùng cùng thứ tự chọn phiên, nhưng mỗi nút có chủ sở
  hữu lượt chờ riêng. Phản hồi cũ không gọi beginSession hoặc lưu phiên dưới tài
  khoản mới; finally cũ không mở khóa nút của lượt đang xử lý.
- Xác nhận trả lời chụp phiên, câu hỏi, transcription, hash preview và bản ghi
  tạm trước khi chờ. Kiểm tra lại sau response và sau thao tác cache; chỉ lượt
  submit còn hiệu lực được cập nhật câu trả lời hay mở khóa controls.
- Kết thúc luyện tập cũng ràng buộc đúng lượt chờ; response cũ không được mở
  report cho phiên mới hoặc bỏ khóa thao tác kết thúc của tài khoản mới.
- Import và chọn đề dùng cùng kiểm tra với bộ chấm: 1–30 tiêu chí, không trùng
  sau chuẩn hóa Unicode/chữ hoa/khoảng trắng. Chọn đề và bộ chấm còn kiểm tra
  trọng số của rubric đã duyệt khi có. File lỗi
  bị từ chối trước khi ghi bất kỳ câu nào, kể cả ở chế độ replace. Câu lỗi đã
  tồn tại bị chặn khi tạo đề; không tự xóa tiêu chí hoặc sửa dữ liệu lịch sử.
- Chuẩn hóa thuật ngữ dùng cách viết tên chữ cái rõ ràng, không bỏ dấu rồi coi
  từ thông thường như “À” là chữ A. Cả acronym lẫn số + acronym đều không ghép
  qua dấu câu/ngắt dòng. Thu gọn tên chữ đã xác minh có giới hạn riêng, vẫn giữ
  kiểm tra số liệu và phủ định; không tải thêm model hoặc tăng checkpoint.

## Mic và phục hồi hàng đợi (1.18.8)

- Mở mic có một token đang chờ, gắn với tài khoản/thế hệ, phiên, câu hỏi và
  lần kiểm tra thiết bị. Stream giữ ở biến cục bộ cho đến khi token còn hợp lệ;
  stream trả muộn bị đóng, không ghi vào state của lượt mới. Bấm lặp không mở
  thêm luồng; dừng recorder vẫn được phép khi phiên vừa hết hạn hoặc hoàn tất.
- Đăng xuất, đổi phiên/câu hoặc mở báo cáo kết thúc đều vô hiệu hóa capture.
  Callback cũ không chuyển dữ liệu sang tài khoản mới. Lỗi mở thiết bị/encoder
  giữ nguyên preview đã có; chỉ capture khởi động thành công mới thay preview.
- Đóng phiên do hết hạn và tạo job chấm câu đã xác nhận cùng nằm trong một
  transaction. Thất bại tạo job sẽ rollback việc đóng phiên. INSERT OR IGNORE
  giữ nguyên job, điểm và số lượt thử đã có. Đọc trạng thái có thể bổ sung job
  bị thiếu từ dữ liệu cũ; không chấm lại hoặc reset job lỗi quá số lần cho phép.
- Các span phát âm khớp chính xác thuật ngữ đã duyệt được chiếu về dạng viết
  trước khi đo phần chỉnh sửa còn lại. Nhờ vậy câu ngắn như “hai tê bê” được
  thành “2TB” mà không nới edit ratio chung. Marker phủ định vẫn đối chiếu với
  raw transcript; số liệu ngoài span vẫn phải giữ nguyên. Raw và audit gốc
  được giữ lại; không cần thêm model, thư viện hoặc tiến trình nền.

## Phục hồi bản ghi và cache đúng lượt (1.18.9)

- Kiểm tra mic giữ đúng tài khoản/thế hệ và phiên trong cả response, catch lẫn
  finally. Đăng xuất, đổi phiên/câu hoặc mở report kết thúc tách controller cũ
  trước khi abort, nên lượt mới không phải chờ AudioContext cũ hoàn tất. Hủy
  kiểm tra bằng nút hiện tại vẫn phục hồi controls của chính lượt đó.
- Khôi phục draft dùng thứ tự yêu cầu riêng: chỉ lượt mới nhất được thay
  transcript hoặc bỏ loading. Khi khôi phục chuyển sang xử lý job đã lưu,
  loading vẫn được giải phóng đúng dù speechRun tăng ở bước bàn giao.
- Callback upload/job và bàn giao bản ghi sau khi lưu cache kiểm tra lại đúng
  tài khoản, phiên, câu và bản ghi. Phản hồi cũ không tự retry bằng tài khoản
  mới, không khởi động xử lý bản ghi của lượt khác hoặc ghi lại cache sau logout.
- IndexedDB put kiểm tra quyền sở hữu tại lúc gọi và khi mở kết nối thành công,
  gồm key tài khoản/phiên và questionKey. Read/delete vẫn giữ hành vi phục hồi
  và dọn đúng key đã chụp. Cache không khả dụng không ngăn voice hiện tại được
  gửi xử lý; không có schema hay thư viện mới.
