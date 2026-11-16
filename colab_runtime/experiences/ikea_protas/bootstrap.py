"""Bounded discovery of an already-mounted IKEA dataset; no video reads."""

from collections import deque
import os
from pathlib import Path


def locate_dataset(my_drive):
    drive = Path(my_drive).resolve()

    def ready(path):
        return any((path / suffix).is_file() for suffix in (
            "extracted/action_annotations/ikea_annotation_db_full",
            "action_annotations/ikea_annotation_db_full", "ikea_annotation_db_full"))

    # The first path is the user's audited layout. Avoid enumerating Drive when
    # it exists; the fallback reads only a bounded set of relevant directories.
    for path in (drive / "Datasets/IKEA_ASM", drive / "IKEA_ASM", drive / "Datasets/ikea_asm"):
        if ready(path):
            return path
    pending, seen = deque([(drive, 0)]), set()
    allowed = {"datasets", "dataset", "data", "ikea_asm", "ikea asm", "ikea", "videosegmentation", "extracted"}
    while pending and len(seen) < 40:
        path, depth = pending.popleft()
        if path in seen:
            continue
        seen.add(path)
        if ready(path):
            return path
        if depth == 4 or not path.is_dir():
            continue
        with os.scandir(path) as entries:
            for i, entry in enumerate(entries):
                if i >= 200:
                    break
                if entry.name.casefold() in allowed and entry.is_dir(follow_symlinks=False):
                    pending.append((Path(entry.path), depth + 1))
    raise FileNotFoundError(
        "Không thấy IKEA_ASM đã giải nén trong My Drive. Cần thư mục chứa "
        "extracted/action_annotations/ikea_annotation_db_full. Nếu dataset ở Shared with me, "
        "thêm shortcut thư mục Datasets vào My Drive; dữ liệu gốc không cần di chuyển.")
