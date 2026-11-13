"""Synthetic integration fixture. Never an IKEA annotation converter or benchmark."""

import json
from pathlib import Path

import numpy as np
import yaml

from .config import Config


def make_demo(output, seed=17):
    output = Path(output).expanduser().resolve()
    manifest = output / "manifest.jsonl"
    if manifest.exists():
        raise ValueError("Demo manifest exists; choose a new directory")
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(seed)
    rows = []
    for split, number in [("train", 6), ("val", 2), ("test", 2)]:
        for index in range(number):
            name = f"demo_{split}_{index}"
            times = np.arange(128, dtype=np.float64) * 0.5
            values = rng.normal(0, 0.08, (128, 8)).astype(np.float32)
            intervals = [(5.0, 19.0), (29.0, 45.0)] if index else []
            instances = []
            for i, (a, b) in enumerate(intervals):
                region = (times >= a) & (times < b)
                phase = (times[region] - a) / (b - a)
                values[region, 0] += 1
                values[region, 1] += phase
                values[(times >= a) & (times <= a + 0.5), 2] += 2
                values[(times >= b) & (times <= b + 0.5), 3] += 2
                # Motion can stop mid-instance without changing membership.
                values[region & ~((times > a + 5) & (times < a + 8)), 4] += 1
                instances.append({"instance_id": f"{name}_{i}", "start": a, "end": b,
                                  "status": "completed"})
            np.save(output / f"{name}.npy", values, allow_pickle=False)
            np.save(output / f"{name}.timestamps.npy", times, allow_pickle=False)
            rows.append({"schema_version": 1, "recording_id": name, "group_id": name,
                         "split": split, "view_domain": "exo", "dataset": "synthetic_debug_only",
                         "task_definition_version": "demo_v1", "duration": 64.0,
                         "coverage": [[0, 64]], "instances": instances,
                         "features": {"path": f"{name}.npy", "timestamps_path": f"{name}.timestamps.npy",
                                      "causal": True, "encoder": "synthetic_debug_only",
                                      "timestamp_semantics": "last_observed_frame"}})
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    cfg = Config()
    cfg.data.manifest = str(manifest)
    cfg.data.task_definition_version = "demo_v1"
    cfg.data.batch_size = 2
    cfg.model.input_dim, cfg.model.hidden_dim, cfg.model.num_layers = 8, 24, 1
    cfg.model.dropout = 0.0
    cfg.trainer.epochs, cfg.trainer.chunk_size, cfg.trainer.num_threads = 3, 32, 2
    cfg.trainer.device, cfg.trainer.amp = "cpu", False
    cfg.evaluation.inference_chunk_size = 8
    cfg.output_dir = str(output / "run")
    config = output / "config.yaml"
    config.write_text(yaml.safe_dump(cfg.to_dict(), sort_keys=False))
    return {"config": str(config), "manifest": str(manifest), "synthetic_only": True}
