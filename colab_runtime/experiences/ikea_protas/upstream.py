"""Pinned author code. Never modify an existing upstream checkout silently."""

import hashlib
import importlib.util
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "ProTAS": ("https://github.com/Yuhan-Shen/ProTAS.git", "0f04ee6b3c4370ce22f9230bca42e9aabe47b428"),
    "IKEA_ASM_Dataset": ("https://github.com/IkeaASM/IKEA_ASM_Dataset.git", "6fc2d9ea67557ca748b43257e99e3beb6d3cf069"),
}
WEIGHTS_URL = "https://raw.githubusercontent.com/piergiaj/pytorch-i3d/05783d11f9632b25fe3d50395a9c9bb51f848d6d/models/rgb_imagenet.pt"
WEIGHTS_SHA256 = "2609088c2e8c868187c9921c50bc225329a9057ed75e76120e0b4a397a2c7538"


def checkout(name, *, fetch=False):
    url, commit = PINS[name]
    path = ROOT / "third_party" / name
    if not path.exists():
        if not fetch:
            raise ValueError("Run python -m experiences.ikea_protas setup first")
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", url, str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "checkout", "--detach", commit], check=True)
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"], text=True)
    if actual != commit or dirty:
        raise ValueError(f"Upstream {name} differs from pinned clean commit {commit}")
    return path


def module(name, relative):
    path = checkout(name) / relative
    spec = importlib.util.spec_from_file_location("ikea_official_" + name + "_" + path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
