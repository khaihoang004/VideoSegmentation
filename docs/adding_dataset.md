# Thêm downloader

Mỗi dataset có một module và một lớp kế thừa `DatasetDownloader`. Lớp đó sở hữu nguồn tải, lựa chọn subset, xác thực nguồn khi cần, kiểm tra dữ liệu và các bước xử lý sau tải. Runner chỉ chọn adapter và gọi `run(args)`.

Ví dụ tối thiểu trong `downloaders/example.py`:

```python
from .base import DatasetDownloader
from videosegmentation.downloads import download_url

class ExampleDownloader(DatasetDownloader):
    key = 'example'
    folder_name = 'Example'
    description = 'Example dataset'
    homepage = 'https://publisher.example/dataset'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--url', required=True)

    def run(self, args):
        if args.list_files:
            print(args.url)
            return
        dataset = self.directory(args)
        paths = [download_url(args.url, dataset / 'raw')]
        self.finish(paths, args, dataset)
```

Import và thêm `ExampleDownloader()` vào registry `DOWNLOADERS` trong `downloaders/__init__.py`. Khi đó `python download.py example --help` tự xuất hiện.

Các hàm transport trong `videosegmentation/downloads.py` chỉ lo tải file. Không đặt điều kiện theo tên dataset vào transport hoặc runner. Các file tải dở, archive, cache payload và dữ liệu giải nén phải nằm dưới thư mục dataset, mặc định trên Drive. `--list-files` phải dừng trước khi tải payload.

Nếu nguồn chỉ cung cấp cổng đăng nhập/link tạm thời, nêu rõ yêu cầu nguồn thay vì gán một URL giả hoặc báo dataset đã tải thành công. Ghi nguồn chính thức trong README và kiểm thử cách chọn file/dispatch, ngoài các tests transport dùng chung.
