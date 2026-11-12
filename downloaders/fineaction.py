"""FineAction: publisher OpenXLab CLI, existing Drive archives, or a direct URL."""

import os
import shutil
import subprocess
from pathlib import Path

from .base import DirectArchiveDownloader, add_mounted_arguments


class FineActionDownloader(DirectArchiveDownloader):
    key = "fineaction"
    folder_name = "FineAction"
    description = "FineAction — publisher OpenXLab SDK or mounted archives/direct file links"
    homepage = "https://github.com/Richard-61/FineAction"
    repo = "OpenDataLab/FineAction"
    parts = {
        "annotations": "/raw/annotations_gt.json",
        "videos": "/raw/video",
        "i3d": "/raw/i3d_feature",
        "i3d-100": "/raw/i3d_feature_100",
        "videomae-h": "/raw/mae_h_feature",
        "videomae-g": "/raw/mae_g_feature",
    }

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_mounted_arguments(parser)
        parser.add_argument("--part", choices=(*self.parts, "all"), default="annotations")
        parser.add_argument("--openxlab-bin", default=os.environ.get("OPENXLAB_BIN"), help="Path to OpenXLab CLI in its separate virtual environment")

    def run(self, args):
        if args.source_dir:
            if args.url:
                raise ValueError("Choose either --source-dir or --url for FineAction.")
            self.extract_mounted(args)
            return
        if args.url:
            if args.include or args.recursive:
                raise ValueError("--include/--recursive require --source-dir.")
            super().run(args)
            return
        if args.include or args.recursive or args.filename or args.sha256:
            raise ValueError("Use --part for OpenXLab; --include/--recursive need --source-dir and --filename/--sha256 need --url.")
        if args.list_files:
            for name, remote in self.parts.items():
                if args.part in (name, "all"):
                    print(f"{name}\t{self.repo}:{remote}")
            print("Publisher source paths (not a live file listing). Downloads require OpenXLab access and its CLI.")
            return
        executable = args.openxlab_bin or shutil.which("openxlab")
        if not executable and Path("/content/openxlab-env/bin/openxlab").is_file():
            executable = "/content/openxlab-env/bin/openxlab"
        executable = shutil.which(str(executable)) if executable else None
        if not executable:
            raise ValueError("OpenXLab CLI not found. Install it in a separate environment as shown in README, then pass --openxlab-bin PATH. Or use --source-dir/--url.")
        dataset = self.directory(args)
        raw = dataset / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        command = [str(Path(executable).resolve()), "dataset"]
        if args.part == "all":
            command.extend(["get", "--dataset-repo", self.repo])
        else:
            command.extend(["download", "--dataset-repo", self.repo, "--source-path", self.parts[args.part]])
        command.extend(["--target-path", str(raw)])
        # SDK cache and temporary payloads must also stay on the destination drive.
        temporary = raw / ".cache" / "tmp"
        temporary.mkdir(parents=True, exist_ok=True)
        environment = {**os.environ, "TMPDIR": str(temporary)}
        subprocess.run(command, cwd=raw, env=environment, check=True)
        files = [path for path in raw.rglob("*") if path.is_file() and ".cache" not in path.relative_to(raw).parts]
        if not files:
            raise ValueError("OpenXLab returned without any dataset files. Check access permissions and the selected source path.")
        if args.part == "annotations" and not any(path.name == "annotations_gt.json" and path.stat().st_size for path in files):
            raise ValueError("OpenXLab did not produce annotations_gt.json. Check access permissions and SDK output.")
        self.finish(files, args, dataset)
