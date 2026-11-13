"""Streaming decoding and feature replay, with explicit observation/emission clocks."""

from dataclasses import asdict
import time

import numpy as np
import torch

from .config import DecoderConfig


class InstanceDecoder:
    def __init__(self, cfg: DecoderConfig, recording_id: str, task_version: str):
        self.cfg = cfg
        self.recording_id = recording_id
        self.task_version = task_version
        self.open_start = None
        self.start_high = False
        self.pending_end = None
        self.pending_count = 0
        self.pending_score = 0.0
        self.next_start = None
        self.completion_armed = True
        self.last_closed = -float("inf")
        self.last_time = -float("inf")
        self.counter = 0
        self.replaced_candidates = 0

    def update(self, timestamp, probabilities, *, observed_until=None, emitted_at=None):
        timestamp = float(timestamp)
        observed_until = timestamp if observed_until is None else float(observed_until)
        emitted_at = observed_until if emitted_at is None else float(emitted_at)
        if timestamp <= self.last_time or not timestamp <= observed_until <= emitted_at:
            raise ValueError("Stream clocks must increase and timestamp <= observed_until <= emitted_at")
        p = np.asarray(probabilities)
        if p.shape != (3,) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError("Expected three finite probabilities in [0,1]")
        self.last_time = timestamp
        # Membership is a diagnostic/training head, NOT motion activity. A fall
        # in membership never closes an instance: pauses need explicit completion.
        high = p[1] >= self.cfg.start_threshold
        onset = high and not self.start_high
        self.start_high = bool(high)
        if self.open_start is None:
            if onset and timestamp - self.last_closed >= self.cfg.refractory_seconds:
                self.open_start = timestamp
                self.completion_armed = p[2] < self.cfg.completion_threshold
            return []
        if p[2] < self.cfg.completion_threshold:
            self.completion_armed = True
            self.pending_end, self.pending_count, self.pending_score = None, 0, 0.0
            candidate = timestamp if onset else self.next_start
            if candidate is not None and candidate > self.open_start:
                self.replaced_candidates += 1  # not a claim of actual abortion
                self.open_start = candidate
            self.next_start = None
            return []
        if not self.completion_armed:
            if onset:
                self.replaced_candidates += 1
                self.open_start = timestamp
            return []
        if self.pending_end is None:
            self.pending_end = timestamp
        if onset and timestamp > self.open_start:
            self.next_start = timestamp
        self.pending_count += 1
        self.pending_score = max(self.pending_score, float(p[2]))
        if self.pending_count < self.cfg.completion_patience:
            return []
        if self.pending_end <= self.open_start or self.pending_end - self.open_start < self.cfg.min_duration_seconds:
            return []
        self.counter += 1
        event_id = f"{self.recording_id}:{self.counter:06d}:completed"
        event = {
            "recording_id": self.recording_id, "event_id": event_id,
            "instance_id": f"{self.recording_id}:{self.counter:06d}",
            "task_definition_version": self.task_version,
            "start": self.open_start, "end": self.pending_end,
            "status": "completed", "confidence": self.pending_score,
            "observed_until": observed_until, "emitted_at": emitted_at,
            "is_final": True, "timing_mode": "feature_replay_simulated",
        }
        self.last_closed = timestamp
        # End the old instance BEFORE accepting a start at the same timestamp.
        # This preserves two adjacent instances even without background frames.
        self.open_start = self.next_start
        self.next_start = None
        self.completion_armed = False
        self.pending_end, self.pending_count, self.pending_score = None, 0, 0.0
        return [event]

    def summary(self):
        # End-of-file NEVER emits a completed event.
        return {"open_start": self.open_start, "replaced_candidates": self.replaced_candidates,
                "completed_count": self.counter, "decoder": asdict(self.cfg)}


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


@torch.inference_mode()
def replay_recording(model, record, decoder_cfg, device, chunk_size=1):
    """Chronological replay; no labels, video duration or total count enter model/decoder.

    A batched chunk arrives at its LAST timestamp. All events decoded from that
    chunk are emitted after its forward pass, never backdated to earlier frames.
    The virtual clock includes temporal-head/transfer/decoder work, not the cost
    of creating the precomputed features. This is not raw-camera latency.
    """
    model.eval()
    decoder = InstanceDecoder(decoder_cfg, record.entry["recording_id"],
                              record.entry["task_definition_version"])
    state, events, elapsed_total = None, [], 0.0
    virtual_clock = float(record.timestamps[0])
    for begin in range(0, len(record), chunk_size):
        end = min(begin + chunk_size, len(record))
        frontier = float(record.timestamps[end - 1])
        synchronize(device)
        before = time.perf_counter()
        data = np.array(record.features[begin:end], dtype=np.float32, copy=True)
        if not np.isfinite(data).all():
            raise ValueError("Non-finite feature in replay")
        logits, state = model(torch.from_numpy(data).unsqueeze(0).to(device), state)
        scores = logits.sigmoid()[0].float().cpu().numpy()
        synchronize(device)
        compute_time = time.perf_counter() - before
        elapsed_total += compute_time
        virtual_clock = max(virtual_clock, frontier) + compute_time
        for timestamp, probs in zip(record.timestamps[begin:end], scores):
            before = time.perf_counter()
            emitted = decoder.update(timestamp, probs, observed_until=frontier,
                                     emitted_at=virtual_clock)
            dt = time.perf_counter() - before
            virtual_clock += dt
            elapsed_total += dt
            for event in emitted:
                event["emitted_at"] = virtual_clock
            events.extend(emitted)
    summary = decoder.summary()
    summary.update(recording_id=record.entry["recording_id"],
                   processing_seconds=elapsed_total, feature_steps=len(record),
                   feature_steps_per_second=len(record) / max(elapsed_total, 1e-12),
                   timing_mode="feature_replay_simulated", feature_extraction_cost_included=False)
    return events, summary
