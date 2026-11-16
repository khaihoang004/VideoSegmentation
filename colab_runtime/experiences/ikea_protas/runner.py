"""Thin experiment runner around the pinned ProTAS model and preprocessing utilities.

The objective is the author's CE + clipped temporal MSE + progress MSE + graph
loss with Adam. Extra code handles IKEA paths, durable resume, and metric bugs.
"""

import json
import logging
import os
import platform
from pathlib import Path
import random
import shutil
import time

import numpy as np
import torch
import torch.nn.functional as F

from videosegmentation.training.checkpoint import atomic_json, atomic_save, random_state, restore_random_state
from .data import sampled_labels, signature
from .upstream import module, digest, PINS


def prepare(index, cache_dir, output_dir):
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    index_id = signature(index)
    identity_file = output / "index_identity.json"
    if identity_file.exists() and json.loads(identity_file.read_text())["index_sha256"] != index_id:
        raise ValueError("Partial preparation belongs to a different index; use a new folder")
    atomic_json(dict(index_sha256=index_id), identity_file)
    existing = output / "prepared.json"
    if existing.exists():
        report = json.loads(existing.read_text())
        if report["index_sha256"] != index_id:
            raise ValueError("Prepared dataset/index differs; choose a new output folder")
        return report
    labels = index["labels"]
    mapping = "".join(f"{i}|{label}\n" for i, label in enumerate(labels))
    (output / "mapping.txt").write_text(mapping)
    gt = output / "groundTruth"
    graph_input = output / "train_graph_input"
    gt.mkdir(exist_ok=True)
    (graph_input / "groundTruth").mkdir(parents=True, exist_ok=True)
    (graph_input / "mapping.txt").write_text(mapping)
    records, feature_settings = [], None
    for record in index["records"]:
        cache = Path(cache_dir).resolve() / record["key"]
        marker = cache / "complete.json"
        if not marker.is_file():
            raise ValueError("Finish feature extraction first: " + record["recording_id"])
        info = json.loads(marker.read_text())
        if info["signature"]["recording_id"] != record["recording_id"]:
            raise ValueError("Feature recording mismatch")
        settings = info["signature"]["settings"]
        if feature_settings is not None and settings != feature_settings:
            raise ValueError("Mixed feature settings are not a controlled baseline")
        feature_settings = settings
        for name, sha in info["checksums"].items():
            if digest(cache / name) != sha:
                raise ValueError("Feature checksum mismatch: " + str(cache / name))
        frames = np.load(cache / "frame_indices.npy", allow_pickle=False)
        features = np.load(cache / "features.npy", mmap_mode="r", allow_pickle=False)
        y = sampled_labels(record, frames)
        if features.shape != (1024, len(y)):
            raise ValueError("Feature/target dimensions do not match")
        name = record["key"] + ".txt"
        text = "".join(labels[i] + "\n" for i in y)
        (gt / name).write_text(text)
        if record["split"] == "train":
            (graph_input / "groundTruth" / name).write_text(text)
        records.append({**record, "cache_dir": str(cache), "feature_checksums": info["checksums"]})
    # Use the actual author utilities on TRAIN ONLY: their default script loops
    # over all groundTruth files, which would leak test order into the graph.
    module("ProTAS", "utils/write_progress_values.py").write_progress_values(str(graph_input), [0], "|")
    module("ProTAS", "utils/write_graph.py").write_graph_from_transcripts(str(graph_input), [0], "|")
    for split in ("train", "test"):
        (output / (split + ".bundle")).write_text("".join(r["key"] + ".txt\n" for r in records if r["split"] == split))
    report = dict(index_sha256=index_id, scope=index["scope"], labels=labels, records=records,
                  feature_settings=feature_settings, split_protocol=index["split_protocol"],
                  graph_source="train_only", graph_sha256=digest(graph_input / "graph/graph.pkl"),
                  progress_contract="official_(arange(segment_length)+1)/segment_length; NA=0",
                  model_source=PINS["ProTAS"][0], model_commit=PINS["ProTAS"][1])
    committed = [output / "mapping.txt", output / "train.bundle", output / "test.bundle",
                 graph_input / "graph/graph.pkl"]
    committed += list(gt.glob("*.txt")) + list((graph_input / "progress").glob("*.npy"))
    report["prepared_checksums"] = {str(p.relative_to(output)): digest(p) for p in committed}
    atomic_json(report, existing)
    return report


def stage(data_dir, local_dir):
    """Cache only the compact training inputs locally, preserving Drive outputs."""
    data = Path(data_dir).resolve()
    report = json.loads((data / "prepared.json").read_text())
    identity = digest(data / "prepared.json")
    local = Path(local_dir).resolve() / identity[:20]
    paths = []
    for r in report["records"]:
        paths.append((Path(r["cache_dir"]) / "features.npy", Path("features") / (r["key"] + ".npy"), r["feature_checksums"]["features.npy"]))
        paths.append((data / "groundTruth" / (r["key"] + ".txt"), Path("groundTruth") / (r["key"] + ".txt"), None))
        if r["split"] == "train":
            paths.append((data / "train_graph_input/progress" / (r["key"] + ".npy"), Path("progress") / (r["key"] + ".npy"), None))
    paths += [(data / name, Path(name), None) for name in ("train.bundle", "test.bundle", "mapping.txt")]
    paths.append((data / "train_graph_input/graph/graph.pkl", Path("graph/graph.pkl"), report["graph_sha256"]))
    local.mkdir(parents=True, exist_ok=True)
    needed = sum(src.stat().st_size for src, dest, sha in paths if not (local / dest).is_file())
    if shutil.disk_usage(local).free < needed + 1024**3:
        raise ValueError("Not enough local disk to stage features plus 1 GiB reserve")
    for src, relative, expected in paths:
        dst = local / relative
        expected = expected or report["prepared_checksums"][str(src.relative_to(data))]
        if dst.is_file() and digest(dst) == expected:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        temp = dst.with_suffix(dst.suffix + ".tmp")
        shutil.copy2(src, temp)
        if digest(temp) != expected:
            temp.unlink(missing_ok=True)
            raise ValueError("Staged data checksum mismatch")
        os.replace(temp, dst)
    return report, local, identity


def make_trainer(report, local, *, device, seed=1538574472, graph_reference_fix=False):
    random.seed(seed)
    np.random.seed(seed % 2**32)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    trainer = module("ProTAS", "model.py").Trainer(
        4, 10, 64, report["feature_settings"]["feature_dim"], len(report["labels"]),
        causal=True, logger=logging.getLogger("ikea_protas"), progress_lw=1.0,
        use_graph=True, graph_lw=0.1, init_graph_path=str(local / "graph/graph.pkl"), learnable=True)
    if graph_reference_fix:
        # Upstream nn.Parameter(self.matrix_pre) aliases the trainable storage,
        # so its supposedly fixed reference moves and regularization is zero.
        # CUDA transfer already separates the two Parameters in current Torch;
        # cloning also makes CPU training and checkpoint reload well-defined.
        graph = trainer.model.graph_learner
        graph.matrix_pre_original = torch.nn.Parameter(graph.matrix_pre.detach().clone(), requires_grad=False)
    trainer.model.to(device)
    return trainer


def official_loss(trainer, predictions, progress_predictions, target, progress_target, mask):
    # Same formula, reduction, detach placement and stage sum as model.py:Trainer.train.
    loss, progress_loss = 0, 0
    for p, progress in zip(predictions, progress_predictions):
        loss += trainer.ce(p.transpose(2, 1).contiguous().view(-1, trainer.num_classes), target.view(-1))
        loss += 0.15 * torch.mean(torch.clamp(trainer.mse(F.log_softmax(p[:, :, 1:], dim=1),
                                                         F.log_softmax(p.detach()[:, :, :-1], dim=1)),
                                               min=0, max=16) * mask[:, :, 1:])
        progress_loss += trainer.mse(progress, progress_target).mean()
    graph_loss = trainer.model.graph_learner(predictions[-1], progress_predictions[-1])
    return loss + trainer.progress_lw * progress_loss + trainer.graph_lw * graph_loss


def fit(data_dir, run_dir, local_dir, *, epochs=50, epochs_this_session=1, device="cuda",
        checkpoint_every=5, max_seconds=5400, max_records=None,
        graph_reference_fix=False, minimum_steps=0):
    if (min(epochs, epochs_this_session, checkpoint_every) < 1 or max_seconds <= 0
            or (max_records is not None and max_records < 1) or minimum_steps < 0):
        raise ValueError("Epochs, checkpoint interval and session budget must be positive")
    report, local, data_sha = stage(data_dir, local_dir)
    nominal_epochs = epochs
    training_recordings = sum(r['split'] == 'train' for r in report['records'])
    if not training_recordings:
        raise ValueError('Cannot train without training recordings')
    if minimum_steps:
        epochs = max(epochs, (minimum_steps + training_recordings - 1) // training_recordings)
    run = Path(run_dir).resolve()
    run.mkdir(parents=True, exist_ok=True)
    config = dict(model="official_ProTAS_CAS_APP_TG", model_commit=PINS["ProTAS"][1],
                  data_sha256=data_sha, total_epochs=epochs, seed=1538574472,
                  optimizer="Adam", lr=0.0005, batch_size=1, amp=False,
                  num_stages=4, num_layers=10, num_f_maps=64,
                  feature_settings=report["feature_settings"], scope=report["scope"])
    # Leave old author-profile config byte-for-byte compatible for resume.
    if graph_reference_fix:
        config['graph_reference_fix'] = True
    if minimum_steps:
        config.update(minimum_optimizer_steps=minimum_steps, nominal_epochs=nominal_epochs)
    trainer = make_trainer(report, local, device=device, graph_reference_fix=graph_reference_fix)
    opt = torch.optim.Adam(trainer.model.parameters(), lr=0.0005)
    generator = torch.Generator().manual_seed(config["seed"])
    batch = module("ProTAS", "batch_gen.py").BatchGenerator(len(report["labels"]),
        {s: i for i, s in enumerate(report["labels"])}, str(local / "groundTruth") + "/",
        str(local / "features") + "/", str(local / "progress") + "/", 1, False)
    batch.read_data(str(local / "train.bundle"))
    epoch, steps, partial = 0, 0, dict(loss=0., correct=0., total=0., recordings=0)
    last = run / "last.pt"
    if last.is_file():
        saved = torch.load(last, map_location="cpu", weights_only=True)
        if saved.get("kind") != "ikea_official_protas" or saved["config"] != config:
            raise ValueError("Checkpoint data/model/config differ; use a different run folder")
        trainer.model.load_state_dict(saved["model"])
        opt.load_state_dict(saved["optimizer"])
        epoch, steps, partial = saved["completed_epochs"], saved["optimizer_steps"], saved["partial"]
        batch.list_of_examples, batch.index = saved["batch_order"], saved["next_recording"]
        restore_random_state(saved["rng"], generator)
    elif (run / "run.json").exists():
        raise ValueError("Run metadata exists without checkpoint; inspect before overwriting")
    atomic_json(config, run / "run.json")

    def save():
        atomic_save(dict(kind="ikea_official_protas", format_version=1, config=config,
                         model=trainer.model.state_dict(), optimizer=opt.state_dict(),
                         completed_epochs=epoch, optimizer_steps=steps, partial=partial,
                         batch_order=batch.list_of_examples, next_recording=batch.index,
                         rng=random_state(generator)), last)

    if not last.exists():
        save()
    limit, began, processed = min(epochs, epoch + epochs_this_session), time.monotonic(), 0
    trainer.model.train()
    stopped = "epoch_limit"
    while epoch < limit:
        while batch.has_next():
            x, target, progress, mask = [a.to(device) for a in batch.next_batch(1)]
            opt.zero_grad()
            predictions, progress_predictions = trainer.model(x, mask)
            loss = official_loss(trainer, predictions, progress_predictions, target, progress, mask)
            if not torch.isfinite(loss):
                raise ValueError("Non-finite official objective; checkpoint remains at last committed recording")
            loss.backward()
            opt.step()
            steps += 1
            processed += 1
            partial["loss"] += float(loss.detach())
            partial["correct"] += float(((predictions[-1].argmax(1) == target).float() * mask[:, 0, :]).sum())
            partial["total"] += float(mask[:, 0, :].sum())
            partial["recordings"] += 1
            print(json.dumps(dict(epoch_in_progress=epoch + 1, recording=batch.index,
                                  train_recordings=len(batch.list_of_examples), loss=float(loss.detach()),
                                  optimizer_steps=steps)), flush=True)
            if steps % checkpoint_every == 0:
                save()
            if time.monotonic() - began >= max_seconds or (max_records is not None and processed >= max_records):
                save()
                stopped = "session_budget_at_recording_boundary"
                return dict(completed_epochs=epoch, optimizer_steps=steps, next_recording=batch.index,
                            schedule_complete=False, stopped=stopped, scope=report["scope"])
        epoch += 1
        metrics = dict(epoch=epoch, loss=partial["loss"] / partial["recordings"],
                       accuracy=partial["correct"] / partial["total"], scope=report["scope"])
        partial = dict(loss=0., correct=0., total=0., recordings=0)
        batch.reset()  # Preserve the author's in-place shuffle, including RNG on resume.
        save()
        atomic_json(metrics, run / "metrics" / f"epoch_{epoch:04d}.json")
    return dict(completed_epochs=epoch, optimizer_steps=steps, schedule_complete=epoch >= epochs,
                stopped=stopped, scope=report["scope"])


def segments(prediction, labels):
    """Maximal constant-label intervals, original frame indices, [start,end)."""
    prediction = np.asarray(prediction)
    if prediction.ndim != 1 or not len(prediction):
        raise ValueError('Expected nonempty one-dimensional frame predictions')
    edges = np.r_[0, np.flatnonzero(prediction[1:] != prediction[:-1]) + 1, len(prediction)]
    return [dict(start_frame=int(a), end_frame=int(b), label_id=int(prediction[a]),
                 label=labels[int(prediction[a])]) for a, b in zip(edges[:-1], edges[1:])]


def evaluate(data_dir, run_dir, local_dir, *, device="cuda"):
    report, local, data_sha = stage(data_dir, local_dir)
    run = Path(run_dir).resolve()
    saved = torch.load(run / "last.pt", map_location="cpu", weights_only=True)
    if saved["config"]["data_sha256"] != data_sha:
        raise ValueError("Test data or training inputs differ from frozen run")
    if saved["completed_epochs"] != saved["config"]["total_epochs"] or saved["partial"]["recordings"]:
        raise ValueError("Complete the fixed epoch schedule before final test")
    # Independent reference storage is necessary to load CUDA checkpoints on
    # CPU: otherwise loading the saved reference overwrites the learned graph.
    trainer = make_trainer(report, local, device=device, graph_reference_fix=True)
    trainer.model.load_state_dict(saved["model"])
    trainer.model.eval()
    official = module("ProTAS", "eval.py")
    # Compatibility fix only: author's np.float alias was removed in NumPy 1.24.
    class NumpyCompat:
        def __getattr__(self, name):
            return float if name == "float" else getattr(np, name)
    official.np = NumpyCompat()
    totals = dict(correct=0, frames=0, correct_no_bg=0, frames_no_bg=0, edit=0.)
    counts = np.zeros((3, 3))
    records = []
    labels = report["labels"]
    pred_dir = run / "predictions"
    pred_dir.mkdir(exist_ok=True)
    with torch.inference_mode():
        for record in report["records"]:
            if record["split"] != "test":
                continue
            features = np.load(local / "features" / (record["key"] + ".npy"), allow_pickle=False)
            x = torch.from_numpy(features.astype(np.float32)).unsqueeze(0).to(device)
            logits, progress = trainer.model(x, torch.ones_like(x))
            logits = trainer.model.graph_learner.inference(logits[-1], progress[-1])
            sampled = logits.argmax(1)[0].cpu().numpy()
            frame_ids = np.load(Path(record["cache_dir"]) / "frame_indices.npy", allow_pickle=False)
            dense_frames = np.arange(record["nframes"])
            prediction = sampled[np.searchsorted(frame_ids, dense_frames, side="right") - 1]
            target = sampled_labels(record, dense_frames)
            gt, pred = [labels[i] for i in target], [labels[i] for i in prediction]
            totals["correct"] += int((target == prediction).sum())
            totals["frames"] += len(target)
            totals["correct_no_bg"] += int(((target == prediction) & (target != 0)).sum())
            totals["frames_no_bg"] += int((target != 0).sum())
            has_gt, has_pred = bool((target != 0).any()), bool((prediction != 0).any())
            edit = official.edit_score(pred, gt, bg_class=["NA"]) if has_gt or has_pred else 100.
            totals["edit"] += float(edit)
            for i, overlap in enumerate((.1, .25, .5)):
                if has_gt:
                    counts[i] += official.f_score(pred, gt, overlap, bg_class=["NA"])
                else:
                    counts[i] += [0, len(official.get_labels_start_end_time(pred, ["NA"])[0]), 0]
            np.save(pred_dir / (record["key"] + ".npy"), prediction, allow_pickle=False)
            gt_segments, pred_segments = segments(target, labels), segments(prediction, labels)
            segment_path = run / 'segments' / (record['key'] + '.json')
            atomic_json(dict(recording_id=record['recording_id'], grid='original_SQLite_frame_grid',
                             interval='start_inclusive_end_exclusive', ground_truth=gt_segments,
                             prediction=pred_segments), segment_path)
            records.append(dict(recording_id=record["recording_id"], frames=len(target), edit=float(edit),
                                gt_foreground_segments=sum(s['label_id'] != 0 for s in gt_segments),
                                predicted_foreground_segments=sum(s['label_id'] != 0 for s in pred_segments),
                                segment_file=str(segment_path)))
    f1 = [float(200 * tp / (2 * tp + fp + fn)) if 2 * tp + fp + fn else 0. for tp, fp, fn in counts]
    result = dict(dataset="IKEA_ASM", task="atomic_action_segmentation", scope=report["scope"],
                  checkpoint_sha256=digest(run / "last.pt"), model_commit=PINS["ProTAS"][1],
                  feature_settings=report["feature_settings"], completed_epochs=saved["completed_epochs"],
                  metrics=dict(Acc=100 * totals["correct"] / totals["frames"],
                               Acc_no_NA=100 * totals["correct_no_bg"] / max(1, totals["frames_no_bg"]),
                               Edit=totals["edit"] / len(records), **dict(zip(("F1@10", "F1@25", "F1@50"), f1))),
                  metric_grid="original_SQLite_frame_grid; previous-observation_hold_from_causal_samples",
                  adaptations=["IKEA_exocentric_cross_environment", "RGB_only_I3D_1024_not_paper_2048",
                               "train_only_graph", "numpy_float_compat_and_empty_gt_guards"],
                  same_as_paper_benchmark=False, records=records)
    result["runtime"] = dict(torch=str(torch.__version__), numpy=np.__version__, python=platform.python_version(),
                             cuda=torch.version.cuda, device=str(device),
                             gpu=torch.cuda.get_device_name(0) if str(device).startswith("cuda") else None)
    result['training_profile'] = dict(graph_reference_fix=saved['config'].get('graph_reference_fix', False),
                                      minimum_optimizer_steps=saved['config'].get('minimum_optimizer_steps', 0),
                                      optimizer_steps=saved['optimizer_steps'])
    atomic_json(result, run / "test.json")
    return result
