"""RepCount: keep publisher-specific access requirements in its own adapter."""

from .base import DirectArchiveDownloader, add_mounted_arguments


class RepCountDownloader(DirectArchiveDownloader):
    key = "repcount"
    folder_name = "RepCount"
    homepage = "https://svip-lab.github.io/dataset/RepCount_dataset.html"
    description = "RepCount — extract mounted archives or download an authorized direct archive URL"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_mounted_arguments(parser)

    def run(self, args):
        if args.source_dir:
            if args.url:
                raise ValueError("Choose either --source-dir or --url for RepCount.")
            self.extract_mounted(args)
            return
        if args.include or args.recursive:
            raise ValueError("--include/--recursive require --source-dir.")
        super().run(args)
