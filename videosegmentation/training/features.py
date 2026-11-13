"""Frame-wise RGB -> ResNet18 features. Timestamps use decoded presentation PTS."""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile

import numpy as np
import torch

from .checkpoint import atomic_json
from .data import load_manifest
from .trainer import resolve_device, seed_everything


def extract_features(manifest, output_manifest, output_dir, *, root=None, sample_hz=2.0,
                     batch_size=32, weights="imagenet", device_name="auto", seed=42,
                     overwrite=False):
    try:
        import av
        import torchvision
        from torchvision.models import ResNet18_Weights, resnet18
        from torchvision.transforms import functional as TF
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ValueError("Install video extras: pip install -e '.[train,video]'") from error
    if not math.isfinite(sample_hz) or sample_hz <= 0 or batch_size <= 0:
        raise ValueError("sample_hz and batch_size must be positive")
    if weights not in {"imagenet", "none"}:
        raise ValueError("weights must be imagenet or none (debug only)")
    output = Path(output_dir).expanduser().resolve()
    destination = Path(output_manifest).expanduser().resolve()
    if destination == Path(manifest).expanduser().resolve():
        raise ValueError("Write a NEW feature manifest; preserve input annotations")
    output.mkdir(parents=True, exist_ok=True)
    # Weight payload/cache stays with the dataset on Drive, not a transient home.
    torch.hub.set_dir(str(output / ".cache/torch"))
    seed_everything(seed)
    device = resolve_device(device_name)
    encoder = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if weights == "imagenet" else None)
    encoder.fc = torch.nn.Identity()
    encoder.to(device).eval()
    entries = load_manifest(manifest, root)
    encoded_rows = []
    for row in entries:
        if not row.get("video_path"):
            raise ValueError(f"{row['recording_id']}: video_path is required")
        video = Path(row["video_path"])
        stat = video.stat()
        digest = hashlib.sha256((row["recording_id"] + str(video)).encode()).hexdigest()[:12]
        name = re.sub(r"[^a-zA-Z0-9_.-]", "_", row["recording_id"])[:60] + "-" + digest
        feature_path, time_path, info_path = (output / f"{name}{suffix}" for suffix in
                                               [".npy", ".timestamps.npy", ".json"])
        signature = {"video_path": str(video), "source_size": stat.st_size,
                     "source_mtime_ns": stat.st_mtime_ns, "sample_hz": sample_hz,
                     "weights": weights, "seed": seed, "encoder": "resnet18_framewise",
                     "preprocess": "full_frame_letterbox_224_imagenet_normalization",
                     "torchvision_version": str(torchvision.__version__)}
        cached = False
        if info_path.exists() and feature_path.exists() and time_path.exists() and not overwrite:
            info = json.loads(info_path.read_text())
            if info["signature"] != signature:
                raise ValueError(f"Feature cache differs for {row['recording_id']}; choose new output or --overwrite")
            f = np.load(feature_path, mmap_mode="r", allow_pickle=False)
            t = np.load(time_path, mmap_mode="r", allow_pickle=False)
            cached = f.shape == (info["frames"], 512) and t.shape == (info["frames"],)
            if not cached:
                raise ValueError(f"Incomplete feature cache {name}; inspect or use --overwrite")
        if not cached:
            with tempfile.TemporaryDirectory(prefix=name + "-", dir=output) as work:
                work = Path(work)
                tensors, pending_times, count = [], [], 0
                feature_binary, time_binary = work / "features.f32", work / "times.f64"
                with feature_binary.open("wb") as ff, time_binary.open("wb") as tf:
                    @torch.inference_mode()
                    def flush():
                        nonlocal count
                        if not tensors:
                            return
                        values = encoder(torch.stack(tensors).to(device)).float().cpu().numpy()
                        values.astype(np.float32).tofile(ff)
                        np.array(pending_times, dtype=np.float64).tofile(tf)
                        count += len(tensors)
                        tensors.clear(); pending_times.clear()

                    def append(frame, timestamp):
                        # Preserve the full view; default ImageNet center crop
                        # could hide the product/hand-over zone in an exo scene.
                        picture = ImageOps.pad(frame.to_image(), (224, 224),
                                               method=Image.Resampling.BILINEAR, color=(0, 0, 0))
                        tensor = TF.to_tensor(picture)
                        tensors.append(TF.normalize(tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]))
                        pending_times.append(timestamp)
                        if len(tensors) >= batch_size:
                            flush()

                    origin, last_time, last_selected, last_frame = None, -1.0, -1.0, None
                    next_sample = 0.0
                    with av.open(str(video)) as container:
                        if not container.streams.video:
                            raise ValueError(f"No video stream: {video}")
                        for frame in container.decode(video=0):
                            if frame.time is None:
                                raise ValueError(f"{video}: missing presentation timestamp; do not invent FPS")
                            if origin is None:
                                origin = float(frame.time)
                            timestamp = float(frame.time) - origin
                            if timestamp <= last_time:
                                raise ValueError(f"{video}: repeated/nonmonotonic PTS; inspect source")
                            last_time, last_frame = timestamp, frame
                            if timestamp + 1e-8 >= next_sample:
                                append(frame, timestamp)
                                last_selected = timestamp
                                next_sample = (math.floor(timestamp * sample_hz + 1e-8) + 1) / sample_hz
                    if last_frame is None:
                        raise ValueError(f"Empty video: {video}")
                    if last_time > row["duration"] + 1e-5:
                        raise ValueError(f"{video}: decoded timeline exceeds annotated duration")
                    if last_selected < last_time:
                        append(last_frame, last_time)
                    flush()
                features = np.lib.format.open_memmap(work / "features.npy", mode="w+", dtype=np.float32,
                                                    shape=(count, 512))
                binary = np.memmap(feature_binary, mode="r", dtype=np.float32, shape=(count, 512))
                for begin in range(0, count, 4096):
                    features[begin:begin + 4096] = binary[begin:begin + 4096]
                features.flush(); del features, binary
                times = np.fromfile(time_binary, dtype=np.float64)
                np.save(work / "timestamps.npy", times, allow_pickle=False)
                os.replace(work / "features.npy", feature_path)
                os.replace(work / "timestamps.npy", time_path)
                info = {"signature": signature, "frames": count, "feature_dim": 512,
                        "source_pts_origin_seconds": origin, "causal": True,
                        "timestamp_semantics": "last_observed_frame",
                        "note": "Frame-wise frozen encoder; extraction throughput is not streaming inference latency"}
                # Marker is committed last; a partial file pair is never a cache hit.
                atomic_json(info, info_path)
        row["features"] = {"path": str(feature_path), "timestamps_path": str(time_path),
                           "encoder": "resnet18_framewise", "weights": weights,
                           "causal": True, "timestamp_semantics": "last_observed_frame",
                           "metadata_path": str(info_path)}
        encoded_rows.append(row)
        print(f"{row['recording_id']}: {'cached' if cached else 'extracted'} {info['frames']} features", flush=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        temporary.write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in encoded_rows))
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"records": len(encoded_rows), "manifest": str(destination), "feature_dim": 512,
            "pretrained": weights == "imagenet"}
