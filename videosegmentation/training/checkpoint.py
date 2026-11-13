"""Atomic epoch-boundary checkpoints, including optimizer and random generators."""

import json
import os
from pathlib import Path
import random
import uuid

import numpy as np
import torch


def atomic_json(value, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_save(value, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        torch.save(value, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_checkpoint(path):
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or payload.get("format_version") != 1:
        raise ValueError("Unsupported checkpoint format")
    return payload


def random_state(generator):
    rng = np.random.get_state()
    return {"python": random.getstate(),
            "numpy": {"name": rng[0], "keys": rng[1].tolist(), "position": rng[2],
                      "has_gauss": rng[3], "cached_gauss": rng[4]},
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "loader": generator.get_state()}


def restore_random_state(value, generator):
    random.setstate(value["python"])
    rng = value["numpy"]
    np.random.set_state((rng["name"], np.array(rng["keys"], dtype=np.uint32), rng["position"],
                         rng["has_gauss"], rng["cached_gauss"]))
    torch.set_rng_state(value["torch"])
    generator.set_state(value["loader"])
    if value["cuda"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(value["cuda"])
