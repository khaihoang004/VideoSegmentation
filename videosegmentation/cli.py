"""Runner: parse the dataset choice and delegate to its downloader."""

import argparse
import os
import sys
from pathlib import Path

from downloaders import DOWNLOADERS
from . import __version__
from .storage import DEFAULT_ROOT, archive_stem, dataset_directory, extract_archive


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Choose a dataset to download directly into Google Drive.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--list", action="store_true", help="List dataset downloaders without accessing the network")
    commands = parser.add_subparsers(dest="dataset")
    for key, downloader in DOWNLOADERS.items():
        command = commands.add_parser(key, help=downloader.description, description=downloader.description)
        downloader.add_arguments(command)
        command.set_defaults(downloader=downloader)
    extract = commands.add_parser("extract", help="Extract an archive already on Drive")
    extract.add_argument("archive", type=Path)
    extract.add_argument("--name", required=True, help="Dataset folder name, e.g. IndustReal")
    extract.add_argument("--root", default=os.environ.get("VIDEOSEG_DATA_ROOT", str(DEFAULT_ROOT)))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list:
        for key, downloader in DOWNLOADERS.items():
            print(f"{key:14} {downloader.description}")
        return 0
    if not args.dataset:
        parser.print_help()
        return 0
    try:
        if getattr(args, "workers", 1) < 1:
            raise ValueError("--workers must be at least 1.")
        if args.dataset == "extract":
            dataset = dataset_directory(args.root, args.name)
            if (dataset / "extracted").resolve().parent != dataset:
                raise ValueError("The extraction directory must stay inside the dataset.")
            extract_archive(args.archive, dataset / "extracted" / archive_stem(args.archive))
        else:
            args.downloader.run(args)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted. Files already on Drive are retained; rerun to retry.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
