"""Canonical goal-level manifests and chronological, memory-mapped recordings."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from .config import Config


STATUSES = {"completed", "aborted", "ongoing", "unknown"}


def _number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def resolve_path(value: str, base: Path) -> Path:
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def load_manifest(path: str | Path, root: str | None = None) -> list[dict]:
    path = Path(path).expanduser().resolve()
    base = Path(root).expanduser().resolve() if root else path.parent
    entries, ids, group_splits, path_splits = [], set(), {}, {}
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            required = {"schema_version", "recording_id", "group_id", "split",
                        "view_domain", "task_definition_version", "duration",
                        "coverage", "instances"}
            if not isinstance(row, dict) or not required <= row.keys():
                raise ValueError(f"Missing fields: {sorted(required - row.keys()) if isinstance(row, dict) else required}")
            if row["schema_version"] != 1:
                raise ValueError("Only manifest schema_version=1 is supported")
            for key in ["recording_id", "group_id", "split", "task_definition_version"]:
                if not isinstance(row[key], str) or not row[key].strip():
                    raise ValueError(f"{key} must be a nonempty string")
            if row["recording_id"] in ids:
                raise ValueError("Duplicate recording_id")
            ids.add(row["recording_id"])
            if row["view_domain"] not in {"exo", "ego", "unknown"}:
                raise ValueError("Invalid view_domain")
            split = row["split"]
            old = group_splits.setdefault(row["group_id"], split)
            if old != split:
                raise ValueError(f"group_id {row['group_id']} leaks across splits")
            row["duration"] = _number(row["duration"], "duration")
            if row["duration"] <= 0:
                raise ValueError("duration must be positive")
            last_end = -1.0
            if not isinstance(row["coverage"], list):
                raise ValueError("coverage must be a list of [start,end) ranges")
            for bounds in row["coverage"]:
                if not isinstance(bounds, list) or len(bounds) != 2:
                    raise ValueError("Bad coverage range")
                a, b = (_number(v, "coverage") for v in bounds)
                if not 0 <= a < b <= row["duration"] or a < last_end:
                    raise ValueError("coverage must be sorted, disjoint and inside duration")
                last_end = b
            instance_ids, spans = set(), []
            for item in row["instances"]:
                if not isinstance(item, dict) or not {"instance_id", "start", "end", "status"} <= item.keys():
                    raise ValueError("Instances need instance_id,start,end,status")
                if item["status"] not in STATUSES or not isinstance(item["instance_id"], str):
                    raise ValueError("Invalid instance status/id")
                if not item["instance_id"] or item["instance_id"] in instance_ids:
                    raise ValueError("Empty/duplicate instance_id")
                instance_ids.add(item["instance_id"])
                for flag in ["left_censored", "right_censored"]:
                    if flag in item and type(item[flag]) is not bool:
                        raise ValueError(f"{flag} must be boolean")
                a = 0.0 if item["start"] is None else _number(item["start"], "start")
                b = row["duration"] if item["end"] is None else _number(item["end"], "end")
                if not 0 <= a < b <= row["duration"]:
                    raise ValueError("Instance interval must be inside duration with start < end")
                if item["start"] is None and not item.get("left_censored", False):
                    raise ValueError("null start requires left_censored=true")
                if item["end"] is None and not (item.get("right_censored", False) or item["status"] in {"ongoing", "unknown"}):
                    raise ValueError("null end requires ongoing/unknown or right_censored")
                spans.append((a, b))
            for previous, current in zip(sorted(spans), sorted(spans)[1:]):
                if previous[1] > current[0]:
                    raise ValueError("Baseline supports only one non-overlapping target instance at a time")
            if row.get("video_path"):
                row["video_path"] = str(resolve_path(row["video_path"], base))
            if "features" in row:
                feature = row["features"]
                if not isinstance(feature, dict) or not {"path", "timestamps_path", "causal", "encoder", "timestamp_semantics"} <= feature.keys():
                    raise ValueError("features needs path,timestamps_path,causal,encoder,timestamp_semantics")
                if feature["causal"] is not True or feature["timestamp_semantics"] != "last_observed_frame":
                    raise ValueError("Features must have audited causal=true and last_observed_frame timestamps")
                if not isinstance(feature["encoder"], str) or not feature["encoder"]:
                    raise ValueError("features.encoder is required")
                for key in ["path", "timestamps_path"]:
                    feature[key] = str(resolve_path(feature[key], base))
            candidates = [row.get("video_path")]
            if "features" in row:
                candidates += [row["features"]["path"], row["features"]["timestamps_path"]]
            for candidate in filter(None, candidates):
                prior = path_splits.setdefault(candidate, split)
                if prior != split:
                    raise ValueError(f"Same media/features path used in multiple splits: {candidate}")
            entries.append(row)
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f"{path}:{line_no}: {error}") from error
    if not entries:
        raise ValueError("Manifest is empty")
    return entries


def supervised_instance(item: dict) -> bool:
    return (item["status"] in {"completed", "aborted"}
            and item["start"] is not None and item["end"] is not None
            and not item.get("left_censored", False) and not item.get("right_censored", False))


def ignored_ranges(row):
    return [(0.0 if i["start"] is None else i["start"],
             row["duration"] if i["end"] is None else i["end"])
            for i in row["instances"] if not supervised_instance(i)]


def labelled_ranges(row):
    result = [tuple(x) for x in row["coverage"]]
    for a, b in ignored_ranges(row):
        result = [(s, e) for left, right in result
                  for s, e in [(left, min(right, a)), (max(left, b), right)] if s < e]
    return result


def interval_covered(a, b, ranges):
    cursor = a
    for left, right in ranges:
        if right <= cursor:
            continue
        if left > cursor + 1e-8:
            return False
        cursor = right
        if cursor >= b - 1e-8:
            return True
    return False


def make_targets(row, timestamps, boundary_width):
    """Channels: whole-instance membership, start, completed end (never motion)."""
    targets = np.zeros((len(timestamps), 3), dtype=np.float32)
    valid = np.zeros(len(timestamps), dtype=bool)
    for a, b in labelled_ranges(row):
        valid |= (timestamps >= a) & (timestamps < b)
    for item in row["instances"]:
        if not supervised_instance(item):
            continue
        a, b = item["start"], item["end"]
        targets[(timestamps >= a) & (timestamps < b), 0] = 1.0
        for channel, when in [(1, a), (2, b)]:
            if channel == 2 and item["status"] != "completed":
                continue
            index = int(np.searchsorted(timestamps, when, side="left"))
            if index == len(timestamps):
                raise ValueError(f"{row['recording_id']}: boundary {when} has no observed feature at/after it; inspect sampling/censoring")
            # All positive boundary bins are AT or AFTER the event, never before it.
            stop = max(index + 1, int(np.searchsorted(timestamps, when + boundary_width, side="right")))
            targets[index:stop, channel] = 1.0
    mask = np.repeat(valid[:, None], 3, axis=1)
    return torch.from_numpy(targets), torch.from_numpy(mask)


@dataclass
class Recording:
    entry: dict
    features: np.ndarray
    timestamps: np.ndarray
    targets: torch.Tensor
    mask: torch.Tensor

    def __len__(self):
        return len(self.timestamps)


class FeatureDataset(Dataset):
    def __init__(self, cfg: Config, split: str, *, with_targets=True):
        self.cfg = cfg
        self.with_targets = with_targets
        rows = load_manifest(cfg.data.manifest, cfg.data.root)
        self.entries = [r for r in rows if r["split"] == split]
        if not self.entries:
            raise ValueError(f"No records for split {split!r}")
        for row in self.entries:
            if row["view_domain"] not in cfg.data.view_domains:
                raise ValueError(f"{row['recording_id']}: view_domain excluded by config")
            if row["task_definition_version"] != cfg.data.task_definition_version:
                raise ValueError(f"{row['recording_id']}: task_definition_version differs; baseline is single-task")
            if "features" not in row:
                raise ValueError(f"{row['recording_id']}: run extract-features first")

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, index):
        row = self.entries[index]
        features = np.load(row["features"]["path"], mmap_mode="r", allow_pickle=False)
        times = np.load(row["features"]["timestamps_path"], allow_pickle=False)
        if features.ndim != 2 or features.shape[1] != self.cfg.model.input_dim or not np.issubdtype(features.dtype, np.floating):
            raise ValueError(f"{row['recording_id']}: features must be floating [T,{self.cfg.model.input_dim}]")
        if times.ndim != 1 or len(times) != len(features) or not len(times):
            raise ValueError(f"{row['recording_id']}: timestamps must be nonempty [T]")
        times = times.astype(np.float64)
        if not np.isfinite(times).all() or times[0] < 0 or times[-1] > row["duration"] or (np.diff(times) <= 0).any():
            raise ValueError(f"{row['recording_id']}: timestamps must be finite, increasing and within duration")
        if self.with_targets:
            labels, mask = make_targets(row, times, self.cfg.loss.boundary_width_seconds)
        else:
            labels = torch.zeros(len(times), 3)
            mask = torch.zeros(len(times), 3, dtype=torch.bool)
        return Recording(row, features, times, labels, mask)


def collate_recordings(records):
    """Do not pad/copy entire recordings: GPU tensors are built one chunk at a time."""
    return records


def iter_chunks(records: list[Recording], size: int):
    for start in range(0, max(map(len, records)), size):
        length = min(size, max(map(len, records)) - start)
        x = torch.zeros(len(records), length, records[0].features.shape[1])
        y = torch.zeros(len(records), length, 3)
        mask = torch.zeros(len(records), length, 3, dtype=torch.bool)
        for b, record in enumerate(records):
            count = min(length, len(record) - start)
            if count <= 0:
                continue
            data = np.asarray(record.features[start:start + count])
            if not np.isfinite(data).all():
                raise ValueError(f"{record.entry['recording_id']}: non-finite feature")
            x[b, :count] = torch.from_numpy(np.array(data, dtype=np.float32, copy=True))
            y[b, :count] = record.targets[start:start + count]
            mask[b, :count] = record.mask[start:start + count]
        yield x, y, mask


def manifest_fingerprint(cfg):
    rows = load_manifest(cfg.data.manifest, cfg.data.root)
    # Canonical JSON includes the annotation content and resolved source paths.
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
