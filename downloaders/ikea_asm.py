"""IKEA ASM: extract archives from mounted Drive, or fetch publisher packages."""

from pathlib import Path

from videosegmentation.downloads import download_drive
from videosegmentation.storage import find_archives
from .base import DatasetDownloader, add_mounted_arguments


class IkeaASMDownloader(DatasetDownloader):
    key = "ikea_asm"
    folder_name = "IKEA_ASM"
    description = "IKEA ASM — extract existing mounted Drive archives; optional publisher downloads"
    homepage = "https://github.com/IkeaASM/ikea_asm_dataset"
    default_source = Path("/content/drive/MyDrive/Datasets/ikea_asm_dataset_public")
    mounted_assets = {
        "utilities": "data/utility_files.zip",
        "camera": "data/camera_params.zip",
        "rgb-top": "data/ikea_asm_dataset_RGB_top.zip",
        "rgb-multi": "data/ikea_asm_dataset_RGB_multiview*.zip",
        "depth": "data/ikea_asm_dataset_depth.zip",
        "depth-frames": "data/all_depth_frames.tar.gz",
        "annotations": "annotations/action_annotations.zip",
        "pose": "annotations/pose_annotations.zip",
        "segmentation": "annotations/segmentation_tracking_annotation.zip",
        "model-action": "trained_models/pt_models_action_recognition.zip",
        "model-pose": "trained_models/pt_models_pose_estimation.zip",
        "model-segmentation": "trained_models/pt_models_instance_segmentation.zip",
    }
    default_mounted_parts = ["rgb-top", "annotations", "utilities"]
    assets = {
        "utilities": "11D7d8XBRg-CPIxMroviQEaaMhw3EaGnB",
        "camera": "1BRq9HJQeEJFbhnCwGwY3eXe1587TybCe",
        "rgb-top": "1CFOH-W-6N50AVA_NqHnm06GUsfpcka0L",
        "rgb-multi": "1eCbrIuw--16xCmI3RtBhRJ-r9K_FVkL6",
        "depth": "18FKRSzoUiO3EV_J2WmQyvmPGiHJcH28S",
        "annotations": "1SwBNLViktSpk99jhh3sMXVGTMVr6tpju",
        "pose": "1RE7Ya1gwogqJtJIi5WeYOH4_Cs1RuTx7",
        "segmentation": "1_jRCcLAz9zhXTnNnslBUJcu2sZjp9dVV",
    }

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_mounted_arguments(parser)
        parser.add_argument("--source", choices=("mounted", "download"), default="mounted", help="Default: extract archives already on mounted Drive")
        parser.add_argument("--part", choices=(*self.mounted_assets, "all"), action="append", help="Repeat to select packages; mounted default: rgb-top, annotations, utilities")

    def run_mounted(self, args):
        source = args.source_dir or self.default_source
        if args.part and args.include:
            raise ValueError("Choose --part or custom --include patterns, not both.")
        if args.list_files and not args.source_dir and not source.exists():
            for part in args.part or self.default_mounted_parts:
                for key in (self.mounted_assets if part == "all" else [part]):
                    print(f"{key}\t{source / self.mounted_assets[key]}")
            print("Planned publisher paths; mount Drive to inspect the actual files.")
            return
        source = source.expanduser().resolve(strict=True)
        if (Path(args.root).expanduser() / self.folder_name).resolve().is_relative_to(source):
            raise ValueError("The extraction destination must be outside the shared source directory.")
        has_publisher_layout = source.is_dir() and (source / "data").is_dir() and (source / "annotations").is_dir()
        if has_publisher_layout and not args.include:
            parts = list(self.mounted_assets) if args.part and "all" in args.part else (args.part or self.default_mounted_parts)
            paths = []
            # Resolve every selected part before extracting any large archives.
            for part in dict.fromkeys(parts):
                matches = find_archives(source, [self.mounted_assets[part]], recursive=True)
                if len(matches) != 1:
                    raise ValueError(f"Expected one archive for IKEA part {part}; found {len(matches)}.")
                paths.extend(matches)
        else:
            if args.part:
                raise ValueError("--part requires the publisher data/ and annotations/ layout; use --include for a custom folder.")
            paths = find_archives(source, args.include, recursive=args.recursive or has_publisher_layout)
        if args.list_files:
            for path in paths:
                print(path)
            return
        self.finish(paths, args, self.directory(args), force_extract=True)

    def run(self, args):
        if args.source == "mounted":
            self.run_mounted(args)
            return
        if args.source_dir or args.include or args.recursive:
            raise ValueError("--source-dir/--include/--recursive apply to mounted archives; use --part for publisher downloads.")
        parts = args.part or ["annotations", "utilities"]
        if "all" in parts:
            parts = list(self.assets)
        parts = list(dict.fromkeys(parts))
        if any(part not in self.assets for part in parts):
            raise ValueError("Some selected parts are only available through --source mounted.")
        if args.list_files:
            for part in parts:
                print(f"{part}\thttps://drive.google.com/file/d/{self.assets[part]}/view")
            return
        dataset = self.directory(args)
        paths = []
        for part in parts:
            url = f"https://drive.google.com/file/d/{self.assets[part]}/view"
            paths.extend(download_drive(url, dataset / "raw", None, False, None))
        self.finish(paths, args, dataset)
