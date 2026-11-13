"""One runner for training tasks; dataset downloading remains in download.py."""

import argparse
import json
from pathlib import Path
import sys

from .checkpoint import atomic_json
from .config import load_config
from .data import FeatureDataset, iter_chunks
from .demo import make_demo
from .metrics import evaluate_events
from .streaming import replay_recording
from .trainer import Trainer, model_from_checkpoint


def build_parser():
    parser = argparse.ArgumentParser(description="Causal online task-instance training and feature replay")
    commands = parser.add_subparsers(dest="command", required=True)
    fit = commands.add_parser("fit", aliases=["train"], help="Train a supervised causal baseline")
    fit.add_argument("--config", required=True)
    fit.add_argument("--resume", help="Epoch-boundary resume including optimizer/scheduler/RNG")
    fit.add_argument("--warm-start", help="Model weights only, for a NEW training objective/schedule")
    for name in ["evaluate", "predict"]:
        sub = commands.add_parser(name, help="Replay features chronologically; no EOF completion")
        sub.add_argument("--checkpoint", required=True)
        sub.add_argument("--manifest", help="Override feature manifest, retaining checkpoint task/feature configuration")
        sub.add_argument("--root", help="Root for relative paths in the override manifest")
        sub.add_argument("--split", default="test")
        sub.add_argument("--device", default="auto")
        sub.add_argument("--output", required=True, help="Report JSON including events and replay metadata")
    validate = commands.add_parser("validate-data", help="Validate canonical labels, features, splits and causality metadata")
    validate.add_argument("--config", required=True)
    validate.add_argument("--split", action="append", help="Repeat; default train and validation")
    demo = commands.add_parser("make-demo", help="Generate synthetic integration data, NOT a video benchmark")
    demo.add_argument("--output-dir", required=True)
    extract = commands.add_parser("extract-features", help="Frame-wise ResNet18 RGB feature extraction")
    extract.add_argument("--manifest", required=True, help="JSONL with manually checked goal-level labels and video_path")
    extract.add_argument("--output-manifest", required=True)
    extract.add_argument("--output-dir", required=True)
    extract.add_argument("--root")
    extract.add_argument("--sample-hz", type=float, default=2.0)
    extract.add_argument("--batch-size", type=int, default=32)
    extract.add_argument("--weights", choices=["imagenet", "none"], default="imagenet")
    extract.add_argument("--device", default="auto")
    extract.add_argument("--seed", type=int, default=42)
    extract.add_argument("--overwrite", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"fit", "train"}:
            result = Trainer(load_config(args.config), resume=args.resume, warm_start=args.warm_start).fit()
        elif args.command == "make-demo":
            result = make_demo(args.output_dir)
        elif args.command == "extract-features":
            from .features import extract_features
            result = extract_features(args.manifest, args.output_manifest, args.output_dir,
                                      root=args.root, sample_hz=args.sample_hz, batch_size=args.batch_size,
                                      weights=args.weights, device_name=args.device,
                                      seed=args.seed, overwrite=args.overwrite)
        elif args.command == "validate-data":
            cfg = load_config(args.config)
            result = {}
            for split in args.split or [cfg.data.train_split, cfg.data.val_split]:
                data = FeatureDataset(cfg, split)
                steps, labelled = 0, 0
                for index in range(len(data)):
                    record = data[index]
                    for _, _, mask in iter_chunks([record], cfg.trainer.chunk_size):
                        labelled += int(mask[:, :, 0].sum())
                    steps += len(record)
                if not labelled:
                    raise ValueError(f"{split}: no labelled feature bins")
                result[split] = {"recordings": len(data), "feature_steps": steps, "labelled_steps": labelled}
        else:
            model, cfg, device = model_from_checkpoint(args.checkpoint, args.device)
            if args.manifest:
                cfg.data.manifest = str(Path(args.manifest).expanduser().resolve())
                cfg.data.root = args.root
            elif args.root:
                cfg.data.root = args.root
            data = FeatureDataset(cfg, args.split, with_targets=args.command == "evaluate")
            events, summaries = [], []
            for index in range(len(data)):
                decoded, summary = replay_recording(model, data[index], cfg.decoder, device,
                                                    cfg.evaluation.inference_chunk_size)
                events.extend(decoded); summaries.append(summary)
            result = {"events": events, "streams": summaries,
                      "manifest": cfg.data.manifest, "task_definition_version": cfg.data.task_definition_version,
                      "evaluation_config": cfg.to_dict()["evaluation"],
                      "decoder_config": cfg.to_dict()["decoder"],
                      "checkpoint": str(Path(args.checkpoint).resolve()), "split": args.split}
            if args.command == "evaluate":
                result["metrics"] = evaluate_events(data.entries, events, cfg.evaluation)
            atomic_json(result, args.output)
            result = {"output": str(Path(args.output).resolve()),
                      "events": len(events), **({"metrics": result["metrics"]} if "metrics" in result else {})}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
        return 0
    except (ValueError, FileNotFoundError, ImportError, RuntimeError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Resume from last.pt at the last completed epoch.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
