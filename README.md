# VideoSegmentation

Tải dataset nghiên cứu video trực tiếp vào **Google Drive** từ **Google Colab**. Mỗi dataset có một downloader riêng; `download.py` chỉ chọn và chạy downloader tương ứng.

Mặc định lưu vào `/content/drive/MyDrive/Datasets/<tên_dataset>`. Không cần tải dataset về máy rồi upload lại.

## Colab: mount → clone → chạy CLI

[Mở notebook trên Colab](https://colab.research.google.com/github/khaihoang004/VideoSegmentation/blob/main/notebooks/colab_download.ipynb)

Mount Drive trong **cell Python**, mỗi phiên Colab một lần:

```python
from google.colab import drive
drive.mount('/content/drive')
```

Clone và cài công cụ:

```python
!git clone https://github.com/khaihoang004/VideoSegmentation.git /content/VideoSegmentation
%cd /content/VideoSegmentation
%pip install -q -e .
!python download.py --list
```

Nếu đã clone trong phiên này, dùng `!git pull --ff-only` trong thư mục repo. Khi Colab reset, mount và clone/cài lại; dataset trên Drive vẫn còn. Không mount bằng `!python`: bước này cần chạy trong kernel notebook để hiện yêu cầu cấp quyền.

## Chọn dataset

```bash
python download.py --list
python download.py industreal --help
python download.py industreal --part rgb --list-files
python download.py industreal --part rgb --extract
```

Trong cell Colab, thêm `!` trước lệnh CLI. Có thể dùng tương đương `python -m videosegmentation ...` hoặc `videoseg ...` sau khi cài đặt.

| Dataset | Downloader | Nguồn và cách xử lý |
| --- | --- | --- |
| `industreal` | `downloaders/industreal.py` | Đọc danh mục API 4TU, chọn gói RGB/labels/train/val/test, tải từng file, kiểm tra kích thước và MD5 từ nhà phát hành |
| `assembly101` | `downloaders/assembly101.py` | Repo Hub chính thức `cvml-nus/assembly101`; chọn annotations/videos/features/poses và góc camera |
| `ikea_asm` | `downloaders/ikea_asm.py` | Mặc định giải nén archive từ Drive đã mount; tùy chọn tải gói của nhà phát hành |
| `breakfast` | `downloaders/breakfast.py` | Annotations/features trên Hub; raw video dùng link Drive riêng, có thể bị quota |
| `ha4m` | `downloaders/ha4m.py` | Nhận URL file trực tiếp từ cổng nguồn; chưa tự đăng nhập/liệt kê toàn bộ ownCloud hoặc ScienceDB |
| `repcount` | `downloaders/repcount.py` | Archive trên Drive đã mount hoặc URL archive trực tiếp |
| `fineaction` | `downloaders/fineaction.py` | CLI OpenXLab chính thức; hỗ trợ archive trên Drive hoặc URL trực tiếp |

Mặc định IndustReal/Assembly101/Breakfast/FineAction chọn gói **nhãn**; video chỉ được tải khi chọn `--part` tương ứng. IKEA tự nhận shortcut `/content/drive/MyDrive/Datasets/ikea_asm_dataset_public`; có thể đổi bằng `--source-dir` hoặc chọn rõ `--source download`. HA4M cần `--url`; RepCount cần `--source-dir` hoặc `--url`. `--list-files` không tải payload: tùy nguồn, nó hiển thị danh mục thực tế hoặc các gói/đường dẫn nguồn được công bố.

### IndustReal

```python
# Xem file RGB + action labels.
!python download.py industreal --part rgb --list-files

# Tải RGB + action labels.
!python download.py industreal --part rgb --extract

# Bản ghi đầy đủ của một split, có các modality và nhãn đi kèm.
!python download.py industreal --part train --list-files
!python download.py industreal --part train --extract

# Chọn một file theo tên/glob, ghi đè lựa chọn --part.
!python download.py industreal --include 'action_recognition_labels.zip' --extract
```

Các `--part`: `labels` (mặc định), `rgb`, `train`, `val`, `test`, `recordings`, `all`. Gói RGB/action labels không thay thế toàn bộ nhãn procedure-step và dữ liệu đa phương thức trong các bản ghi đầy đủ. Danh mục theo phiên bản hiện hành của API nhà phát hành; runner in phiên bản record trước khi tải. `--part all` bao gồm cả các gói khác như weights/synthetic data, không chỉ video.

### Assembly101

```python
!python download.py assembly101 --part annotations --list-files
!python download.py assembly101 --part annotations

# Chỉ video góc cố định v1; chưa tải các góc còn lại.
!python download.py assembly101 --part videos --view v1 --list-files
!python download.py assembly101 --part videos --view v1

# Chọn file/pattern trực tiếp nếu chỉ cần một recording.
!python download.py assembly101 --include 'recordings/RECORDING_NAME/C10095_rgb.mp4'
```

`--view`: `all`, `fixed`, `egocentric`, `v1`…`v8`, dùng với `--part videos`. `--include`/`--exclude` có thể lặp; khi có `--include`, adapter dùng các pattern đó thay cho `--part`/`--view`. `--revision <commit_SHA>` cố định phiên bản Hub; mặc định `main`. `--workers` mặc định 2.

Repo Assembly101 trên Hub có kiểm soát truy cập: đăng nhập, chấp nhận điều khoản tại nguồn rồi cấp token đã được quyền truy cập. Dùng Colab Secrets, không ghi token vào code:

```python
import os
from google.colab import userdata
os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN')
```

### IKEA ASM

```python
!python download.py ikea_asm --list-files

# Shortcut đã có tại MyDrive/Datasets/ikea_asm_dataset_public: chỉ cần chạy.
!python download.py ikea_asm

# Đổi thành đường dẫn thư mục hoặc shortcut trên Drive của bạn.
!python download.py ikea_asm --source-dir '/content/drive/MyDrive/Datasets/ikea_asm_dataset_public' --list-files

# Chọn góc khác, nhãn hành động và utility files.
!python download.py ikea_asm --part rgb-multi --part annotations --part utilities

# Chỉ xem các gói depth, chưa giải nén.
!python download.py ikea_asm --part depth --part depth-frames --list-files

# Tùy chọn: tải gói của nhà phát hành khi chưa có trên Drive.
!python download.py ikea_asm --source download --part annotations --part utilities --extract
```

Downloader đi theo symlink/shortcut tới thư mục công khai chỉ đọc. Với cấu trúc chính thức có `data/`, `annotations/`, `trained_models/`, mặc định chỉ giải nén **RGB top + action annotations + utility files**. Không mặc định giải nén depth, pose, multiview hay trained models. Các gói lựa chọn được kiểm tra đầy đủ trước khi bắt đầu giải nén.

Trong chế độ mounted, `--part` có thể lặp: `rgb-top`, `rgb-multi`, `annotations`, `utilities`, `camera`, `depth`, `depth-frames`, `pose`, `segmentation`, `model-action`, `model-pose`, `model-segmentation`, `all`. `all` bao gồm toàn bộ gói, kể cả depth và trained models. Có thể dùng `--include 'annotations/action*'` thay cho `--part` để chọn theo đường dẫn tương đối.

`--source-dir` cũng nhận một archive/thư mục tùy chỉnh và **luôn giải nén**, không tải/copy lại. Với thư mục tùy chỉnh không theo cấu trúc nhà phát hành, mặc định chỉ tìm ở cấp thư mục đó; thêm `--recursive` nếu cần. `--include` phân biệt hoa/thường. Archive gốc không bị sửa hoặc di chuyển. Kết quả nằm tại `MyDrive/Datasets/IKEA_ASM/extracted/<tên_archive>`, bên ngoài shortcut chỉ đọc.

Chỉ với `--source download`, `--part` có thể lặp: `annotations`, `utilities`, `camera`, `rgb-top`, `rgb-multi`, `depth`, `pose`, `segmentation`, `all`. Mặc định annotations + utilities. Các gói được chọn độc lập; tên archive lấy từ phản hồi Drive.

### FineAction

Nguồn của tác giả là `OpenDataLab/FineAction` trên OpenXLab. SDK `openxlab==0.1.3` yêu cầu requests/setuptools cũ, nên cài trong **venv riêng**, không cài đè môi trường chính:

```python
import subprocess, sys
subprocess.run([sys.executable, '-m', 'venv', '/content/openxlab-env'], check=True)
subprocess.run(['/content/openxlab-env/bin/python', '-m', 'pip', 'install', 'openxlab==0.1.3'], check=True)
```

Đăng nhập tài khoản OpenXLab của bạn và chấp nhận điều khoản/quyền truy cập FineAction tại nguồn. CLI nhận biến môi trường `OPENXLAB_AK`/`OPENXLAB_SK`; lấy giá trị từ Colab Secrets nếu cần, không ghi khóa vào notebook/repo. Với login tương tác, chạy `/content/openxlab-env/bin/openxlab login` trong terminal phù hợp.

```python
!python download.py fineaction --list-files
!python download.py fineaction --part annotations
!python download.py fineaction --part videos --extract
```

Runner tự nhận `/content/openxlab-env/bin/openxlab`, hoặc chỉ định `--openxlab-bin /path/to/openxlab`. Các `--part`: `annotations` (mặc định), `videos`, `i3d`, `i3d-100`, `videomae-h`, `videomae-g`, `all`. `--list-files` hiển thị đường dẫn nguồn được tác giả công bố, không đăng nhập hay liệt kê file trực tiếp từ portal. SDK chạy với target và thư mục tạm ở `MyDrive/Datasets/FineAction/raw`; cấu trúc con do SDK quyết định. Tải tiếp/checksum của nguồn OpenXLab do SDK quản lý.

Nếu đã có archive trên Drive hoặc được cấp link file trực tiếp:

```python
!python download.py fineaction --source-dir '/content/drive/MyDrive/FineAction-archives' --recursive
!python download.py fineaction --url 'https://HOST/PATH/videos.zip' --filename videos.zip --extract
```

`--source-dir` luôn giải nén mà không copy archive, giống IKEA. `--part` chỉ chọn dữ liệu ở chế độ OpenXLab; với archive có sẵn, dùng `--include`. Không tự xem nhãn FineAction là nhãn hoàn thành công việc nhiều bước nếu chưa gán/kiểm tra nhãn cấp công việc.

### Breakfast

```python
!python download.py breakfast --part annotations --extract
!python download.py breakfast --part videos --extract

# Kiểm tra kết nối bằng một file nhỏ; chỉ README, không phải video.
!python download.py breakfast --include README.md
```

`--part features` tải archive feature, không phải raw video. Hub của nhà phát hành hiện phân phối annotations/features; downloader video dùng link Drive gốc, có thể tạm không truy cập được do quota.

### HA4M và RepCount

```python
!python download.py ha4m --list-files
!python download.py repcount --list-files

# RepCount nếu đã có archive trên Drive: giải nén trực tiếp.
!python download.py repcount --source-dir '/content/drive/MyDrive/RepCount-archives' --recursive

# Thay URL/filename bằng link file thật được cấp từ nguồn.
!python download.py ha4m --url 'https://HOST/PATH/data.zip' --filename data.zip --extract
!python download.py repcount --url 'https://HOST/PATH/repcount.zip' --filename repcount.zip --extract
```

Có thể thêm `--sha256 SHA256` nếu nguồn cung cấp checksum. URL phải là link file HTTP(S), không phải trang giới thiệu hoặc trang nhập mật khẩu. Adapter cũng nhận link file chia sẻ Google Drive. Mount Drive đích không tự cấp quyền truy cập nguồn của nhà phát hành. CLI không tự đăng nhập hoặc vượt qua giới hạn truy cập/quota.

## Lưu trữ và chạy tiếp

```text
MyDrive/Datasets/
└── IndustReal/
    ├── raw/                 # File gốc, archive, file tải dở và metadata Hub
    └── extracted/
        └── all_rgb_videos/  # Nội dung archive, giữ nguyên cây thư mục của nguồn
```

- Chạy lại lệnh cũ để tiếp tục. File hoàn tất đã tồn tại được bỏ qua; IndustReal kiểm tra lại size/MD5, còn các nguồn khác chỉ kiểm tra checksum khi được cung cấp.
- HTTP: tải tiếp khi máy chủ hỗ trợ Range và có ETag/Last-Modified phù hợp; nếu không, tải lại phần dở từ đầu. File `.part` và metadata luôn nằm trong thư mục đích trên Drive.
- Với URL ký số hết hạn, nếu cần đổi link hãy dùng filename mới hoặc chủ động xóa đúng cặp `.part`/`.part.json` cũ. CLI không ghép dữ liệu từ hai URL khác nhau.
- Drive dùng cơ chế tải tiếp của `gdown`; Hugging Face quản lý metadata trong `raw/.cache/huggingface`. Cache Xet tùy chọn cũng mặc định đặt trong thư mục dataset trước khi import Hub.
- Không chạy đồng thời hai tiến trình tải vào cùng file hoặc cùng repo Hub/thư mục đích. Phần tải chưa có khóa phối hợp nhiều tiến trình.
- Giải nén có khóa chống hai job cùng thư mục trong **một runtime**. Không chạy hai Colab runtime cùng ghi vào một thư mục đích.
- Có thể đổi vị trí bằng `--root /path/to/Datasets` hoặc biến `VIDEOSEG_DATA_ROOT`; `--root` được ưu tiên. Nếu dùng `/content/drive` nhưng chưa mount, CLI báo lỗi thay vì tạo thư mục giả trong bộ nhớ phiên.

## Giải nén

Thêm `--extract` sau lệnh dataset, hoặc giải nén archive đã có:

```python
!python download.py extract '/content/drive/MyDrive/Datasets/IndustReal/raw/all_rgb_videos.zip' --name IndustReal
```

Hỗ trợ ZIP, TAR, TAR.GZ/TGZ, TAR.BZ2/TBZ2, TAR.XZ/TXZ. File nén được giữ lại. Các file không phải archive hỗ trợ được giữ trong `raw`; chưa tự ghép archive nhiều part (`.zip.001`, `.zip.002`), giải mã archive, hoặc giải nén RAR/7Z. Với `--part all`, các part archive chưa hỗ trợ vẫn chỉ nằm trong `raw`.

Giải nén mới lưu vào thư mục cố định `.NAME.extracting` trên **Drive**. Mỗi file được ghi vào file tạm, đọc hết/kiểm tra rồi mới đổi tên; nhật ký `.videoseg-progress.jsonl` ghi tiến độ theo từng file. Khi xong archive, thư mục được đổi thành tên kết quả. Cần đủ dung lượng cho archive và dữ liệu giải nén. Archive có đường dẫn thoát ra ngoài thư mục đích hoặc symlink/hardlink bị từ chối.

Nếu bị ngắt, **chạy lại đúng lệnh cũ** sau khi mount Drive. Giữ nguyên `.NAME.extracting`, `.videoseg-state.json` và `.videoseg-progress.jsonl`; không xóa chúng để “dọn file tạm”. File hoàn tất đã có checkpoint và đúng kích thước được bỏ qua, file chưa hoàn tất được giải nén lại. Nếu runtime chết trước khi flush checkpoint, ZIP có thể kiểm tra CRC file đã ghi để tái sử dụng. Chưa tiếp tục ở giữa byte của một file: nếu ngắt lúc ghi một video lớn thì video đó được làm lại.

ZIP đọc trực tiếp từng entry cần tiếp tục. TAR nén vẫn phải đọc/giải mã luồng từ đầu để đi đến entry tiếp theo, nhưng bỏ qua việc ghi lại file đã hoàn tất. Thêm `--verify-existing` để đọc và kiểm tra CRC các file cũ, thay cho chế độ nhanh tin vào checkpoint và kích thước. Việc kiểm tra lại này tốn I/O. Chỉnh sửa thủ công cùng kích thước không được phát hiện ở chế độ nhanh.

Kết quả giải nén hoàn tất từ bản cũ (bao gồm IKEA đã chạy xong) vẫn được nhận diện. Các thư mục ngẫu nhiên `.NAME.extract-*` còn dở từ bản cũ không có journal nên chưa được tự nhận để tiếp tục. Không chạy bản cũ và mới cùng lúc. Nếu thay đổi archive nguồn, công cụ từ chối trộn tiến độ của hai archive khác nhau.

### Chạy nhanh hơn

```python
# ZIP: thử 2 luồng. Mặc định là 1; không mặc định dùng nhiều luồng trên Drive.
!python download.py industreal --part rgb --extract --extract-workers 2

# IKEA nếu chỉ cần video: bỏ frame ảnh trong gói RGB, vẫn giữ đủ labels/utilities.
# Không cần chạy lại nếu IKEA của bạn đã hoàn tất.
!python download.py ikea_asm --video-only --extract-workers 2

# Lọc file bên trong một archive; có thể lặp --extract-include/--extract-exclude.
!python download.py extract '/content/drive/MyDrive/Datasets/IndustReal/raw/all_rgb_videos.zip' --name IndustReal --extract-include '*.mp4' --extract-include '*.avi'
```

`--include` chọn **archive/file nguồn** của downloader; `--extract-include` chọn **entry bên trong archive**. Bộ lọc giải nén chung áp dụng cho tất cả archive được chọn, nên chọn cả pattern nhãn nếu cần. `--video-only` của IKEA chỉ lọc các gói RGB, không bỏ nhãn hoặc utility files. Nếu một bộ lọc không khớp file nào, công cụ báo lỗi thay vì đánh dấu xong archive rỗng.

`--extract-workers` áp dụng cho ZIP, tối đa 8; TAR giải nén tuần tự. Hai luồng có thể giúp chồng lấp đọc/ghi nhưng không bảo đảm nhanh hơn trên Drive; nhiều luồng có thể làm I/O tệ hơn. Bộ giải nén tránh resolve lại cả cây thư mục trên Drive cho mỗi entry và ghi checkpoint theo batch. Chưa có benchmark tốc độ trên Drive thật. Dữ liệu và checkpoint mặc định vẫn nằm trên Drive.

Theo [FAQ Colab](https://research.google.com/colaboratory/faq.html), nhiều thao tác I/O nhỏ trên Drive có thể chậm. Nếu ưu tiên tốc độ tuyệt đối khi train, có thể chọn dùng ổ local runtime cho một phiên; dữ liệu đó sẽ mất khi runtime bị xóa. CLI này vẫn mặc định lưu bền trên Drive theo quy ước của dự án.

## Chạy nền và dataset tiếp theo: IndustReal

Sau khi mount Drive, cập nhật repo trong Colab rồi xem file trước khi tải:

```python
%cd /content/VideoSegmentation
!git pull --ff-only
!python download.py industreal --part rgb --list-files

# Tải RGB + action labels, giải nén và ghi log trên Drive; cell trả về ngay.
!python download.py industreal --part rgb --extract --extract-workers 2 --background

# Xem job mới nhất và 20 dòng log cuối:
!python download.py status --name IndustReal
```

Log và metadata job nằm tại `MyDrive/Datasets/IndustReal/jobs/`; lệnh khởi chạy in PID và đường dẫn log. Có thể xem thêm bằng `--tail 50`. Không lưu URL/token trong metadata job. Nếu muốn dừng một job, dùng đúng PID được in ra (`kill -TERM PID` trong cell shell); sau đó chạy lại lệnh tải để tiếp tục. Không khởi chạy bản thứ hai khi job đầu còn chạy.

`--background` cũng dùng được với các dataset khác và lệnh `extract`. Đây là tiến trình tách khỏi cell **trong runtime hiện tại**. Nếu Colab thu hồi/reset runtime, tiến trình sẽ dừng; nó không phải dịch vụ chạy liên tục khi tắt máy. Mount Drive lại, clone/cài lại nếu cần, rồi chạy đúng lệnh cũ để tiếp tục từ file đã lưu. `status` nhận biết job cũ không còn chạy/runtime thay đổi. Giới hạn runtime vẫn theo [FAQ Colab](https://research.google.com/colaboratory/faq.html); công cụ không có cơ chế giữ phiên sống bằng tương tác giả.

Gói `--part rgb` gồm video và action labels, phù hợp xem dữ liệu ban đầu; các bản ghi đa phương thức và nhãn quy trình đầy đủ nằm trong các gói `train`/`val`/`test`. Tải những gói đó sau nếu cần nghiên cứu trạng thái hoàn thành.

## Cấu trúc code

```text
download.py                     # Runner chính
downloaders/
├── __init__.py                 # Registry dataset → downloader
├── base.py                     # Giao diện chung và các thao tác dùng lại
├── industreal.py               # Nguồn, bộ lọc, kiểm tra và xử lý IndustReal
├── assembly101.py
├── ikea_asm.py
├── breakfast.py
├── ha4m.py
├── repcount.py
└── fineaction.py
videosegmentation/
├── cli.py                      # Parse lựa chọn và gọi downloader.run()
├── downloads.py                # Transport HTTP, Drive, Hugging Face
├── storage.py                  # Đường dẫn, mount guard
├── extraction.py               # Giải nén tiếp tục theo file, lọc và song song
└── jobs.py                     # Chạy nền, log và trạng thái job
notebooks/colab_download.ipynb
tests/
```

Thêm dataset bằng một file mới trong `downloaders/`, implement `add_arguments()` và `run()`, rồi đăng ký instance trong `downloaders/__init__.py`. Runner không cần thêm nhánh xử lý riêng. Xem [hướng dẫn thêm downloader](docs/adding_dataset.md).

## Chạy ngoài Colab và kiểm thử

Yêu cầu Python 3.10+:

```bash
python3 -m pip install -e .
python3 download.py --list
python3 download.py industreal --root ./Datasets --part labels --extract
python3 -m unittest discover -s tests -v
```

Tests dùng HTTP server cục bộ và file tổng hợp; không tải video dataset. Repo hiện cung cấp downloader, chưa có mô hình phân đoạn/huấn luyện.

## Nguồn

- [IndustReal](https://github.com/TimSchoonbeek/IndustReal) / [4TU metadata API](https://data.4tu.nl/v2/articles/b008dd74-020d-4ea4-a8ba-7bb60769d224)
- [Assembly101 downloader chính thức](https://github.com/assembly-101/assembly101-download-scripts) / [Hub](https://huggingface.co/datasets/cvml-nus/assembly101)
- [IKEA ASM: các gói tải chính thức](https://github.com/IkeaASM/ikea_asm_dataset)
- [Breakfast: phân phối annotations/features](https://huggingface.co/datasets/Serrelab/breakfast-actions)
- [HA4M](https://baltig.cnr.it/ISP/ha4m) / [RepCount](https://svip-lab.github.io/dataset/RepCount_dataset.html)
- [FineAction: nguồn chính thức](https://github.com/Richard-61/FineAction) / [OpenXLab SDK](https://openxlab.org.cn/docs/en/developers/%E6%95%B0%E6%8D%AE%E9%9B%86/%E6%95%B0%E6%8D%AE%E9%9B%86python%20SDK.html)
- [Colab Drive mount](https://colab.research.google.com/notebooks/io.ipynb) / [gdown](https://github.com/wkentaro/gdown) / [Hub download](https://huggingface.co/docs/huggingface_hub/en/guides/download)
