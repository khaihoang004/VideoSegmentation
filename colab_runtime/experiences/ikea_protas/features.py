"""Causal RGB-only I3D input adaptation; one local video copy at a time."""

from collections import deque
import json
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np
import torch

from videosegmentation.training.checkpoint import atomic_json
from .upstream import module, digest, PINS, WEIGHTS_SHA256


def encoder(weights_path, device):
    if digest(weights_path) != WEIGHTS_SHA256:
        raise ValueError("I3D pretrained weight checksum differs from the pinned asset")
    model = module("IKEA_ASM_Dataset", "action/clip_based/i3d/pytorch_i3d.py").InceptionI3d(400, in_channels=3)
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
    return model.eval().to(device)


def prepare_features(index, output_dir, weights_path, *, stride=2, batch_size=1, device="cuda",
                     max_new_records=None, scratch=None):
    import av
    from PIL import Image
    if stride < 1 or batch_size < 1 or (max_new_records is not None and max_new_records < 1):
        raise ValueError("stride, batch_size and max_new_records must be positive")
    if device == "cuda" and not torch.cuda.is_available():
        raise ValueError("No CUDA GPU; select a GPU runtime or explicitly use --device cpu")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    settings = dict(encoder="official_ikea_rgb_i3d_kinetics", feature_dim=1024,
                    weights_sha256=digest(weights_path), history_frames=32, stride_frames=stride,
                    resize_short_side=256, center_crop=224, normalization="rgb_float_minus1_plus1",
                    timestamp_semantics="last_observed_frame", causal=True,
                    ikea_commit=PINS["IKEA_ASM_Dataset"][1], adaptation="RGB_only_1024_vs_paper_2048")
    model, completed, created = None, [], 0
    for record in index["records"]:
        source = Path(record["video_path"])
        stat = source.stat()
        expected = dict(settings=settings, recording_id=record["recording_id"],
                        source_path=str(source), source_bytes=stat.st_size, source_mtime_ns=stat.st_mtime_ns,
                        expected_nframes=record["nframes"])
        target = output / record["key"]
        marker = target / "complete.json"
        if marker.is_file():
            old = json.loads(marker.read_text())
            if old["signature"] != expected:
                raise ValueError("Feature cache changed; choose a new output: " + str(target))
            for name, sha in old["checksums"].items():
                if not (target / name).is_file() or digest(target / name) != sha:
                    raise ValueError("Incomplete/corrupt committed feature cache: " + str(target))
            completed.append(record["key"])
            continue
        if max_new_records is not None and created >= max_new_records:
            continue
        if model is None:
            model = encoder(weights_path, device)
        target.mkdir(parents=True, exist_ok=True)
        # Copy only this video to ephemeral disk. Never modify a source video.
        scratch_root = Path(scratch) if scratch else Path(tempfile.gettempdir())
        scratch_root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(scratch_root).free < stat.st_size + 1024**3:
            raise ValueError("Not enough local scratch for one video plus 1 GiB reserve")
        print("Extracting:", record["recording_id"], flush=True)
        with tempfile.TemporaryDirectory(prefix="ikea-video-", dir=scratch_root) as work:
            work = Path(work)
            local = work / ("video" + source.suffix)
            shutil.copy2(source, local)
            if local.stat().st_size != stat.st_size:
                raise ValueError("Incomplete local video copy")
            source_sha = digest(local)
            history, frame_ids, timestamps = deque(maxlen=32), [], []
            chunks, ndecoded, previous_time, origin = [], 0, None, None
            # Reuse a fixed host buffer: repeatedly allocating/normalizing large
            # float clips interleaved with PIL buffers can fragment the CPU heap.
            cpu_batch = torch.empty(batch_size, 3, 32, 224, 224, dtype=torch.float32)
            pending_count = 0

            @torch.inference_mode()
            def flush():
                nonlocal pending_count
                if pending_count:
                    x = cpu_batch[:pending_count].to(device)
                    values = model.extract_features(x).mean(dim=(2, 3, 4)).float().cpu().numpy()
                    chunks.append(values.copy())
                    pending_count = 0

            with av.open(str(local)) as container:
                container.streams.video[0].thread_count = 1
                for i, frame in enumerate(container.decode(video=0)):
                    ndecoded = i + 1
                    if i >= record["nframes"]:
                        # Some released AVI files carry one trailing frame more
                        # than SQLite. The original loader uses only nframes.
                        continue
                    if frame.time is None:
                        raise ValueError("Decoded frame has no PTS")
                    t = float(frame.time)
                    if previous_time is not None and t <= previous_time:
                        raise ValueError("Repeated/nonmonotonic video PTS")
                    previous_time = t
                    origin = t if origin is None else origin
                    im = frame.to_image().convert("RGB")
                    w, h = im.size
                    scale = 256 / min(w, h)
                    im = im.resize((round(w * scale), round(h * scale)), Image.Resampling.BILINEAR)
                    w, h = im.size
                    im = im.crop(((w - 224) // 2, (h - 224) // 2, (w - 224) // 2 + 224, (h - 224) // 2 + 224))
                    history.append(np.array(im, dtype=np.uint8))
                    if i % stride == 0:
                        # Left padding repeats only an already observed first frame.
                        frames = [history[0]] * (32 - len(history)) + list(history)
                        x = torch.from_numpy(np.stack(frames)).permute(3, 0, 1, 2)
                        cpu_batch[pending_count].copy_(x).div_(127.5).sub_(1)
                        pending_count += 1
                        frame_ids.append(i)
                        timestamps.append(t - origin)
                        if pending_count == batch_size:
                            flush()
                        if len(frame_ids) % 128 == 0:
                            print(f"  {record['recording_id']}: decoded={i + 1}/{record['nframes']}, features={len(frame_ids)}", flush=True)
            flush()
            if not record["nframes"] <= ndecoded <= record["nframes"] + 1:
                raise ValueError(f"Frame count mismatch for {record['recording_id']}: decoded {ndecoded}, SQLite {record['nframes']}")
            values = np.concatenate(chunks)
            if values.shape != (len(frame_ids), 1024) or not np.isfinite(values).all():
                raise ValueError("Invalid I3D features")
            # Marker is committed last. An interrupted record is recomputed safely.
            arrays = dict(features=values.T, frame_indices=np.array(frame_ids, dtype=np.int64),
                          timestamps=np.array(timestamps, dtype=np.float64))
            for name, value in arrays.items():
                temporary = target / (name + ".tmp")
                with temporary.open("wb") as stream:
                    np.save(stream, value, allow_pickle=False)
                os.replace(temporary, target / (name + ".npy"))
            atomic_json(dict(signature=expected, source_sha256=source_sha, decoded_frames=ndecoded,
                             used_frames=record["nframes"], trailing_unannotated_frames=ndecoded - record["nframes"],
                             checksums={name + ".npy": digest(target / (name + ".npy")) for name in arrays}), marker)
        created += 1
        completed.append(record["key"])
    return dict(new_records=created, ready=len(completed), total=len(index["records"]),
                all_ready=len(completed) == len(index["records"]), settings=settings)
