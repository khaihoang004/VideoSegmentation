"""IKEA ASM: extract archives from mounted Drive, or fetch publisher packages."""

from videosegmentation.downloads import download_drive
from .base import DatasetDownloader, add_mounted_arguments


class IkeaASMDownloader(DatasetDownloader):
    key = "ikea_asm"
    folder_name = "IKEA_ASM"
    description = "IKEA ASM — extract existing mounted Drive archives; optional publisher downloads"
    homepage = "https://github.com/IkeaASM/ikea_asm_dataset"
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
        parser.add_argument("--part", choices=(*self.assets, "all"), action="append", help="Repeat to select packages; default: annotations and utilities")

    def run(self, args):
        if args.source_dir:
            if args.source != "mounted" or args.part:
                raise ValueError("Use --source-dir with mounted mode and --include, not --source download or --part.")
            self.extract_mounted(args)
            return
        if args.source == "mounted":
            if args.list_files:
                print(f"Add the publisher shared folder to MyDrive, mount Drive, then use --source-dir PATH.\n{self.homepage}")
                return
            raise ValueError("Specify --source-dir with the archive/folder path on mounted Drive, or use --source download.")
        if args.include or args.recursive:
            raise ValueError("--include/--recursive apply to mounted archives; use --part for publisher downloads.")
        parts = args.part or ["annotations", "utilities"]
        if "all" in parts:
            parts = list(self.assets)
        parts = list(dict.fromkeys(parts))
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
