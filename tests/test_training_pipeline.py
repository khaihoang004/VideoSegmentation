"""Behavioral tests for chronology, annotation safety, event metrics and resume."""

import copy
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
pytest.importorskip("yaml")

from videosegmentation.training.checkpoint import load_checkpoint
from videosegmentation.training.cli import main
from videosegmentation.training.config import Config, DecoderConfig, EvaluationConfig, config_from_dict, load_config
from videosegmentation.training.data import FeatureDataset, load_manifest, make_targets
from videosegmentation.training.demo import make_demo
from videosegmentation.training.metrics import evaluate_events
from videosegmentation.training.model import build_model
from videosegmentation.training.streaming import InstanceDecoder, replay_recording
from videosegmentation.training.trainer import Trainer


@pytest.fixture(autouse=True)
def cpu_threads():
    old = torch.get_num_threads()
    torch.set_num_threads(2)
    yield
    torch.set_num_threads(old)


def row():
    return {"schema_version": 1, "recording_id": "r1", "group_id": "g1", "split": "test",
            "view_domain": "exo", "task_definition_version": "task_v1", "duration": 20.0,
            "coverage": [[0, 20]], "instances": [
                {"instance_id": "i1", "start": 2.0, "end": 10.0, "status": "completed"}]}


def event(start=2.0, end=10.0, emitted=10.1, event_id="e1"):
    return {"recording_id": "r1", "start": start, "end": end,
            "observed_until": max(end, emitted), "emitted_at": emitted,
            "event_id": event_id, "confidence": 0.9, "status": "completed"}


def test_causal_model_prefix_suffix_and_chunk_state():
    cfg = Config().model
    cfg.input_dim, cfg.hidden_dim, cfg.num_layers = 8, 12, 2
    model = build_model(cfg).eval()
    x = torch.randn(2, 13, 8)
    with torch.no_grad():
        full, _ = model(x)
        prefix, state = model(x[:, :6])
        suffix, _ = model(x[:, 6:], state)
        changed = x.clone(); changed[:, 6:] = torch.randn_like(changed[:, 6:]) * 100
        altered, _ = model(changed)
    torch.testing.assert_close(prefix, full[:, :6])
    torch.testing.assert_close(torch.cat([prefix, suffix], 1), full)
    torch.testing.assert_close(altered[:, :6], full[:, :6])


def test_targets_pause_membership_aborted_end_and_unknown_mask():
    r = row()
    r["instances"] += [{"instance_id": "abort", "start": 12.0, "end": 14.0, "status": "aborted"},
                       {"instance_id": "unknown", "start": 16.0, "end": None, "status": "unknown"}]
    times = np.arange(20, dtype=float)
    targets, mask = make_targets(r, times, 0.0)
    assert targets[2:10, 0].eq(1).all()  # Whole-instance membership includes any pause.
    assert targets[12:14, 0].eq(1).all()
    assert targets[12, 1] == 1 and targets[14, 2] == 0
    assert targets[9, 2] == 0 and targets[10, 2] == 1  # Never reward early completion.
    assert not mask[16:].any()  # Unknown is not background.


def test_sparse_event_targets_quantize_forward_not_backward():
    r = row(); r["instances"][0].update(start=2.2, end=9.2)
    targets, _ = make_targets(r, np.arange(0, 20, 1.0), 0.0)
    assert targets[2, 1] == 0 and targets[3, 1] == 1
    assert targets[9, 2] == 0 and targets[10, 2] == 1


def test_manifest_rejects_group_and_path_leakage(tmp_path):
    first = row(); second = copy.deepcopy(first)
    first["split"] = "train"; second.update(recording_id="other", split="val")
    p = tmp_path / "manifest.jsonl"
    p.write_text(json.dumps(first) + "\n" + json.dumps(second))
    with pytest.raises(ValueError, match="leaks across splits"):
        load_manifest(p)
    second["group_id"] = "other_group"
    first["video_path"] = second["video_path"] = "same.avi"
    p.write_text(json.dumps(first) + "\n" + json.dumps(second))
    with pytest.raises(ValueError, match="Same media/features"):
        load_manifest(p)


def test_manifest_rejects_unaudited_features_and_overlapping_instances(tmp_path):
    r = row(); r["features"] = {"path": "x.npy", "timestamps_path": "t.npy", "encoder": "center_clip",
                              "causal": False, "timestamp_semantics": "last_observed_frame"}
    p = tmp_path / "manifest.jsonl"; p.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="audited causal"):
        load_manifest(p)
    r.pop("features")
    r["instances"].append({"instance_id": "overlap", "start": 9, "end": 15, "status": "completed"})
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError, match="non-overlapping"):
        load_manifest(p)


def test_decoder_preserves_pause_and_never_completes_at_eof():
    decoder = InstanceDecoder(DecoderConfig(), "r", "v1")
    assert decoder.update(1, [1, 0.9, 0]) == []
    assert decoder.update(5, [0, 0, 0]) == []  # Activity falls; still the same instance.
    assert decoder.summary()["open_start"] == 1
    emitted = decoder.update(10, [0, 0, 0.9])
    assert emitted[0]["start"] == 1 and emitted[0]["end"] == 10
    assert decoder.update(11, [0, 0, 0.9]) == []
    decoder.update(20, [1, 0.9, 0])
    assert decoder.summary()["open_start"] == 20
    assert decoder.summary()["completed_count"] == 1


def test_decoder_adjacent_instances_and_confirmation_latency():
    decoder = InstanceDecoder(DecoderConfig(completion_patience=2), "r", "v1")
    decoder.update(1, [1, 0.9, 0])
    decoder.update(2, [1, 0, 0])
    assert decoder.update(5, [1, 0.9, 0.9]) == []
    first = decoder.update(6, [1, 0.9, 0.9])
    assert first[0]["start"] == 1 and first[0]["end"] == 5
    assert first[0]["emitted_at"] == 6
    assert decoder.summary()["open_start"] == 5
    decoder.update(7, [1, 0, 0])
    decoder.update(9, [0, 0, 0.9])
    second = decoder.update(10, [0, 0, 0.9])
    assert second[0]["start"] == 5 and second[0]["end"] == 9
    assert first[0]["event_id"] != second[0]["event_id"]


def test_metrics_same_intervals_different_emission_and_spam():
    cfg = EvaluationConfig(tiou_thresholds=[0.5], max_latency_seconds=2)
    fast = evaluate_events([row()], [event()], cfg)
    slow = evaluate_events([row()], [event(emitted=18)], cfg)
    assert fast["mean_interval_ap"] == slow["mean_interval_ap"] == 1
    assert fast["completion"]["timely_recall"] == 1
    assert slow["completion"]["timely_recall"] == 0
    spam = evaluate_events([row()], [event(), event(event_id="e2")], cfg)
    assert spam["completion"]["false_completions"] == 1
    assert spam["completion"]["recall"] == 1


def test_early_completion_is_false_even_if_iou_matches():
    metrics = evaluate_events([row()], [event(end=9.5, emitted=9.7)], EvaluationConfig(tiou_thresholds=[0.5]))
    assert metrics["mean_interval_ap"] == 1
    assert metrics["completion"]["early_completions"] == 1
    assert metrics["completion"]["recall"] == 0
    assert metrics["completion"]["false_completions"] == 1


def test_unknown_is_ignored_but_aborted_false_completion_is_counted():
    r = row()
    r["instances"] += [{"instance_id": "abort", "start": 12, "end": 14, "status": "aborted"},
                       {"instance_id": "unknown", "start": 16, "end": 19, "status": "unknown"}]
    metrics = evaluate_events([r], [event(12, 14, 14.1), event(16, 18, 18.1, "e2")], EvaluationConfig())
    assert metrics["ignored_predictions"] == 1
    assert metrics["completion"]["false_completions"] == 1


def test_config_unknown_keys_and_bad_threshold_fail():
    with pytest.raises(ValueError, match="Unknown trainer keys"):
        config_from_dict({"trainer": {"epohs": 3}})
    with pytest.raises(ValueError, match="Thresholds"):
        config_from_dict({"decoder": {"completion_threshold": -1}})


def test_feature_dimension_and_nonmonotonic_time_validation(tmp_path):
    generated = make_demo(tmp_path / "demo")
    cfg = load_config(generated["config"])
    cfg.model.input_dim = 9
    with pytest.raises(ValueError, match="features must"):
        FeatureDataset(cfg, "train")[0]
    cfg.model.input_dim = 8
    path = tmp_path / "demo/demo_train_0.timestamps.npy"
    times = np.load(path); times[4] = times[3]; np.save(path, times)
    with pytest.raises(ValueError, match="timestamps must"):
        FeatureDataset(cfg, "train")[0]


def test_full_cli_fit_evaluate_predict_and_resume(tmp_path):
    generated = make_demo(tmp_path / "demo")
    cfg = load_config(generated["config"])
    cfg.trainer.epochs = 2
    cfg.model.num_layers, cfg.model.dropout = 2, 0.2
    # Train a full run and an interrupted/resumed run with identical schedules.
    full = copy.deepcopy(cfg); full.output_dir = str(tmp_path / "full")
    Trainer(full).fit()
    partial = copy.deepcopy(cfg); partial.output_dir = str(tmp_path / "resumed")
    Trainer(partial).fit(until_epoch=1)
    Trainer(partial, resume=Path(partial.output_dir) / "last.pt").fit()
    a = load_checkpoint(Path(full.output_dir) / "last.pt")
    b = load_checkpoint(Path(partial.output_dir) / "last.pt")
    assert a["global_step"] == b["global_step"]
    assert a["optimizer"]["param_groups"] == b["optimizer"]["param_groups"]
    assert a["scheduler"] == b["scheduler"]
    for key in a["model"]:
        torch.testing.assert_close(a["model"][key], b["model"][key], rtol=0, atol=0)
    checkpoint = str(Path(full.output_dir) / "best.pt")
    report = tmp_path / "evaluation.json"
    assert main(["evaluate", "--checkpoint", checkpoint, "--output", str(report), "--device", "cpu"]) == 0
    assert "metrics" in json.loads(report.read_text())
    prediction = tmp_path / "prediction.json"
    assert main(["predict", "--checkpoint", checkpoint, "--output", str(prediction), "--device", "cpu"]) == 0
    assert "metrics" not in json.loads(prediction.read_text())


def test_chunk_replay_logs_last_observed_frontier(tmp_path):
    generated = make_demo(tmp_path / "demo")
    cfg = load_config(generated["config"])
    record = FeatureDataset(cfg, "test")[1]

    class Scripted(torch.nn.Module):
        def forward(self, features, state=None):
            # A deterministic causal head driven by the synthetic current frame.
            logits = torch.stack([features[..., 0] * 10 - 5,
                                  features[..., 2] * 10 - 5,
                                  features[..., 3] * 10 - 5], dim=-1)
            return logits, state

    events, summary = replay_recording(Scripted(), record, cfg.decoder, torch.device("cpu"), 8)
    assert len(events) == 2
    for value in events:
        assert value["end"] <= value["observed_until"] <= value["emitted_at"]
        # Every chunk ends on timestamps 3.5, 7.5, ...; no backdated emissions.
        assert (value["observed_until"] + 0.5) % 4 == 0
    assert summary["feature_extraction_cost_included"] is False
