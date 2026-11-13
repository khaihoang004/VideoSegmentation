"""Recording-wise TBPTT trainer, deterministic epoch resume and streaming validation."""

from contextlib import nullcontext
import json
from pathlib import Path
import random

import numpy as np
import torch
from torch.utils.data import DataLoader

from .checkpoint import atomic_json, atomic_save, load_checkpoint, random_state, restore_random_state
from .config import Config, config_from_dict
from .data import FeatureDataset, collate_recordings, iter_chunks, manifest_fingerprint
from .losses import build_loss
from .metrics import evaluate_events
from .model import build_model
from .optim import build_optimizer, build_scheduler
from .streaming import replay_recording


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(name):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if name == "auto" else torch.device(name)
    if device.type not in {"cpu", "cuda"}:
        raise ValueError("Pipeline v0 supports cpu/cuda devices")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but unavailable")
    return device


class Trainer:
    def __init__(self, cfg: Config, *, resume=None, warm_start=None):
        if resume and warm_start:
            raise ValueError("Choose resume or warm_start")
        self.cfg = cfg
        torch.set_num_threads(cfg.trainer.num_threads)
        seed_everything(cfg.trainer.seed)
        self.device = resolve_device(cfg.trainer.device)
        self.output = Path(cfg.output_dir)
        if not resume and (self.output / "last.pt").exists():
            raise ValueError("Output already has last.pt; use --resume or a new output directory")
        self.output.mkdir(parents=True, exist_ok=True)
        self.train_data = FeatureDataset(cfg, cfg.data.train_split)
        self.val_data = FeatureDataset(cfg, cfg.data.val_split)
        self.generator = torch.Generator().manual_seed(cfg.trainer.seed)
        self.loader = DataLoader(self.train_data, batch_size=cfg.data.batch_size, shuffle=True,
                                 num_workers=cfg.data.num_workers, generator=self.generator,
                                 collate_fn=collate_recordings, pin_memory=False)
        self.model = build_model(cfg.model).to(self.device)
        self.criterion = build_loss(cfg.loss).to(self.device)
        self.optimizer = build_optimizer(self.model, cfg.optimizer)
        self.scheduler = build_scheduler(self.optimizer, cfg.scheduler, cfg.trainer.epochs)
        self.use_amp = cfg.trainer.amp and self.device.type == "cuda"
        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)
        self.fingerprint = manifest_fingerprint(cfg)
        self.epoch, self.global_step, self.best_loss = 0, 0, float("inf")
        if resume:
            self._resume(resume)
        elif warm_start:
            saved = load_checkpoint(warm_start)
            if saved["config"]["model"] != cfg.to_dict()["model"]:
                raise ValueError("Warm-start model architecture differs")
            self.model.load_state_dict(saved["model"])
        atomic_json({"config": cfg.to_dict(), "manifest_fingerprint": self.fingerprint,
                     "training_mode": "supervised_online", "device": str(self.device),
                     "torch_version": str(torch.__version__),
                     "resume": str(resume) if resume else None,
                     "warm_start": str(warm_start) if warm_start else None}, self.output / "run.json")

    def _resume(self, path):
        saved = load_checkpoint(path)
        old, new = saved["config"], self.cfg.to_dict()
        if Path(old["output_dir"]).resolve() != self.output.resolve():
            raise ValueError("Resume must keep output_dir to preserve best.pt/history; use warm-start for a new run")
        # Epoch horizon is part of scheduler semantics. Use warm-start for a new
        # objective/schedule, rather than silently mutating a resumed experiment.
        for key in ["data", "model", "loss", "optimizer", "scheduler", "trainer", "decoder", "evaluation"]:
            left, right = dict(old[key]), dict(new[key])
            if key == "trainer":
                for optional in ["device", "num_threads", "save_epoch_every", "log_every_steps"]:
                    left.pop(optional, None); right.pop(optional, None)
            if left != right:
                raise ValueError(f"Resume {key} differs; use --warm-start and a new output for a new experiment")
        if saved["manifest_fingerprint"] != self.fingerprint:
            raise ValueError("Manifest changed since checkpoint")
        self.model.load_state_dict(saved["model"])
        self.optimizer.load_state_dict(saved["optimizer"])
        if self.scheduler:
            self.scheduler.load_state_dict(saved["scheduler"])
        self.scaler.load_state_dict(saved["scaler"])
        self.epoch, self.global_step = saved["epoch"], saved["global_step"]
        self.best_loss = saved["best_loss"]
        restore_random_state(saved["random_state"], self.generator)

    def _autocast(self):
        return torch.autocast(device_type="cuda", dtype=torch.float16) if self.use_amp else nullcontext()

    def train_epoch(self):
        self.model.train()
        numerator, denominator = 0.0, 0
        for records in self.loader:
            state = None  # New independent recording batch only, never each chunk.
            for features, targets, mask in iter_chunks(records, self.cfg.trainer.chunk_size):
                features, targets, mask = (x.to(self.device) for x in (features, targets, mask))
                self.optimizer.zero_grad(set_to_none=True)
                with self._autocast():
                    logits, state = self.model(features, state)
                    loss = self.criterion(logits, targets, mask)
                count = int(mask.sum())
                if count:
                    if not torch.isfinite(loss):
                        raise ValueError("Non-finite training loss")
                    self.scaler.scale(loss).backward()
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.cfg.trainer.grad_clip,
                                                  error_if_nonfinite=True)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                    self.global_step += 1
                    numerator += float(loss.detach()) * count
                    denominator += count
                    if self.cfg.trainer.log_every_steps and self.global_step % self.cfg.trainer.log_every_steps == 0:
                        print(json.dumps({"stage": "train", "epoch": self.epoch + 1,
                                          "global_step": self.global_step, "loss": float(loss.detach())}), flush=True)
                state = state.detach()  # TBPTT: retain values, truncate gradients.
        if not denominator:
            raise ValueError("Training split has no labelled feature bins")
        return numerator / denominator

    @torch.inference_mode()
    def validate(self):
        self.model.eval()
        numerator, denominator, events, summaries = 0.0, 0, [], []
        for index in range(len(self.val_data)):
            record = self.val_data[index]
            state = None
            for features, targets, mask in iter_chunks([record], self.cfg.trainer.chunk_size):
                features, targets, mask = (x.to(self.device) for x in (features, targets, mask))
                logits, state = self.model(features, state)
                loss = self.criterion(logits, targets, mask)
                count = int(mask.sum())
                numerator += float(loss) * count
                denominator += count
            decoded, summary = replay_recording(self.model, record, self.cfg.decoder, self.device,
                                                self.cfg.evaluation.inference_chunk_size)
            events.extend(decoded); summaries.append(summary)
        if not denominator:
            raise ValueError("Validation split has no labelled feature bins")
        metrics = evaluate_events(self.val_data.entries, events, self.cfg.evaluation)
        metrics["loss"] = numerator / denominator
        return metrics, events, summaries

    def save(self, path):
        atomic_save({"format_version": 1, "epoch": self.epoch, "global_step": self.global_step,
                     "best_loss": self.best_loss, "config": self.cfg.to_dict(),
                     "manifest_fingerprint": self.fingerprint,
                     "model": self.model.state_dict(), "optimizer": self.optimizer.state_dict(),
                     "scheduler": self.scheduler.state_dict() if self.scheduler else None,
                     "scaler": self.scaler.state_dict(), "random_state": random_state(self.generator)}, path)

    def fit(self, *, until_epoch=None):
        """until_epoch supports intentional epoch-boundary interruption, not a new LR horizon."""
        limit = self.cfg.trainer.epochs if until_epoch is None else min(until_epoch, self.cfg.trainer.epochs)
        while self.epoch < limit:
            train_loss = self.train_epoch()
            validation, events, summaries = self.validate()
            self.epoch += 1
            improved = validation["loss"] < self.best_loss
            if improved:
                self.best_loss = validation["loss"]
            learning_rate = self.optimizer.param_groups[0]["lr"]
            if self.scheduler:
                self.scheduler.step()
            report = {"epoch": self.epoch, "global_step": self.global_step,
                      "train_loss": train_loss, "learning_rate": learning_rate, "validation": validation}
            atomic_json(report, self.output / f"metrics/epoch_{self.epoch:04d}.json")
            atomic_json({"events": events, "streams": summaries}, self.output / "validation_events.json")
            self.save(self.output / "last.pt")
            if improved:
                self.save(self.output / "best.pt")
            if self.cfg.trainer.save_epoch_every and self.epoch % self.cfg.trainer.save_epoch_every == 0:
                self.save(self.output / f"epoch_{self.epoch:04d}.pt")
            print(json.dumps({"epoch": self.epoch, "train_loss": train_loss,
                              "val_loss": validation["loss"], "val_mean_ap": validation["mean_interval_ap"],
                              "val_timely_recall": validation["completion"]["timely_recall"]}), flush=True)
        return {"epoch": self.epoch, "global_step": self.global_step, "best_loss": self.best_loss}


def model_from_checkpoint(path, device_name="auto"):
    saved = load_checkpoint(path)
    cfg = config_from_dict(saved["config"])
    torch.set_num_threads(cfg.trainer.num_threads)
    device = resolve_device(device_name)
    model = build_model(cfg.model).to(device)
    model.load_state_dict(saved["model"])
    model.eval()
    return model, cfg, device
