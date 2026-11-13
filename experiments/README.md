# Thí nghiệm trực quan

## I3D

Mở [`i3d.html`](i3d.html) bằng trình duyệt. Trang là một file HTML độc lập, chạy offline, không cần cài package hoặc tải model weights. Nếu muốn mở qua HTTP, chạy từ thư mục repo:

```bash
python -m http.server 8000
```

Sau đó truy cập `http://localhost:8000/experiments/i3d.html`.

Các phần tương tác:

- Conv2D so với Conv3D trên video tổng hợp: đổi hướng chuyển động, vị trí patch, frame và kernel thời gian; các đáp ứng được tính trực tiếp trong JavaScript.
- Inflation: lặp kernel 2D, bật/tắt chia N để kiểm tra đáp ứng trên video đứng yên.
- Shape explorer: clip 32/64/96 frame qua I3D, các nhánh Inception, classification head gốc và nhánh trích feature bằng pooling không gian.
- RGB/flow, cửa sổ quanh tâm so với chỉ quá khứ, thời điểm thực sự đủ đầu vào cho dự đoán online.
- Năm câu kiểm tra với giải thích ngay sau mỗi câu trả lời.

Kernel chuyển động nhỏ là ví dụ tự thiết kế, không phải trọng số I3D. Đây là mô phỏng để giải thích phép tính, không phải inference hoặc benchmark. Timeline online minh họa quy tắc truy cập frame; không biểu diễn receptive field chính xác của toàn bộ mạng. Nhánh spatial pooling để giữ chuỗi feature là lựa chọn ứng dụng thêm, được phân biệt với classification head gốc ngay trong trang.

Nguồn: [paper I3D, CVPR 2017](https://arxiv.org/abs/1705.07750), [mã I3D chính thức của Google DeepMind](https://github.com/google-deepmind/kinetics-i3d/blob/master/i3d.py).
