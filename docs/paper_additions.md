# Đối chiếu 13 link và các paper bổ sung

Ngày kiểm tra **2026-11-13**. Kết quả: **4 bài trùng, 9 bài mới**. Đã tải 9 PDF vào [papers/additions](../papers/additions/README.md); [manifest](../papers/additions/manifest.json) lưu đủ 13 link đầu vào, cách đối chiếu, tác giả, phiên bản, checksum và bằng chứng kết quả. Số liệu là tác giả báo cáo, chưa tái lập. Mức ưu tiên dưới đây là **ưu tiên đọc cho dự án**, không phải xếp hạng model bằng metric khác nhau.

Tất cả 9 bài có lý do để giữ, nhưng không nên đưa cả 9 vào tuyến đọc bắt buộc. A01/A02/A03 gần nhất về endpoint/instance/procedure online; A06 dễ liên hệ với baseline GRU nhưng objective là error detection. A04/A09 bổ sung bằng chứng state; A05/A07/A08 là các nhánh đọc có điều kiện.

## 1. Trùng hay mới — đủ 13 link

| Link người dùng gửi | Nhận diện | Quyết định |
| --- | --- | --- |
| [2408.02957](https://arxiv.org/pdf/2408.02957) | **P18 MATR** | Trùng arXiv ID/tên; đã giữ bản proceedings ECCV. Không tải thêm một bản trùng. |
| [SciTePress DOI](https://www.scitepress.org/Link.aspx?doi=10.5220/0013249700003912) | **A01 Online Detection of End of Take and Release Actions** | Mới; DOI khớp trang publisher và PDF VISAPP 2025. Đã tải. |
| [2407.12987](https://arxiv.org/pdf/2407.12987) | **A02 ActionSwitch** | Mới; arXiv v1. Bài 2024 ngoài cửa sổ hai năm nhưng là prerequisite trực tiếp hữu ích của OpenHOUSE. |
| [2408.06437](https://arxiv.org/pdf/2408.06437) | **P11 HAT** | Trùng arXiv ID/tên; đã có v1. |
| [IEEE 10658157](https://ieeexplore.ieee.org/document/10658157/) | **P12 ProTAS**, theo tên người dùng xác nhận | Tên đầy đủ khớp bản CVF hiện có. Trang IEEE bị xác minh/không đọc được metadata trực tiếp; ghi rõ cách đối chiếu thay vì suy đoán DOI. Không tải lại. |
| [2608.27562](https://arxiv.org/pdf/2608.27562) | **A03 VidParse** | Mới; chọn **v2**, sửa GTEA từ split 1 sang trung bình 4 split chuẩn theo version note của tác giả. |
| [2503.11953](https://arxiv.org/pdf/2503.11953) | **A04 SPOC** | Mới; chọn **v2**. Spatial/pixel state-change segmentation, không phải temporal action segmentation. |
| [2512.20409](https://arxiv.org/pdf/2512.20409) | **A05 DETACH** | Mới; v1. Giữ ở nhánh video–ambient-sensor representation, có điều kiện dữ liệu. |
| [2411.01122](https://arxiv.org/pdf/2411.01122) | **P10 OnlineTAS** | Trùng arXiv ID/tên; đã có bản proceedings NeurIPS. |
| [2606.25317](https://arxiv.org/pdf/2606.25317) | **A06 ESTANet** | Mới; v1. Nhánh online error detection; không nhầm với ESTimator của P05 GEBD. |
| [2411.16934](https://arxiv.org/pdf/2411.16934) | **A07 ESOM / Online Episodic Memory VQL** | Mới; chọn **v3**. Object memory/query localization khác action-memory interval detector. |
| [2610.00069](https://arxiv.org/pdf/2610.00069) | **A08 Ego–Exo WEM Framework** | Mới; v1. Bài nêu rõ offline batch processing và để benchmark định lượng cho future work. |
| [2503.21055](https://arxiv.org/pdf/2503.21055) | **A09 State-Change Counterfactuals** | Mới; chọn **v6**. Representation learning; không phải sẵn một online completion detector. |

Không ghi đè PDF P01–P23 hoặc đổi ID đã dùng trong tài liệu. Các bản A01–A09 là tập bổ sung riêng; [map 23 bài](paper_map.md) giữ phạm vi cũ và dẫn tới trang này. Roadmap đã tích hợp cả hai tập.

## 2. Bảng phân tích để scan

| Paper / mức đọc | Vấn đề và motivation | Giải pháp | Kết quả rất ngắn trong cùng bài | Đáp ứng dự án tới đâu? / đọc sau gì? |
| --- | --- | --- | --- | --- |
| [A01 ODAE, 2025](../papers/additions/A01_2025_online_action_end.pdf) — **đọc sớm**; [publisher](https://www.scitepress.org/PublishedPapers/2025/132497/) | Contact/start quan sát chưa đủ để biết take/release thật sự xảy ra; cần một event cho mỗi lần kết thúc. | Đặt ODAE, benchmark online/offline, TeSTra/Mamba, label propagation; point-level AP với matching one-to-one. | EK100 take/release, không label propagation: verb mp-mAP **20,32 → 24,55** khi thêm 1 Mamba layer vào short-memory; Table 3, PDF tr. 6. | Rất hữu ích cho end-event/protocol, nhưng chỉ endpoint thao tác; thiếu start và goal toàn lượt. Đọc formulation/metric sau MiniROAD/OAD; không cần chọn Mamba ngay. |
| [A02 ActionSwitch, 2024](../papers/additions/A02_2024_actionswitch.pdf) — **đọc sớm**; [arXiv](https://arxiv.org/abs/2407.12987) | Class-conditioned grouping khó tách overlapping/same-class instances; cần class-agnostic instance prediction. | Switch/state formulation, state-emitting causal GRU, conservativeness loss giảm flicker/chuyển state giả. | FineAction instance F1: CAG-QIL **15,67 → 19,44**; Table 1, PDF tr. 10. | Khớp việc tách instance và chống fragmentation; chưa là achieved goal. Overlap rộng hơn phạm vi một lượt đang mở của dự án. **MiniROAD → ActionSwitch → OpenHOUSE.** |
| [A03 VidParse, 2026](../papers/additions/A03_2026_vidparse.pdf) — **đọc sớm**; [arXiv v2](https://arxiv.org/abs/2608.27562v2) | Frame predictions nhiễu/over-segmentation làm hỏng cấu trúc nhiều bước; muốn tránh fine-tuning temporal model. | Frozen DINOv2 + hand-object features; similarity/checkerboard boundary; micro-prototypes; hard task graph và beam search. | EgoPER F1@0.5: ProTAS **51,31 → 77,60** trong Table 1 của bài, PDF tr. 11. | Có causal/buffered procedure parsing, chưa chứng minh whole-task completion/ownership. Graph và prototype vẫn cần nhãn train; hard constraints cần thử với repair/deviation. Đọc sau ProTAS/OnlineTAS, so với PROVIA. |
| [A04 SPOC, 2025, bản v2](../papers/additions/A04_2025_spoc.pdf) — **nhánh state**; [arXiv](https://arxiv.org/abs/2503.11953v2) | Temporal state-change labels không nói vùng nào đã chuyển trạng thái; cần actionable/transformed regions để hiểu tiến trình vật thể. | VLM pseudo masks, causal-ordering/ambiguity constraints; mask-level CLIP + global DINO và temporal Transformer; WhereToChange benchmark. | WTC-HowTo pseudo-label mIoU **0,411 → 0,455** với constraints; model đã train **0,502**; Table 2, PDF tr. 6. | Ý tưởng mạnh cho evidence sản phẩm ở exo; pixel score không là interval/emit latency. “Causal ordering” ở đây là dynamics của nhãn, không chứng minh streaming. Đọc sau P14/P13. |
| [A05 DETACH, 2025](../papers/additions/A05_2025_detach.pdf) — **có điều kiện**; [arXiv](https://arxiv.org/abs/2512.20409v1) | Global alignment bỏ mất chi tiết/vị trí ở exo–ambient sensors; cần tách không gian/thời gian. | Sensor spatial clustering, staged spatial rồi temporal alignment, contrastive weights xử lý negative khác nhau. | Opportunity++ weighted F1 **0,56 → 0,73** so CAV-MAE; Table 1, PDF tr. 6. | Kết quả là **classification từ sensor encoder**, không phải RGB localization. Chỉ ưu tiên nếu có ambient sensors hoặc nghiên cứu cross-modal representation; không là prerequisite pipeline RGB. |
| [A06 ESTANet, 2026](../papers/additions/A06_2026_estanet.pdf) — **nhánh error/state online**; [arXiv](https://arxiv.org/abs/2606.25317v1) | Một action predictor dễ bỏ qua execution errors hoặc thiếu ngữ cảnh; muốn hệ thống online nhẹ. | Ensemble 4 GRU detectors: standard/error-sensitive, temporal contexts khác nhau; temporal-aware dynamic transform và voting theo prediction mismatch. | EgoPER error-segment F1@0.5: DTGL **20,9 → 21,6**; Table 1, PDF tr. 9. | Dễ liên hệ baseline GRU để học error-sensitive evidence, nhưng báo error khác phát completed. Hai dataset thủ tục vẫn dùng first-error-truncated protocol. Đọc sau GRU/MiniROAD và cùng PROVIA §III. |
| [A07 ESOM, 2024, bản v3/2025](../papers/additions/A07_2024_esom.pdf) — **memory tùy nhu cầu**; [arXiv](https://arxiv.org/abs/2411.16934v3) | Offline episodic retrieval cần giữ cả video; muốn truy hồi lần cuối thấy vật từ compact online memory. | Object discovery + tracking + memory, query image → response track trong quá khứ. | OVQ2D success **3,03 → 4,02%** so VideoAgent adapted baseline; **81,92% chỉ là oracle**; Table 1, PDF tr. 6. | Mượn memory/provenance/identity; không tự phát hiện task completion, cần query patch. Detector/tracker là nút thắt. Đọc sau MATR/P04 nếu cần object ownership. |
| [A08 WEM Framework, 2026](../papers/additions/A08_2026_wem_framework.pdf) — **đọc cuối/ý tưởng**; [arXiv](https://arxiv.org/abs/2610.00069v1) | Workplace video dài, dư thừa và khó lưu/truy hồi; muốn procedural memory có bằng chứng. | Multi-cue event segmentation; event cards chứa actor/action/object/pre–post state/confidence/provenance; cập nhật Work Environment Model. | **Chưa có benchmark định lượng**; §4 để evaluation cho future work, PDF tr. 4. | Hợp tư duy evidence-linked state memory, nhưng §3/Fig.1 nêu **offline batch**, không là model online đã kiểm chứng. Đọc sau OpenHOUSE/P04/PROVIA, không cần trước khi train. |
| [A09 State-Change Counterfactuals, 2025](../papers/additions/A09_2025_state_change_counterfactuals.pdf) — **nhánh state/representation**; [arXiv v6](https://arxiv.org/abs/2503.21055v6) | Học thứ tự chưa mô hình hóa cảnh thay đổi thế nào hoặc thất bại có thể trông ra sao. | LLM sinh before/after descriptions và counterfactual failure outcomes; clip/video contrastive learning với hard negatives. | EgoPER segmentation F1@0.5: HierVL **52,6 → 54,4**; Table 1, PDF tr. 6. | Hợp học phân biệt attempted/achieved; downstream TAS dùng ASFormer offline. Cần causal encoder/prefix-safe negatives và kiểm tra nhãn trạng thái, không chuyển cả-video context sang inference. Đọc sau P13/P14, ghép nhánh SPOC. |

## 3. Các điểm làm thay đổi roadmap

### 3.1. ActionSwitch là prerequisite cụ thể của OpenHOUSE

OpenHOUSE §3.3.1 dẫn **[18] ActionSwitch** cho state-emitting head và cross-entropy training. Đây là quan hệ sử dụng thành phần, mạnh hơn việc chỉ có cùng chủ đề. ActionSwitch §4.3 dùng simple stacked GRU theo OAD literature, phù hợp đọc sau MiniROAD. Roadmap mới chèn ActionSwitch trước OpenHOUSE; vẫn không bắt buộc đọc mọi nhánh overlap nếu dự án chỉ giữ một lượt.

### 3.2. VidParse: training-free không có nghĩa label-free hoặc không trễ

§3.4 lấy **training examples** để clustering/slicing micro-prototypes; §3.5 dùng **step-ordered annotations** để dựng graph. Có thể không cập nhật gradient nhưng vẫn có ngân sách nhãn và priors phải tính khi so baseline.

Boundary Eq.5 kiểm local peak với `Δ(t±k)`; §3.5 dùng **fixed-lag commitment** và cho phép sửa các dự đoán trong buffer vài giây. Đây có thể là thiết kế online có trễ hợp lệ nếu chỉ dùng prefix **tại lúc phát**; không được ghi timestamp phát bằng mốc boundary sớm hơn dữ liệu xác nhận. Cần tái lập xem k/lag thực là bao nhiêu, event nào đã final và độ trễ end-to-end. Không gắn nhãn “zero-delay” từ từ “online”.

Hard graph có thể giúp chống hallucinated transitions nhưng cũng có thể loại recovery/skip/step lạ. Đề xuất thử cùng visual features: no graph, hard graph và soft graph có error/repair branch. Chấm cả task-instance merge/split và false completion; không chỉ N-step transition score. N-step metric bổ sung chẩn đoán procedure, chưa thay interval matching hoặc emission latency.

### 3.3. ODAE giúp completion-event protocol, chưa xác nhận whole-task achievement

§3 dùng one-to-one point matching nhưng tolerance đối xứng **1–10 giây**, lấy trung bình mp-mAP. Vì vậy điểm có thể dung thứ phát sớm/trễ hơn yêu cầu ứng dụng. Evaluator dự án vẫn phải tách early false completion, deadline/timely recall và t_emit; không chỉ chép metric của bài. Đoạn mô tả unmatched GT có chỗ ghi nhầm “false positives”; khi triển khai cần đối chiếu công thức/code và giữ nghĩa FN/FP chuẩn.

Không lặp khẳng định “Mamba thắng mọi setting” từ abstract: Table 4 cho THUMOS14 TeSTra long/short memory **53,75**, cao hơn Mamba tốt nhất được bảng đó báo **42,12**. Gain trong Table 3 ở EK100 không bảo đảm một backbone tốt nhất cho mọi miền, cũng không đảm bảo RGB end-to-end real-time khi dùng optical flow.

### 3.4. Error/state/representation cần được chấm đúng objective

- **ESTANet:** §4.1 nói Assembly-101-O và EPIC-Tent-O kết thúc tại lỗi đầu. Không dùng gain ở đó như chứng minh whole-trial sau repair; EgoPER là setting khác. Mode-filter window **30 frame ở 10 FPS** cần audit trailing/centered và t_emit; số này không tự bằng delay 3 giây.
- **SPOC:** monotonic actionable → transformed hữu ích với thay đổi tiến dần; chưa mặc định hợp assembly có tháo ra/làm lại. Giữ pixel supervision/extra detectors trong ngân sách nhãn và compute. Nhánh goal-state của dự án vẫn phải quyết định bằng chứng nào đủ ở cấp mục tiêu đã chọn.
- **Counterfactuals:** Table 2 so HierVL có EDA **71,3 → 72,7**, nhưng AUC **66,2 → 60,5**. Không gọi là thắng mọi trục. LLM state descriptions/counterfactuals cần kiểm tra đúng vật thể/goal và hard negatives có thực tế không; đây là prior art representation, không thể coi “thêm state-change head” tự là ý tưởng mới.
- **DETACH:** §4 evaluation protocol đóng băng **sensor encoder** rồi linear classification. Không gán F1 đó cho RGB encoder hoặc cho temporal segmentation chỉ vì tựa đề có exocentric. “Online clustering” là thuật toán thành phần, không chứng minh toàn pipeline video causal.
- **ESOM:** dùng con số thực **4,02%** cùng memory/query time; oracle discovery/tracking chỉ phân tích bottleneck. Object identity trong compact memory hữu ích nhưng không thay raw-video buffer để xuất đầy đủ clip.
- **WEM:** event cards/provenance là thiết kế đáng học; chưa có kết quả để xếp nó cao hơn model thực nghiệm. Đề xuất causal hóa cần rolling normalization, prefix-safe fusion và quyết định emit; đó là thích nghi của dự án, không phải tính năng đã chứng minh của bài gốc.

## 4. Tuyến đọc sau khi bổ sung

1. **Định nghĩa:** P13 §3 + P14 intro; A01 ODAE formulation/metric để hiểu event end.
2. **Interval branch:** F03 lướt → F01 OAT → P18 MATR. P11 HAT vẫn là nhánh history tùy chọn, không prerequisite của MATR.
3. **OAD/hierarchy branch:** F02 MiniROAD → **A02 ActionSwitch** → P12 ProTAS (progress) → P03 OpenHOUSE. Chỉ hai quan hệ backbone/state head đã đối chiếu là cạnh kế thừa; ProTAS là nền khái niệm.
4. **Graph và state:** P12/P10 → **A03 VidParse**; F02/GRU → **A06 ESTANet**; đọc cùng **P19 PROVIA** để so quyền sửa prediction, priors, errors/repair và protocol. Đây là các hướng đối chiếu, không phải chuỗi nâng cấp code.
5. **Bằng chứng đạt goal:** P14/P13 → **A09 Counterfactuals + A04 SPOC**; nghiên cứu thêm branch trạng thái sản phẩm cho exo, chưa cần tái lập toàn bộ pretraining.
6. **Khi cần:** P18/P04 → A07 ESOM; có ambient sensors → A05 DETACH; cuối cùng A08 WEM để tổ chức memory/evidence. P01 OnPoint vẫn thêm sau khi nhãn là nút thắt.

Lộ trình và graph chính được cập nhật tại [reading_order.md](reading_order.md). Bộ A01–A09 lấp thêm literature về state evidence và structured decoding; **không còn phù hợp để mô tả những ý tưởng chung đó là khoảng trống chưa ai làm**. Câu hỏi cần kiểm chứng vẫn là hiệu quả ở đúng cấp toàn lượt, giữ ownership qua pause/repair và completion emission online trên exo, ở cùng nhãn/compute/latency.
