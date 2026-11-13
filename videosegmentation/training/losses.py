"""Objective factory: a future distillation objective can be added here."""

import torch
from torch import nn
from torch.nn import functional as F

from .config import LossConfig


class BoundaryLoss(nn.Module):
    def __init__(self, cfg: LossConfig):
        super().__init__()
        self.register_buffer("pos_weight", torch.tensor(cfg.pos_weight))
        self.register_buffer("head_weight", torch.tensor(cfg.head_weight))

    def forward(self, logits, targets, mask):
        values = F.binary_cross_entropy_with_logits(
            logits.float(), targets.float(), pos_weight=self.pos_weight, reduction="none")
        count = mask.sum().clamp_min(1)
        return (values * mask * self.head_weight).sum() / count


def build_loss(cfg):
    if cfg.name != "boundary_bce":
        raise ValueError(f"Unknown loss {cfg.name!r}")
    return BoundaryLoss(cfg)
