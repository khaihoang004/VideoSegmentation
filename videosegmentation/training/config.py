"""Typed, strict configuration; paths resolve relative to the YAML file."""

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
import math

import yaml


@dataclass
class DataConfig:
    manifest: str = "manifest.jsonl"
    root: str | None = None
    train_split: str = "train"
    val_split: str = "val"
    task_definition_version: str = "pilot_v1"
    view_domains: list[str] = field(default_factory=lambda: ["exo"])
    batch_size: int = 1
    num_workers: int = 0


@dataclass
class ModelConfig:
    name: str = "causal_gru"
    input_dim: int = 512
    hidden_dim: int = 128
    num_layers: int = 2
    dropout: float = 0.1


@dataclass
class LossConfig:
    name: str = "boundary_bce"
    pos_weight: list[float] = field(default_factory=lambda: [1.0, 10.0, 10.0])
    head_weight: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    boundary_width_seconds: float = 0.5


@dataclass
class OptimizerConfig:
    name: str = "adamw"
    lr: float = 0.001
    weight_decay: float = 0.01
    momentum: float = 0.9


@dataclass
class SchedulerConfig:
    name: str = "cosine"
    min_lr: float = 0.000001
    step_size: int = 10
    gamma: float = 0.5


@dataclass
class TrainerConfig:
    epochs: int = 20
    chunk_size: int = 128
    device: str = "auto"
    amp: bool = True
    grad_clip: float = 1.0
    seed: int = 42
    num_threads: int = 4
    save_epoch_every: int = 0
    log_every_steps: int = 50


@dataclass
class DecoderConfig:
    start_threshold: float = 0.5
    completion_threshold: float = 0.5
    completion_patience: int = 1
    min_duration_seconds: float = 0.1
    refractory_seconds: float = 0.5


@dataclass
class EvaluationConfig:
    tiou_thresholds: list[float] = field(default_factory=lambda: [0.3, 0.5, 0.7])
    endpoint_tolerance_seconds: float = 1.0
    max_latency_seconds: float = 2.0
    inference_chunk_size: int = 1


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    loss: LossConfig = field(default_factory=LossConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    trainer: TrainerConfig = field(default_factory=TrainerConfig)
    decoder: DecoderConfig = field(default_factory=DecoderConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    output_dir: str = "runs/online_gru"

    def to_dict(self):
        return asdict(self)


SECTIONS = {
    "data": DataConfig, "model": ModelConfig, "loss": LossConfig,
    "optimizer": OptimizerConfig, "scheduler": SchedulerConfig,
    "trainer": TrainerConfig, "decoder": DecoderConfig,
    "evaluation": EvaluationConfig,
}


def config_from_dict(raw: dict) -> Config:
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a mapping")
    unknown = set(raw) - {f.name for f in fields(Config)}
    if unknown:
        raise ValueError(f"Unknown config keys: {sorted(unknown)}")
    kwargs = dict(raw)
    for name, cls in SECTIONS.items():
        part = raw.get(name, {})
        if not isinstance(part, dict):
            raise ValueError(f"{name} must be a mapping")
        unknown = set(part) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown {name} keys: {sorted(unknown)}")
        kwargs[name] = cls(**part)
    cfg = Config(**kwargs)
    validate_config(cfg)
    return cfg


def validate_config(cfg: Config):
    positive = {
        "batch_size": cfg.data.batch_size, "input_dim": cfg.model.input_dim,
        "hidden_dim": cfg.model.hidden_dim, "num_layers": cfg.model.num_layers,
        "epochs": cfg.trainer.epochs, "chunk_size": cfg.trainer.chunk_size,
        "num_threads": cfg.trainer.num_threads,
        "completion_patience": cfg.decoder.completion_patience,
        "inference_chunk_size": cfg.evaluation.inference_chunk_size,
        "step_size": cfg.scheduler.step_size,
    }
    for name, value in positive.items():
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    for name, value in {"num_workers": cfg.data.num_workers,
                        "save_epoch_every": cfg.trainer.save_epoch_every,
                        "log_every_steps": cfg.trainer.log_every_steps}.items():
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    for name, value in {
        "lr": cfg.optimizer.lr, "weight_decay": cfg.optimizer.weight_decay,
        "min_lr": cfg.scheduler.min_lr, "gamma": cfg.scheduler.gamma,
        "grad_clip": cfg.trainer.grad_clip,
        "boundary_width_seconds": cfg.loss.boundary_width_seconds,
        "min_duration_seconds": cfg.decoder.min_duration_seconds,
        "refractory_seconds": cfg.decoder.refractory_seconds,
        "max_latency_seconds": cfg.evaluation.max_latency_seconds,
        "endpoint_tolerance_seconds": cfg.evaluation.endpoint_tolerance_seconds,
    }.items():
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")
    if cfg.optimizer.lr <= 0 or cfg.scheduler.min_lr > cfg.optimizer.lr:
        raise ValueError("lr must be positive and min_lr <= lr")
    if not 0 <= cfg.model.dropout < 1:
        raise ValueError("dropout must be in [0,1)")
    for p in [cfg.decoder.start_threshold, cfg.decoder.completion_threshold,
              *cfg.evaluation.tiou_thresholds]:
        if not isinstance(p, (int, float)) or not 0 < p <= 1:
            raise ValueError("Thresholds must be in (0,1]")
    if not cfg.evaluation.tiou_thresholds:
        raise ValueError("At least one tIoU threshold is required")
    for name in ["pos_weight", "head_weight"]:
        values = getattr(cfg.loss, name)
        if len(values) != 3 or any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError(f"{name} needs 3 positive finite values (membership,start,completion)")
    if not cfg.data.view_domains or not set(cfg.data.view_domains) <= {"exo", "ego", "unknown"}:
        raise ValueError("view_domains must select exo, ego and/or unknown")
    if cfg.data.train_split == cfg.data.val_split:
        raise ValueError("Train and validation splits must differ")


def load_config(path: str | Path) -> Config:
    path = Path(path).expanduser().resolve()
    with path.open() as f:
        cfg = config_from_dict(yaml.safe_load(f))
    def resolve(value):
        p = Path(value).expanduser()
        return str((path.parent / p).resolve()) if not p.is_absolute() else str(p)
    cfg.data.manifest = resolve(cfg.data.manifest)
    if cfg.data.root:
        cfg.data.root = resolve(cfg.data.root)
    cfg.output_dir = resolve(cfg.output_dir)
    return cfg
