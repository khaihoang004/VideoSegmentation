"""Single-task interval and emitted-completion metrics with one-to-one matching."""

import numpy as np

from .data import interval_covered, labelled_ranges, supervised_instance


def tiou(a, b):
    overlap = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    return overlap / max(a["end"] - a["start"] + b["end"] - b["start"] - overlap, 1e-12)


def _ap(tp, fp, total):
    if not total:
        return None
    if not tp:
        return 0.0
    tp, fp = np.cumsum(tp), np.cumsum(fp)
    recall, precision = tp / total, tp / np.maximum(tp + fp, 1)
    r = np.concatenate([[0.0], recall, [1.0]])
    p = np.concatenate([[0.0], precision, [0.0]])
    p = np.maximum.accumulate(p[::-1])[::-1]
    return float(np.sum((r[1:] - r[:-1]) * p[1:]))


def _prf(tp, predicted, truth):
    precision = tp / predicted if predicted else 0.0
    recall = tp / truth if truth else 0.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def evaluate_events(entries, events, cfg):
    rows = {r["recording_id"]: r for r in entries}
    truth, ignored_gt, valid_seconds = {}, 0, 0.0
    ranges = {}
    for key, row in rows.items():
        ranges[key] = labelled_ranges(row)
        valid_seconds += sum(b - a for a, b in ranges[key])
        truth[key] = []
        for item in row["instances"]:
            if item["status"] != "completed":
                continue
            if supervised_instance(item) and interval_covered(item["start"], item["end"], ranges[key]):
                truth[key].append(item)
            else:
                ignored_gt += 1
    valid, ignored_predictions = [], 0
    seen_ids = set()
    for event in events:
        key = event["recording_id"]
        if key not in rows:
            raise ValueError(f"Unknown prediction recording_id {key}")
        if event["event_id"] in seen_ids:
            raise ValueError("Repeated event_id in event log; do not silently deduplicate model outputs")
        seen_ids.add(event["event_id"])
        if not (0 <= event["start"] < event["end"] <= event["observed_until"] <= event["emitted_at"]):
            raise ValueError("Invalid event interval/clocks")
        if interval_covered(event["start"], event["end"], ranges[key]):
            valid.append(event)
        else:
            ignored_predictions += 1
    valid.sort(key=lambda x: (-x["confidence"], x["emitted_at"], x["event_id"]))
    total = sum(map(len, truth.values()))
    result = {"gt_instances": total, "predicted_instances": len(valid),
              "ignored_gt_instances": ignored_gt, "ignored_predictions": ignored_predictions,
              "labelled_seconds": valid_seconds,
              "total_recording_seconds": sum(r["duration"] for r in entries),
              "timing_mode": "feature_replay_simulated", "feature_extraction_cost_included": False}
    aps = []
    for threshold in cfg.tiou_thresholds:
        used, tps, fps, errors = set(), [], [], []
        for event in valid:
            key = event["recording_id"]
            choices = [(tiou(event, item), i, item) for i, item in enumerate(truth[key]) if (key, i) not in used]
            score, index, gt = max(choices, key=lambda x: x[0]) if choices else (0, -1, None)
            matched = gt is not None and score >= threshold
            tps.append(int(matched)); fps.append(int(not matched))
            if matched:
                used.add((key, index))
                errors.append((abs(event["start"] - gt["start"]), abs(event["end"] - gt["end"])))
        ap = _ap(tps, fps, total)
        if ap is not None:
            aps.append(ap)
        result[f"interval@{threshold:g}"] = {
            **_prf(sum(tps), len(valid), total), "ap": ap, "true_positives": sum(tps),
            "start_mae_on_tp": float(np.mean([e[0] for e in errors])) if errors else None,
            "end_mae_on_tp": float(np.mean([e[1] for e in errors])) if errors else None,
        }
    result["mean_interval_ap"] = float(np.mean(aps)) if aps else None
    # Completion-event matching is independent of interval geometry. Early emits
    # cannot match, and a late correct completion is distinguished from a timely one.
    used, delays, timely, early = set(), [], 0, 0
    for event in sorted(valid, key=lambda x: (x["emitted_at"], -x["confidence"])):
        key = event["recording_id"]
        choices = [(abs(event["end"] - item["end"]), i, item) for i, item in enumerate(truth[key])
                   if (key, i) not in used and abs(event["end"] - item["end"]) <= cfg.endpoint_tolerance_seconds]
        if not choices:
            continue
        _, index, gt = min(choices, key=lambda x: x[0])
        delay = event["emitted_at"] - gt["end"]
        if delay < -1e-8:
            early += 1
            continue
        used.add((key, index))
        delays.append(max(0.0, delay))
        timely += int(delay <= cfg.max_latency_seconds)
    false = len(valid) - len(delays)
    result["completion"] = {
        **_prf(len(delays), len(valid), total), "timely_recall": timely / total if total else 0.0,
        "timely_true_positives": timely, "max_latency_seconds": cfg.max_latency_seconds,
        "endpoint_tolerance_seconds": cfg.endpoint_tolerance_seconds,
        "early_completions": early, "late_true_positives": len(delays) - timely,
        "false_completions": false,
        "false_completions_per_minute": false * 60 / valid_seconds if valid_seconds else None,
        "median_delay_on_tp": float(np.median(delays)) if delays else None,
        "p95_delay_on_tp": float(np.percentile(delays, 95)) if delays else None,
    }
    return result
