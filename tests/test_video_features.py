"""Optional real decode test: no network or pretrained-weight download."""

import json
from fractions import Fraction
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
av = pytest.importorskip("av")
pytest.importorskip("yaml")
pytest.importorskip("torchvision")

from videosegmentation.training.features import extract_features


def test_pts_feature_extraction_resume_and_config_conflict(tmp_path):
    torch.set_num_threads(2)
    video = tmp_path / "small.mkv"
    with av.open(str(video), "w") as output:
        stream = output.add_stream("ffv1", rate=4)
        stream.width, stream.height, stream.pix_fmt = 64, 48, "yuv420p"
        for index in range(9):
            frame = av.VideoFrame.from_ndarray(np.full((48, 64, 3), index * 20, dtype=np.uint8), format="rgb24")
            frame.pts, frame.time_base = index, Fraction(1, 4)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    row = {"schema_version": 1, "recording_id": "real_decode", "group_id": "g", "split": "train",
           "view_domain": "exo", "task_definition_version": "task_v1", "video_path": str(video),
           "duration": 2.25, "coverage": [[0, 2.25]], "instances": []}
    source = tmp_path / "source.jsonl"; source.write_text(json.dumps(row))
    dest = tmp_path / "features.jsonl"
    result = extract_features(source, dest, tmp_path / "features", sample_hz=2,
                              weights="none", device_name="cpu", batch_size=2)
    assert result["pretrained"] is False
    encoded = json.loads(dest.read_text())
    timestamps = np.load(encoded["features"]["timestamps_path"])
    np.testing.assert_allclose(timestamps, [0, 0.5, 1, 1.5, 2])
    assert np.load(encoded["features"]["path"]).shape == (5, 512)
    assert encoded["features"]["causal"] is True
    path = encoded["features"]["path"]
    before = Path(path).stat().st_mtime_ns
    extract_features(source, dest, tmp_path / "features", sample_hz=2,
                     weights="none", device_name="cpu", batch_size=4)
    assert Path(path).stat().st_mtime_ns == before
    with pytest.raises(ValueError, match="cache differs"):
        extract_features(source, dest, tmp_path / "features", sample_hz=1,
                         weights="none", device_name="cpu")
