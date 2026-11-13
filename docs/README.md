# Tài liệu dự án

| Tài liệu | Nội dung | Trạng thái |
| --- | --- | --- |
| [problem.md](problem.md) | Yêu cầu, định nghĩa lượt công việc, ràng buộc online/exocentric và cách đánh giá | Đã hoàn tất bước mô tả hiện tại; cập nhật góc nhìn theo xác nhận bổ sung. Các câu hỏi mở vẫn cần dữ liệu để trả lời. |
| [datasets.md](datasets.md) | Bảng tóm tắt nội dung/góc nhìn/phần thiếu/việc cần làm, cùng ghi chú xử lý video từng dataset | Bản tạm v0.3; cần kiểm tra file thực tế và sửa sau pilot. |
| [paper_map.md](paper_map.md) | Graph 8 nhóm paper, quan hệ với thành phần và ma trận 23 bài × 9 thành phần; nguồn/bằng chứng và phần còn thiếu | Bản phân loại v0.1; N/R theo setting gốc, chưa tái lập hoặc chứng minh novelty. |
| [reading_order.md](reading_order.md) | TAS survey đọc định hướng, lộ trình từ nền tảng, graph phát triển và nhánh đọc thêm | Đối chiếu method/related work; 4 PDF nền bổ sung và A01–A09, không gán quan hệ kế thừa chỉ từ citation/baseline. |
| [paper_additions.md](paper_additions.md) | Đối chiếu 13 link: 4 trùng/9 mới; bảng phân tích, kết quả, giới hạn causal và vị trí đọc cho A01–A09 | Đã tải PDF phiên bản cố định; roadmap tích hợp, map P01–P23 giữ phạm vi gốc. |
| [literature_review.md](literature_review.md) | 23 paper: bảng vấn đề/motivation/giải pháp/kết quả/mức đáp ứng, phân tích kỹ thuật, khoảng trống và giả thuyết cải tiến | Bản nghiên cứu v0.2; PDF và metadata trong [papers/](../papers/README.md), chưa tái lập model. |
| [related_work_and_evaluation.md](related_work_and_evaluation.md) | PROVIA, WARI/SMS, range metrics, unseen views; protocol, phản ví dụ evaluator và ảnh hưởng tới novelty | Bản tạm v0.1; phân biệt kết quả paper với thiết kế đề xuất của dự án. |
| [training_pipeline.md](training_pipeline.md) | Dataset/feature extraction, causal model, loss, optimizer, trainer, resume và evaluation CLI trên Colab | Pipeline v0 có smoke/behavioral tests; dữ liệu thật cần manifest nhãn cấp lượt đã kiểm tra. |
| [adding_dataset.md](adding_dataset.md) | Cách thêm downloader riêng và đăng ký với runner | Hướng dẫn kỹ thuật. |

Hướng dẫn mount Drive, tải/giải nén, resume và chạy nền nằm tại [README của repo](../README.md). Khảo sát dataset chưa phải pipeline tiền xử lý đã triển khai; không dùng các đề xuất trong đó như quyết định thực nghiệm đã chốt.
