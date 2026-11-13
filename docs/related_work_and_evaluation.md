# Nghiên cứu ảnh hưởng gián tiếp: PROVIA, metric và protocol

Ngày cập nhật: **2026-11-13**, bản tạm v0.1. Tiếp nối [bảng 23 paper](literature_review.md). Số liệu dưới đây là tác giả báo cáo; chưa tái lập code hoặc kiểm chứng thống kê. Phần áp dụng cho dự án là đề xuất, chưa sửa evaluator hay đặc tả đã chốt.

## 1. Mở tiêu chí chọn paper

Một paper không cần trả đúng interval công việc vẫn đáng đọc nếu nó thay đổi một trong các quyết định sau:

| Trục ảnh hưởng | Câu hỏi cần lấy được | Paper đã bổ sung |
| --- | --- | --- |
| Đặt bài toán / protocol | Model cần nhìn video hay có thể thắng bằng vị trí/thời lượng? | P19 PROVIA |
| Mô hình hóa | Đã làm gì khác với tiến trình nào được chấp nhận như thế nào? | P19; đối chiếu P13/P15/P16 |
| Metric / chẩn đoán | Một điểm số đang che loại lỗi gì? | P20 WARI/SMS, P22 affiliation, P23 range P/R |
| Biểu diễn / chuyển góc | Tín hiệu nào nên bất biến view, tín hiệu nào cần giữ? | P21 unseen-view TAS |
| Điều kiện hệ thống | Features, latency, annotation, buffer và quan sát có hợp lệ không? | Đối chiếu các bài trong khảo sát chính |

Phải tách **trùng objective**, **chuyển giao kỹ thuật** và **ảnh hưởng tới cách đánh giá**. Dùng “không giải quyết trọn bài toán” để mô tả phạm vi, không dùng nó để bỏ qua một paper quan trọng.

## 2. PROVIA nói về segmentation và metric theo nghĩa nào?

### 2.1. Nội dung cần phân biệt

[PROVIA, arXiv v1](../papers/P19_2026_provia.pdf) có **online step segmentation** bằng marked point process (§IV-B, tr. PDF 3), không phải mask vật thể. Đóng góp đánh giá chính là **protocol whole-trial, false-alarm budget và no-perception controls**, không nên rút thành “một F1 segmentation mới”. Xem vấn đề/motivation/giải pháp trong hàng P19 của [bảng tổng hợp](literature_review.md).

Tác giả chỉ ra fixed-time predictor đạt F1 1.000 ở protocol first-mistake được họ kiểm tra (§III); kết quả đó không có nghĩa mọi benchmark online đều có lỗi tương tự. Cần kiểm tra evaluator của từng setting.

**Hệ quả cho dự án:** nếu video luôn được cắt đúng một lần hoàn thành, model đoán “cuối file là xong” có thể được thưởng mà không hiểu goal. Vì thế giữ whole-session, lượt không hoàn thành, negative và cấm EOF làm tín hiệu completion là phần của thiết kế đánh giá, không phải chi tiết phụ.

### 2.2. Không đọc riêng con số tốt nhất

Ví dụ tại **budget trên validation 0,1 báo giả/phút**, Bảng IV tr. PDF 8:

| Dataset | PROVIA recall | Đối chứng | Cách diễn giải |
| --- | --- | --- | --- |
| CaptainCook4D | 0,154 | MistSense-RGB-style: 0,128 | Gain ở operating point này; không suy ra thắng mọi budget. |
| HoloAssist | 0,034 | Causal-TCN: 0,015 | Recall tuyệt đối còn thấp. |
| IndustReal | 0,098 | Causal-TCN: 0,255; time-only: 0,294 | AP/ranking tốt chưa chứng minh lợi ích vận hành. |

Budget validation **không bảo đảm** test đạt cùng rate; phải báo rate test thực tế. Đối chứng trong bài dùng chung segmentation/features và có điều chỉnh, không phải so nguyên xi mọi hệ thống gốc.

### 2.3. Phần protocol không nên chép nguyên

Paper gán alarm theo completion cells; quy tắc chính cho phép một alarm credit hai mistake kế tiếp, và bài có kiểm tra bổ sung one-to-one (§III, §V-F). **Đối với dự án**, một clip dự đoán không được tự tính là phát hiện hai lượt hoàn thành: phải giữ matching one-to-one theo task-instance.

Chỉ tiêu “later mistakes” có điều kiện decoded và chỉ tiêu AP trên step cũng khác recall của mọi task-instance; step metrics của paper còn loại step ngắn hơn 0,5 giây (§III). Đề xuất của dự án là báo cả end-to-end recall trên toàn GT và kết quả có điều kiện nhìn thấy/decoded, cùng số mẫu; không thay mẫu số để che lỗi segmentation.

Mẫu số báo giả của paper theo phút **correct operation**. Trong bài toán completed-event, “ngoài sự kiện completion” không tương đương “ngoài mọi interval công việc”. Đề xuất báo riêng:

- False completion trên mỗi phút giám sát hợp lệ, kể cả báo sai khi người vẫn đang làm.
- FP/phút background trên vùng background đã annotate, với mẫu số công khai.
- Duplicate/revision trên lượt đã phát, không bỏ chúng khi tổng hợp.

### 2.4. Kỹ thuật ảnh hưởng tới hướng mô hình

P19 tách factual state khỏi accepted progress và dùng filtering; “exact” là trong mô hình trạng thái/automaton đã chọn, không bảo đảm biết đúng trạng thái thực của thế giới. **Nhận định:** cần thử xem thông tin nào còn quan sát được ở exo và cần nhãn gì để huấn luyện.

Không nên đổi tên các status thành active/paused/completed rồi coi đó là đóng góp mới. Bài toán đích cần kiểm tra thêm: start của toàn lượt, ownership qua gián đoạn, hai sản phẩm giống nhau nối tiếp, goal chưa quan sát đủ và tránh đóng lượt khi chỉ một bước con đã xong. Segmentation chia kín theo các bước cũng chưa tự tạo khoảng background giữa các lượt.

### 2.5. Kỹ thuật đáng khảo sát: completion hazard

Theo §IV-B, với intensity causal `λ_t` và khoảng frame `Δt`, hazard được viết:

$$
h_t=1-\exp(-\lambda_t\Delta t),\qquad
S(t)=\prod_{\nu=b}^{t}(1-h_\nu).
$$

PROVIA decode sự kiện theo median: lần đầu survival `S(t)` xuống 1/2 kể từ event trước. Đây là quy tắc quantile cụ thể, không có nghĩa không tồn tại tham số/quy ước quyết định, cũng không chứng minh median tối ưu với mọi chi phí trễ.

**Nhận định áp dụng:** có thể so completion hazard ở cấp goal với start/end head trực tiếp. Dự án cần học sự kiện đúng cấp lượt và có trạng thái ngoài lượt; nếu cứ reset hazard tại mọi action con thì vẫn giải sai bài toán. Kiểm tra calibration theo thời lượng, sensitivity khi pause dài và lợi ích của hình ảnh so với hazard chỉ học duration. Thử nhiều quantile trên validation nếu chi phí báo sớm/trễ bất đối xứng; ghi rõ đó là biến thể của dự án, không phải kết quả nguyên bản của PROVIA.

## 3. Các metric lân cận bổ sung được gì?

### 3.1. P20: WARI và SMS cho time-series segmentation

[P20 — NeurIPS 2025](../papers/P20_2025_interpretable_segmentation_metrics.pdf) đề xuất WARI nhạy khoảng cách tới boundary và SMS phân biệt **delay, isolation, transition, missing** (§2.2–3). Đây là metric trạng thái thời gian, không phải metric event emission. Bảng P20 trong khảo sát chính nêu kết quả kiểm tra metric, không trình bày như gain của một detector.

**Nhận định áp dụng:**

- Một segmentation trễ gần boundary có thể được xem nhẹ trong state detection, nhưng cùng độ trễ có thể làm báo completion quá hạn. Giữ metric latency riêng.
- SMS có bước Hungarian map nhãn. Nếu active/completed có nghĩa cố định, map lại theo GT test có thể che nhầm semantics; chỉ dùng mapping đúng protocol và ghi rõ mọi biến thể.
- WARI phụ thuộc khoảng cách thời gian và tham số. Khi đổi FPS, phải kiểm tra đơn vị/chuẩn hóa, không lấy cùng alpha rồi giả định cùng mức phạt.
- Một state có thể lặp qua nhiều lượt. Đánh giá state labels vẫn cần interval/instance IDs để không mất ranh giới giữa hai lượt cùng task.

### 3.2. P22/P23: range metrics và khả năng bị khai thác

[P23](../papers/P23_2018_range_precision_recall.pdf) mở P/R sang interval với overlap/cardinality/positional bias. [P22](../papers/P22_2022_affiliation_metrics.pdf) kiểm tra metric gaming và đề xuất affiliation dựa trên khoảng cách cục bộ, so với dự đoán ngẫu nhiên. Chúng cung cấp lý do để kiểm tra **metric trên phản ví dụ**, không chỉ chạy metric trên model tốt.

**Nhận định áp dụng:** dùng range score làm phân tích chất lượng đoạn, không thay t_emit. Không áp metric cho interval anomaly trực tiếp lên điểm completion có độ dài zero mà thiếu quy ước. Không tune độ rộng dung sai hoặc trọng số sau khi đã xem test/model ranking.

### 3.3. P21: representation ảnh hưởng cả mục tiêu đo

[P21 — bản arXiv 2025](../papers/P21_2025_unseen_view_tas.pdf) nghiên cứu generalization sang góc chưa thấy; cần nhiều view train và không đồng nghĩa “model dùng mọi camera lúc test”. Đây là hướng cần đưa vào nghiên cứu exocentric dù objective là TAS.

**Nhận định áp dụng:** sequence/action invariance có thể thử ở training của causal model. Giữ một nhánh quan sát trạng thái/ROI nếu vị trí vật thể có ý nghĩa với completion. Đánh giá riêng đổi người/session và đổi camera, tránh giải thích gain do có nhiều dữ liệu train như gain thuần do view invariance. Khi ghép data nhiều góc phải giữ các bản quay cùng trial trong một split theo protocol dự án.

## 4. Bộ đánh giá đề xuất cho dự án

Đây là bảng thiết kế **tạm**, chưa phải evaluator mới đã triển khai hoặc metric mới được chứng minh.

| Trục | Chỉ số/kiểm tra đề xuất | Nó bắt được gì? | Giới hạn phải ghi |
| --- | --- | --- | --- |
| Đoạn và identity | AP/tIoU, start/end MAE, one-to-one matching, count/merge/split | Clip có đúng lượt và bao trọn công việc không? | Không tự đo lúc người dùng nhận được kết quả. |
| Quyết định online | Timely precision/recall theo deadline, early false completion, p50/p95 delay | Phát đúng và đủ nhanh không? | Không chỉ tính latency trên số ít TP dễ; báo recall/coverage. |
| Ngân sách vận hành | Recall ở threshold chọn trên validation theo FP/phút; rate test thực | Đổi chất lượng lấy bao nhiêu báo sai? | Validation budget khác guarantee trên test. |
| Lỗi segmentation phụ | Frame metrics, edit/F1, error taxonomy; cân nhắc WARI/SMS | Bỏ bước, tách/gộp hoặc trễ boundary ra sao? | Nhãn bước khác nhãn toàn lượt; state mapping/duration weights cần rõ. |
| Phụ thuộc hình ảnh | No-perception controls, shuffled/replaced frames, timestamp-only | Model đang hiểu video hay nhớ vị trí? | Controls vẫn cần dùng cùng quyền thông tin và train/validation budget. |
| Quan sát / thiếu nhãn | Recall toàn GT và nhóm rõ/mơ hồ; tỷ lệ ignore/unknown | Score cao vì bỏ hard case hay vì giải được? | Giữ riêng unknown, chưa annotate và negative. |
| Chuyển miền | Seen/unseen exo camera, ego pilot báo riêng | Độ bền góc nhìn và miền dữ liệu | Không gộp tất cả thành một điểm che domain shift. |
| Hệ thống | Raw-input latency, FPS/backlog, buffer và clip-ready time | Có thực sự chạy và xuất clip theo stream không? | Kể cả chi phí decode, feature và I/O nằm trên đường phát. |

Không dùng thuật toán Hungarian của evaluator để đưa GT vào model. Evaluator có thể nhìn toàn nhãn để ghép/chấm; model chỉ có prefix. Timestamp t_emit đã phát phải bất biến, kể cả khi sửa start/end sau đó.

## 5. Phản ví dụ cần dùng để kiểm tra evaluator

Các ví dụ sau là **thiết kế kiểm tra của dự án**, chưa phải kết quả thực nghiệm mới.

| Dự đoán giả lập | Sai ở đâu? | Evaluator phải phản ánh |
| --- | --- | --- |
| Cùng interval [10,40] nhưng một model phát lúc 41, model khác lúc 90 | AP/IoU có thể giống nhau, trải nghiệm online khác hẳn | Cùng chất lượng interval, khác timely recall/delay. |
| Hai lượt cùng task nối tiếp, model gộp thành một đoạn | Frame class có thể vẫn đúng | Instance recall/count/merge phải phạt, không chỉ state accuracy. |
| Phát completed đều theo thời lượng trung bình học từ train | Không cần nhận biết goal trong video | Không được thắng chỉ vì video đã trim mỗi file một lượt. |
| Phát event khi EOF hoặc dựa trên tỷ lệ thời lượng toàn file | Dùng thông tin không có ở stream đang mở | Causal audit thất bại; không nhận đây là baseline online hợp lệ. |
| Spam completed liên tục hoặc phát lại cùng lượt nhiều lần | Có thể chạm mọi cửa sổ dung sai | FP/duplicate tăng; một event không credit nhiều lượt. |
| Phát một interval dài phủ cả ca làm việc | Overlap một phần với nhiều GT | Matching/merge/boundary error không được cho thành nhiều TP tốt. |
| Pause dài rồi tiếp tục cùng lượt | Chia action hợp lý nhưng chia task sai | Giữ một task-instance; phạt split nếu đã đóng lượt ở pause. |
| Đổi toàn nhãn active và completed nhưng giữ partition | Clustering partition vẫn có thể đẹp | Metric semantics và completion event phải phát hiện; không remap che sai lớp. |
| Chỉ báo khi dễ, bỏ toàn bộ bị che khuất/sửa lỗi | Latency/MAE trên TP có thể rất đẹp | Recall toàn GT, coverage và phân bố hard case phải lộ thiếu sót. |

No-perception controls hợp lệ nên gồm elapsed-time, index/số quyết định và prior thời lượng/task học từ train. Cố định chúng trên validation; không cho biết số lượt cuối hoặc tổng thời lượng test. Báo chúng cả trên stream tự nhiên và video ghép, không chỉ một setting thuận lợi.

## 6. Ảnh hưởng tới hướng cải tiến và novelty

1. **Protocol trước model:** khóa matching, mẫu số báo giả, deadline và controls; kiểm tra phản ví dụ trước khi tối ưu leaderboard.
2. **State tracking có prior art:** factual/accepted progress và filtering không còn được mô tả như khoảng trống chưa ai xử lý sau khi đã đọc PROVIA.
3. **Câu hỏi ứng dụng còn mở:** liệu goal-level instance + evidence exo giữ được một lượt qua pause/repair và giảm false completion ở cùng nhãn/latency/compute hay không?
4. **View invariance có prior art:** đối chiếu P21 trước khi đề xuất representation; kiểm tra lợi ích khi giữ lại tín hiệu ROI/trạng thái đặc thù exo.
5. **Metric mới không tự tốt hơn:** WARI/SMS/affiliation nên được xét theo lỗi ứng dụng, không thay toàn bộ metric hiện có chỉ vì mới hơn.

Đây là mở rộng phạm vi đọc và kế hoạch kiểm chứng, không phải bằng chứng đã tìm được một đóng góp mới hay đã tái lập các bài.
