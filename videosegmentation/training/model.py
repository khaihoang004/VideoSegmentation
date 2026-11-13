"""A small single-task baseline, not a reproduction of MATR/OnPoint."""

import torch
from torch import nn

from .config import ModelConfig


class CausalGRU(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        # LayerNorm operates on each frame's features, not across future time.
        self.project = nn.Sequential(nn.LayerNorm(cfg.input_dim),
                                     nn.Linear(cfg.input_dim, cfg.hidden_dim), nn.GELU())
        self.temporal = nn.GRU(cfg.hidden_dim, cfg.hidden_dim, cfg.num_layers,
                               batch_first=True, bidirectional=False,
                               dropout=cfg.dropout if cfg.num_layers > 1 else 0.0)
        self.head = nn.Linear(cfg.hidden_dim, 3)

    def forward(self, features: torch.Tensor, state=None):
        encoded, state = self.temporal(self.project(features), state)
        return self.head(encoded), state


def build_model(cfg: ModelConfig):
    if cfg.name != "causal_gru":
        raise ValueError(f"Unknown model {cfg.name!r}")
    return CausalGRU(cfg)
