"""Shared downloader contract; dataset-specific decisions belong in each adapter."""

import argparse
import os
from abc import ABC, abstractmethod
from pathlib import Path

from videosegmentation.storage import DEFAULT_ROOT, archive_stem, dataset_directory, extract_archive, find_archives


class DatasetDownloader(ABC):
    key: str
    folder_name: str
    description: str
    homepage: str

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--root", default=os.environ.get("VIDEOSEG_DATA_ROOT", str(DEFAULT_ROOT)), help="Dataset root (default: /content/drive/MyDrive/Datasets)")
        parser.add_argument("--list-files", action="store_true", help="Show available files/parts or source instructions without downloading payload")
        parser.add_argument("--extract", action="store_true", help="Extract selected supported archives on Drive, keeping originals")

    def directory(self, args: argparse.Namespace) -> Path:
        dataset = dataset_directory(args.root, self.folder_name)
        for child in ("raw", "extracted"):
            if (dataset / child).resolve().parent != dataset:
                raise ValueError(f"{child} must stay inside the dataset directory.")
        print(f"Dataset directory: {dataset}")
        return dataset

    def finish(self, paths: list[Path], args: argparse.Namespace, dataset: Path, force_extract: bool = False) -> None:
        if args.extract or force_extract:
            for path in paths:
                try:
                    stem = archive_stem(path)
                except ValueError:
                    print(f"Retained without extraction: {path.name}")
                    continue
                extract_archive(path, dataset / "extracted" / stem)

    def extract_mounted(self, args: argparse.Namespace) -> None:
        paths = find_archives(args.source_dir, getattr(args, "include", None), args.recursive)
        if args.list_files:
            for path in paths:
                print(path)
            return
        self.finish(paths, args, self.directory(args), force_extract=True)

    @abstractmethod
    def run(self, args: argparse.Namespace) -> None:
        """Own the source selection, download and postprocessing for this dataset."""


def add_hf_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--include", action="append", help="Override part selection with a file glob; repeat for more patterns")
    parser.add_argument("--exclude", action="append", help="File glob to exclude; repeat for more patterns")
    parser.add_argument("--revision", default="main", help="Hub branch/tag/commit SHA (default: main)")
    parser.add_argument("--workers", type=int, default=2)


def add_mounted_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-dir", type=Path, help="Existing archive or folder on mounted Drive; extract without downloading/copying")
    parser.add_argument("--recursive", action="store_true", help="Find archives in subdirectories of --source-dir")
    parser.add_argument("--include", action="append", help="Select existing archives by relative filename glob; repeat for more patterns")


class DirectArchiveDownloader(DatasetDownloader):
    """For publisher portals that require a user-supplied direct download link."""

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--url", help="Direct HTTP(S) file URL supplied by the publisher")
        parser.add_argument("--filename", help="Filename, required when the direct URL has no meaningful filename")
        parser.add_argument("--sha256", help="Official SHA-256 checksum, if available")

    def run(self, args: argparse.Namespace) -> None:
        from videosegmentation.downloads import download_drive, download_url

        if args.list_files:
            print(f"{self.folder_name}: {self.homepage}\n{self.description}")
            print("Use --url with an actual file download link; this adapter does not automate portal authentication.")
            return
        if not args.url:
            raise ValueError(f"{self.folder_name} requires --url. Get a file download link from {self.homepage}")
        dataset = self.directory(args)
        from urllib.parse import urlsplit
        if urlsplit(args.url).hostname in ("drive.google.com", "docs.google.com"):
            paths = download_drive(args.url, dataset / "raw", args.filename, False, args.sha256)
        else:
            paths = [download_url(args.url, dataset / "raw", args.filename, args.sha256)]
        self.finish(paths, args, dataset)
