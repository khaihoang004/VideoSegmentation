"""Breakfast: annotations/features on Hub; raw video archive on publisher Drive."""

from videosegmentation.downloads import download_drive, download_hf
from .base import DatasetDownloader, add_hf_arguments


class BreakfastDownloader(DatasetDownloader):
    key = "breakfast"
    folder_name = "Breakfast"
    description = "Breakfast — Hub annotations/features; raw videos use the publisher Drive link"
    homepage = "https://serre.lab.brown.edu/breakfast-actions-dataset.html"
    repo = "Serrelab/breakfast-actions"
    video_url = "https://drive.google.com/file/d/1jgSoof1AatiDRpGY091qd4TEKF-BUt6I/view"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_hf_arguments(parser)
        parser.add_argument("--part", choices=("annotations", "features", "videos"), default="annotations")

    def run(self, args):
        if args.part == "videos" and args.include:
            raise ValueError("--include selects Hub files; omit it when using --part videos.")
        if args.part == "videos" and args.list_files:
            print(f"Raw video archive (Drive, quota may apply): {self.video_url}")
            return
        dataset = self.directory(args)
        if args.part == "videos":
            paths = download_drive(self.video_url, dataset / "raw", "BreakfastII_15fps_qvga_sync.tar.gz", False, None)
        else:
            patterns = args.include or (["segmentation_coarse.tar.gz", "segmentation_fine.tar.gz"] if args.part == "annotations" else ["breakfast_data.tar.gz"])
            paths = download_hf(self.repo, dataset / "raw", args.revision, patterns, args.exclude, args.workers, args.list_files)
        self.finish(paths, args, dataset)
