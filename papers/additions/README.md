# 9 paper bổ sung từ danh sách người dùng

Ngày kiểm tra **2026-11-13**. Danh sách 13 link gồm **4 bài trùng và 9 bài mới**; 9 PDF mới đã lưu tại đây, giữ nguyên nội dung. Quyền tác giả/điều kiện sử dụng theo nguồn gốc. Các bản arXiv được cố định phiên bản để tái kiểm tra; không lưu text trích xuất vào repo.

Xem [bảng đối chiếu, vấn đề/motivation/giải pháp/kết quả và mức phù hợp](../../docs/paper_additions.md), [roadmap cập nhật](../../docs/reading_order.md), [manifest có nguồn/checksum và audit 13 link](manifest.json). Số liệu là tác giả báo cáo; chưa tái lập.

| ID / PDF | Phiên bản đã tải | Vai trò và ưu tiên đọc |
| --- | --- | --- |
| [A01 — Online Detection of End of Take and Release Actions from Egocentric Videos](A01_2025_online_action_end.pdf) | VISAPP 2025 publisher PDF; DOI 10.5220/0013249700003912 | Đọc sớm: online endpoint formulation, one-to-one point evaluation. |
| [A02 — ActionSwitch: Class-agnostic Detection of Simultaneous Actions in Streaming Videos](A02_2024_actionswitch.pdf) | arXiv 2407.12987 **v1**, 2024; ngoại lệ bài nền | Đọc trước OpenHOUSE: state-emitting head, instance separation và conservative decoding. |
| [A03 — VidParse: Online Parsing of Egocentric Procedures Like a Pro](A03_2026_vidparse.pdf) | arXiv 2608.27562 **v2**, 2026; sửa averaging GTEA | Đọc sớm sau ProTAS/OnlineTAS: training-free graph decoding; audit nhãn/prototypes/fixed lag. |
| [A04 — SPOC: Spatially-Progressing Object State Change Segmentation in Video](A04_2025_spoc.pdf) | arXiv 2503.11953 **v2**, 2025 | Nhánh state evidence: pixel actionable/transformed; chưa là streaming interval detector. |
| [A05 — DETACH: Decomposed Spatio-Temporal Alignment for Exocentric Video and Ambient Sensors with Staged Learning](A05_2025_detach.pdf) | arXiv 2512.20409 **v1**, 2025 | Có điều kiện ambient sensors; downstream đánh giá sensor representation. |
| [A06 — ESTANet: Efficient Online Error Detection in Procedural Videos via Prediction Inconsistency](A06_2026_estanet.pdf) | arXiv 2606.25317 **v1**, 2026 | Nhánh online error/state: ensemble GRU; đối chiếu protocol với PROVIA. |
| [A07 — Online Episodic Memory Visual Query Localization with Egocentric Streaming Object Memory](A07_2024_esom.pdf) | arXiv 2411.16934 **v3**, 2025; first submission 2024 | Nhánh object memory nếu cần identity/provenance, không là completion detector. |
| [A08 — A Framework for Egocentric and Exocentric Procedural Understanding via Temporal Segmentation and Semantic Abstraction](A08_2026_wem_framework.pdf) | arXiv 2610.00069 **v1**, 2026 | Đọc cuối: offline conceptual WEM/event cards; chưa báo benchmark định lượng. |
| [A09 — What Changed and What Could Have Changed? State-Change Counterfactuals for Procedure-Aware Video Representation Learning](A09_2025_state_change_counterfactuals.pdf) | arXiv 2503.21055 **v6**, 2025 | Nhánh representation/state evidence; kiểm tra causal adaptation và mixed metric gains. |

Các bản trùng giữ nguyên ở tập chính: **P18 MATR, P11 HAT, P12 ProTAS, P10 OnlineTAS**. Riêng IEEE được khớp theo tên đầy đủ do người dùng xác nhận, vì metadata trực tiếp bị chặn. Tập bổ sung A01–A09 và ba bài nền F01–F03 tách riêng với map P01–P23; chúng đã được đưa vào roadmap, không thay ID cũ.
