"""IndustReal: discover publisher file URLs from the 4TU metadata API."""

import fnmatch
import hashlib
import requests

from videosegmentation.downloads import download_url
from .base import DatasetDownloader


class IndustRealDownloader(DatasetDownloader):
    key = "industreal"
    folder_name = "IndustReal"
    description = "IndustReal — 4TU file catalog, RGB videos, multimodal recordings and labels"
    homepage = "https://github.com/TimSchoonbeek/IndustReal"
    metadata_url = "https://data.4tu.nl/v2/articles/b008dd74-020d-4ea4-a8ba-7bb60769d224"
    parts = {
        "labels": ["action_recognition_labels.zip"],
        "rgb": ["all_rgb_videos.zip", "action_recognition_labels.zip"],
        "train": ["train_p*.zip"], "val": ["val_p*.zip"], "test": ["test_p*.zip"],
        "recordings": ["train_p*.zip", "val_p*.zip", "test_p*.zip"],
        "all": ["*"],
    }

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--part", choices=self.parts, default="labels")
        parser.add_argument("--include", action="append", help="Override part selection with filename globs")

    def run(self, args):
        response = requests.get(self.metadata_url, timeout=30)
        response.raise_for_status()
        metadata = response.json()
        patterns = args.include or self.parts[args.part]
        files = [item for item in metadata["files"] if any(fnmatch.fnmatchcase(item["name"], pattern) for pattern in patterns)]
        if not files:
            raise ValueError("No IndustReal files match the selected part/patterns.")
        print(f"IndustReal publisher record version: {metadata.get('version', 'unknown')}")
        for item in files:
            print(f"{item['name']}\t{item['size']:,} bytes")
        if args.list_files:
            return
        dataset = self.directory(args)
        paths = []
        for item in files:
            if item.get("is_link_only") or item.get("is_incomplete"):
                raise ValueError(f"Publisher file is not a complete downloadable asset: {item['name']}")
            path = download_url(item["download_url"], dataset / "raw", item["name"])
            if path.stat().st_size != item["size"]:
                raise ValueError(f"Publisher size mismatch: {path}")
            expected = item.get("computed_md5")
            if expected:
                digest = hashlib.md5(usedforsecurity=False)
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected.lower().zfill(32):
                    raise ValueError(f"Publisher MD5 mismatch: {path}")
                print(f"Publisher MD5 verified: {path.name}")
            paths.append(path)
        self.finish(paths, args, dataset)
