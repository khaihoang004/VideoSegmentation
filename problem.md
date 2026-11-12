# Định nghĩa bài toán: định vị online từng lượt hoàn thành công việc trong video

Ngày cập nhật: 2026-11-13 (Asia/Saigon). Trạng thái: đặc tả nghiên cứu ban đầu, chưa lựa chọn kiến trúc mô hình.

## 1. Phát biểu mục tiêu

Cho một luồng video quan sát một người thực hiện công việc, xử lý các frame/chunk theo thứ tự khi chúng tới, phát hiện lượt công việc hoàn thành và phát kết quả bắt đầu–kết thúc của lượt đó ngay trong quá trình luồng đang chạy. **Online là yêu cầu bắt buộc đã được người dùng xác nhận.** Tại mỗi quyết định chỉ được dùng dữ liệu đã quan sát đến thời điểm đó; không chờ toàn bộ video hoặc các lượt tiếp theo mới trả kết quả.

Mỗi lượt có thể gồm nhiều thao tác khác nhau, có khoảng nghỉ, hoạt động ngoài công việc hoặc sửa lỗi. Đầu ra cần bao trọn **một lượt công việc**, thay vì chỉ lấy thao tác chính hoặc mỗi động tác nhỏ. Có thể dùng video đã quay để mô phỏng stream, nhưng pipeline suy luận vẫn phải tuân thủ ràng buộc online.

Ví dụ minh họa, không phải quy trình bắt buộc:

```text
Video:
nghỉ | lấy hộp → cho đồ vào → nghe điện thoại → chỉnh đồ → đóng hộp → giao hộp | nghỉ | lượt tiếp theo
     └──────────────────── một lượt đóng gói hoàn chỉnh ───────────────────┘

Đầu ra: [bắt đầu lượt 1, hoàn thành lượt 1], [bắt đầu lượt 2, hoàn thành lượt 2], ...
```

Phần lặp là **mục tiêu công việc được thực hiện nhiều lần**. Không giả định hình dáng chuyển động, số bước, thứ tự bước hoặc thời lượng các lượt giống nhau. Dấu hiệu hoàn thành có thể nằm ở thao tác, trạng thái vật thể hoặc kết quả công việc; cần hiểu dấu hiệu đó trong ngữ cảnh.

Tên mô tả dùng trong dự án: **định vị online từng lượt công việc dựa trên mục tiêu hoàn thành**. Từ khóa tìm tài liệu gồm *online temporal action localization (On-TAL)*, *online action detection*, *work-cycle segmentation*, *online completion detection* và *procedure understanding*. Đây là tổ hợp các khía cạnh nghiên cứu; chưa khẳng định một tên benchmark duy nhất bao phủ đúng toàn bộ yêu cầu.

## 2. Yêu cầu đã xác nhận và các giả định

### 2.1. Đã được người dùng xác nhận

| ID | Yêu cầu |
| --- | --- |
| U01 | Đầu vào là video quan sát một người đang thực hiện công việc. |
| U02 | Cần xác định khi bắt đầu và khi kết thúc công việc để cắt video. |
| U03 | Trong một video có thể có nhiều lượt cùng công việc; phải trả về nhiều đoạn riêng. |
| U04 | Một lượt có thể chứa nhiều thao tác/hoạt động khác nhau. |
| U05 | Đơn vị đầu ra là toàn bộ một lượt hoàn thành công việc, bao gồm gián đoạn bên trong. |
| U06 | Có dấu hiệu kết thúc khi làm xong; cần khảo sát cách quan sát và sử dụng dấu hiệu này. |
| U07 | Phải xác định rõ yêu cầu và các vấn đề trước khi chọn hướng từ paper. |
| U08 | Dữ liệu dự án lưu trên Google Drive trong `MyDrive/Datasets`; thao tác dữ liệu chủ yếu chạy bằng CLI trên Colab. |
| U09 | Bài toán phải chạy online: xử lý luồng theo thời gian và phát kết quả khi nhận biết hoàn thành, không đợi xem hết video. |

U06 là mô tả của ứng dụng, **chưa chứng minh dấu hiệu này luôn nhìn thấy, luôn duy nhất hoặc đủ để xác nhận hoàn thành trong mọi video**.

### 2.2. Phạm vi làm việc đề xuất cho phiên bản đầu — cần kiểm chứng bằng dữ liệu

- Suy luận causal theo prefix là hệ quả của U09: ở thời điểm quyết định chỉ dùng frame đã tới. Độ trễ cho phép, chunk size, tốc độ nguồn và phần cứng cụ thể chưa chốt; không tự đồng nhất online với độ trễ bằng 0.
- Chỉ bắt buộc RGB một góc nhìn lúc suy luận. Pose, vật thể, depth, audio hoặc nhiều góc có thể dùng khi thực sự có sẵn, nhưng phải công bố rõ đầu vào của từng thực nghiệm.
- Mỗi lần chạy đã xác định công việc mục tiêu bằng cấu hình/model phù hợp. Chưa yêu cầu nhập mô tả tùy ý hoặc một video mẫu để tìm công việc chưa từng học.
- Có một người chính và một lượt mục tiêu đang hoạt động tại một thời điểm. Các lượt cùng loại không đan xen theo nhiều sản phẩm ở phiên bản đầu.
- Không biết trước số lượt trong video. Cần chấp nhận cả video không có lượt hoàn thành nào để kiểm tra báo nhầm.
- Đơn vị công việc và quy ước ranh giới phải được định nghĩa trước khi gán nhãn; không tự chọn đơn vị chỉ vì dataset có nhãn thuận tiện.

Ngoài ràng buộc online/causal xuất phát từ U09, các giới hạn còn lại là đề xuất nghiên cứu, không được ghi lại thành nhu cầu đã xác nhận của người dùng.

### 2.3. Những việc không mặc định nằm trong yêu cầu cốt lõi

Chấm điểm kỹ năng/chất lượng, phát hiện mọi lỗi quy trình, nhận dạng người, đếm từng nhịp chuyển động, vẽ bounding box, phân đoạn từng pixel và dự đoán thời gian còn lại không phải đầu ra bắt buộc hiện tại. Một số có thể là tín hiệu phụ hoặc hướng mở rộng. Không biến việc gán nhãn mọi bước nhỏ thành điều kiện bắt buộc nếu mục tiêu chỉ cần ranh giới lượt công việc.

### 2.4. Hợp đồng online bắt buộc

- Phát hiện và đóng từng lượt ngay trong quá trình quan sát, với ngân sách độ trễ hữu hạn cần chốt trước khi đánh giá. Không được trì hoãn đến hết video/ca làm việc.
- Không dùng frame tương lai chưa tới, tổng thời lượng luồng, số lượt cuối cùng, end-of-file hoặc thao tác của lượt kế tiếp như thông tin có sẵn để quyết định ở hiện tại.
- Một chút dữ liệu đến sau mốc hoàn thành GT có thể giúp xác nhận; nếu sử dụng nó, thời điểm phát thực tế phải muộn tương ứng và được tính vào latency. Không ghi lùi thời điểm phát để giả lập phát hiện tức thì.
- Có thể tinh chỉnh mốc bắt đầu về một thời điểm đã quan sát trong quá khứ. Điều này không cho phép giả vờ đã phát hiện bắt đầu từ lúc đó; phải giữ riêng timestamp ranh giới và timestamp phát quyết định.
- Hệ thống phải giữ đủ lịch sử/trạng thái và video đã ghi để xuất trọn đoạn, kể cả khi nhận ra bắt đầu muộn hoặc lượt có gián đoạn dài.
- Phải phân biệt causal inference với tốc độ thực thi: một model không nhìn tương lai vẫn có thể quá chậm để theo kịp stream. Cần kiểm tra cả causal correctness và throughput/latency.

## 3. Đơn vị công việc và mục tiêu hoàn thành

### 3.1. Các cấp độ phải phân biệt

| Cấp độ | Ví dụ | Có thể coi là một lượt của bài toán không? |
| --- | --- | --- |
| Động tác/chuyển động nhỏ | Một vòng xoay tua vít | Chỉ khi đó chính là đơn vị người dùng cần; không mặc định sử dụng. |
| Công việc có mục tiêu cục bộ | Gắn xong một chân bàn | Có, nếu đây là công việc mục tiêu đã chọn. Nó có thể gồm lấy, căn chỉnh, xoay, siết và kiểm tra. |
| Quy trình lớn | Lắp xong toàn bộ một cái bàn | Có, nếu đây là công việc mục tiêu; không được thay bằng một lần gắn chân bàn. |

Yêu cầu “toàn bộ một lần công việc” đã được xác nhận; **công việc cụ thể và cấp độ mục tiêu thực tế còn phải chốt**. Các ví dụ đóng gói hoặc gắn chân bàn trong tài liệu là minh họa.

### 3.2. Hợp đồng mô tả một công việc

Mỗi loại công việc cần một `task_definition` có phiên bản, tối thiểu mô tả:

1. Mục tiêu/kết quả cuối cùng cần đạt và đối tượng công việc, ví dụ một sản phẩm hoặc một bộ phận.
2. Điều kiện khởi đầu và hoạt động đầu tiên được tính vào lượt.
3. Tiêu chí xác nhận hoàn thành, bằng chứng có thể quan sát và giới hạn của bằng chứng đó.
4. Phạm vi: có tính chuẩn bị, lấy dụng cụ, kiểm tra, bàn giao, đặt sản phẩm và dọn dẹp vào lượt không?
5. Những biến thể hợp lệ về thứ tự, cách làm, số thao tác, thử lại và sửa lỗi.
6. Điều gì phân biệt cùng một lượt được tiếp tục với một lượt mới.
7. Cách ghi nhận bỏ dở, không quan sát đủ và video cắt mất đầu/cuối.
8. Quy ước mốc thời gian, độ bất định chấp nhận được và ví dụ đối chứng.

Không cần một danh sách động tác cứng nếu công việc có nhiều cách thực hiện hợp lệ. Tuy nhiên, phải có mô tả đủ cụ thể để hai người gán nhãn có thể thống nhất về cùng một lượt.

### 3.3. Hoàn thành và chất lượng là hai thuộc tính khác nhau

`completed` nghĩa là đã đáp ứng tiêu chí hoàn thành được định nghĩa cho công việc trong nghiên cứu. Nó không tự động chứng minh mọi tiêu chuẩn chất lượng, an toàn, lực siết hoặc độ chính xác sản phẩm đều đạt.

Nếu mục tiêu quy định “lắp đúng”, trạng thái lắp đúng trở thành một phần tiêu chí hoàn thành. Nếu mục tiêu chỉ quy định “kết thúc một lượt đóng gói/bàn giao”, kết quả chất lượng có thể phải ghi riêng. Những tiêu chuẩn không quan sát được từ RGB không được suy diễn thành nhãn đúng/sai chắc chắn.

Việc người đó ngừng làm, buông vật, rời bàn hoặc làm động tác cuối quen thuộc chưa đủ để kết luận hoàn thành. Cũng không nên mặc định mọi lượt làm khác mẫu đều là làm sai.

## 4. Định nghĩa đầu vào và đầu ra

### 4.1. Đầu vào

- Một luồng frame/chunk chưa cắt sẵn thành từng lượt, có timestamp/frame hoặc PTS. Trong benchmark video ghi sẵn có duration `D`, nhưng model online không được dùng duration tương lai hoặc đọc trước phần chưa được phát.
- Một người chính cần theo dõi; không bắt buộc cung cấp sẵn skeleton hoặc bounding box.
- Định nghĩa công việc mục tiêu `g`: có thể là cấu hình của model, không nhất thiết là một câu văn đầu vào.
- Metadata cần giữ: video ID, phiên bản nguồn, duration, timestamp/fps, độ phân giải, camera/view và recording/session ID khi có.
- Metadata phục vụ chia tập/gán nhãn như participant ID hoặc ground truth không được đưa vào model nếu lúc triển khai không có.

Online đã chốt; còn chưa chốt độ trễ tối đa, tốc độ nguồn/FPS, độ phân giải, số loại công việc, độ dài context và phần cứng. Đầu vào có thể là camera trực tiếp hoặc video replay tuần tự; nguồn triển khai cụ thể còn cần xác định. Stream có thể kéo dài và chưa biết thời điểm kết thúc.

### 4.2. Đầu ra cốt lõi

Một chuỗi sự kiện được phát khi stream đang chạy. Mỗi lượt hoàn thành tạo một kết quả interval; danh sách bên dưới là snapshot tích lũy của các kết quả đã phát, không phải kết quả phải đợi hết video mới tạo:

```json
{
  "video_id": "example_video",
  "time_unit": "seconds",
  "interval_convention": "[start, end)",
  "task_definition_version": "pack_product_v1",
  "instances": [
    {
      "instance_id": "example_video_001",
      "task_type": "pack_product",
      "start": 4.2,
      "end": 38.5,
      "status": "completed",
      "event_id": "example_video_001_completed",
      "observed_until": 39.0,
      "emitted_at": 39.3,
      "is_final": true,
      "confidence": 0.91
    },
    {
      "instance_id": "example_video_002",
      "task_type": "pack_product",
      "start": 45.0,
      "end": 92.1,
      "status": "completed",
      "event_id": "example_video_002_completed",
      "observed_until": 92.6,
      "emitted_at": 92.9,
      "is_final": true,
      "confidence": 0.86
    }
  ]
}
```

Các số trên chỉ minh họa schema, không phải dự đoán trên dữ liệu thực. `confidence` là điểm xếp hạng; chỉ được hiểu như xác suất nếu đã đánh giá/hiệu chỉnh xác suất.

`observed_until` là mốc timeline đã thực sự được model sử dụng, tính cả khoảng thời gian của frame/chunk cuối. `emitted_at` là thời điểm phát kết quả quy về cùng gốc thời gian video trong phép đo; triển khai phải lưu thêm clock thực/đồng bộ nguồn để đo end-to-end. Không lấy thời gian nhận request hoặc chỉ timestamp dự đoán `end` để thay cho thời điểm phát thực tế. Ví dụ đầu có ranh giới kết thúc 38,5 s nhưng thông báo lúc 39,3 s, không phải thông báo tại 38,5 s.

Nếu cung cấp sự kiện bắt đầu/cập nhật `in_progress`, phải phân biệt provisional với final. Yêu cầu bắt buộc hiện tại là phát lượt hoàn thành online; có cần báo bắt đầu ngay lập tức và cho phép sửa/rút thông báo đến mức nào còn cần chốt. Phải giữ event log theo thời điểm phát thực, không chỉ snapshot cuối cùng đã được chỉnh cho đúng. `event_id` hỗ trợ chống tạo thêm lượt khi gửi lại cùng kết quả.

Điều kiện hợp lệ: `0 <= start < end <= D`, sắp theo thời gian và không có hai dự đoán trùng cho cùng một lượt. Hai lượt cùng loại nối tiếp nhau vẫn phải có hai `instance_id`. Không xuất một đoạn từ lần bắt đầu đầu tiên đến lần kết thúc cuối cùng để gộp toàn bộ video.

Clip video cắt ra là sản phẩm suy ra từ timestamp đã phát và video quá khứ được giữ lại. Kết quả định vị phải lưu độc lập với việc encode clip. Đo riêng lúc phát sự kiện và lúc clip xuất xong; encoder/upload không được làm mất các frame mới của stream.

### 4.3. Trạng thái nghiên cứu bổ sung

Ground truth cần phân biệt các trường hợp sau, dù API chính chỉ trả các lượt hoàn thành:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `completed` | Quan sát đủ bằng chứng thỏa tiêu chí hoàn thành đã định nghĩa. |
| `aborted` | Có bằng chứng lượt bị bỏ/hủy mà chưa đáp ứng tiêu chí hoàn thành. Không suy ra chỉ từ một khoảng nghỉ dài. |
| `ongoing` | Ở cuối video có bằng chứng công việc còn đang thực hiện. |
| `unknown` | Không đủ bằng chứng để xác định trạng thái, ví dụ hoàn thành ngoài khung hình. |

Các cờ `left_censored`/`right_censored` ghi riêng việc video không quan sát được phần đầu/cuối. Chúng không phải kết luận về thành công. Khi không biết một ranh giới, lưu `null` hoặc khoảng bất định, không biến thời điểm bắt đầu/kết thúc file thành mốc công việc thật.

Benchmark interval chính đề xuất chỉ dùng lượt hoàn thành có cả hai biên quan sát đủ để chấm, đồng thời báo rõ coverage. Một lượt bị mất phần đầu nhưng có mốc hoàn thành rõ vẫn có thể tham gia đánh giá completion event riêng, không được gán start bằng 0 để ép vào metric interval.

Tùy mục tiêu mở rộng, có thể thêm `work_item_id`, `completion_event`, `boundary_uncertainty`, `evidence_visible`, `quality_outcome` hoặc các bước con. Các trường này phải được định nghĩa và kiểm tra annotation trước khi dùng để đánh giá.

## 5. Mô hình hóa hình thức

Biểu diễn video là `V = {(I_t, τ_t)}`, trong đó `I_t` là frame và `τ_t` là timestamp của frame trong video nguồn. Công việc mục tiêu là `g`. Ground truth cốt lõi:

```text
Y_g = {(s_i, e_i)} từ i = 1 đến N,
N >= 0, 0 <= s_i < e_i <= D.

(h_k, E_k) = F_theta(V_<=a_k, h_(k-1); g)

a_k: mốc dữ liệu đã quan sát trong stream ở bước k.
h_k: trạng thái/bộ nhớ cập nhật.
E_k: các sự kiện/cập nhật phát ở bước k, có thể rỗng.
Mỗi sự kiện hoàn thành mang (s_hat_j, e_hat_j, score_j, emitted_at_j).
0 <= s_hat_j < e_hat_j <= a_k <= emitted_at_j khi các mốc đã đồng bộ cùng clock.
```

`N` và `M` không biết trước, không cần bằng nhau. Định nghĩa `g` có thể đã cố định trong model; công thức không yêu cầu bắt buộc có text encoder.

`M` là tổng số instance hoàn thành dự đoán sau khi gộp các sự kiện theo instance ID; số thông báo thực tế có thể lớn hơn nếu có update/revision và phải được lưu để chấm hành vi online.

`Y_g` là mô tả GT của recording để đánh giá; model chỉ được truy cập prefix `V_<=a_k`. Cùng một prefix, trạng thái khởi tạo và cấu hình phải cho cùng lịch sử quyết định bất kể phần video nối tiếp sau đó. Đầu ra đã phát ở bước k không được âm thầm thay bằng kết quả dùng toàn bộ video. Điều kiện causal là cần nhưng chưa đủ: thời điểm phát còn phải đáp ứng ngân sách độ trễ và khả năng theo kịp stream.

Với phiên bản một lượt mục tiêu hoạt động tại một thời điểm, ground truth có thể có `e_i <= s_(i+1)`, bao gồm cả `e_i = s_(i+1)`. Không áp dụng ràng buộc không chồng lấp một cách phổ quát: nếu người đó làm xen kẽ hai sản phẩm, hai khoảng bao trọn lượt có thể chồng lấp dù chỉ có một người.

Một đoạn `[s_i, e_i)` có thể chứa nhiều khoảng hoạt động, nghỉ và thao tác ngoài mục tiêu. Vì vậy, membership của **toàn bộ lượt công việc** khác với nhãn **động tác đang diễn ra ở từng frame**. Không tự động cắt đoạn khi nhãn động tác đổi hoặc khi tay tạm dừng.

Nếu một bước downstream cần bỏ khoảng nghỉ, có thể tạo thêm activity mask hoặc clip dẫn xuất; phải giữ bản interval bao trọn theo yêu cầu gốc và đánh giá hai đầu ra khác nhau.

## 6. Quy tắc xác định ranh giới

### 6.1. Bắt đầu lượt

Mốc bắt đầu là hoạt động sớm nhất được định nghĩa là thuộc lượt mục tiêu, với đủ ngữ cảnh để gắn nó với lượt đó. Không mặc định lấy lúc xuất hiện người, lúc video bắt đầu, lúc tay bắt đầu chuyển động hoặc lần đầu xuất hiện dụng cụ.

Quy tắc có thể là bắt đầu lấy phôi mới, bắt đầu tương tác với sản phẩm mới hoặc bước chuẩn bị bắt buộc. Chọn quy tắc theo `task_definition`, dùng nhất quán giữa annotator và dataset.

### 6.2. Kết thúc lượt và bằng chứng hoàn thành

Mốc kết thúc gắn với tiêu chí kết thúc công việc đã chọn, mặc định là thời điểm đầu tiên mục tiêu được hoàn thành đủ rõ theo quy ước. Nếu kiểm tra/bàn giao là phần bắt buộc của công việc, mốc kết thúc phải bao gồm phần đó.

Phải phân biệt:

- `t_goal`: thời điểm tiêu chí hoàn thành thực sự được đáp ứng theo nhãn.
- `t_evidence`: lúc có đủ bằng chứng để người/model xác nhận; có thể muộn hơn.
- `t_emit`: lúc hệ thống online phát thông báo; còn gồm độ trễ xử lý.
- `clip_end`: mốc cắt sau khi thêm context/padding nếu ứng dụng cần; không thay ground-truth endpoint.

Annotator có thể xem toàn recording để xác định GT, nhưng model online tại thời điểm phát chỉ được dùng dữ liệu đã tới. Ví dụ hoàn thành GT tại 38,5 s, dùng bằng chứng đến 39,0 s rồi phát lúc 39,3 s là một quyết định causal có trễ; phải báo đầy đủ độ trễ đó. Không được dùng bằng chứng ở 45 s rồi ghi nhận đã báo từ 38,5 s. Nếu không xác định được chính xác lúc hoàn thành, phải ghi khoảng bất định.

Một dấu hiệu kết thúc cần được kiểm tra với các hard negative: buông vật để chỉnh lại, đặt xuống tạm, rời vị trí lấy dụng cụ, làm động tác tương tự giữa quy trình, hoặc kết thúc thao tác nhưng kết quả chưa đạt mục tiêu.

### 6.3. Ngắt quãng, sửa lỗi và lượt mới

- Nghỉ/nghe điện thoại/tìm dụng cụ rồi tiếp tục cùng lượt: giữ chung một đoạn, theo yêu cầu đã xác nhận.
- Thử thao tác nhiều lần hoặc sửa lỗi trước khi hoàn thành: mặc định vẫn là một lượt nếu cùng mục tiêu và cùng đối tượng công việc.
- Sau khi một lượt thực sự hoàn thành, bắt đầu xử lý đối tượng/lượt mới: tạo đoạn mới, kể cả khi không có background giữa hai lượt.
- Không dùng một timeout cố định để suy ra mọi khoảng nghỉ dài đều là kết thúc. Nếu cần timeout vận hành, phải công bố đó là một quy tắc ứng dụng và đánh giá lỗi nó gây ra.
- Không tự gán sửa lỗi sau hoàn thành thành lượt mới. Cần quy tắc về rework/revision theo công việc và đối tượng.
- Nếu không thể biết người đó quay lại cùng sản phẩm hay bắt đầu sản phẩm khác, ghi bất định hoặc loại khỏi metric ranh giới chính theo quy tắc công khai.

### 6.4. Quy ước thời gian và cắt clip

- Lưu giây theo timeline gốc, đồng thời lưu frame index nguồn khi có thể.
- Dùng `[start_frame, end_frame_exclusive)` cho nhãn frame. Nếu frame `k` chứa bằng chứng hoàn thành cần giữ, endpoint phải bao gồm frame `k`.
- Khi import nhãn có end-frame inclusive, đổi quy ước rõ ràng; kiểm tra off-by-one và FPS gốc.
- Với variable frame rate, ưu tiên PTS; không quy đổi bằng một FPS giả định.
- Nếu resample video hoặc trích feature, giữ mapping về timeline gốc. Độ phân giải feature ảnh hưởng khả năng đặt ranh giới; cần đo thay vì hứa độ chính xác nhỏ hơn sampling stride mà không có bước tinh chỉnh.
- Xuất clip phải kiểm tra frame đầu/cuối, seek theo keyframe, audio sync nếu giữ audio và duration thực tế. Cắt bằng stream-copy có thể không chính xác như timestamp; encode lại khi yêu cầu cần ranh giới chính xác.
- Context trước/sau clip là tùy chọn xuất dữ liệu, không được dùng để làm đẹp metric định vị.

### 6.5. Bộ đệm và vòng đời của một lượt online

- Duy trì trạng thái cho một lượt đang mở qua các chunk, khoảng nghỉ, che khuất và sửa lỗi; không reset chỉ vì hết cửa sổ model.
- Giữ pre-roll để bao gồm hoạt động đầu tiên nếu phát hiện bắt đầu bị trễ. Khi đã mở lượt, có thể ghi video nén liên tục ra storage thay vì giữ mọi frame trong RAM.
- Nếu chưa có giới hạn thời lượng lượt, một ring buffer cố định không đủ bảo đảm giữ toàn bộ video từ start đến end. Cần chính sách lưu đoạn đang mở, dung lượng và hết chỗ; không lặng lẽ cắt mất đầu lượt dài.
- Trong lúc hoàn thiện/thông báo lượt trước, vẫn tiếp nhận và theo dõi dữ liệu của lượt kế tiếp. Thời gian xuất clip không được gộp hai lượt hoặc làm mất lần bắt đầu mới.
- Chốt rõ lúc nào có thể tinh chỉnh start/end và khi nào kết quả đã final. Nếu cho phép rút/sửa cảnh báo, dùng event có phiên bản và đo cả cảnh báo sai đã từng phát.
- Mất kết nối, thiếu frame, timestamp reset hoặc khởi động giữa lượt là vấn đề continuity/censoring, không phải bằng chứng hoàn thành. Khôi phục state phải gắn đúng stream/session và timeline; nếu không đủ bằng chứng thì chuyển unknown/reset có ghi nhận.

## 7. Các trường hợp khó phải có trong phân tích và benchmark

| Nhóm | Tình huống | Hành vi/điều cần kiểm tra |
| --- | --- | --- |
| Số lượt | Không có lượt mục tiêu; chỉ chuẩn bị hoặc làm việc khác | Có thể trả danh sách rỗng; đo false positives. |
| Số lượt | Một lượt; nhiều lượt; hai lượt nối tiếp không nghỉ | Không cố định số đoạn, không gộp vì cùng lớp. |
| Gián đoạn | Nghỉ ngắn/dài, ra ngoài khung hình rồi quay lại | Giữ liên kết lượt khi có bằng chứng; không bịa mốc trong vùng không nhìn thấy. |
| Quy trình | Đổi thứ tự hợp lệ, thêm bước tùy chọn, gộp/tách thao tác | Theo dõi mục tiêu thay vì khớp cứng một chuỗi mẫu. |
| Thử lại | Động tác lặp nhiều lần, lỗi và sửa lỗi | Không đếm mỗi lần thử thành một lượt hoàn thành. |
| Hoàn thành giả | Động tác cuối quen thuộc nhưng chỉ đặt tạm/lắp chưa xong | Không kết thúc sớm chỉ vì hình dáng chuyển động. |
| Hoàn thành kín | Kết quả đạt khi tay/vật bị che hoặc ngoài khung | Phân biệt có thể nhận biết kết quả với có thể định vị chính xác thời điểm. |
| Bỏ dở | Dừng, cất vật lỗi, chuyển việc nhưng chưa hoàn thành | Không nhận nhầm là completed; cần positive evidence cho aborted. |
| Biên video | Lượt đang làm từ trước; video dừng trước khi xong | Gắn cờ censoring, không dùng biên file thay biên công việc. |
| Chuyển cảnh | Edit/cut cảnh, tua nhanh, mất frame hoặc timestamp nhảy | Không coi cut là ranh giới ngữ nghĩa nếu chưa có bằng chứng. |
| Stream | Frame tới trễ/sai thứ tự, gián đoạn mạng, reconnect hoặc reset timestamp | Có chính sách reorder/drop/reset, ghi nhận khoảng thiếu dữ liệu và tính phần trễ vào end-to-end. |
| Stream | Inference chậm, queue tăng, xuất clip chặn nhận frame | Không được gọi là theo kịp stream chỉ vì model có tính causal; đo backlog, frame drop và tail latency. |
| Stream | Khởi động giữa lượt hoặc chạy liên tục qua nhiều lượt dài | Không bịa start; giữ state đúng session và quản lý buffer/storage. |
| Thị giác | Che khuất, vật nhỏ, tay đổi bên, nhiều cách cầm dụng cụ | Kiểm tra khả năng dùng ngữ cảnh và trạng thái vật thể. |
| Thị giác | Ánh sáng, blur, camera rung, góc nhìn, độ phân giải khác | Đánh giá theo điều kiện; không chỉ đo trên video dễ. |
| Nhiễu | Người đi ngang hoặc hỗ trợ thoáng qua | Không tự đổi người mục tiêu; nhiều người cùng làm chính là biến thể cần đặc tả riêng. |
| Định danh lượt | Hai vật giống nhau, thay sản phẩm, lặp lại trạng thái ban đầu | Xác định reset/lượt mới bằng nhiều bằng chứng, tránh trộn identity. |
| Đan xen | Làm sản phẩm A, làm sản phẩm B, quay lại A | Khoảng bao trọn có thể chồng lấp; cần `work_item_id`/association hoặc đặt ngoài phạm vi v1. |
| Mở rộng | Công việc mới, sản phẩm mới, workstation mới | Phân biệt generalization trong cùng task với nhận biết task chưa học. |

Tình huống chưa hỗ trợ phải được gắn nhãn và báo coverage, không lặng lẽ loại khỏi kết quả hoặc tuyên bố đã giải quyết.

## 8. Các vấn đề nghiên cứu cốt lõi

### P01. Từ chuyển động sang mục tiêu

Nhận ra “xoay”, “đặt vật” hoặc “đưa tay ra xa” không đủ biết mục tiêu đã hoàn thành. Cần khảo sát kết hợp lịch sử thao tác, đối tượng tương tác và trạng thái trước–sau. Không giả định mô hình pose thuần túy luôn đủ cho kết quả phụ thuộc chi tiết vật thể.

### P02. Duy trì identity của một lượt qua gián đoạn

Trong khoảng nghe điện thoại, hình ảnh cục bộ có thể giống hệt background ở video không có task. Muốn quyết định khoảng này thuộc lượt nào, model cần ngữ cảnh/trạng thái. Một bộ phân loại frame độc lập có thể không chứa đủ thông tin; smoothing đơn giản cũng có thể gộp nhầm hai lượt.

### P03. Tách các lượt cùng loại sát nhau

Chuỗi lớp `A A A A` không chứa ranh giới instance nếu hai lượt A nối tiếp. Cần nhãn ranh giới/instance hoặc tín hiệu bổ sung. Tần suất chuyển động hoặc density đếm không tự xác định chính xác cả hai biên của một công việc nhiều bước.

### P04. Ngữ cảnh dài và độ chính xác ranh giới

Cần đủ ngữ cảnh để biết tiến trình, nhưng vẫn giữ chi tiết ngắn tại lúc bắt đầu/hoàn thành. Phải khảo sát thời lượng context, sampling, windowing và xử lý lượt vượt qua nhiều cửa sổ. Merge/NMS không được xóa lượt hợp lệ ở sát nhau hoặc tạo trùng khi cửa sổ chồng lấp.

Trong online, bộ nhớ/context chỉ lấy từ lịch sử đã tới. Một model có thể cần vài frame xác nhận sau mốc hoàn thành GT; tác động đó là latency cần đo, không phải ngữ cảnh tương lai miễn phí.

### P05. Mức độ quan sát được và bất định

Nếu tiêu chí là lực siết hoặc trạng thái bên trong không nhìn thấy, RGB có thể không đủ thông tin. Phải phân biệt thiếu dữ liệu quan sát với thiếu năng lực mô hình. Các lựa chọn nghiên cứu gồm thay tiêu chí bằng proxy có kiểm chứng, dùng modality bổ sung, hoặc cho phép unknown; không đánh đồng proxy với sự thật vật lý.

### P06. Dữ liệu và supervision không đúng cấp độ

Nhãn thao tác nhỏ, nhãn đếm và nhãn hoàn thành bước chỉ bao phủ một phần bài toán. Chuyển nhãn có thể cần grouping, identity vật và gán bổ sung. Cần đo chi phí annotation và sai số chuyển đổi; pseudo-label không được dùng như ground truth hoàn toàn đáng tin.

### P07. Học shortcut ngoài ý nghĩa công việc

Model có thể nhớ người, phòng, vị trí cuối video, số lượt trung bình, độ dài quen thuộc, nhịp lặp hoặc dấu nối clip. Cần đối chứng làm mất những shortcut này và kiểm tra chuyển sang recording/người/môi trường mới.

### P08. Nhầm kết thúc với thành công hoặc chất lượng

Một model có thể cắt đúng lúc kết thúc lượt nhưng chưa biết sản phẩm đúng/sai; cũng có thể nhận ra trạng thái thành công mà cắt đầu/cuối sai. Phải tách mục tiêu và metric, thay vì kết luận chất lượng từ điểm localization.

### P09. Rò rỉ tương lai trong toàn bộ pipeline

Không chỉ attention của model: feature encoder, clip được đặt giữa timestamp, smoothing hai chiều, optical flow cần frame kế tiếp, nội suy, normalization theo toàn video hoặc hậu xử lý toàn recording đều có thể dùng dữ liệu chưa tới. Phải gắn mỗi feature/decision với frame mới nhất thực sự được tiêu thụ và audit đến tầng trích feature. Dùng clip kết thúc sau mốc sự kiện là hợp lệ chỉ khi quyết định được phát muộn tương ứng và vẫn đáp ứng budget online.

### P10. Trạng thái bền, bộ nhớ có kiểm soát và backlog

Stream chưa biết trước tổng độ dài. Không thể mặc định lưu toàn bộ lịch sử đặc trưng hoặc video trong RAM, hay chạy lại toàn bộ prefix mỗi frame mà không đánh giá chi phí. Cần chọn cơ chế giữ thông tin dài hạn, lưu video đang mở, cập nhật state theo chunk, nhận diện reset và quản lý queue. Giới hạn RAM của model khác với dung lượng video nén phải giữ để xuất cả lượt.

### P11. Đánh đổi báo sớm, báo sai và báo muộn

Chờ thêm bằng chứng có thể giảm false completion nhưng tăng độ trễ; báo quá sớm có thể gây cắt thiếu hoặc thông báo hoàn thành cho lượt chưa xong. Cần đường trade-off accuracy–latency và một chính sách commit/revision rõ ràng. Một bộ kết quả cuối đẹp sau khi sửa mọi cảnh báo không phản ánh trải nghiệm online.

## 9. Liên hệ với các bài toán và hướng paper

| Hướng | Thành phần có thể dùng | Khoảng cách với yêu cầu của dự án |
| --- | --- | --- |
| Online Temporal Action Localization (On-TAL) | Phát hiện nhiều instance start/end trên stream | Sát cấu trúc đầu ra; vẫn cần ngữ nghĩa hoàn thành và nhãn toàn bộ lượt công việc. |
| Online Action Detection (OAD) | Phân loại frame hiện tại bằng lịch sử và bộ nhớ causal | Nhãn frame hiện tại chưa tự cho instance, cả hai biên hoặc bằng chứng hoàn thành. |
| Temporal Action Detection/Localization offline | Tham khảo detector/representation và đối chứng nhìn toàn video | Kết quả offline không phải kết quả chính; phải audit/cải biến causal và đo lại độ trễ nếu chuyển sang online. |
| Temporal Action Segmentation | Ngữ cảnh thời gian và các bước con | Nhãn lớp/frame có thể mất ranh giới lượt sát nhau; cần kiểm tra tính causal, nhiều cách TAS dùng context tương lai. |
| Repetitive action counting/localization | Tự tương đồng và nhiều lần xuất hiện | Chu kỳ động tác không tương đương chu kỳ công việc có nhiều bước biến đổi. |
| Completion moment detection | Bằng chứng hoàn thành và incomplete attempts | Chỉ tìm mốc hoàn thành chưa đủ; kiểm tra có dùng frame sau sự kiện và thời điểm phát thực hay không. |
| Procedure understanding / step recognition | Tiến trình, trạng thái sản phẩm, biến thể thứ tự và lỗi | Hoàn thành từng bước chưa tự cho grouping toàn bộ lượt ở cấp mục tiêu đã chọn. |
| Text/exemplar-conditioned localization | Chọn task bằng mô tả/video mẫu | Chỉ cần nếu ứng dụng phải đổi task hoặc nhận biết task chưa học; không mặc định thuộc v1. |
| Action Quality Assessment | Có thể sử dụng clip sau phân đoạn | Chấm chất lượng là mục tiêu kế tiếp, không thay thế định vị lượt. |

Các điểm phân biệt trên dùng để đọc và đối chiếu paper, không phải tuyên bố mô hình nào đã giải quyết bài toán này. Tài liệu tham chiếu cho định nghĩa hướng nghiên cứu: [ActionFormer](https://arxiv.org/abs/2202.07925), [MS-TCN](https://github.com/yabufarha/ms-tcn), [TransRAC](https://arxiv.org/abs/2204.01018), [Action Completion](https://dimadamen.github.io/ActionCompletion/) và [IndustReal](https://arxiv.org/abs/2310.17323).

Với yêu cầu online đã chốt, bổ sung các điểm xuất phát: [CAG-QIL — On-TAL, ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Kang_CAG-QIL_Context-Aware_Actionness_Grouping_via_Q_Imitation_Learning_for_Online_ICCV_2021_paper.html), [LSTR — OAD, NeurIPS 2021](https://arxiv.org/abs/2107.03377) và [Online Temporal Action Localization with Memory-Augmented Transformer — ECCV 2024](https://arxiv.org/abs/2408.02957). Chúng gợi ý các hướng streaming, temporal memory và định vị instance; chưa chứng minh giải quyết đúng ngữ nghĩa lượt công việc trong dự án.

## 10. Yêu cầu dữ liệu và chuyển đổi dataset

### 10.1. Một mẫu benchmark phù hợp cần gì?

- Video liên tục có trước/sau hành động, không chỉ clip đã cắt đúng cả lượt.
- Có thể replay tuần tự theo timestamp mà không lộ tương lai; biết rõ feature tải sẵn đã dùng những frame nào. Nhãn và metadata của phần tương lai chỉ được evaluator sử dụng.
- Danh sách instance đầy đủ ở cấp công việc đã chọn; có liên kết thao tác con nếu dùng chúng để suy ra nhãn.
- Bằng chứng cho bắt đầu, hoàn thành và sự phân biệt giữa hai lượt liên tiếp.
- Mẫu không chứa task, lượt bỏ dở/không đủ quan sát và các gián đoạn gần với ứng dụng thực tế.
- Metadata đủ để nhóm recording đồng bộ, participant, view, work item và các bản sao cùng nguồn.
- Lưu lineage từ nguồn → xử lý → nhãn mới; kiểm tra điều kiện sử dụng của từng nguồn trước khi phân phối dữ liệu hoặc clip dẫn xuất.

### 10.2. Vai trò dự kiến của các nguồn đã khảo sát

| Nguồn | Giá trị cho dự án | Điều phải kiểm tra/gán thêm |
| --- | --- | --- |
| [IKEA ASM](https://arxiv.org/abs/2007.00394) | Thao tác lắp ráp, góc cố định, thông tin người–vật; phù hợp thử grouping công việc | Nhãn atomic khác với lượt hoàn thành. Nếu chọn “gắn một chân bàn”, phải kiểm tra grouping theo chân; nếu chọn “lắp cả bàn”, không đổi sang bài toán nhỏ hơn. |
| [IndustReal](https://arxiv.org/abs/2310.17323) | Nhận biết hoàn thành bước, trạng thái lắp ráp và lỗi | Group bước thành mục tiêu cần cắt; kiểm tra quan hệ thời gian giữa nhãn thao tác và completion. Gói RGB/action labels không đảm bảo chứa đủ nhãn quy trình. |
| [Assembly101](https://assembly-101.github.io/) | Biến thể thứ tự, lỗi/sửa lỗi, nhiều góc đồng bộ | Chọn cấp coarse/fine phù hợp và gán lượt; không chia các góc cùng recording sang train và test. |
| [RepCount](https://arxiv.org/abs/2204.01018) | Ranh giới chu kỳ và gián đoạn khi lặp | Dùng đối chứng cho lặp; không coi một chu kỳ vận động là nhãn sẵn cho công việc nhiều bước. |
| [FineAction](https://arxiv.org/abs/2105.11107) | Benchmark nhiều đoạn hành động, lớp và background đa dạng | Phù hợp đối chứng TAL; không có bằng chứng nhãn hiện tại tự biểu diễn toàn bộ lượt công việc mục tiêu. |
| [HA4M](https://pmc.ncbi.nlm.nih.gov/articles/PMC9718853/) | Quy trình lắp ráp và các thao tác lặp trong một lượt | Kiểm tra/gán thêm cấp toàn bộ công việc và nhu cầu nhiều lượt liên tục. |

Đây là đánh giá phù hợp từ mô tả/paper. **Chưa phải kết quả audit toàn bộ file nhãn/video đã tải về.** Tải được dataset hoặc giải nén thành công không chứng minh có nhãn đúng bài toán.

### 10.3. Nguyên tắc chuyển nhãn

1. Nếu có start/end đúng cấp lượt: giữ từng instance, chuẩn hóa timestamp và trạng thái.
2. Nếu chỉ có action segments: nhóm theo mục tiêu và đối tượng, kiểm tra thủ công; không chỉ lấy min(start)/max(end) của một class trên toàn video.
3. Nếu chỉ có nhãn lớp từng frame: có thể lấy các run liên tục khi có ranh giới lớp; hai lượt cùng lớp sát nhau cần nhãn bổ sung.
4. Nếu chỉ có tổng số lần: không chia đều duration để tạo nhãn start/end.
5. Nếu chỉ có completion timestamps: cần tìm/gán cả mốc bắt đầu; khoảng giữa hai completion có thể chứa nghỉ hoặc việc khác không thuộc lượt.
6. Nếu video chỉ chứa một lượt/đã trim: không lấy biên file làm GT nếu chưa kiểm tra. Có thể hỗ trợ học mục tiêu, nhưng chưa đủ đánh giá phát hiện nhiều lượt trong video liên tục.
7. Có thể tổng hợp video nhiều lượt để khởi tạo/đối chứng. Cần chia theo nguồn trước khi ghép, tránh dấu nối thành shortcut, và giữ test video liên tục thật.

## 11. Gán nhãn và kiểm soát chất lượng

### 11.1. Các lớp annotation

- Bắt buộc cho ground truth chính: video/recording ID, task definition version, instance ID, start/end có quan sát được, trạng thái và censoring.
- Với ranh giới không rõ: ghi khoảng `[earliest, latest]`, mức chắc chắn và lý do như che khuất, thiếu frame hoặc nhiều cách hiểu quy tắc.
- Khi cần grouping: work item identity hoặc quan hệ giữa các bước và lượt.
- Tùy chọn: mốc completion/evidence, thao tác nhỏ, loại lỗi, pose/object state. Không yêu cầu gán dày đặc tất cả nếu chưa phục vụ một giả thuyết cụ thể.

Một video phải được annotate các lượt theo quy tắc nhất quán, không chỉ những lượt model dễ tìm. Vùng chưa có nhãn phải mang trạng thái chưa được audit; không tự động biến thành negative sạch.

### 11.2. Quy trình đề xuất

1. Chọn một task rõ ràng và viết guideline có ví dụ positive, negative, gián đoạn, bỏ dở và censoring.
2. Gán thử một tập nhỏ đa dạng. Một phần có ít nhất hai annotator độc lập trước khi thảo luận.
3. Đo đồng thuận về số lượt, trạng thái và độ lệch start/end; không chỉ dùng độ đồng thuận nhãn lớp.
4. Ghi các bất đồng, sửa guideline, rồi gán lại những mẫu bị ảnh hưởng.
5. Với mẫu không thể phân xử từ video, giữ bất định/unknown thay vì ép một timestamp chính xác.
6. Lưu annotation version, annotator/adjudication và mapping về nguồn. Kiểm tra tự động giới hạn thời gian, thứ tự, trùng instance và consistency.

Tỷ lệ gán kép, kích thước pilot và dung sai ranh giới chưa được chốt. Cần chọn dựa trên độ đa dạng dữ liệu và sai khác annotator, không dựa vào con số tùy ý.

### 11.3. Annotation và supervision cho online

- Annotator được xem toàn recording để tạo GT; model tại thời điểm đánh giá vẫn chỉ thấy prefix. Quyền của annotator và quyền của model là khác nhau.
- Khi có thể, gán cả mốc hoàn thành theo mục tiêu và mốc đủ bằng chứng quan sát, để tách độ trễ do không nhìn thấy với độ trễ thuật toán.
- Một lượt cuối cùng sẽ completed vẫn là chưa hoàn thành ở các prefix trước mốc đó. Không truyền nhãn completed của cả clip cho mọi frame của lượt.
- Target smoothing/gaussian quanh mốc completion không được vô tình khuyến khích phát thông báo completed trước khi sự kiện xảy ra. Nếu dự đoán trước, đánh giá riêng như anticipation, không lẫn với xác nhận hoàn thành.
- Cần vùng bắt đầu stream giữa lượt, mất frame và reconnect để đánh giá censoring/khôi phục state; không chỉ các stream luôn bắt đầu từ background sạch.

## 12. Thiết kế benchmark và chia tập

### 12.1. Ngăn rò rỉ dữ liệu

- Chia theo recording/session/người trước khi cắt clip, trích cửa sổ hoặc tổng hợp video.
- Các camera đồng bộ của cùng một lần thực hiện, crop/augment và bản copy của video nguồn phải cùng một partition.
- Không để cùng object instance/trial ở cả train và test nếu điều đó làm lộ tiến trình hoặc mốc completion; công bố quy tắc grouping.
- Nếu đánh giá môi trường mới, tách workstation/môi trường. Nếu đánh giá người mới, giữ subject split. Không gọi hai protocol này là một.
- Ghi nguồn và mức chồng lặp đã biết của dữ liệu pretrain; không dùng nhãn test để tạo feature có supervision, pseudo-label hoặc chọn checkpoint.
- Chỉ dùng validation để chọn threshold, dung sai vận hành, hyperparameter và luật hậu xử lý. Khóa test trước khi so sánh.

### 12.2. Các điều kiện đánh giá riêng

Benchmark chính: cùng loại công việc đã định nghĩa, video/phiên/người mới, suy luận **online causal**, mặc định đề xuất một góc RGB. Phát kết quả từng lượt trong khi stream còn chạy, có ngân sách latency cần chốt. Cần có nhóm nhiều lượt, background/negative và gián đoạn, không chỉ video một lượt đã trim.

Các nhóm mở rộng: view mới, vật thể/sản phẩm mới, cách thực hiện mới, task mới có mô tả/exemplar, nhiều người và nhiều lượt đan xen. Online không còn là một nhóm mở rộng. Offline chỉ dùng làm đối chứng/upper bound có ghi rõ quyền nhìn tương lai, không thay benchmark chính.

Mỗi thực nghiệm phải công bố chế độ supervision: nhãn interval đầy đủ, chỉ mốc completion/timestamp, nhãn video, few-shot/exemplar, bán giám sát hoặc không giám sát. So sánh ở cùng ngân sách nhãn hoặc báo riêng chi phí nhãn. Transcript/thứ tự bước/số lượt được cung cấp sẵn lúc test phải được đánh dấu là thông tin bổ sung/oracle, không tính như cùng setting video-only.

### 12.3. Những đối chứng cần có

- Cắt theo thời lượng cố định/chu kỳ trung bình để đo model có thực sự hiểu ngữ nghĩa hay chỉ nhớ nhịp.
- Chỉ dùng dấu hiệu cuối so với dùng dấu hiệu cuối cùng lịch sử/ngữ cảnh.
- Nhãn frame + grouping đơn giản so với mô hình giữ ranh giới instance.
- On-TAL trên nhãn cấp lượt so với quy trình nhận biết bước rồi nhóm lượt theo cách causal.
- RGB so với pose/object-state hoặc modality bổ sung, nếu dữ liệu cho phép đánh giá công bằng.
- Ngữ cảnh ngắn/dài; nhiều mức sampling; có/không xử lý gián đoạn; video thật so với tổng hợp.
- Nhiều mức thời gian chờ xác nhận, chunk size, bộ nhớ và tài nguyên để đo trade-off độ đúng–latency. Nếu có đối chứng offline dùng toàn video, báo thành một protocol khác.

Chỉ đưa một đối chứng vào thực nghiệm khi nó kiểm tra một giả thuyết rõ và đủ thông tin/nhãn để thực hiện. Đây là kế hoạch đánh giá, chưa phải lựa chọn mô hình đã chốt.

### 12.4. Protocol stream và kiểm tra causal

1. Replay frame/chunk theo PTS; tại bước k chỉ chuyển prefix mới tới cho model/state. Không truyền số lượt, duration cuối cùng, GT boundary hoặc future feature.
2. Ghi append-only event log: thời điểm quan sát cuối, mốc dự đoán, thời điểm phát, score, event/instance ID và mọi revision/retraction.
3. Kiểm tra prefix invariance: thay đổi phần suffix sau một thời điểm không được thay đổi những quyết định đã phát trước thời điểm đó, nếu cùng seed/config/state đầu.
4. Audit encoder, normalization, smoothing, feature cache, batching và hậu xử lý. Feature 3D/optical flow có sử dụng frame sau phải được tính sẵn vào thời điểm sớm nhất feature có thể có.
5. Replay nhanh có thể đo causal accuracy và throughput, nhưng không được lấy latency wall-clock của replay tăng tốc làm latency triển khai thật. Dùng replay đúng tốc độ nguồn hoặc protocol đồng hồ mô phỏng có công bố để đo end-to-end.
6. Quy định chunk/window sizes, warm-up, queue, lookback, state reset và cách xử lý missing/out-of-order frame. Một chunk phải được nhận đủ mới dùng được; không bỏ qua thời gian chờ chunk.
7. Chấm cảnh báo tại thời điểm chúng được phát, không chỉ chấm danh sách được sửa lại sau khi xem hết video. Không dùng end-of-file làm trigger mặc định để hoàn thành lượt cuối.

## 13. Đánh giá kết quả

### 13.1. Độ đúng của đoạn

Với đoạn dự đoán `P` và GT `G`, temporal IoU là `duration(P ∩ G) / duration(P ∪ G)`.

Đánh giá precision/recall/F1 theo instance ở threshold và dung sai công bố trước. Cần one-to-one matching: một GT chỉ được một dự đoán nhận là đúng; dự đoán trùng là false positive. Với AP/mAP, dùng quy trình matching theo confidence của evaluator TAD đã chọn và ghi rõ phiên bản. Nếu dùng Hungarian matching cho diagnostic cố định, phải mô tả riêng, không trộn với cách tính AP.

Với bài toán online, interval metrics cuối video chỉ là một thành phần. Một interval có tIoU cao nhưng chỉ được báo sau thời hạn vẫn không phải một phát hiện kịp thời. Evaluator TAD offline không thay thế được evaluator event/latency.

Một dải tIoU có thể được đề xuất cho benchmark mới, nhưng phải giải thích theo nhu cầu ứng dụng và sai khác annotator. Không tự gọi ngưỡng của một dataset khác là chuẩn cho bài toán này.

Với một task/class duy nhất, báo AP của task đó; nếu nhiều task/class, ghi rõ cách lấy mAP. Trung bình qua các ngưỡng tIoU và trung bình qua các class là hai phép tổng hợp khác nhau, phải nêu rõ.

### 13.2. Độ chính xác ranh giới và completion

- Sai số tuyệt đối và sai số có dấu của start/end, tính bằng giây và có thể chuẩn hóa theo độ dài lượt.
- Tỷ lệ cả hai ranh giới cùng nằm trong dung sai cho phép.
- Precision/recall của sự kiện completion trong cửa sổ thời gian cho phép, phân biệt kết thúc sớm và muộn.
- Timely precision/recall/F1 hoặc AP theo ngân sách trễ `Δ`: chỉ nhận TP kịp thời khi vừa khớp instance/ranh giới vừa được phát trong cửa sổ thời gian hợp lệ sau completion. Quá hạn phải được báo là late/miss theo protocol công bố, không âm thầm nhận là TP kịp thời.
- Báo đường trade-off theo `Δ`, threshold và thời gian chờ xác nhận; không chỉ một con số AP cuối video.
- Báo median và các percentile khi phân bố lỗi lệch, không chỉ mean.

Sai số ranh giới trên các TP phải đi cùng recall/số mẫu được ghép. Model chỉ tìm được ít lượt dễ không được đánh giá là tốt chỉ vì MAE nhỏ.

Phát `completed` trước khi đạt tiêu chí hoàn thành là false completion, trừ vùng bất định GT đã quy định trước; không được hợp thức hóa bằng cách nhìn thấy lượt đó hoàn thành về sau. Nếu có dự báo hoàn thành trong tương lai thì dùng loại event/metric anticipation riêng.

### 13.3. Đếm lượt, gộp/tách và false positives

- Count MAE/sai số số lượt theo video, kèm instance metrics. Đếm đúng có thể che giấu một lượt bỏ sót và một lượt báo thừa.
- Số/tỷ lệ merge: nhiều GT thành một dự đoán; split: một GT thành nhiều dự đoán.
- False completions trên lượt bỏ dở hoặc dấu hiệu cuối giả.
- False positives trên video không có lượt hoàn thành: theo video và theo thời lượng background, ví dụ FP/phút.
- Kiểm tra duplicate predictions do cửa sổ chồng lấp hoặc hậu xử lý.
- Đếm thông báo sai/trùng từng được phát và số lần rút/sửa, không chỉ các instance còn lại trong snapshot cuối. Gửi lại cùng `event_id` do cơ chế vận chuyển khác với model tạo thêm lượt; evaluator phải phân biệt.

### 13.4. Bất định, vùng không quan sát được và coverage

Với GT chỉ biết ranh giới trong khoảng, báo metric tương thích khoảng bất định và metric point-boundary trên phần đủ rõ, tách riêng. Quy tắc ignore phải công bố và khóa trước khi test. Không lặng lẽ bỏ toàn bộ hard case hoặc biến unknown thành negative.

Báo tỷ lệ dữ liệu được đánh giá, bị censor/ignore và phân bố theo nhóm khó. Threshold abstention nếu có phải được chọn trên validation; đo trade-off giữa coverage và lỗi.

### 13.5. Độ trễ và tài nguyên online bắt buộc

Phải tách các mốc trong cùng clock đã đồng bộ:

- `t_goal`: completion GT; nếu bất định thì dùng protocol khoảng tương ứng.
- `t_evidence`: lúc sớm nhất có đủ bằng chứng quan sát theo guideline, nếu có nhãn này.
- `t_observed`: timeline input cuối thực sự được dùng trong quyết định.
- `t_emit`: thời điểm phát thông báo thực tế.
- `t_clip_ready`: lúc clip hoàn chỉnh sẵn sàng sử dụng.

Đo `t_emit - t_goal` và `t_clip_ready - t_goal` riêng. Khi có nhãn evidence, có thể phân tích phần trễ do quan sát và phần trễ sau khi đã đủ bằng chứng. Timestamp `end` dự đoán không được thay thế `t_emit`. Tất cả thời gian chờ chunk, mạng, queue, decode, trích feature, inference và commit phải được tính nếu nằm trên đường phát thông báo.

Báo mean/median và p95/p99 khi đủ mẫu, kèm timely recall, false completions và số mẫu; metric latency chỉ trên TP không đủ đại diện. Đo throughput so với tốc độ nguồn, backlog theo thời gian, tỷ lệ drop frame, peak RAM/VRAM, kích thước state/cache và dung lượng video đang giữ. Tốc độ trung bình nhanh hơn nguồn không bảo đảm không có đợt trễ dài.

Đánh giá riêng cold start giữa lượt, nhiều lượt liên tục, pause dài, mất kết nối và khôi phục state. Model online cần có thể tiếp tục nhận stream khi job xuất clip/lưu Drive đang chạy. Bộ nhớ model phải có chính sách kiểm soát; không mặc định lịch sử model tăng vô hạn theo thời lượng stream.

Đối chứng offline có thể báo thời gian/video và RTF trong protocol riêng. Kết quả dùng toàn video không được đưa vào bảng chính như một hệ thống online cùng điều kiện.

### 13.6. Tổng hợp và độ tin cậy

Báo cả tổng thể và theo task, nhóm khó, người, view/môi trường khi đủ mẫu. Nêu rõ macro/micro weighting để video dài không vô tình chi phối tất cả. Với dữ liệu đa góc/cùng trial, tính độ bất định bằng grouping ở recording/người thay vì coi mọi frame/view là mẫu độc lập. Báo seed, độ biến thiên khi phù hợp và số mẫu thực tế của từng nhóm.

## 14. Tiêu chí chấp nhận

### 14.1. Có thể kiểm tra ngay ở mức logic

| ID | Điều kiện |
| --- | --- |
| A01 | Video không có lượt hoàn thành có thể trả về danh sách rỗng. |
| A02 | N lượt đúng cấp công việc được biểu diễn thành N instance riêng, kể cả cùng loại nối tiếp. |
| A03 | Khoảng nghỉ/hoạt động xen vào trong cùng lượt không tự tạo ranh giới mới. |
| A04 | Bắt đầu và hoàn thành được xử lý riêng; không lấy toàn bộ khoảng giữa hai completion làm một lượt nếu có thời gian ngoài lượt. |
| A05 | Động tác giống kết thúc nhưng chưa đủ tiêu chí không tự được nhận là completed. |
| A06 | Lượt thiếu đầu/cuối hoặc không đủ quan sát không có nhãn ranh giới chính xác giả tạo. |
| A07 | Timestamp hợp lệ, nhất quán với video gốc và không trùng dự đoán cùng lượt. |
| A08 | Clip xuất ra bao gồm bằng chứng hoàn thành theo quy ước, không bị lỗi quy đổi frame/time. |
| A09 | Model không được yêu cầu số lượt hoặc GT của video test. |
| A10 | Có thể giải thích sự khác nhau giữa metric đoạn, mốc completion, số lượt và chất lượng công việc. |
| A11 | Mọi quyết định chỉ phụ thuộc prefix đã nhận; thay suffix không đổi các sự kiện đã phát trước đó. |
| A12 | Kết quả từng lượt được phát khi stream đang chạy, có timestamp phát thực và được chấm theo ngân sách latency. |
| A13 | Có cơ chế giữ phần đầu và toàn bộ lượt đang mở để xuất clip, kể cả khi start được nhận biết muộn. |
| A14 | State không mất chỉ vì đổi chunk; queue, frame drop và tài nguyên được đo theo thời lượng stream. |
| A15 | Thông báo sai/trùng/revision đã từng phát được giữ trong event log và tham gia đánh giá. |
| A16 | Mất kết nối hoặc end-of-file không tự được xem là completed; có xử lý censoring/reset được ghi nhận. |

Đây là yêu cầu về đặc tả và hành vi cần thử, không phải tuyên bố model tương lai sẽ đúng 100% mọi mẫu.

### 14.2. Các chỉ tiêu định lượng chưa được chốt

Dung sai start/end, ngân sách latency phát hiện/xuất clip, recall đúng hạn tối thiểu, số FP/phút tối đa, tỷ lệ merge/split chấp nhận, tốc độ nguồn và phần cứng, giới hạn state/buffer/RAM/VRAM và coverage cần được quyết định trước benchmark chính dựa trên pilot và nhu cầu ứng dụng. Online đã là bắt buộc; chưa chốt budget không có nghĩa được đợi đến hết stream. Không tự đặt ngưỡng tùy ý rồi coi đó là yêu cầu người dùng hoặc bảo đảm của hệ thống.

## 15. Yêu cầu triển khai phục vụ nghiên cứu

- Lưu dữ liệu nguồn, annotation và cache bền trên Drive theo quy ước dự án. Colab runtime có thể mất; pipeline cần checkpoint và tái chạy được.
- Tách tải/giải nén, chuyển nhãn, kiểm tra nhãn, trích feature, huấn luyện, suy luận, đánh giá và cắt clip. Trạng thái hoàn thành của một bước không đại diện cho các bước sau.
- Cấu hình có version: task definition, split, mapping timestamp, dữ liệu/nhãn nguồn, feature backbone, sampling, threshold và checkpoint model.
- Không tải lại/giải nén lại dữ liệu đã có nếu còn hợp lệ; không sửa nguồn trong shortcut Drive công khai chỉ đọc.
- Cache/feature phải gắn với video và phiên bản nhãn/config tương ứng. Không sử dụng cache cũ khi FPS, crop hoặc timeline đã đổi mà không có mapping.
- Feature dùng cho online phải ghi mốc frame/chunk cuối cần để tính nó, kiểm tra không dùng tương lai. Feature tải sẵn từ dataset chưa qua audit không được mặc định hợp lệ cho online.
- Giữ nguyên đầu vào RGB toàn cảnh khi tạo baseline; nếu thêm ROI/pose/object detector phải ghi chi phí và lỗi phụ thuộc của chúng.
- Khi chạy nhiều lượt/cửa sổ, tránh duplicate đầu ra; lưu kết quả đủ để truy nguyên về video gốc và tái lập evaluation.
- Không mặc định GPU giúp giải quyết nút thắt đọc/ghi hoặc decode; đo từng giai đoạn trước khi tối ưu.
- Quản lý dung lượng cho video, frame, feature và checkpoint. Việc chỉ trích video hoặc chỉ một góc phải giữ đúng dữ liệu nhãn tương ứng.
- Tách luồng nhận/decode, suy luận và lưu/xuất clip bằng chính sách queue rõ ràng; đo drop/backpressure thay vì âm thầm bỏ frame làm thay đổi ranh giới.
- Lưu trạng thái lượt, session/timestamp origin và event ID để khôi phục/idempotency; có chính sách khi thiếu video lịch sử hoặc không thể nối continuity sau reconnect.
- Colab/Drive là môi trường chuẩn bị dữ liệu và mô phỏng nghiên cứu. Yêu cầu dịch vụ camera chạy liên tục, loại thiết bị edge/server và SLA triển khai chưa được chốt; tiến trình nền Colab không tự đáp ứng uptime của hệ thống online.

## 16. Các câu hỏi còn mở phải trả lời qua pilot

| ID | Câu hỏi | Hệ quả nếu chưa rõ |
| --- | --- | --- |
| Q01 | Công việc thực tế và đơn vị đầu ra chính xác là gì? | Không thể chốt GT cấp lượt hoặc so sánh dataset một cách công bằng. |
| Q02 | “Làm xong” là kết thúc thao tác, bàn giao hay đạt trạng thái sản phẩm nào? | Khác endpoint và hard negatives. |
| Q03 | Bắt đầu có tính lấy vật/dụng cụ và chuẩn bị không? | Sai khác annotation có hệ thống. |
| Q04 | Task cố định hay đổi bằng text/exemplar? Có task chưa học không? | Khác bài toán closed-set/open-set và đầu vào cần thiết. |
| Q05 | Độ trễ phát hiện/xuất clip tối đa là bao nhiêu; có cần thông báo start ngay và cho phép sửa/rút cảnh báo không? | Online đã chốt; các budget và chính sách commit này quyết định model, buffer và metric. |
| Q06 | Có lượt đan xen nhiều sản phẩm hoặc nhiều người chính không? | Có thể cần association và khoảng chồng lấp, không chỉ phân hoạch timeline. |
| Q07 | Xử lý/cắt clip cho aborted/unknown như thế nào? | Khác API và cách tính FP/ignore. |
| Q08 | Dấu hiệu hoàn thành có quan sát đủ từ RGB không? | Có thể cần bổ sung cảm biến hoặc điều chỉnh tiêu chí quan sát được. |
| Q09 | Dung sai cắt video và chi phí bỏ sót/báo thừa là bao nhiêu? | Khác threshold, metric chính và mục tiêu tối ưu. |
| Q10 | Nguồn camera/replay, góc nhìn, FPS, độ dài lượt/stream, mất frame và phần cứng thực tế ra sao? | Khác yêu cầu context, sampling, queue, lưu video và tài nguyên online. |
| Q11 | Bao nhiêu lượt công việc đúng cấp nhãn có thể lấy từ mỗi dataset? | Khác giá trị dữ liệu thực, không chỉ số GB/video. |
| Q12 | Mức biến thiên annotator và tỷ lệ trường hợp không thể xác định là bao nhiêu? | Giới hạn độ chính xác có thể đo một cách có ý nghĩa. |

Trong khi chờ quyết định, nghiên cứu có thể tiếp tục với một task pilot cụ thể, nhưng mọi giả định phải được ghi lại và không mở rộng kết luận vượt phạm vi pilot.

## 17. Khung đọc paper và chọn hướng tiếp theo

Mỗi paper cần được ghi nhận theo cùng một mẫu:

1. Bài toán và đơn vị nhãn: động tác, bước, lượt công việc hay mốc completion?
2. Input thật lúc test; có cần text, exemplar, transcript, số lượt, order, pose, nhiều góc hoặc nhãn phụ không?
3. Output: class/frame, interval, timestamp, count, progress hay trạng thái sản phẩm?
4. Có xử lý nhiều instance, instance sát nhau, pause, thao tác ngoài mục tiêu, sửa lỗi và incomplete attempts không?
5. Có giả định nhịp lặp, thứ tự bước cố định, video trim, một instance/video hoặc bắt đầu từ đầu quy trình không?
6. Có thực sự causal từ encoder/feature đến hậu xử lý không; decision dùng frame cuối ở đâu và phát lúc nào? Có event log, latency, bounded memory/queue hay chỉ gắn nhãn online cho việc chạy theo cửa sổ?
7. Nhãn nào dùng train/validation/test, có đúng cấp công việc của dự án không và chi phí annotation ra sao?
8. Protocol chia tập có giữ recording/participant/view đồng bộ không?
9. Metric có đo endpoint, false completion và latency/timely recall hay chỉ classification/count/IoU trên kết quả cuối?
10. Cơ chế nào có thể chuyển sang dự án, phần nào phải thay và rủi ro khi thay là gì?
11. Code/checkpoint/data có tái lập được không; tài nguyên và chi phí feature là bao nhiêu?
12. Hạn chế nào tác giả đã chứng minh và hạn chế nào là suy luận của người đọc?

Thứ tự đọc đề xuất: **On-TAL và OAD/memory causal** để chốt giao thức streaming; completion/goal-state và procedure understanding để hiểu tiêu chí “xong”; TAS causal để hiểu các bước/context; repetition để hiểu chu kỳ và ngắt quãng. TAL/TAS offline dùng để tham khảo thành phần hoặc đối chứng riêng. Không chọn model chỉ theo leaderboard thiếu ràng buộc online hoặc có đơn vị nhãn khác.

## 18. Kế hoạch nghiên cứu tối thiểu và rủi ro quyết định

1. **Chốt một task pilot:** viết mục tiêu, quy tắc bắt đầu/kết thúc và ví dụ phản chứng.
2. **Audit nhãn/video thật:** ưu tiên IKEA/IndustReal cho thao tác và completion; ghi rõ các gói dữ liệu đã thực sự kiểm tra.
3. **Gán nhãn pilot cấp lượt:** có multi-instance, gián đoạn, negative và censoring; đo đồng thuận.
4. **Khóa evaluation online:** xác định replay, prefix audit, event log, matching, split, dung sai và latency budget dựa trên nhu cầu cùng sai khác annotator.
5. **Tái lập baseline causal đơn giản:** so với luật/chu kỳ và một hướng On-TAL/OAD hoặc completion online phù hợp, có buffer xuất clip. Không cần triển khai mọi hướng ngay.
6. **Phân tích lỗi:** xác định lỗi nằm ở start, completion, identity, grouping, quan sát hay nhãn.
7. **Chọn giả thuyết cải tiến:** ví dụ trạng thái vật thể + lịch sử thao tác giúp giảm false completion; hoặc tín hiệu boundary/instance giúp tránh gộp lượt sát nhau.
8. **Kiểm tra chuyển miền và stream liên tục thật:** đánh giá causal correctness, độ đúng–latency, tài nguyên và clip xuất ra; kiểm tra cải tiến không chỉ học người, bối cảnh hoặc dấu cắt cảnh.

Các ý tưởng ở bước 7 là giả thuyết cần kiểm nghiệm, chưa phải đóng góp mới đã được xác nhận. Không tuyên bố novelty trước khi rà soát literature trực tiếp liên quan. Tài liệu này đủ để định hướng bước đọc paper; hiệu năng và tính khả thi vẫn phụ thuộc định nghĩa task cùng bằng chứng dữ liệu.

## 19. Nguồn khái niệm

Các yêu cầu U01–U09 đến từ trao đổi trong dự án; U09 chốt online là bắt buộc và thay giả định offline của bản ban đầu. Quy tắc benchmark, schema, tiêu chí chấp nhận và kế hoạch là đặc tả đề xuất, không được trình bày như kết quả của các paper sau.

- [Action Completion: A Temporal Model for Moment Detection — BMVC 2018](https://dimadamen.github.io/ActionCompletion/): tham chiếu khái niệm hoàn thành mục tiêu và định vị mốc completion.
- [IndustReal — WACV 2024](https://arxiv.org/abs/2310.17323): tham chiếu procedure step recognition, trạng thái lắp ráp và lỗi.
- [CAG-QIL — ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Kang_CAG-QIL_Context-Aware_Actionness_Grouping_via_Q_Imitation_Learning_for_Online_ICCV_2021_paper.html): tham chiếu định vị instance hành động trên stream (On-TAL).
- [Long Short-Term Transformer — NeurIPS 2021](https://arxiv.org/abs/2107.03377): tham chiếu bộ nhớ lịch sử cho phân loại hành động online (OAD); không tự là bài toán hoàn thành toàn bộ lượt công việc.
- [Online Temporal Action Localization with Memory-Augmented Transformer — ECCV 2024](https://arxiv.org/abs/2408.02957): tham chiếu cơ chế ngữ cảnh/bộ nhớ cho định vị instance online.
- [ActionFormer — ECCV 2022](https://arxiv.org/abs/2202.07925): tham chiếu TAL và dự đoán đoạn hành động.
- [MS-TCN — CVPR 2019, repo tác giả](https://github.com/yabufarha/ms-tcn): tham chiếu hướng temporal action segmentation.
- [TransRAC/RepCount — CVPR 2022](https://arxiv.org/abs/2204.01018): tham chiếu chu kỳ hành động lặp và annotation chu kỳ.
- [The IKEA ASM Dataset — WACV 2021](https://arxiv.org/abs/2007.00394): tham chiếu video lắp ráp và nhãn atomic actions.
- [Assembly101 — CVPR 2022](https://assembly-101.github.io/): tham chiếu quy trình lắp/tháo với biến thể và nhiều góc.
- [FineAction — IEEE TIP 2022](https://arxiv.org/abs/2105.11107): tham chiếu fine-grained temporal action localization.
- [HA4M — Scientific Data 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9718853/): tham chiếu dữ liệu thao tác lắp ráp đa phương thức.
