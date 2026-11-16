"""IKEA ASM -> pinned ProTAS baseline; run with python -m experiences.ikea_protas."""

import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("setup")
    setup.add_argument("--weights", required=True)
    index = commands.add_parser("index")
    index.add_argument("--dataset-root", required=True)
    index.add_argument("--output", required=True)
    index.add_argument("--scope", choices=["pilot", "full"], default="full")
    index.add_argument("--train-limit", type=int, default=2)
    index.add_argument("--test-limit", type=int, default=1)
    extract = commands.add_parser("extract")
    extract.add_argument("--index", required=True)
    extract.add_argument("--cache-dir", required=True)
    extract.add_argument("--weights", required=True)
    extract.add_argument("--stride", type=int, default=2)
    extract.add_argument("--batch-size", type=int, default=1)
    extract.add_argument("--device", default="cuda")
    extract.add_argument("--max-new-records", type=int)
    extract.add_argument("--scratch")
    extract.add_argument("--report", help="Save the latest extraction status as JSON")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--index", required=True)
    prepare.add_argument("--cache-dir", required=True)
    prepare.add_argument("--output-dir", required=True)
    for action in ("fit", "evaluate"):
        sub = commands.add_parser(action)
        sub.add_argument("--data-dir", required=True)
        sub.add_argument("--run-dir", required=True)
        sub.add_argument("--local-dir", default="/content/ikea_protas_features")
        sub.add_argument("--device", default="cuda")
        if action == "fit":
            sub.add_argument("--epochs", type=int, default=50)
            sub.add_argument("--epochs-this-session", type=int, default=1)
            sub.add_argument("--checkpoint-every", type=int, default=5)
            sub.add_argument("--max-seconds", type=float, default=5400)
            sub.add_argument("--max-records", type=int, help="Stop after N additional recordings (debug/session boundary)")
            sub.add_argument('--graph-reference-fix', action='store_true',
                             help='Clone the graph prior reference to fix upstream shared-storage regularization')
            sub.add_argument('--minimum-steps', type=int, default=0,
                             help='Increase the fixed epoch schedule to reach at least this many optimizer updates')
    args = parser.parse_args(argv)
    try:
        import torch
        torch.set_num_threads(2)
        from videosegmentation.training.checkpoint import atomic_json
        if args.action == "setup":
            from .upstream import checkout, PINS, WEIGHTS_URL, WEIGHTS_SHA256, digest
            for name in PINS:
                checkout(name, fetch=True)
            import requests
            weights = Path(args.weights).expanduser().resolve()
            if not weights.is_file():
                weights.parent.mkdir(parents=True, exist_ok=True)
                temporary = weights.with_suffix(weights.suffix + ".part")
                with requests.get(WEIGHTS_URL, stream=True, timeout=(30, 120)) as response:
                    response.raise_for_status()
                    with temporary.open("wb") as stream:
                        for block in response.iter_content(1024 * 1024):
                            stream.write(block)
                # Verify loadability/model shapes before committing an asset.
                from .features import encoder
                encoder(temporary, "cpu")
                temporary.replace(weights)
            if digest(weights) != WEIGHTS_SHA256:
                raise ValueError("Existing I3D weights do not match the pinned SHA256")
            result = dict(pins=PINS, weights=str(weights), weights_sha256=digest(weights))
            atomic_json(result, weights.with_suffix(".provenance.json"))
        elif args.action == "index":
            from .data import build_index
            result = build_index(args.dataset_root, scope=args.scope, train_limit=args.train_limit, test_limit=args.test_limit)
            out = Path(args.output)
            if out.exists() and json.loads(out.read_text()) != result:
                raise ValueError("Index differs from previous run; choose a new output")
            atomic_json(result, out)
            result = dict(index=str(out), scope=result["scope"], labels=len(result["labels"]),
                          recordings=len(result["records"]), official_counts=result["original_split_counts"],
                          missing=len(result["missing_videos"]))
        elif args.action == "extract":
            from .features import prepare_features
            if args.report and Path(args.report).resolve() in {Path(args.index).resolve(), Path(args.weights).resolve()}:
                raise ValueError("Report must not overwrite input index or weights")
            result = prepare_features(json.loads(Path(args.index).read_text()), args.cache_dir, args.weights,
                                      stride=args.stride, batch_size=args.batch_size, device=args.device,
                                      max_new_records=args.max_new_records, scratch=args.scratch)
            if args.report:
                atomic_json(result, args.report)
        elif args.action == "prepare":
            from .runner import prepare
            result = prepare(json.loads(Path(args.index).read_text()), args.cache_dir, args.output_dir)
            result = dict(data_dir=args.output_dir, records=len(result["records"]), scope=result["scope"])
        elif args.action == "fit":
            from .runner import fit
            result = fit(args.data_dir, args.run_dir, args.local_dir, epochs=args.epochs,
                         epochs_this_session=args.epochs_this_session, device=args.device,
                         checkpoint_every=args.checkpoint_every, max_seconds=args.max_seconds, max_records=args.max_records,
                         graph_reference_fix=args.graph_reference_fix, minimum_steps=args.minimum_steps)
        else:
            from .runner import evaluate
            result = evaluate(args.data_dir, args.run_dir, args.local_dir, device=args.device)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f"IKEA-ProTAS: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
