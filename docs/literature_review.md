# Paper cho định vị online từng lượt công việc

Ngày khảo sát: **2026-11-13**. Trạng thái: **bản nghiên cứu v0.2**, chưa tái lập thực nghiệm và chưa chốt model. Bổ sung nghiên cứu ảnh hưởng gián tiếp: PROVIA, protocol/metric và chuyển góc nhìn. Đối chiếu với [problem.md](problem.md) và [datasets.md](datasets.md): video **exocentric**, xử lý causal, trả start/end cho **toàn bộ một lượt công việc**, giữ gián đoạn bên trong, xử lý nhiều lượt và nhận biết hoàn thành.

## 1. Phạm vi và cách đọc

Đã tải **23 PDF** vào [`papers/`](../papers/README.md). Danh mục ghi tên đầy đủ, nguồn, phiên bản và lý do giữ bài cũ; [`manifest.json`](../papers/manifest.json) lưu checksum, số trang và vị trí bằng chứng kết quả. Xem thêm [phân tích PROVIA, metric và protocol](related_work_and_evaluation.md).

Ưu tiên thời gian **2024-11-13 đến 2026-11-13**: P01–P09 thuộc 2025–2026. P10 có preprint ngày 2024-11-02, hơi ngoài cửa sổ, dù công bố NeurIPS 2024; giữ như bài nền online TAS. P11–P18 là ngoại lệ có chủ đích để hiểu instance localization, completion, tiến trình, thời lượng và suy luận xác suất. Không dùng ngày crawler/index thay cho ngày công bố.

P19–P21 bổ sung ba bài 2025–2026 về procedure-state/protocol, metric segmentation và unseen views; P22–P23 là bài nền metric. Tiêu chí chọn mở rộng gồm **cách đặt bài toán, mô hình hóa, biểu diễn, dữ liệu, metric và protocol**, không chỉ trùng objective đầu ra. Một bài không trả interval hoàn thành vẫn có thể ảnh hưởng quyết định nghiên cứu; cột “đã giải quyết chưa” không phải tiêu chí loại bài.

Tìm theo On-TAL/OAD/online TAS, completion/goal-state/procedure verification, hierarchical streaming, Bayesian changepoint và semi-Markov; lần theo tài liệu liên quan của các bài sát nhất. Dùng PDF và trang chính thức/arXiv của tác giả để phân tích, không dùng bản tóm tắt tự động làm bằng chứng kết quả. Đây là tập bài chọn lọc, **chưa phải systematic review hoặc bằng chứng không còn bài liên quan nào khác**.

Quy ước:

- **Tác giả báo cáo:** vấn đề, motivation, kỹ thuật và số liệu trong bài. Các số liệu chưa được chạy lại tại repo.
- **Nhận định dự án:** mức phù hợp, giới hạn khi chuyển bài toán và đề xuất cải tiến của người viết; không mặc định là hạn chế mà tác giả tự tuyên bố.
- **“Đã giải quyết chưa?”** xét toàn bộ yêu cầu của dự án, không phủ nhận bài đã giải được nhiệm vụ riêng của nó.
- `pp` = điểm phần trăm; không phải phần trăm tương đối. mAP interval, frame-mAP, F1 segmentation, recall grounding và F1 verification không so trực tiếp với nhau. Chỉ tính cải thiện giữa các cấu hình trong **cùng bảng của cùng bài**.
- “Tr. PDF” tính từ trang đầu file tải về, khác số trang proceedings. Mỗi ID ở bảng dẫn tới PDF đó.

**Kết luận trong phạm vi 23 bài:** chưa xác lập được một giải pháp đã chứng minh trọn gói yêu cầu của dự án. P03 gần về phân cấp và có thử exo; P13 về hoàn thành đúng bước; P18/P01 gần cấu trúc đầu ra online. **P19 là prior art quan trọng** về factual state, accepted progress, filtering và đánh giá whole-trial; phải đối chiếu trước khi coi ý tưởng state tracking là mới. Cần kiểm chứng ở đúng cấp mục tiêu, không chỉ ghép các module rồi gọi là giải quyết xong.

## 2. Bảng tổng hợp để scan

### 2.1. Nhóm ưu tiên 2025–2026

| Paper | Vấn đề bài nhận ra | Motivation | Giải pháp chính | Kết quả rất ngắn, tác giả báo cáo | Đã giải quyết bài toán dự án chưa? |
| --- | --- | --- | --- | --- | --- |
| [P01 — OnPoint, 2026](../papers/P01_2026_onpoint.pdf), ECCV, bản arXiv v1 | On-TAL cần interval labels đắt; mô hình ít nhãn thường offline | Học streaming với một điểm nhãn/instance | Teacher offline → student online, distillation nhiều mức và attention theo actionness | THUMOS14 avg mAP@0.1:0.7: **46,3 → 51,1**, +4,8 pp; Bảng 1, tr. 11 | **Một phần:** có nhiều interval online, chưa có ngữ nghĩa hoàn thành toàn công việc; point nhãn chưa mặc định là completion. |
| [P02 — DUGO, 2026](../papers/P02_2026_dugo.pdf), preprint | Context đơn thang hạn chế On-TAL thủ tục | Nắm chi tiết ngắn và ngữ cảnh dài | Encoder hai thang, Gaussian prototypes có điều kiện, gated attention | EGTEA avg mAP@0.1:0.5 so HAT: **21,5 → 24,3**, +2,8 pp; Bảng I, tr. 7 | **Một phần:** định vị action, chưa chứng minh grouping/completion cấp lượt; exo ở MUSES chưa là quy trình công nghiệp. |
| [P03 — OpenHOUSE, 2025](../papers/P03_2025_openhouse.pdf), ICCV | Streaming chưa hiểu phân cấp; hành động sát nhau khó tách | Hiểu substep–step–goal, gọi VLM đúng lúc | Boundary hybrid actionness/progression; streaming module + VLM; nhãn phân cấp có LLM và người kiểm tra | EgoGS step F1 localization@0.5: MiniROAD **12,46 → 39,70**; exo **39,73**; Bảng 3, tr. 7 | **Gần nhất nhưng chưa đủ:** có exo/phân cấp; goal accuracy chưa chứng minh phát hiện mốc hoàn thành đúng và nhiều lượt goal có gián đoạn. |
| [P04 — Hierarchical Event Memory, 2025](../papers/P04_2025_hierarchical_event_memory.pdf), ICCV | FIFO frame memory quên lịch sử; proposals làm start báo muộn | Grounding online có nhớ dài và giảm trễ | Memory sự kiện nhiều thang, gộp thích nghi, nhánh dự báo start | TACoS R@1 IoU0.5: HAT **34,15 → 44,19**; bật dự báo còn **37,44**; Bảng 1, tr. 7 | **Một phần:** cần text query; đánh đổi anticipation–accuracy, chưa là completion detector cho toàn lượt. |
| [P05 — Online GEBD/ESTimator, 2025](../papers/P05_2025_online_gebd.pdf), ICCV | GEBD offline dùng tương lai; thiếu boundary online không phụ thuộc lớp | Tách sự kiện khi frame mới tới | Dự đoán quan sát, đo prediction error, ngưỡng thích nghi từ lịch sử | Kinetics-GEBD avg F1: MiniROAD-BC **0,681 → 0,748**; Bảng 1, tr. 6 | **Chưa:** boundary chung có thể là đổi thao tác/nghỉ, chưa là kết thúc công việc. Hữu ích làm tín hiệu ứng viên. |
| [P06 — CMeRT, 2025](../papers/P06_2025_cmert.pdf), CVPR | Context lúc train khác lúc test trong OAD | Học tốt frame hiện tại thay vì frame trung gian | Bổ sung near-past và sinh near-future từ memory | THUMOS14 frame-mAP: MAT **71,6 → 73,2**; Bảng 2, tr. 6 | **Chưa:** phân loại frame, thiếu instance và completion; dùng làm encoder/baseline causal. |
| [P07 — OZ-TAL/VFEAL, 2026](../papers/P07_2026_oz_tal.pdf), preprint | On-TAL closed-set khó gặp action chưa học | Định vị online zero-shot | VLM đóng băng, memory-guided enhancement, phân biệt background và gộp frame | THUMOS14 split lớp 75/25, avg mAP@0.3:0.7: Baseline-II **3,49 → 9,30**; Bảng I, tr. 6 | **Một phần:** mở lớp mới, chưa xác minh mục tiêu đạt; điểm thấp ở biên chặt. Zero-shot chưa là yêu cầu cốt lõi. |
| [P08 — PHGC, 2025](../papers/P08_2025_phgc.pdf), CVPR | Video–luật ngôn ngữ lệch modality và cấp biểu diễn | Kiểm tra quy trình có thỏa chỉ dẫn không | Heterogeneous graph, cross-modal path và discriminative entities | CSV-NL mean F1 verification: NSG **61,04 → 68,49**; Bảng 2, tr. 6 | **Chưa:** verification video–rule, không chứng minh phát nhiều interval causal; có thể mượn cấu trúc goal/state. |
| [P09 — Bayesian-VSLNet, 2026](../papers/P09_2026_bayesian_vslnet.pdf), CVIU, online 2025-12-31 | Text giống nhau dễ trỏ nhầm lần thực hiện lặp | Dùng thứ tự để phân biệt step occurrence | Likelihood grounding × temporal-order prior | Ego4D Goal-Step val, IndOrder R@1 IoU0.3: VSLNet **12,15 → 23,75**; Bảng 1, tr. 6 | **Chưa:** grounding offline theo cả video và danh sách bước; cần thay prior/decoder để causal và cho thứ tự linh hoạt. |

### 2.2. Bài nền và mô hình toán/xác suất

| Paper | Vấn đề bài nhận ra | Motivation | Giải pháp chính | Kết quả rất ngắn, tác giả báo cáo | Đã giải quyết bài toán dự án chưa? |
| --- | --- | --- | --- | --- | --- |
| [P10 — OnlineTAS, 2024](../papers/P10_2024_onlinetas.pdf), NeurIPS | Thiếu context khi bỏ tương lai; over-segmentation | Segmentation theo luồng thay cho cả video | Memory thích nghi, feature augmentation, causal TCN và post-processing | Breakfast online F1@50: **9,3 → 30,5** khi thêm post-processing; Bảng 1, tr. 6 | **Một phần:** có exo/TAS; thiếu toàn lượt/completion. Phải phân biệt online và semi-online, đo delay do giữ nhãn. |
| [P11 — HAT, 2024](../papers/P11_2024_hat.pdf), ECCV | Anchor On-TAL thiên context ngắn | Dùng lịch sử trong quy trình | History module, refinement anchor và focal loss thích nghi | EGTEA avg mAP@0.1:0.5: OAT **19,6 → 21,5**; Bảng 1, tr. 10 | **Một phần:** interval online, chưa biết đạt goal. Hữu ích làm đối chứng lịch sử. |
| [P12 — ProTAS, 2024](../papers/P12_2024_protas.pdf), CVPR | Online segmentation bỏ qua progress và cấu trúc task | Dùng tiến trình để giảm dự đoán bước sai | Causal segmentation, action-progress head và task graph | EgoProceL F1@50: CAS **33,0 → 35,7** với APP+TG; Bảng 1, tr. 6 | **Một phần:** progress từng action chưa là goal completion; thí nghiệm EgoPER của bài chỉ dùng video normal. |
| [P13 — IndustReal/PSR, 2024](../papers/P13_2024_industreal.pdf), WACV, preprint 2023 | Nhận ra thao tác không đảm bảo thực hiện xong/đúng | Theo dõi hoàn thành bước và lỗi | ASD + tích lũy confidence + ràng buộc quy trình; dataset và metric PSR | B1→B3: F1 **0,779 → 0,883** nhưng delay **14,9 → 22,4 s**; Bảng 4, tr. 8 | **Gần completion bước:** ego, chưa đủ start/end toàn lượt; minh họa rõ accuracy–latency và lỗi thực thi. |
| [P14 — Action Completion, 2018](../papers/P14_2018_action_completion.pdf), BMVC | Classifier vẫn nhận action ở lần thử thất bại | Phân biệt attempted với achieved, định vị completion moment | CNN–LSTM voting classification/regression qua chuỗi | **89%** mốc trong 1 giây khi dùng frame trước **và sau** completion; abstract, tr. 1 | **Chưa:** kết quả này dùng bằng chứng hậu completion và đầu ra cấp chuỗi/first completion, chưa streaming nhiều lượt/start. |
| [P15 — BOCPD, 2007](../papers/P15_2007_bocpd.pdf), technical report | Bayesian changepoint thường suy luận hồi cứu | Cập nhật phân bố ranh giới theo prefix | Message passing trên posterior run length, likelihood và hazard | Minh họa **3 chuỗi thực**, không có điểm TAL/completion để so; §3 | **Chưa:** change phân phối chưa là goal; là cơ sở filtering và bất định ranh giới. |
| [P16 — HDP-HSMM, 2013](../papers/P16_2013_hdp_hsmm.pdf), JMLR | HMM ép thời lượng trạng thái dạng geometric | Cho prior thời lượng và số trạng thái linh hoạt | Explicit-duration semi-Markov + HDP, Gibbs inference | Power disaggregation: mean accuracy **67,2 → 81,5%** so F-HDP-HMM; Bảng 1, tr. 25 | **Chưa:** kết quả ngoài video; Gibbs theo chuỗi không tự là causal filter. Mượn mô hình duration/state. |
| [P17 — Robust BOCPD, 2023](../papers/P17_2023_robust_bocpd.pdf), ICML | Outlier/misspecification gây change giả; robust Bayes cũ chậm | Filtering bền hơn với nhiễu, tính được nhanh | Generalized Bayes bằng diffusion score matching | Tác giả báo **>10×** nhanh hơn đối thủ gần nhất trong đánh giá của bài; abstract | **Chưa:** không có ngữ nghĩa task; có thể thử trên feature/object-state nhiễu. Không suy ra tốc độ video tương ứng. |
| [P18 — MATR, 2024](../papers/P18_2024_memory_augmented_transformer.pdf), ECCV | Context ngắn khó tìm start của action dài | Định vị instance dùng lịch sử | Memory queue; end decoder rồi truy hồi start; online NMS | THUMOS14 avg mAP@0.3:0.7: OAT-OSN **44,6 → 49,5**; Bảng 1, tr. 11 | **Một phần:** khớp dạng interval; chưa nhận biết kết quả công việc và ownership qua pause. Baseline trực tiếp đáng thử. |

Không dùng các con số giữa các bảng để xếp hạng model. Ngay cả EGTEA trong HAT và OnPoint cũng có cấu hình/split/feature khác; phải tái lập cùng điều kiện mới so sánh cho dự án.

### 2.3. Nghiên cứu ảnh hưởng qua protocol, metric và biểu diễn

| Paper | Vấn đề bài nhận ra | Motivation | Giải pháp/đóng góp chính | Kết quả rất ngắn, tác giả báo cáo | Ảnh hưởng tới dự án / đã giải quyết chưa? |
| --- | --- | --- | --- | --- | --- |
| [P19 — PROVIA, 2026](../papers/P19_2026_provia.pdf), preprint | First-mistake protocol thưởng vị trí; sai làm thay đổi trạng thái thực tế | Phát hiện lỗi suốt trial, còn hoạt động sau recovery | Step segmentation causal; factual state tách accepted progress; filter + sequential alarms; whole-trial protocol | CaptainCook4D recall tại budget validation 0,1 FA/phút: **0,128 → 0,154** so MistSense-RGB-style; Bảng IV, tr. 8 | **Ảnh hưởng lớn:** protocol/negative controls và prior art state tracking. Chưa là exo whole-task interval detector; không thắng mọi operating point. |
| [P20 — Interpretable TSS Metrics, 2025](../papers/P20_2025_interpretable_segmentation_metrics.pdf), NeurIPS | ARI không xét vị trí/loại lỗi temporal segmentation | Biết lỗi sai theo cách nào, không chỉ một điểm số | WARI theo khoảng cách boundary; SMS với delay/isolation/transition/missing | Synthetic và 5 dataset thực; tách loại lỗi mà ARI không phân biệt; §4, tr. 8–10 | **Metric bổ trợ**, chưa là metric completion/latency; mapping nhãn và trọng số cần phù hợp bài toán supervised. |
| [P21 — Unseen-view TAS, 2025](../papers/P21_2025_unseen_view_tas.pdf), bản arXiv v1 | TAS giảm chất lượng khi đổi góc camera | Generalize sang view chưa thấy | Sequence/action-level similarity losses trên nhiều view train | Assembly101 unseen exo F1@50 **11,7 → 13,2**, +1,5 pp; Hình 4, tr. 7 | **Biểu diễn/protocol hữu ích** cho exo; chưa chứng minh causal/completion. Lợi ích cần thử lại với temporal backbone online. |
| [P22 — Affiliation Metrics, 2022](../papers/P22_2022_affiliation_metrics.pdf), KDD | Range metrics có thể bị khai thác bằng dự đoán xấu | Đánh giá cục bộ, diễn giải bằng thời gian và baseline ngẫu nhiên | Affiliation precision/recall từ khoảng cách trong vùng GT | Adversarial predictor đạt TaP/TaR F1 **0,96** ở NYC-Taxi; Bảng 5, tr. 7 | **Bài nền chống metric gaming**; dùng để kiểm tra evaluator, không thay one-to-one task matching hoặc emission latency. |
| [P23 — Precision/Recall for Time Series, 2018](../papers/P23_2018_range_precision_recall.pdf), NeurIPS | Point P/R không diễn đạt coverage/vị trí/phân mảnh interval | Cho phép ưu tiên theo ứng dụng | Range P/R: existence, overlap, cardinality và positional bias | Khái quát point P/R và minh họa thay đổi đánh giá theo yêu cầu; §4–5 | **Bài nền thiết kế metric**; tham số phải khóa trước test, cần đối chứng chống gaming như P22. |

## 3. Ghi chú theo từng paper

### P01 — OnPoint

**Đọc để dùng:** phù hợp khi chi phí interval annotation là nút thắt. Teacher được nhìn toàn video **train**, student test chỉ dùng prefix; điều này tự nó không vi phạm online. Điểm gán nhãn của bài không đồng nghĩa điểm hoàn thành: phụ lục có điểm được lấy gần tâm interval từ GT, nên cần thử nhãn người thật ở cấp công việc. Tác giả công bố ECCV 2026 trên [arXiv](https://arxiv.org/abs/2607.00289). Phụ lục B.2–B.3 nêu trade-off ONMS/OSN và throughput loại chi phí feature extractor; cần đo lại toàn pipeline.

### P02 — DUGO

**Đọc để dùng:** Gaussian memory là kỹ thuật đáng khảo sát, nhưng không mặc định là posterior xác suất công việc đã hoàn thành. §III-C tạo learned prototypes và điều kiện hóa bằng context cửa sổ hiện tại. **Nhận định:** cần kiểm tra memory có thực sự giữ sự kiện của lượt cụ thể qua pause dài hay chỉ mang prior học được; thí nghiệm thay prefix nhưng giữ nguyên cửa sổ cuối có thể phân biệt. Preprint [2026-10-30](https://arxiv.org/abs/2610.41402), chưa coi là kết quả đã tái lập/đánh giá độc lập.

### P03 — OpenHOUSE

**Đọc để dùng:** ưu tiên đọc đầu tiên vì có phân cấp và kết quả exo thực sự trong Bảng 3, không chỉ nêu khả năng chuyển miền. Không nhầm goal **classification/description** với mốc goal **achievement**. Nhãn step tạo từ atomic labels có kiểm tra của người vẫn cần đối chiếu định nghĩa lượt của dự án. **Nhận định:** progression reset giúp tách action sát nhau nhưng có thể nhầm khi thử lại; cần kiểm tra giữ cùng task-instance qua repair. [Nguồn ICCV](https://openaccess.thecvf.com/content/ICCV2025/papers/Kang_Open-ended_Hierarchical_Streaming_Video_Understanding_with_Vision_Language_Models_ICCV_2025_paper.pdf).

### P04 — Hierarchical Event Memory

**Đọc để dùng:** học cách nén lịch sử theo sự kiện, không chỉ FIFO frame. Với TACoS, bật nhánh future prediction giảm start delay từ 22,38 s xuống −1,28 s nhưng giảm R@1@0.5 từ 44,19 xuống 37,44; end delay cũng có thể âm. **Nhận định:** đây là anticipation, không phải bằng chứng đã hoàn thành. Mượn memory nhưng tách sự kiện dự báo khỏi sự kiện completed; không lấy negative delay làm lợi thế completion. [Nguồn ICCV/arXiv](https://arxiv.org/abs/2508.04546).

### P05 — Online GEBD

**Đọc để dùng:** có thể phát boundary candidates mà không học mọi lớp công việc. **Nhận định:** thay đổi do lấy dụng cụ, nghỉ hoặc che khuất cũng có thể làm prediction error tăng. Bắt buộc có tầng quyết định cấp task để không cắt mỗi boundary. Thử thêm ROI/trạng thái vật thể ở camera ngoài, so với full-frame error; chuẩn hóa bằng lịch sử đã tới, không thống kê cả video. [Nguồn ICCV](https://openaccess.thecvf.com/content/ICCV2025/html/Jung_Online_Generic_Event_Boundary_Detection_ICCV_2025_paper.html).

### P06 — CMeRT

**Đọc để dùng:** điểm quan trọng là training–inference discrepancy và non-causal shortcut khi học anticipation, không chỉ thêm memory. Sinh near-future từ dữ liệu quá khứ khác với đọc frame tương lai. **Nhận định:** khi học nhiều timestamp trong cùng window, phải kiểm tra từng target nhận context nào; train causal đúng cho frame cuối chưa chứng minh loss của mọi frame trung gian đều đúng. Kết quả OAD không thay metric interval/completion. [Nguồn CVPR](https://openaccess.thecvf.com/content/CVPR2025/html/Pang_Context-Enhanced_Memory-Refined_Transformer_for_Online_Action_Detection_CVPR_2025_paper.html).

### P07 — OZ-TAL

**Đọc để dùng:** lựa chọn mở rộng nếu sau này cần đổi công việc bằng text hoặc gặp task chưa học. Bài dùng VFEAL và logic chuyển action-active sang inactive để tạo interval. **Nhận định:** score tụt vì gián đoạn không bảo đảm goal hoàn tất; đóng interval ngay có thể tách một lượt thành nhiều phần. Chỉ nên ưu tiên sau baseline đúng cấp task. [Nguồn preprint](https://arxiv.org/abs/2605.09976); dòng “journal template” trong PDF không được xem là thông tin đã được nhận vào journal.

### P08 — PHGC

**Đọc để dùng:** gợi ý mô hình hóa quan hệ giữa mục tiêu, trạng thái và thao tác, thay vì chỉ nhãn action phẳng. **Nhận định:** verification sau khi xem operation flow không tự trở thành detector online bằng cách chạy lặp trên prefix. Cần biểu diễn “chưa thấy bước cần thiết”, phân biệt pending với violated, và xử lý sửa lỗi trước khi kết luận thất bại. Không cần ép đầu vào text nếu task đã cấu hình cố định. [Nguồn CVPR](https://openaccess.thecvf.com/content/CVPR2025/papers/Jiang_PHGC_Procedural_Heterogeneous_Graph_Completion_for_Natural_Language_Task_Verification_CVPR_2025_paper.pdf).

### P09 — Bayesian-VSLNet

**Đọc để dùng:** tách visual likelihood và prior thứ tự giúp xem rõ model dựa vào hình ảnh hay vị trí. §4.2 có prior theo thứ tự query trên timeline toàn video. **Nhận định:** không mang trực tiếp prior dùng tổng chiều dài video vào streaming chưa biết kết thúc; thay bằng trạng thái quy trình và thời lượng đã quan sát. Ưu tiên kết quả validation v++ trong bảng trên; không trộn nó với bản v0 thắng challenge 2024. [Nguồn bản journal](https://zaguan.unizar.es/record/168247).

### P10 — OnlineTAS

**Đọc để dùng:** backbone/baseline cho stream exo như Breakfast, 50Salads. §3.4 tách online chỉ giữ dự đoán cuối clip với semi-online trả mọi frame của clip; không báo hai chế độ là cùng latency. Post-processing giữ nhãn cũ khi confidence thấp là causal nhưng có thể kéo dài endpoint. **Nhận định:** tăng F1 lớn chưa chứng minh phản ứng hoàn thành nhanh hơn; cần ablation có/không post-processing với event delay. [Nguồn NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2024/file/6c6c5fccf3c8661fcae219be7ca226f7-Paper-Conference.pdf).

### P11 — HAT

**Đọc để dùng:** đối chứng cho giả thuyết “lịch sử giúp hiểu thao tác hiện tại”. Không biến mỗi anchor/action thành một task-instance. **Nhận định:** thông tin quan trọng từ trước một pause có thể nằm ngoài history window; cần phân tích theo độ dài lượt và pause. Bài có kết quả procedural ego và non-PREGO; lợi ích này chưa xác nhận đầy đủ cho exo công việc đích. [Nguồn ECCV/arXiv](https://arxiv.org/abs/2408.06437).

### P12 — ProTAS

**Đọc để dùng:** progress và task graph là cấu trúc cần đối chiếu trước khi tự đề xuất. Đặc biệt, phần EgoPER của bài chỉ dùng normal videos (§5.1), nên chưa suy ra khả năng với lỗi/repair từ bảng kết quả đó. **Nhận định:** với dự án, graph cần soft constraints và đường quay lại khi sửa; progress có thể giảm/reset mà task-instance chưa kết thúc. [Nguồn CVPR](https://openaccess.thecvf.com/content/CVPR2024/html/Shen_Progress-Aware_Online_Action_Segmentation_for_Egocentric_Procedural_Task_Videos_CVPR_2024_paper.html).

### P13 — IndustReal/PSR

**Đọc để dùng:** phân biệt thao tác và kết quả, và luôn đọc F1 cùng delay. B3 tốt hơn B1 về F1 nhưng chậm hơn; lỗi vật thể khó nhìn vẫn gây false completion. **Nhận định:** ràng buộc quy trình có thể che lỗi nếu chỉ cho phép các bước hợp lệ; cần giữ nhánh unknown/error và đo riêng video lỗi. PSR chưa cung cấp trực tiếp toàn bộ start/end cấp công việc, cũng chưa xác nhận exo. [Nguồn paper](https://arxiv.org/abs/2310.17323).

### P14 — Action Completion

**Đọc để dùng:** bài nền xác lập khác biệt giữa action attempt và đạt mục tiêu. Mô hình recurrent không có nghĩa toàn bộ pipeline được đánh giá causal: kết quả nổi bật tích lũy voting cả frame sau completion và nhắm first completion của chuỗi. **Nhận định:** mượn tiêu chí quan sát và incomplete examples; muốn streaming cần chốt emission policy bằng prefix, nhiều instance và mô hình start riêng. [Trang tác giả](https://dimadamen.github.io/ActionCompletion/).

### P15 — BOCPD

**Đọc để dùng:** posterior run length cho phép giữ nhiều giả thuyết ranh giới thay vì một threshold cứng. **Nhận định:** chuyển action, đổi cảnh và hoàn thành task là các cấp change khác nhau; không reset task ở mọi changepoint. Prior i.i.d. theo segment cũng khó khớp feature video liên tiếp. Bản exact tăng chi phí theo lịch sử; phải kiểm tra truncation/pruning và hiệu ứng mất ranh giới hiếm. [Nguồn tác giả](https://lips.cs.princeton.edu/pdfs/adams2007changepoint.pdf).

### P16 — HDP-HSMM

**Đọc để dùng:** mô hình hóa thời lượng rõ ràng thay vì ép phân bố geometric của HMM. **Nhận định:** không nhất thiết cần HDP hoặc Gibbs của bài; pilot có thể dùng HSMM hữu hạn với số trạng thái ít, filtering causal. Kết quả power disaggregation chỉ cho thấy ích lợi của duration modeling trên bài gốc, không phải hiệu năng video. Pause cần giữ identity lượt và có clock riêng; prior thời lượng quá cứng sẽ cắt nhầm. [Nguồn JMLR](https://jmlr.org/papers/v14/johnson13a.html).

### P17 — Robust BOCPD

**Đọc để dùng:** xem như đối chứng khi feature/object tracker có outlier. Robust update có cơ sở toán trong điều kiện của bài, không bảo đảm tự xử lý mọi nhiễu video. **Nhận định:** phải đo cả giảm báo nhầm lẫn bỏ sót thay đổi thật; làm detector ít nhạy hơn có thể tăng delay. Chưa dùng cấu hình được tune trên toàn stream test để tuyên bố online. [Nguồn ICML](https://proceedings.mlr.press/v202/altamirano23a.html).

### P18 — MATR

**Đọc để dùng:** khớp nhu cầu báo xong rồi tìm lại start trong lịch sử, có thể là baseline interval chính. §3.4 bỏ proposal có end dự đoán vượt thời điểm hiện tại và dùng online NMS. **Nhận định:** điều đó không bảo đảm goal đã đạt, và memory feature không thay bộ đệm video để xuất clip. Cần huấn luyện ở đúng cấp nhãn lượt, log timestamp phát và kiểm tra duplicate khi nhiều lượt sát nhau. [Nguồn ECCV](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/02834.pdf).

### P19 — PROVIA

**Đọc để dùng:** bài [preprint 2026-09-17](https://arxiv.org/abs/2609.20638v1) đánh giá mistake detection, không phải mask segmentation. Nhận định cho dự án: phải có bước kiểm tra evaluator bằng predictor không nhìn video trước khi so model. Cần so cả ranking và vận hành tại budget báo giả. Cấu trúc state của bài làm thu hẹp phạm vi đóng góp tiềm năng nêu ở mục 5; không được coi “factual state + accepted progress” là ý tưởng chưa có. Phân tích chuyển giao và giới hạn ở [tài liệu protocol](related_work_and_evaluation.md).

### P20 — Interpretable Evaluation Measures

**Đọc để dùng:** [nguồn NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/file/09425891e393e64b0535194a81ba15b7-Paper-Conference.pdf) giúp phân loại lỗi. Nhận định: dung sai cho nhãn bước không đồng nghĩa chấp nhận trễ báo hoàn thành. WARI/SMS hợp làm diagnostic; với lớp có nghĩa cố định, không được dùng remapping tối ưu GT để che nhầm semantics. Với cùng một công việc lặp liền nhau, nhãn state còn có thể giống hệt dù thiếu boundary instance. Cần giữ interval/event metrics và ID lượt riêng.

### P21 — Generalizing TAS to Unseen Views

**Đọc để dùng:** [bản arXiv v1](https://arxiv.org/abs/2504.02512v1) là nền liên quan trực tiếp đến giả thuyết exo của dự án dù không có objective completion. Cần nhiều view lúc train; chưa được giả định có đủ từ bản IKEA top-view hiện tại. Nhận định: nên thử loss chỉ ở train với encoder causal, giữ một view ở test. Không áp cùng mức bất biến view cho mọi tín hiệu: vị trí khay thành phẩm có thể hữu ích cho completion, trong khi action representation cần ít phụ thuộc camera.

### P22 — Affiliation Metrics

**Đọc để dùng:** [paper KDD](https://arxiv.org/abs/2206.13167v1) nhắc kiểm thử metric trước khi tối ưu theo nó. Nhận định: predictor luôn bật, spam event, interval rất dài hoặc chạm nhẹ mọi GT cần được chấm kém ở ít nhất một trục vận hành quan trọng. Không mặc định metric có cơ sở toán sẽ ngăn mọi shortcut trong miền mới. Các điểm completion có độ dài bằng không cần quy ước riêng; không biến thành vùng dung sai tùy ý để áp metric rồi giấu thay đổi.

### P23 — Precision and Recall for Time Series

**Đọc để dùng:** [nguồn NeurIPS](https://proceedings.neurips.cc/paper/2018/hash/8f468c873a32bb0619eaeb2050ba45d1-Abstract.html) cho ngôn ngữ mô tả yêu cầu metric theo ứng dụng. Nhận định: overlap và fragmentation ảnh hưởng clip xuất ra; early reward hợp phát hiện sự cố chưa chắc hợp completed event. Chỉ áp positional bias khi có lý do ứng dụng; công bố trọng số, kiểm tra độ nhạy và không dùng test để chọn cấu hình xếp model mình cao nhất.

## 4. Kỹ thuật đáng phân tích sâu

### 4.1. Từ phân cấp mô tả sang trạng thái hoàn thành — gợi ý từ P03/P13

Điểm cần giữ là hai tầng: **thao tác đang diễn ra** và **kết quả công việc đã đạt**. “Đang đóng hộp” và “đã có hộp đóng hoàn chỉnh, đúng đối tượng của lượt này” cần bằng chứng khác nhau. Biết nhãn goal “đóng gói” cũng chưa biết lúc goal được đạt.

**Đề xuất dự án:** dùng temporal model cho thao tác/context, thêm nhánh đọc trạng thái sản phẩm/vùng bàn giao từ RGB exo. Tầng instance giữ start và identity qua nghỉ/sửa lỗi. Chỉ phát completed khi đủ bằng chứng theo task definition; nếu bị che khuất thì giữ unknown/pending. Pose/ROI là tín hiệu phụ theo điều kiện camera, không phải bắt buộc và không tự là bằng chứng hoàn thành.

Thử hai cấu hình cùng backbone: temporal-only và temporal + goal-state. Nếu nhánh trạng thái chỉ tăng AP trên video dễ mà không giảm false completion ở ca sửa/bỏ dở, giả thuyết chưa được hỗ trợ. Nhãn trạng thái GT ở test chỉ phục vụ phân tích oracle, không làm đầu vào mặc định.

### 4.2. Boundary không phải completion — gợi ý từ P05/P15/P17

Có thể dùng prediction surprise hoặc changepoint làm **đề xuất ranh giới**. Việc quyết định “ranh giới thuộc cấp thao tác, nghỉ hay kết thúc lượt” vẫn cần goal/context. Đặt mọi boundary thành end sẽ trái yêu cầu giữ gián đoạn bên trong.

**Đề xuất dự án:** so sánh boundary-only, completion-only và kết hợp có context. Gán rõ các hard negatives: rời tay để lấy dụng cụ, đặt vật tạm, làm động tác cuối rồi sửa lại, vật đi qua vùng ra nhưng chưa xong. Đánh giá gain ở cùng FP/phút hoặc cùng timely recall, tránh đổi threshold rồi coi là cải tiến kiến trúc.

Lưu ý toán khi dùng BOCPD: với quy ước run reset sau quan sát trong recursion gốc và hazard hằng, cùng predictive likelihood xuất hiện ở nhánh growth và reset; sau chuẩn hóa, xác suất `r_t = 0` có thể bằng chính hazard hằng. Không mặc định lấy riêng nó làm “completion score”. Cần kiểm tra quy ước, posterior vị trí change đã tích lũy bằng chứng hoặc fixed-lag; nếu dùng thêm L frame thì ghi đúng latency. Đây là cảnh báo triển khai từ recursion, không phải kết luận paper sai.

### 4.3. Memory dài: phân biệt prior học được và ký ức của lượt này

**Nhận định từ P02/P04/P11/P18:** memory vector tốt cho biểu diễn chưa chắc lưu được “đã lấy phôi nào, lượt bắt đầu lúc nào, bước nào đã thực sự xong”. Memory Gaussian cũng chưa tự cho uncertainty được calibration ở cấp goal.

**Đề xuất dự án:** tách cache feature gần đây, tóm tắt sự kiện của lượt đang mở và video buffer để xuất clip. Tóm tắt chỉ cập nhật từ prefix; ghi provenance frame. Thử pause dài hơn cửa sổ, hai lượt nhìn giống nhau nhưng trạng thái trước khác nhau và cold start giữa lượt. So cùng giới hạn RAM/context, đo cả merge/split và khôi phục start; không chỉ AP trung bình.

### 4.4. Teacher offline hợp lệ, teacher test nhìn tương lai thì không — gợi ý từ P01/P06

Teacher mạnh có thể dùng toàn video train để cung cấp pseudo labels; student inference phải causal. Vấn đề mở của dự án là teacher có tách lượt **đúng mục tiêu** hay chỉ tách atomic action. Nếu pseudo label sai cấp thì student có thể học rất tốt bài sai.

**Đề xuất dự án:** bắt đầu với tập interval nhỏ được người kiểm tra, rồi thử thêm pseudo labels/point supervision. Đo hiệu quả theo số phút gán nhãn người thật, không chỉ “một điểm/video”. Audit vị trí điểm (giữa lượt hay completion), chất lượng pseudo label trên validation và sai số start/end. So với baseline full-interval cùng ngân sách nhãn. Không dùng test để tạo pseudo label, sửa task definition hoặc chọn teacher.

## 5. Mô hình toán đề xuất để kiểm chứng

Phần này là **thiết kế nghiên cứu của dự án**, lấy cảm hứng từ các bài trên; không phải mô hình đã chạy, không tuyên bố mới so với toàn bộ literature.

**Cập nhật sau P19:** procedure-state belief, factual/accepted progress, completion hazard và sequential decision đã có prior art gần. Mô hình dưới đây là khung tổ chức giả thuyết/baseline. Chỉ chuyển từ ego sang exo hoặc đổi tên mistake thành completion chưa tạo ra đóng góp mới; cần chứng minh khác biệt ở goal-level instance, pause ownership, bằng chứng quan sát và kết quả theo protocol khó hơn.

### 5.1. Trạng thái ẩn có thời lượng và identity

Ở thời điểm t, chỉ có quan sát đã tới `o_1:t` và định nghĩa mục tiêu g. Xét:

```text
I_t : identity của lượt đang mở hoặc none
S_t : idle / active / paused / completed / aborted / unknown
A_t : bước con nếu mô hình thực sự cần dùng
Z_t : trạng thái sản phẩm quan sát/ẩn
d_t : thời gian đã ở trạng thái hiện tại
b_t : phân bố niềm tin về (I_t, S_t, A_t, Z_t, d_t) từ o_1:t
```

Một dạng filtering tổng quát:

$$
b_t(x) \propto L_\theta(o_t\mid x,g)
\sum_{x'} T_\phi(x\mid x',g,\Delta t)\,b_{t-1}(x'),
\quad x=(I,S,A,Z,d).
$$

`T` thể hiện tiến triển, pause/resume, sửa lỗi và khởi tạo lượt mới; `L` là mô hình quan sát cần học/kiểm chứng. Không mặc định các score RGB, pose và object detector độc lập rồi nhân trực tiếp. Chúng có thể dùng cùng ảnh, dẫn tới đếm bằng chứng hai lần; cần fusion/calibration trên validation.

Semi-Markov cho phép hazard phụ thuộc thời lượng:

$$
h_s(d,c)=P(D_s=d\mid D_s\ge d,c),
$$

với c là context đã quan sát. Thời gian của **task-instance**, trạng thái pause và bước con cần phân biệt: hết duration thường gặp của một action không tự đóng task. Camera mất frame thì cập nhật theo `Δt`, không giả vờ mọi bước thời gian bằng nhau. Chọn prior mềm; rework có thể quay lại trạng thái trước, nên không ép mọi quy trình thành đường tuyến tính hoặc DAG không có vòng.

Một phương án ít tốn nhãn là học visual head bằng nhãn nguồn và interval/completion cấp lượt, giữ state machine/HSMM nhỏ để kiểm chứng trước. Không bắt buộc người gán nhãn mọi biến ẩn; nếu các biến không được giám sát thì phải kiểm tra tính định danh và độ tin cậy, không đặt tên state rồi coi nó đúng ngữ nghĩa.

### 5.2. Completion là quyết định dừng, không chỉ một frame score

Đặt `q_t(i)` là niềm tin lượt i đã đạt tiêu chí hoàn thành theo bằng chứng hiện có. Một chính sách ứng viên có thể dùng threshold, thời gian xác nhận hữu hạn và điều kiện quan sát, nhưng phải giữ riêng:

```text
start_hat, end_hat : timestamp ranh giới trên video đã quan sát
t_emit             : lúc phát quyết định thật
event_id           : tránh phát lặp cùng lượt
```

Nếu chưa đủ bằng chứng, chờ hoặc abstain. `completed` được giữ cho identity đã đóng; việc nhìn tiếp sản phẩm hoàn chỉnh không sinh thêm lượt. Chỉ mở identity mới khi có bằng chứng bắt đầu công việc mới. Một trạng thái sản phẩm sẵn có từ trước lúc camera bật không tự trở thành lượt vừa được làm xong.

Có thể tối ưu chính sách dừng theo rủi ro:

$$
R(\pi)=c_{FP}\,E[N_{false}]+c_{FN}\,E[N_{miss}]
+c_L\,E[\text{late time}]+c_B\,E[\text{boundary error}]
+c_D\,E[N_{duplicate}].
$$

Đây là mục tiêu đề xuất, cần chốt matching và các hệ số theo ứng dụng. Early completion là false completion, không được giấu bằng việc chỉ phạt latency dương; ranh giới dự báo tương lai phải thành event anticipation riêng. Báo Pareto accuracy–latency thay vì một tổng điểm tùy trọng số.

### 5.3. Khả năng quan sát và unknown

Camera exo có thể cho trạng thái vùng bàn/sản phẩm và pose, nhưng không đảm bảo thấy chi tiết hoàn thành. Cần đo tỷ lệ completion nhìn thấy và sai khác annotator. Có thể một lượt đã xong về vật lý nhưng phải đợi vật hết bị che mới có bằng chứng; khi có thể, ghi `t_goal` và `t_evidence` riêng.

Giải pháp phải báo coverage khi abstain. Không tăng độ chính xác bằng cách loại mọi hard case mà không báo số lượng. Cũng không lấy một phép kiểm tra vật lý ngoài ảnh làm ground truth “nhìn thấy rõ” để kết luận model RGB yếu.

## 6. Khoảng trống và hướng cải thiện cần thử

Các khoảng trống dưới đây là **suy luận trong phạm vi bài đã đọc**, không phải tuyên bố novelty toàn lĩnh vực.

| Khoảng trống | Dấu hiệu từ tập paper | Giả thuyết cải thiện | Cách bác bỏ/kiểm chứng |
| --- | --- | --- | --- |
| G1. Sai cấp mục tiêu: action/step/goal label khác goal achieved | P03 có phân cấp; P13/P14 phân biệt kết quả và thao tác | Hợp nhất interval head với goal-state head | Cùng backbone/nhãn: so false completion ở aborted/repair, không chỉ AP. |
| G2. Giữ một lượt qua pause, rework và lượt giống nhau nối tiếp | P05 tìm boundary; P07 gộp frame; P12 có progress/graph | Instance state riêng với pause/resume, reset có điều kiện | Tăng độ dài pause, hoán đổi repair; đo split/merge/duplicate và start recall. |
| G3. Lợi ích đặc trưng exo chưa được xác nhận cho task đích | P03 có exo, nhiều bài thủ tục thử trên ego | RGB + ROI/pose/object state theo điều kiện quan sát | Ablation exo cùng task; test view/ánh sáng mới, che vật thể và camera rung. |
| G4. AP/F1 tốt nhưng completion muộn hoặc phát sớm sai | P04 có delay âm/dự báo; P13 F1 tăng cùng delay | Chính sách dừng theo rủi ro và evidence | Timely recall/AP theo budget, FP/phút, early false completion, p95 delay. |
| G5. Chi phí/audit feature và hậu xử lý chưa đồng nhất | P01 loại feature cost khỏi throughput; P10 có hai mode | Replay causal toàn pipeline với frontier cho từng feature | Thay suffix không đổi event quá khứ; đo raw video→event/clip và backlog. |
| G6. Nhãn cấp lượt đắt; điểm nhãn có thể sai ngữ nghĩa | P01 sparse points; P03 hierarchical pseudo labels | Teacher offline + tập nhỏ interval/completion được kiểm tra | Đường learning curve theo phút annotation; kiểm tra pseudo label đúng cấp goal. |
| G7. Prior tiến trình/thời lượng dễ thành shortcut | P09 dùng order trên toàn timeline; P12 graph; P16 duration | Prior mềm theo prefix, có pause/error và unknown | Đổi tốc độ, thứ tự hợp lệ, pause dài; xem model có vẫn hoàn thành theo đồng hồ. |
| G8. Memory không đủ giữ trạng thái lượt và video lịch sử | P02 prototype, P04 event memory, P18 feature queue | Tách feature memory, instance state và video buffer | Stream dài, cold start, reconnect; đo RAM, continuity và clip còn đủ đầu. |
| G9. Bất định latent chưa là confidence completion đáng tin | P02 có Gaussian latent; P15–P17 có posterior theo mô hình | Calibration/robustness và abstention ở mức event | Reliability, coverage–risk, FP/delay dưới occlusion/outlier; kiểm tra bỏ sót thật. |
| G10. Protocol/metric có thể thưởng timing hoặc loại lỗi mà không cần hiểu video | P19 kiểm tra timing controls; P20/P22/P23 chỉ ra blind spots khác nhau | Whole-session test, no-perception controls, nhiều trục đánh giá | Cố định threshold trên validation, báo test FA thực, kiểm tra evaluator bằng phản ví dụ; xem tài liệu protocol. |

P19 và P21 là prior art cần đối chiếu cho G3/G8/G9: state tracking và view generalization đã có nghiên cứu. Các hàng này mô tả câu hỏi còn cần kiểm chứng cho **task đích**, không tuyên bố các cơ chế đó chưa tồn tại.

## 7. Kế hoạch thực nghiệm tối thiểu đề xuất

### 7.1. Khóa một benchmark nhỏ trước

Ưu tiên IKEA ASM exo đã có; chọn task và gán nhãn theo [datasets.md](datasets.md), không đổi thành atomic cycle chỉ để có nhiều mẫu. Dùng IndustReal cho completion/repair như dữ liệu thay thế và báo riêng ego. Nếu thiếu video tự nhiên nhiều lượt/bỏ dở, phải bổ sung hoặc thu thêm; ghép clip chỉ là kiểm tra kỹ thuật.

Giữ split theo recording/subject/view group; khóa test trước khi tune. Pilot cần đại diện lượt ngắn/dài, pause, sửa lại, dấu hiệu cuối giả, thiếu đầu/cuối và zero-completion. Cỡ mẫu phụ thuộc số recording và chi phí nhãn sau kiểm kê; chưa ấn định một số tùy ý như yêu cầu chính thức.

### 7.2. Baseline theo thứ tự, tránh thêm mọi module cùng lúc

| Mã | Cấu hình đề xuất | Câu hỏi cần trả lời |
| --- | --- | --- |
| B0 | RGB causal đơn giản + start/end head trên nhãn cấp lượt | Video/nhãn/evaluator đã chạy đúng và đạt mức nền nào? |
| B1 | MATR hoặc HAT huấn luyện lại ở cấp lượt, chọn một baseline | Instance localization đơn thuần đã đủ chưa; lỗi nằm ở biên hay ngữ nghĩa hoàn thành? |
| B2 | Ý tưởng phân cấp OpenHOUSE, task labels được người kiểm tra | Cấu trúc substep–task giúp grouping hay chỉ thêm supervision? |
| B3 | B1 + goal-state head RGB exo | Trạng thái sản phẩm giảm false completion không? |
| B4 | B3 + state machine/HSMM hữu hạn nhỏ, pause/rework và stopping policy | Ràng buộc xác suất có ích thêm so với heuristic cùng ngân sách latency? |
| B5 | Chỉ khi nhãn là nút thắt: teacher offline/point supervision kiểu OnPoint | Giữ chất lượng với ít công annotation hơn không? |

Giữ feature/backbone, split, nhãn và quyền truy cập dữ liệu ngang nhau khi so từng thành phần. Nếu B2 có nhãn bước dày hơn B1, báo riêng chi phí và thêm đối chứng cùng ngân sách nhãn. Chỉ thêm pose/calibration/multi-view khi dữ liệu thực sự có; báo setting và tổng latency mới.

Sau khi bổ sung P19, nếu thử factual state/accepted progress phải có đối chứng với cơ chế kiểu PROVIA. Công bố nhãn bước/correctness và demonstrations cần thêm; biến thể đổi sang goal completion phải được ghi là bản thích nghi, không gọi là tái lập nguyên bản hoặc so ngang ngân sách nhãn khi chưa đáp ứng điều kiện đó.

### 7.3. Báo cáo để tránh kết luận sai

- Interval AP/tIoU và sai số start/end đi cùng recall; goal-completion precision/recall và FP/phút ở negative/aborted.
- Timely recall theo ngân sách trễ; p50/p95 latency, early false completions, duplicate/revision và thời gian clip sẵn sàng.
- Merge/split qua gián đoạn; coverage/unknown; phân tích theo pause, repair, view và độ quan sát completion.
- Throughput, RAM/VRAM/buffer, decode/feature/inference/output cost; không dùng FPS temporal head thay tốc độ hệ thống.
- Lặp seed/đánh giá độ bất định theo recording khi đủ dữ liệu. Không coi gain nhỏ trên pilot hoặc một run là cải tiến ổn định.

## 8. Thứ tự đọc và quyết định hiện tại

Đọc kỹ **P19 → P20/P22 → P03 → P13 → P18 → P01 → P12 → P10**: kiểm tra protocol trước khi chọn model. P21 bổ sung góc nhìn/representation; P04/P05 cho memory/boundary, P15/P16/P17 cho xác suất. P06 giúp audit train/test causal; P07/P08/P09 hữu ích khi mở rộng sang task mới, luật ngôn ngữ hoặc prior thứ tự.

Hướng nên kiểm chứng đầu tiên là **định vị instance online + bằng chứng goal-state exocentric + trạng thái lượt giữ qua pause**. Temporal model có thể là baseline có sẵn; chưa cần VLM lớn hoặc HDP-HSMM đầy đủ. Chỉ đi sâu mô hình xác suất nếu phân tích lỗi cho thấy uncertainty/duration/grouping thực sự là nút thắt.

Đây là định hướng và giả thuyết, chưa có kết quả mới của repo. Trước khi tuyên bố đóng góp, cần rà thêm literature sát tổ hợp được chọn, tái lập baseline và chứng minh hiệu quả ở cùng nhãn, compute, causal access và latency budget.
