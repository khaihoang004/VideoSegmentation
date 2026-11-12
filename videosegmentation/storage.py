"""Storage layout and archive extraction without writing outside the dataset."""

import fnmatch
import re
from pathlib import Path

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


def extract_archive(archive: Path, destination: Path, **options) -> Path:
    """Extract with persistent per-file progress; see extraction.py for the engine."""
    from .extraction import extract_archive as extract

    return extract(archive, destination, **options)
