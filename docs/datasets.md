# Dataset cho định vị online từng lượt công việc — bản tạm

Phiên bản: **v0.1 — 2026-11-13 (Asia/Saigon)**. Có thể thay đổi sau khi xem dữ liệu và chạy pilot. Yêu cầu bài toán tham chiếu [problem.md](problem.md); tài liệu này không thay đổi yêu cầu đó và chưa chốt kiến trúc, FPS, độ phân giải hay tập benchmark cuối cùng.

## 1. Phạm vi và mức độ xác minh

Cần video liên tục để phát hiện **toàn bộ một lượt công việc nhiều bước**, bao gồm gián đoạn, và nhận biết hoàn thành trong lúc luồng đang chạy. Nhiều lượt có thể xuất hiện trong cùng video. Nhãn động tác, nhãn bước quy trình và nhãn lượt công việc là ba cấp khác nhau.

Quy ước đọc tài liệu:

- **Nguồn công bố:** thông tin từ trang dự án, paper, repo hoặc danh mục phát hành chính thức; dẫn nguồn tại từng bộ.
- **Người dùng xác nhận:** thông tin về Drive đã được cung cấp trong phiên làm việc.
- **Chưa kiểm tra:** nội dung file/nhãn cụ thể chưa mở trên Colab. Môi trường viết tài liệu này không mount Drive của người dùng.
- **Đề xuất:** cách chọn subset, đổi nhãn và xử lý video cho nghiên cứu; chưa được triển khai hoặc kiểm chứng.

Tình trạng dữ liệu của dự án:

| Dataset | Đã biết về bản trên Drive | Việc còn cần kiểm tra |
| --- | --- | --- |
| IKEA ASM | Người dùng đã cung cấp cây thư mục nguồn và báo giải nén xong | Cây bên trong thư mục đã giải nén, video thực có, schema nhãn và căn chỉnh thời gian |
| IndustReal | Đã có log bắt đầu tải nền; sau đó người dùng yêu cầu tải toàn bộ | Job đã hoàn tất chưa; những gói nào đã tải/giải nén thành công |
| Assembly101, FineAction, RepCount, HA4M, Breakfast | Repo có downloader; chưa có xác nhận đã tải xong | Quyền truy cập, phiên bản phát hành và nội dung file thực tế |

Không ghi số lượng video tải thành công từ số liệu paper. `--list-files` của một số adapter chỉ in đường dẫn công bố; không chứng minh đã truy cập được payload. Cách dùng CLI chi tiết ở [README](../README.md).

## 2. Ưu tiên nghiên cứu tạm thời

Đây là đánh giá phù hợp với yêu cầu dự án, không phải xếp hạng chất lượng dataset.

| Dataset | Điểm nên khai thác | Khoảng thiếu so với đầu ra cần có | Vai trò đề xuất |
| --- | --- | --- | --- |
| IKEA ASM | Lắp ráp nhiều thao tác, camera cố định; dữ liệu đã giải nén | Nhãn atomic action chưa xác định cả lượt; phải kiểm tra số lượt và bằng chứng hoàn thành | Pilot chính đầu tiên vì đã có dữ liệu |
| IndustReal | Quy trình, trạng thái lắp ráp, lỗi thực thi và hoàn thành bước | Hoàn thành bước chưa đồng nghĩa hoàn thành toàn công việc; góc nhìn đeo đầu | Pilot chính về dấu hiệu hoàn thành và sửa lỗi |
| Assembly101 | Thao tác lắp/tháo tự nhiên, nhiều góc và biến thể trình tự | Cần chọn mục tiêu, nhóm nhãn và kiểm tra lượt hoàn chỉnh | Mở rộng sau pilot; ưu tiên một góc |
| RepCount | Có ranh giới từng chu kỳ lặp | Chu kỳ vận động thường đơn giản hơn lượt công việc nhiều bước | Kiểm tra cơ chế tách nhiều lượt và khoảng nghỉ |
| FineAction | Nhiều đoạn hành động với start/end, nhiều lớp | Nhãn hành động chưa có mục tiêu hoàn thành công việc | Dữ liệu phụ cho học biểu diễn/định vị ranh giới |
| HA4M | Quy trình lắp ráp trong môi trường sản xuất mô phỏng | Cần nhãn cấp lượt; chọn modality để hạn chế dung lượng | Đối chứng công nghiệp sau khi kiểm tra quyền tải |
| Breakfast | Hoạt động nhiều bước trong bếp | Đổi miền; nhãn action unit chưa là nhãn lượt | Dữ liệu phụ nếu cần kiểm tra khả năng tổng quát |

**Chưa có cơ sở coi một bộ nào là benchmark khớp hoàn toàn.** Đặc biệt, khả năng phát hiện nhiều lượt trong một stream dài, video không có lượt hoàn thành và độ trễ online cần được kiểm tra riêng. Nếu mỗi file chỉ có một quy trình, nó vẫn hữu ích cho pilot nhưng chưa đủ chứng minh yêu cầu nhiều lượt liên tiếp.

## 3. IKEA ASM

### Dữ liệu và nhãn

**Nguồn công bố:** 371 mẫu lắp ráp, 48 người, 4 loại đồ nội thất; mỗi mẫu có 3 góc RGB và một luồng depth. Có 33 lớp hành động nguyên tử với mốc bắt đầu/kết thúc theo frame, cùng pose, segmentation/tracking vật thể và calibration. Nhãn hành động là cấp thao tác. [Trang dự án IKEA ASM](https://ikeaasm.github.io/).

**Người dùng xác nhận:** nguồn sau là shortcut Drive chỉ đọc, trỏ tới thư mục chia sẻ của tác giả:

```text
/content/drive/MyDrive/Datasets/ikea_asm_dataset_public/
├── data/
│   ├── ikea_asm_dataset_RGB_top.zip
│   ├── ikea_asm_dataset_RGB_multiview.zip
│   ├── ikea_asm_dataset_depth.zip
│   ├── all_depth_frames.tar.gz
│   ├── camera_params.zip
│   └── utility_files.zip
├── annotations/
│   ├── action_annotations.zip
│   ├── pose_annotations.zip
│   └── segmentation_tracking_annotation.zip
└── trained_models/
    └── ...
```

Cây này mô tả **archive nguồn**, chưa mô tả đường dẫn video bên trong. Kết quả adapter được ghi sang thư mục có quyền ghi `Datasets/IKEA_ASM/`; không ghi đè shortcut. Người dùng đã báo giải nén xong, nên ưu tiên đọc kết quả hiện có.

### Đề xuất xử lý

1. Đối chiếu archive đã giải nén với action annotations và utility files. Tạo nhóm theo lần quay gốc; các góc cùng mẫu nằm chung một split.
2. Dùng một góc RGB cho pilot; xem góc đó có thấy tay, vật thể và trạng thái hoàn thành không. Nếu có video nén thì đọc trực tiếp, chưa xuất toàn bộ thành ảnh.
3. Chọn rõ mục tiêu: chẳng hạn “lắp xong toàn bộ bàn”. “Gắn xong một chân bàn” chỉ là mục tiêu khác nếu được định nghĩa riêng; không đổi đơn vị để có nhiều mẫu lặp hơn.
4. Dùng các nhãn thao tác để tìm đoạn ứng viên, sau đó xem video để gán mốc bắt đầu/hoàn thành ở cấp mục tiêu. Ghi rõ nghỉ, làm lại, thiếu đầu/cuối và không đủ bằng chứng. Không lấy min/max tất cả nhãn rồi mặc định đó là một lượt hoàn thành.
5. Giữ cả chuẩn bị và hậu cảnh trước/sau lượt trong luồng đánh giá. Có thể tạo clip để xem/gán nhãn, nhưng stream đầu vào đánh giá vẫn giữ timeline gốc.

**Cần kiểm tra:** tên file nhãn và cách nối recording ID; FPS/thời gian của video đã giải nén; frame index bắt đầu từ 0 hay 1; end frame bao gồm hay loại trừ; số lượt thật trên mỗi recording; vật thể hoàn chỉnh có còn trong khung hình hay bị che khuất. Mốc hoàn thành cần dựa trên định nghĩa công việc và bằng chứng quan sát, không dựa vào file sắp hết.

## 4. IndustReal

### Dữ liệu và nhãn

**Nguồn công bố:** 84 video của 27 người, góc nhìn HoloLens 2. Ba nhóm nhãn/bài toán: action recognition (AR), assembly state detection (ASD), procedure step recognition (PSR). Có lỗi trình tự và lỗi thực thi; PSR xét hoàn thành bước đúng. Đây là thông tin gần mục tiêu nghiên cứu, nhưng vẫn cần chuyển từ bước sang lượt công việc. [Paper IndustReal](https://arxiv.org/html/2310.17323v1).

Cấu trúc bản ghi mà tác giả mô tả, rút gọn:

```text
recordings/{train,val,test}/<recording_id>/
├── rgb/                 # ảnh RGB JPG, tác giả ghi nhận 10 FPS
├── stereo_left/
├── stereo_right/
├── depth/
├── ambient_light/
├── gaze.csv
├── hands.csv
├── pose.csv
├── AR_labels.csv
├── OD_labels.json
├── PSR_labels.csv
├── PSR_labels_with_errors.csv
└── PSR_labels_raw.csv
```

Nguồn còn có gói `all_rgb_videos.zip` và `action_recognition_labels.zip`. Hai gói tiện xem RGB/AR không đại diện toàn bộ dữ liệu PSR. Bản ghi ảnh và bản video đóng gói cần kiểm tra tương ứng frame/timestamp. [Repo và mô tả cấu trúc](https://github.com/TimSchoonbeek/IndustReal), [bản phát hành 4TU v2](https://data.4tu.nl/datasets/b008dd74-020d-4ea4-a8ba-7bb60769d224/2).

**Adapter hiện tại:** `--part rgb` chọn video và AR labels; `train`, `val`, `test`, `recordings` chọn các gói bản ghi; `all` còn bao gồm weights/synthetic data. Archive chia đuôi `.zip.001/.zip.002` chỉ được lưu, chưa tự ghép/giải nén. Tải `all` xong không có nghĩa mọi payload đã dùng được.

### Đề xuất xử lý

1. Kiểm kê bản RGB trước, nối với nhãn bằng ID; dùng video có sẵn nếu kiểm chứng được timeline. Nếu cần dựng video từ `rgb/`, đọc frame ID/timestamp và kiểm tra frame thiếu thay vì chỉ sort chuỗi tên file.
2. Đọc nhãn PSR/ASD từ các gói bản ghi cần thiết. Ghi riêng nhãn hành động đang làm, trạng thái vật thể và sự kiện hoàn thành bước; không trộn chúng thành một nhãn end duy nhất.
3. Định nghĩa mục tiêu toàn quy trình hoặc một công việc con có kết quả cụ thể. Đối chiếu PSR với hình ảnh để gán `task_instance_id`, mốc bắt đầu, mốc kết thúc và trạng thái hoàn thành/bỏ dở/chưa rõ.
4. Với lỗi thực thi: tách “đã dừng thao tác”, “đã kết thúc lượt thực hiện” và “đạt kết quả đúng”. Giữ thông tin lỗi để phân tích, nhưng không tự thêm yêu cầu chấm chất lượng vào đầu ra chính.
5. Giữ split chính thức để đối chiếu; kiểm tra participant/recording nào nằm ở mỗi split. Các file chuyển mã, frame và nhãn của cùng recording phải đi cùng nhau.
6. Replay RGB theo thứ tự thời gian. PSR/ASD ground truth chỉ dùng để huấn luyện/đánh giá; nếu cần trạng thái vật thể lúc suy luận thì trạng thái đó phải được dự đoán từ dữ liệu đã tới.

**Cần kiểm tra:** cột và đơn vị timestamp trong từng CSV; nhãn PSR là thời điểm sự kiện hay khoảng; cách biểu diễn bước sai/sửa lại; mapping giữa MP4 đóng gói và ảnh gốc; video chứa assembly/maintenance nào, có đủ đầu/cuối và bao nhiêu lượt. Không giả định mỗi recording thành công chỉ vì có bước cuối được thực hiện.

## 5. Assembly101

### Dữ liệu và nhãn

**Nguồn công bố:** 4.321 video lắp/tháo 101 loại đồ chơi; 8 camera cố định và 4 camera đeo đầu. Có nhãn hành động fine/coarse và các biến thể thao tác tự nhiên. Số video nhiều góc không phải số thử nghiệm độc lập. [Paper Assembly101](https://arxiv.org/abs/2203.14712).

Nguồn phân phối đã chuyển sang [Hugging Face của nhóm tác giả](https://huggingface.co/datasets/cvml-nus/assembly101), theo [thông báo trên trang dự án](https://assembly-101.github.io/). Cần hoàn tất điều kiện truy cập nếu được yêu cầu.

Cấu trúc camera được tác giả mô tả:

```text
recordings/<recording_id>/
├── C10095_rgb.mp4        # một camera cố định; CLI gọi là v1
├── C10115_rgb.mp4        # các camera cố định khác
├── ...
└── HMC_*_mono10bit.mp4   # camera đeo đầu, đơn sắc
```

Có annotations, hand poses và features tính sẵn; định dạng cụ thể cần kiểm tra theo bản phát hành. [Repo tải chính thức](https://github.com/assembly-101/assembly101-download-scripts).

### Đề xuất xử lý

1. Pilot với annotations và một camera cố định, chẳng hạn `--part videos --view v1`; xem trước độ che khuất rồi mới quyết định góc. Không mặc định video đeo đầu cũng là RGB.
2. Nhóm toàn bộ view theo recording trước khi chia dữ liệu. Xem nhãn fine/coarse có dùng chung mốc frame với các view hay cần đồng bộ/offset.
3. Xác định lượt lắp và lượt tháo theo mục tiêu đã chọn; không gộp thành một lượt chỉ vì nằm cùng file. Giữ các bước sửa lỗi bên trong lượt nếu công việc chưa hoàn thành.
4. Dùng coarse labels để tìm vùng ứng viên và fine labels để hiểu diễn biến. Gán thêm ranh giới lượt khi nguồn chưa có; không đồng nhất một coarse segment với hoàn thành toàn bộ đồ chơi.
5. Giữ video nén, decode theo chunk. Features TSM/DINOv2 có thể dùng để thăm dò, nhưng chỉ đưa vào kết quả online sau khi kiểm tra cửa sổ trích feature và timestamp frame cuối đã sử dụng.

**Cần kiểm tra:** schema nhãn, split, lỗi/corrections trong subset, offset giữa camera, đoạn thiếu/cắt và số mục tiêu đạt được mỗi recording. Chưa quyết định dùng toàn bộ dữ liệu đa góc.

## 6. RepCount

### Dữ liệu và nhãn

**Nguồn công bố:** 1.451 video, 19.280 chú giải; nhãn chứa số lần lặp và vị trí bắt đầu/kết thúc chu kỳ. Part-A có 1.041 video từ YouTube, gồm train/val/test; Part-B quay hoạt động thể dục, dùng để kiểm tra tổng quát. Nguồn có đường dẫn OneDrive/Baidu. [Trang RepCount](https://svip-lab.github.io/dataset/RepCount_dataset.html).

**Adapter hiện tại:** nhận archive đã có qua `--source-dir` hoặc URL file thật qua `--url`; không tự đăng nhập portal. Schema file nhãn và layout archive thực tế chưa được kiểm tra ở Drive.

### Đề xuất xử lý

1. Giữ video và nhãn chu kỳ dạng khoảng; nếu gặp density map của baseline thì tìm nhãn gốc, vì density/count không đủ kiểm tra start/end chính xác.
2. Đổi frame sang giây theo đúng bản video được cung cấp; kiểm tra clip đã được tác giả cắt so với nguồn YouTube. Không tải một bản khác rồi dùng nguyên index nhãn.
3. Dùng để kiểm tra tách nhiều lượt, nghỉ và báo lặp. Mỗi chu kỳ chỉ đại diện một công việc của dự án nếu mục tiêu được định nghĩa đúng ở cấp đó.
4. Giữ các khoảng không có chu kỳ. Không nén toàn video về một số frame cố định bằng cách lấy mẫu xuyên suốt tương lai khi giả lập online; không đưa tổng count GT vào bộ suy luận.
5. Giữ Part-B làm đối chứng tổng quát theo protocol nguồn; kiểm tra trùng nguồn trước khi tạo split phụ.

**Giới hạn:** định vị tốt chu kỳ squat/chống đẩy chưa chứng minh hiểu công việc có nhiều bước và kết quả vật thể. Đề xuất dùng làm benchmark phụ, chưa chọn làm dữ liệu chính.

## 7. FineAction

### Dữ liệu và nhãn

**Nguồn công bố:** 16.732 video chưa cắt theo từng instance, 103.324 đoạn thuộc 106 lớp; có nhiều lớp hành động chồng thời gian. Đây là TAL fine-grained, không phải nhãn hoàn thành một công việc nhiều bước. [Paper FineAction](https://arxiv.org/html/2105.11107v3).

Tác giả công bố trên OpenXLab: raw video, `annotations_gt.json`, features I3D/I3D-100 và VideoMAE. [Repo chính thức và đường dẫn tải](https://github.com/Richard-61/FineAction).

**Adapter hiện tại:** chọn `annotations`, `videos`, `i3d`, `i3d-100`, `videomae-h`, `videomae-g`, `all`; chạy SDK OpenXLab trong môi trường riêng. Có thể dùng archive mounted/URL trực tiếp. Bố trí thư mục con do SDK tạo cần kiểm tra sau tải; không mặc định video đã nằm sát `raw/`.

### Đề xuất xử lý

1. Kiểm tra JSON thực tế để lấy video ID, split, tên lớp, khoảng thời gian và đơn vị nhãn. Giữ nguyên nhiều interval chồng lấn; không ép thành một nhãn duy nhất ở mỗi frame.
2. Chọn subset bằng tiêu chí công bố trước: công việc phù hợp, một người chính, đủ quan sát, ít chuyển cảnh. Kiểm tra thủ công subset; tên lớp tự nó chưa đảm bảo các tiêu chí này.
3. Dùng nhãn sẵn cho học/đánh giá ranh giới hành động phụ. Muốn đánh giá đầu ra chính thì cần gán thêm mục tiêu, nhóm các bước và xác nhận hoàn thành trên video.
4. Giữ video untrimmed và background. Cảnh cắt dựng, thiếu đầu/cuối hoặc nhiều người phải có cờ để phân tích; loại trừ theo quy tắc thay vì ngầm coi mọi video phù hợp luồng camera.
5. Dùng raw video cho pipeline causal đã kiểm tra. Feature có sẵn chưa mặc định dùng được online: cần biết frame/window đầu-cuối, stride, cách pooling và thông tin tương lai đã dùng.

**Cần kiểm tra:** payload nhãn thực tế, test labels có công khai ở bản được cấp hay không, class mapping, frame/time alignment và nguồn trùng lặp. Kết quả TAL theo nhãn nguồn phải được báo riêng với kết quả cấp lượt công việc.

## 8. HA4M

### Dữ liệu và nhãn

**Nguồn công bố:** 217 video, 41 người lắp bộ truyền bánh răng, 12 loại thao tác. Dữ liệu gồm RGB, depth, IR, RGB aligned, point cloud, skeleton; toàn bộ khoảng 4,1 TB. Cấu trúc `IDUnVm/` có `Labels.txt` và các thư mục modality. Nhãn từng frame gồm frame number, action ID, repetition index. Có “don't care”; không xem toàn bộ nhóm này là nghỉ. [Bài mô tả HA4M](https://www.nature.com/articles/s41597-022-01843-z).

**Adapter hiện tại:** nhận `--url` file được cấp từ nguồn; không tự liệt kê/đăng nhập portal. Cần đối chiếu bản trên [trang dự án HA4M](https://baltig.cnr.it/ISP/ha4m) với phiên bản mô tả trong paper.

### Đề xuất xử lý

1. Lấy RGB + nhãn của một subset trước, chưa cần tải toàn bộ point cloud/depth. Kiểm tra archive thực tế có tách được modality hay phải chọn gói lớn.
2. Nếu dữ liệu là ảnh, dựng video/proxy từ timestamp trong tên file khi có, kèm bảng ánh xạ frame nguồn. Không sort tên theo chữ rồi tự gán một FPS bất kỳ.
3. Nhóm theo subject và trial. Đề xuất thêm phép đánh giá khác người sau khi kiểm tra protocol nguồn; không gọi split tự tạo là split chính thức.
4. Gán ranh giới hoàn thành toàn bộ bộ truyền nếu đó là mục tiêu; giữ các thao tác lặp bên trong. Repetition index của một action chưa phải ID lượt công việc.
5. Xem riêng đoạn “don't care”, lần đặt/nhả vật thể và che khuất để xác định dấu hiệu hoàn thành có quan sát được hay không.

**Cần kiểm tra:** phiên bản/cohort thực tải, độ đầy đủ RGB/nhãn, timestamp device và frame index, số lượt trong mỗi trial, dung lượng subset thực tế. Chưa xem việc một action cuối kết thúc là bằng chứng đủ cho hoàn thành toàn quy trình.

## 9. Breakfast

### Dữ liệu và nhãn

**Nguồn công bố:** 52 người, 18 bếp, khoảng 77 giờ, 10 hoạt động và 48 action units. Bản phân phối của Serre Lab có `segmentation_coarse.tar.gz`, `segmentation_fine.tar.gz`; `breakfast_data.tar.gz` là Fisher-vector features, không phải raw video. [Dataset card của Serre Lab](https://huggingface.co/datasets/Serrelab/breakfast-actions).

**Adapter hiện tại:** nhãn/features tải từ Hub; video dùng archive Drive gốc. Khả năng truy cập/quota cần kiểm tra lúc tải. Tên gói và cách chạy ở [README](../README.md).

### Đề xuất xử lý

1. Kiểm tra nhãn coarse/fine với đúng bản video; đọc đơn vị thời gian/frame trong XML/text. Không kết luận đã có video từ việc tải được gói features.
2. Chọn một loại công việc chuẩn bị món/đồ uống, xác định trạng thái đầu ra và phạm vi dọn dẹp/đặt món. Dùng action units làm nhãn phụ rồi bổ sung nhãn lượt.
3. Kiểm tra người, session và camera; các bản quay cùng lần thực hiện phải cùng split. Giữ protocol nguồn khi làm đối chứng.
4. Giữ cả nghỉ và thao tác ngoài mục tiêu. Ưu tiên decode video nén; chưa dùng Fisher features làm đầu vào cho benchmark online nếu chưa xác minh cách tính và mốc quan sát.

**Giới hạn:** hữu ích về cấu trúc nhiều bước, nhưng khác bối cảnh công nghiệp và chưa bảo đảm nhiều lượt trong một stream. Để sau các pilot chính.

## 10. Quy trình xử lý video chung — đề xuất, chưa triển khai

### 10.1. Kiểm kê trước khi chuyển đổi hàng loạt

Đọc một mẫu nhỏ trước rồi mới chạy toàn bộ. Mỗi dataset cần báo cáo tối thiểu:

| Nhóm | Thông tin cần ghi |
| --- | --- |
| Nguồn | Dataset/version, archive, checksum khi có, revision/URL, ngày tải, điều kiện sử dụng của bản phát hành |
| Danh tính | Recording/trial ID, người, mục tiêu, góc camera, nhóm đồng bộ và split gốc |
| Media | Đường dẫn tương đối, codec, kích thước, duration, frame count, time base/PTS, FPS danh nghĩa và biến thiên, audio có hay không |
| Nhãn | File nguồn, lớp, cấp action/step/task, đơn vị thời gian, index base, quy tắc end inclusive/exclusive, mức bao phủ nhãn |
| Chất lượng | Lỗi decode, frame thiếu/trùng, mất đồng bộ, chuyển cảnh, che khuất, nhiều người, thiếu đầu/cuối |

Không gán background cho mọi vùng không có nhãn: có thể là chưa được annotate. Không sửa/loại bản ghi âm thầm; lưu lý do và số lượng trước/sau lọc.

### 10.2. Giữ timeline và giảm I/O trên Drive

- Giữ raw/archive và kết quả giải nén gốc. Tạo dữ liệu dẫn xuất riêng theo phiên bản; không giải nén lại IKEA đã xong chỉ để đổi cấu trúc nghiên cứu.
- Nếu có MP4/AVI phù hợp thì đọc trực tiếp; decode theo chunk trong lúc trích feature hoặc huấn luyện. Chưa xuất hàng triệu JPEG trên Drive mặc định.
- Nếu chỉ có ảnh, kiểm tra thứ tự số/timestamp và dựng video khi cần. Giữ mapping từ frame nguồn sang thời gian video; frame thiếu hoặc timestamp không rõ phải được ghi nhận.
- Chưa chốt chung 15/30 FPS hoặc 224/256 pixels. Pilot so sánh độ rõ của vật thể nhỏ, tốc độ decode và độ trễ trước khi giảm chất lượng.
- Nếu tạo proxy hoặc đổi FPS, lưu mapping timestamp/PTS và cấu hình chuyển đổi. Với VFR, không chỉ dùng `frame_index / FPS_trung_bình`. Nhãn dẫn xuất nên dùng giây trên timeline đã chuẩn hóa, đồng thời giữ tọa độ nguồn để truy vết.
- Chưa crop cố định bàn tay/vật thể nếu làm mất dấu hiệu sản phẩm hoàn tất. Chỉ thêm ROI sau khi kiểm chứng; giữ bản toàn khung để đối chiếu.
- Chưa cần optical flow/depth/pose hàng loạt. RGB một góc là pilot đề xuất, không phải yêu cầu tất cả mô hình tương lai.

### 10.3. Tạo nhãn cấp lượt và dữ liệu đánh giá

Nhãn nguồn được giữ nguyên ở một lớp; nhãn dẫn xuất ở lớp khác. Dự kiến mỗi lượt có recording ID, task definition/version, instance ID, start/end, trạng thái completed/aborted/unknown/ongoing, cờ mất đầu/cuối, nguồn nhãn và độ bất định. Đây là **schema dự kiến**, chưa phải định dạng parser đã có. Chi tiết ranh giới theo [problem.md](problem.md).

Một nhãn ứng viên suy từ “bước cuối” phải được kiểm tra bằng video trước khi dùng như ground truth. Có thể khởi đầu bằng gán nhãn thủ công một tập nhỏ đa dạng, nhờ người thứ hai kiểm tra các ca mơ hồ và đo chênh lệch mốc. Xem cả ví dụ thành công, bỏ dở, sửa lỗi và nghỉ; không chỉ chọn video dễ.

Chia recording/subject/view group trước khi sinh window/clip/feature. Giữ split gốc để so sánh paper; split bổ sung phải có tên và protocol riêng. Bản chuyển mã, các view và các clip chồng lấn của cùng trial không đi sang các tập khác nhau.

Nếu thiếu stream nhiều lượt, ghép các recording chỉ để kiểm tra kỹ thuật hoặc augmentation có đánh dấu. Vết cắt, đổi nền và việc mỗi file đều kết thúc bằng hoàn thành có thể tạo shortcut. Kết quả trên video ghép phải báo riêng; cần dữ liệu liên tục tự nhiên trước khi kết luận đáp ứng yêu cầu ứng dụng.

### 10.4. Dùng video đã quay để đánh giá online

1. Phát lại video/frame theo thứ tự thời gian, chunk chỉ chứa dữ liệu đã tới. Không đưa tổng duration, số lượt cuối cùng hoặc EOF vào quyết định hoàn thành.
2. Feature ở mỗi lần phát có cửa sổ xác định và mốc frame cuối đã đọc. Có thể dùng clip encoder trên cửa sổ quá khứ; timestamp “có sẵn” của feature phải là cuối cửa sổ, không phải tâm cửa sổ.
3. Audit toàn pipeline: lấy mẫu xuyên toàn video, pooling/normalization theo toàn chuỗi, smoothing hai chiều, nội suy dùng frame tương lai và hậu xử lý chờ hết video đều cần loại bỏ hoặc ghi đúng thời điểm dữ liệu thực có sẵn.
4. Giữ state của model theo recording khi replay; window không tự trở thành stream mới. Reset ở ranh giới phiên thật hoặc theo protocol công bố. Ground truth tương lai chỉ được evaluator đọc, không đi vào model.
5. Log riêng mốc ranh giới dự đoán và thời điểm phát quyết định; giữ video lịch sử đủ để xuất toàn lượt. Báo chất lượng interval, bỏ sót/báo nhầm/lặp, độ trễ hoàn thành và tốc độ xử lý.
6. Nếu chưa có ngân sách latency/phần cứng, báo đường đánh đổi theo cấu hình; chưa tự đặt một ngưỡng rồi gọi đó là yêu cầu đã chốt.

Trích feature trước để chạy thử không tự gây vi phạm causal. Điều cần chứng minh là **mỗi feature chỉ dùng frame nào và sớm nhất có thể cung cấp lúc nào**. Đánh giá tốc độ hệ thống thực phải tính cả decode/trích feature, không chỉ temporal head.

### 10.5. Cấu trúc dẫn xuất dự kiến trên Drive

```text
/content/drive/MyDrive/Datasets/<Dataset>/
├── raw/                         # tải về; layout chi tiết tùy adapter
├── extracted/                   # giải nén, có thể còn nhiều cấp thư mục
├── jobs/                        # log/status job nếu chạy nền
└── processed/v0/                # ĐỀ XUẤT; CLI hiện chưa tạo phần này
    ├── manifests/
    ├── annotations/
    ├── splits/
    ├── proxies/                 # tùy chọn, không bắt buộc chuyển mã
    └── features/                # tùy chọn, kèm cấu hình causal/timestamp
```

Nguồn mounted như shortcut IKEA có thể nằm ngoài cây đích này; không cần copy lại archive. Mọi dẫn xuất bền vững vẫn lưu ở `MyDrive/Datasets`. Chưa có command `preprocess`/`build-manifest` trong repo; đây là bố trí để xem xét sau pilot.

## 11. Pilot và điều kiện sửa bản tạm

Thứ tự đề xuất:

1. **IKEA hiện có:** kiểm kê một số recording đa dạng; xác nhận cách nối video–nhãn và khả năng quan sát mục tiêu. Gán thử lượt công việc trên timeline gốc.
2. **IndustReal:** đối chiếu bản RGB với PSR của các bản ghi tương ứng, xem ca thành công/lỗi/sửa lại; so sánh bằng chứng hoàn thành với IKEA.
3. **Chốt quyết định dữ liệu sau hai pilot:** đơn vị công việc có khả thi không, cần bổ sung nhãn bao nhiêu, có đủ nhiều lượt liên tiếp/background/bỏ dở không, tài nguyên xử lý có đáp ứng không.
4. **Mở rộng có mục đích:** RepCount cho nhiều chu kỳ, FineAction cho ranh giới phụ; Assembly101/HA4M/Breakfast khi cần kiểm tra một giả thuyết cụ thể. Chưa tải/xử lý tất cả chỉ vì đã có adapter.

Sau pilot, cập nhật tài liệu bằng kết quả kiểm tra: tree và schema thực tế, số recording khả dụng sau lọc, phân bố thời lượng/số lượt/gián đoạn, tỷ lệ quan sát được hoàn thành, nhãn cần bổ sung, protocol split và chi phí lưu trữ/compute. Từ đó mới viết parser/tiền xử lý riêng cho từng dataset và runner chung nếu cần.

Các quyết định **để mở**: công việc/goal cụ thể, subset cuối, dùng một hay nhiều camera, FPS/resolution, backbone và feature, mức nhãn thủ công, ngân sách latency, nhu cầu thu thêm video liên tục. Bản v0.1 là ghi chú nghiên cứu có thể sửa, không phải cam kết mọi dataset đều phù hợp.
