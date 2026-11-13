# Ghi chú đọc paper

Ghi lại ý chính khi đọc, dùng cùng cấu trúc để đối chiếu các bài sau. **Cơ chế/kết quả** là của paper; **nhận xét/ý tưởng áp dụng** là phân tích cho dự án, chưa được kiểm chứng thực nghiệm.

## Bảng tra nhanh

| Paper | Vấn đề cốt lõi | Ý tưởng cần nhớ | Online / phần còn thiếu | Từ khóa đối chiếu |
| --- | --- | --- | --- | --- |
| [P14 — Action Completion](#p14-action-completion) | Nhận ra động tác chưa đủ để biết mục tiêu đã đạt. | **Completion moment + frame-level voting**; tốt nhất là **pre → classification, post → regression (C–R)**. | Tổng vote cả chuỗi, gồm frame sau completion; chỉ tìm completion đầu tiên, chưa xuất nhiều interval start/end. | `goal achievement`, `pre/post state`, `temporal voting`, `classification + regression`, `evidence accumulation` |

<a id="p14-action-completion"></a>
## P14 — Action Completion: A Temporal Model for Moment Detection

**BMVC 2018** · [PDF trong repo](../papers/P14_2018_action_completion.pdf) · [Trang tác giả](https://dimadamen.github.io/ActionCompletion/).

**Một câu để nhớ:** mỗi frame góp bằng chứng về mốc đạt mục tiêu; trước mốc thì xác định nó còn ở phía sau, sau mốc thì định vị ngược lại chính xác hơn.

### 1. Vấn đề → motivation

Hành động thường nhằm đạt một mục tiêu, nhưng **thực hiện động tác không bảo đảm đạt mục tiêu**. Ví dụ: người đã làm động tác bắt bóng nhưng bắt trượt. Action recognition vẫn có thể nhận đúng lớp “bắt bóng”; action localization có thể tìm đúng đoạn động tác, nhưng cả hai chưa xác nhận đã bắt được bóng.

Vì vậy, paper tìm **completion moment**: frame đầu tiên mà người quan sát đủ tin tưởng rằng mục tiêu đã đạt, chia chuỗi thành **pre-completion** và **post-completion**. Mốc này không nhất thiết trùng lúc động tác kết thúc. Nếu chưa đạt mục tiêu thì chuỗi là **incomplete**. Tiêu chí hoàn thành cần được định nghĩa và gán nhãn nhất quán cho từng hành động. [§1, §3; PDF tr. 1–4]

### 2. Cơ chế: frame-level voting

```text
Frame x_t → CNN → LSTM(h_t, lịch sử)
                    ├─ Classification: hiện tại là pre hay post?
                    └─ Regression: mốc completion cách t bao xa?
          → tạo vote từ từng frame → cộng vote → chọn mốc có tổng cao nhất
```

Hai head được huấn luyện bằng loss classification + regression. Paper mô tả kiến trúc có thể train end-to-end; thí nghiệm thực tế train CNN rồi đưa feature fc7 vào LSTM. [§4.1, §5; tr. 4–7]

| Loại vote | Frame dự đoán gì? | Vote được đặt ở đâu? |
| --- | --- | --- |
| **Classification (C)** | Frame t là **pre** hoặc **post** completion. | Nếu **pre**: chia đều vote cho các mốc sau t, gồm ô incomplete. Nếu **post**: chia đều vote cho các mốc từ đầu tới t. Cho biết **phía nào**, chưa chỉ rõ một mốc. |
| **Regression (R)** | Vị trí thời gian tương đối của completion so với t. | Tạo vote dạng Gaussian quanh mốc dự đoán. Cho biết **ở đâu**, tập trung hơn classification. |

Với mốc thật `τ`, regression học `r_t = (t − τ) / τ`; từ đầu ra `R_t` suy ra mốc `τ̂_t = t / (1 + R_t)`. Classification chuẩn hóa tổng vote của mỗi frame bằng 1: mỗi ô nhận `1/t` khi post, hoặc `1/(T−t+1)` khi pre. Ô `T+1` đại diện **incomplete**, không phải một completion thật sau video. [§4.1, Eq. 3–6; tr. 5–6]

**Tổng hợp:** cộng các vote rồi lấy `argmax`. Paper thử C–C, R–R, R–C và **C–R**; thứ tự hai chữ là cách vote của frame **được dự đoán pre / được dự đoán post**, không dùng nhãn thật để chọn nhánh khi test. [§4.2; tr. 6]

**Vì sao C–R tốt nhất?** Trước khi hoàn thành, khó đoán chính xác còn bao lâu, nhưng dễ biết “chưa xong” → dùng C. Sau khi hoàn thành, đã có bằng chứng về sự kiện nên định vị ngược lại đáng tin hơn → dùng R. [Phân tích của tác giả, §5; tr. 8]

**Ví dụ:** bóng được giữ chắc tại frame 10. Frame 6 dự đoán pre và vote cho vùng sau 6; frame 12 dự đoán post và regression cho mốc quanh 10. Cộng bằng chứng giúp xác định mốc 10. Nếu đến frame 12 mới đủ bằng chứng, hệ thống chỉ có thể **thông báo ở frame 12 hoặc muộn hơn**, dù mốc được định vị là 10.

### 3. Kết quả cần nhớ

Table 1: C–R đạt **88,1% accuracy**, so với **85,0%** của baseline Pre-V không voting; sai số thời gian tương đối RD giảm **0,17 → 0,12**. Accuracy ở đây đo tỷ lệ frame được chia đúng pre/post theo mốc dự đoán. Paper báo **89% chuỗi có sai số định vị ≤ 1 giây**; đây là sai số mốc, **không phải độ trễ phát hiện online ≤ 1 giây**. [§5, Table 1, Fig. 5; tr. 8–10]

### 4. Nhận xét cho bài toán online của mình

| Thành phần | Giữ được gì? | Chưa phù hợp ở đâu? |
| --- | --- | --- |
| **Ngữ nghĩa completion** | Phân biệt attempted / achieved; cần cả ví dụ thất bại. | Đơn vị của mình là **toàn bộ một lượt công việc**, không mặc định bằng một action của paper. |
| **CNN → forward LSTM** | Tại t, dùng frame hiện tại và lịch sử; có thể là thành phần streaming. | Tính causal của LSTM chưa bảo đảm toàn bộ cơ chế ra quyết định là online. |
| **Sequence-level voting** | Tích lũy bằng chứng giúp giảm nhiễu của từng frame. | Bản gốc cộng vote toàn chuỗi, gồm frame sau completion; phân bố C còn dùng độ dài cuối T. Chưa có quy tắc chốt event chỉ từ prefix với latency rõ ràng. |
| **Đầu ra / giả định** | Một completion moment hoặc incomplete. | Chuỗi đã được cắt theo action attempt, chỉ tìm **completion đầu tiên** nếu có; chưa tìm start và nhiều lượt trong stream liên tục. |

**Kết luận sử dụng:** tham khảo **định nghĩa completion và cách tích lũy bằng chứng**; chưa dùng nguyên phương pháp làm baseline online cho dự án. [Nhận xét của dự án dựa trên §3–4]

### 5. Đánh dấu để đối chiếu với các paper sau

- **Ý tưởng tái sử dụng:** tách “đã đạt mục tiêu chưa?” khỏi “mốc đạt mục tiêu ở đâu?”; kết hợp state classification với temporal localization.
- **Hướng thích nghi cần thử:** chỉ tích lũy vote từ prefix đã thấy, bỏ phụ thuộc độ dài cuối T; thêm start/instance tracking và chính sách xác nhận completion. Lưu riêng mốc dự đoán và thời điểm phát; không biến dự báo trước khi đạt mục tiêu thành xác nhận đã hoàn thành.
- **Khoảng trống paper tự nêu (§4.2):** chưa mô hình hóa độ tin cậy khác nhau giữa các frame khi tổng hợp vote; uncertainty/temporal attention là hướng mở. Có thể đối chiếu các bài sau có confidence weighting hoặc evidence selection.
- **Câu hỏi khi gặp phương pháp tương tự:** nó tích lũy bằng chứng nào, có nhìn frame sau mốc không, khi nào được chốt, có giữ đúng identity qua pause/repair và phát được nhiều lượt không?
