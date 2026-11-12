"""Assembly101: official Hub release, part selection and camera filtering."""

from videosegmentation.downloads import download_hf
from .base import DatasetDownloader, add_hf_arguments


class Assembly101Downloader(DatasetDownloader):
    key = "assembly101"
    folder_name = "Assembly101"
    description = "Assembly101 — official Hugging Face release (access approval/token may be required)"
    homepage = "https://assembly-101.github.io/"
    repo = "cvml-nus/assembly101"
    cameras = {
        "v1": "C10095", "v2": "C10115", "v3": "C10118", "v4": "C10119",
        "v5": "C10379", "v6": "C10390", "v7": "C10395", "v8": "C10404",
    }

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_hf_arguments(parser)
        parser.add_argument("--part", choices=("annotations", "videos", "features", "poses", "all"), default="annotations")
        parser.add_argument("--view", choices=("all", "fixed", "egocentric", *self.cameras), default="all", help="Video view filter, used with --part videos")

    def patterns(self, args):
        if args.include:
            return args.include
        if args.view != "all" and args.part != "videos":
            raise ValueError("--view is used with --part videos (or use --include for custom file patterns).")
        if args.part == "videos":
            if args.view in self.cameras:
                return [f"recordings/*/{self.cameras[args.view]}_rgb.mp4"]
            if args.view == "fixed":
                return ["recordings/*/C*_rgb.mp4"]
            if args.view == "egocentric":
                return ["recordings/*/HMC_*.mp4"]
            return ["recordings/*"]
        return {
            "annotations": ["annotations/*"],
            "features": ["TSM_features/*", "DINOv2_features/*"],
            "poses": ["AssemblyPoses.zip"],
            "all": ["*"],
        }[args.part]

    def run(self, args):
        patterns = self.patterns(args)
        dataset = self.directory(args)
        paths = download_hf(self.repo, dataset / "raw", args.revision, patterns, args.exclude, args.workers, args.list_files)
        self.finish(paths, args, dataset)
