"""Optimizer/scheduler factories; all settings are saved in checkpoints."""

import torch


def build_optimizer(model, cfg):
    if cfg.name == "adamw":
        return torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    if cfg.name == "sgd":
        return torch.optim.SGD(model.parameters(), lr=cfg.lr, momentum=cfg.momentum,
                               weight_decay=cfg.weight_decay)
    raise ValueError(f"Unknown optimizer {cfg.name!r}")


def build_scheduler(optimizer, cfg, epochs):
    if cfg.name == "none":
        return None
    if cfg.name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=cfg.min_lr)
    if cfg.name == "step":
        return torch.optim.lr_scheduler.StepLR(optimizer, step_size=cfg.step_size, gamma=cfg.gamma)
    raise ValueError(f"Unknown scheduler {cfg.name!r}")
