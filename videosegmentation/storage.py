"""Storage layout and archive extraction without writing outside the dataset."""

import json
import fnmatch
import os
import re
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_ROOT = Path("/content/drive/MyDrive/Datasets")
ARCHIVE_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz", ".tar", ".zip")


def find_archives(source: Path, patterns: list[str] | None = None, recursive: bool = False) -> list[Path]:
    """Select existing archives without copying them off the mounted drive."""
    source = source.expanduser().resolve(strict=True)
    candidates = [source] if source.is_file() else (source.rglob("*") if recursive else source.iterdir())
    selected = []
    for path in candidates:
        if not path.is_file() or not path.name.lower().endswith(ARCHIVE_SUFFIXES):
            continue
        relative = path.name if source.is_file() else path.relative_to(source).as_posix()
        if patterns and not any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns):
            continue
        selected.append(path)
    if not selected:
        raise ValueError(f"No supported archives found at {source}. Select another source/pattern or add --recursive.")
    stems = [archive_stem(path) for path in selected]
    if len(stems) != len(set(stems)):
        raise ValueError("Selected archives have duplicate output names. Narrow --include or process them separately.")
    return sorted(selected)


def dataset_directory(root: str | Path, name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ValueError("Dataset name must start with a letter/digit and use letters, digits, '.', '_' or '-'.")
    root = Path(root).expanduser().absolute()
    if root.is_relative_to("/content/drive") and not Path("/content/drive/MyDrive").is_dir():
        raise ValueError(
            "Google Drive is not mounted. In a Colab Python cell run:\n"
            "from google.colab import drive\ndrive.mount('/content/drive')\n"
            "Or pass --root PATH to use a different location."
        )
    root = root.resolve()
    directory = (root / name).resolve()
    if directory.parent != root:
        raise ValueError("Dataset directory must stay inside the dataset root.")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_filename(name: str) -> str:
    if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
        raise ValueError("Filename must be a single filename without directory components.")
    return name


def archive_stem(path: Path) -> str:
    for suffix in ARCHIVE_SUFFIXES:
        if path.name.lower().endswith(suffix):
            return safe_filename(path.name[:-len(suffix)])
    raise ValueError("Supported archives: zip, tar, tar.gz/tgz, tar.bz2/tbz2, tar.xz/txz.")


def _member_path(base: Path, name: str) -> Path:
    if "\\" in name or "\x00" in name:
        raise ValueError(f"Unsafe archive member: {name!r}")
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts or (member.parts and ":" in member.parts[0]):
        raise ValueError(f"Unsafe archive member: {name!r}")
    target = base.joinpath(*member.parts)
    if not target.resolve().is_relative_to(base.resolve()):
        raise ValueError(f"Archive member escapes the output directory: {name!r}")
    return target


def _copy_member(source, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        shutil.copyfileobj(source, output, length=1024 * 1024)


def extract_archive(archive: Path, destination: Path) -> Path:
    """Extract into a temporary directory on the same drive, then rename on success."""
    archive = archive.resolve(strict=True)
    archive_stem(archive)
    signature = {"archive": archive.name, "size": archive.stat().st_size, "mtime_ns": archive.stat().st_mtime_ns}
    marker = destination / ".videoseg-extracted.json"
    if destination.exists():
        if marker.is_file() and json.loads(marker.read_text()) == signature:
            print(f"Already extracted: {destination}")
            return destination
        raise ValueError(f"Extraction destination already exists: {destination}. Choose another --name or move it first.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.extract-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        if archive.name.lower().endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                for member in bundle.infolist():
                    target = _member_path(staging, member.filename)
                    kind = stat.S_IFMT(member.external_attr >> 16)
                    if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                        raise ValueError(f"Archive links/special files are not supported: {member.filename}")
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        with bundle.open(member) as source:
                            _copy_member(source, target)
        else:
            with tarfile.open(archive, "r|*") as bundle:
                for member in bundle:
                    target = _member_path(staging, member.name)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        with bundle.extractfile(member) as source:
                            _copy_member(source, target)
                    else:
                        raise ValueError(f"Archive links/special files are not supported: {member.name}")
        (staging / ".videoseg-extracted.json").write_text(json.dumps(signature, indent=2) + "\n")
        os.rename(staging, destination)
    print(f"Extracted: {destination}")
    return destination
