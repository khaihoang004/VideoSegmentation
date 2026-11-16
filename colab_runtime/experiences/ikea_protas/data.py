"""Read native SQLite labels and official cross-environment splits, without goal labels."""

import hashlib
import json
from pathlib import Path
import sqlite3

import numpy as np


def file_at(root, candidates):
    paths = [root / p for p in candidates if (root / p).is_file()]
    if len(paths) != 1:
        raise ValueError(f"Expected one file under {root}: {candidates}; found {paths}")
    return paths[0]


def build_index(dataset_root, *, scope="full", train_limit=2, test_limit=1):
    root = Path(dataset_root).expanduser().resolve()
    extracted = root / "extracted" if (root / "extracted").is_dir() else root
    db = file_at(extracted, ["action_annotations/ikea_annotation_db_full", "ikea_annotation_db_full"])
    utility_candidates = [extracted / "utility_files/ANU_ikea_dataset/indexing_files",
                          extracted / "utility_files/indexing_files", extracted / "indexing_files"]
    indexing = [p for p in utility_candidates if (p / "atomic_action_list.txt").is_file()]
    if len(indexing) != 1:
        raise ValueError(f"Cannot locate indexing_files: {utility_candidates}")
    indexing = indexing[0]
    actions = (indexing / "atomic_action_list.txt").read_text().splitlines()
    relations = [tuple(map(int, line.split())) for line in
                 (indexing / "action_object_relation_list.txt").read_text().splitlines()]
    if len(actions) != len(relations) or len(set(actions)) != len(actions):
        raise ValueError("Invalid official action/object mapping")
    pairs = sorted(zip(actions, relations))
    labels = ["NA"] + [a for a, _ in pairs]
    action_ids = {pair: i + 1 for i, (_, pair) in enumerate(pairs)}
    splits = {}
    for split, filename in (("train", "train_cross_env.txt"), ("test", "test_cross_env.txt")):
        for rec in (indexing / filename).read_text().splitlines():
            rec = rec.strip().replace("\\", "/").rstrip("/")
            if not rec or rec.startswith("/") or ".." in Path(rec).parts or rec in splits:
                raise ValueError("Invalid/duplicate/cross-split recording in official split")
            splits[rec] = split
    video_roots = [extracted / "ikea_asm_dataset_RGB_top/ANU_ikea_dataset_video",
                   extracted / "ANU_ikea_dataset_video", extracted]
    records, missing = [], []
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        videos = list(conn.execute("SELECT * FROM videos WHERE annotated=1 AND camera='dev3' ORDER BY video_path"))
        for video in videos:
            rec = "/".join(video["video_path"].replace("\\", "/").split("/")[:2])
            if rec not in splits:
                continue
            candidates = []
            for base in video_roots:
                for suffix in ("dev3/images/scan_video.avi", "dev3/scan_video.avi", "dev3/images/scan_video.mp4",
                               "dev3/scan_video.mp4", "scan_video.avi", "scan_video.mp4"):
                    path = base / rec / suffix
                    if path.is_file():
                        candidates.append(str(path.resolve()))
            candidates = sorted(set(candidates))
            if not candidates:
                missing.append(rec)
                continue
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous top-view video for {rec}: {candidates}")
            annotations = []
            for ann in conn.execute("SELECT * FROM annotations WHERE video_id=?", (video["id"],)):
                label = action_ids.get((ann["atomic_action_id"], ann["object_id"]))
                if label is not None:
                    annotations.append([int(ann["starting_frame"]), min(int(ann["ending_frame"]), video["nframes"]), label])
            records.append(dict(recording_id=rec, split=splits[rec], video_path=candidates[0],
                                nframes=int(video["nframes"]), annotations=annotations,
                                key=hashlib.sha256(rec.encode()).hexdigest()[:20]))
    if scope not in {"pilot", "full"}:
        raise ValueError("scope must be pilot or full")
    if scope == "full" and (missing or len(records) != len(splits)):
        raise ValueError(f"Full split requires all {len(splits)} recordings; found {len(records)}, missing {missing[:8]}")
    if scope == "pilot":
        chosen = []
        for split, limit in (("train", train_limit), ("test", test_limit)):
            available = [r for r in records if r["split"] == split]
            available.sort(key=lambda r: (r["nframes"], r["recording_id"]))
            if limit < 1 or len(available) < limit:
                raise ValueError(f"Pilot needs {limit} available {split} recordings")
            chosen += available[:limit]
        records = chosen
    return dict(schema_version=1, purpose="original_atomic_action_segmentation",
                scope=scope, labels=labels, background_id=0, camera="dev3",
                split_protocol="official_train_cross_env_test_cross_env",
                annotation_endpoint="SQLite_start_inclusive_end_exclusive_as_official_loader",
                dataset_root=str(root), db_path=str(db), records=records,
                missing_videos=missing, original_split_counts={s: list(splits.values()).count(s) for s in ("train", "test")})


def sampled_labels(record, frame_indices):
    """Match author loader: NA initially; later annotations overwrite [start,end)."""
    indices = np.asarray(frame_indices)
    if indices.ndim != 1 or not np.issubdtype(indices.dtype, np.integer):
        raise ValueError("Frame indices must be an integer vector")
    if not len(indices) or indices[0] < 0 or indices[-1] >= record["nframes"] or (np.diff(indices) <= 0).any():
        raise ValueError("Frame indices must increase within the annotated recording")
    y = np.zeros(len(indices), dtype=np.int64)
    for start, end, label in record["annotations"]:
        y[(indices >= start) & (indices < end)] = label
    return y


def signature(index):
    return hashlib.sha256(json.dumps(index, sort_keys=True).encode()).hexdigest()
