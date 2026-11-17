"""Command-line entry points."""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from ipo_forecast.data.io import load_modeling_dataset
from ipo_forecast.evaluation.metrics import regression_metrics
from ipo_forecast.models.baseline import fit_regression_baseline, predict_returns
from ipo_forecast.validation.split import chronological_event_split


def _validate_command(args: argparse.Namespace) -> int:
    frame = load_modeling_dataset(args.dataset)
    print(f"Valid dataset: {len(frame)} forecast rows, {frame['ipo_id'].nunique()} IPO events")
    return 0


def _train_command(args: argparse.Namespace) -> int:
    frame = load_modeling_dataset(args.dataset)
    splits = chronological_event_split(
        frame,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    model = fit_regression_baseline(
        splits["train"],
        args.features,
        target_column=args.target,
        model_kind=args.model,
        random_state=args.random_state,
    )

    report = {
        "model": args.model,
        "target": args.target,
        "features": args.features,
        "counts": {
            name: {
                "rows": int(len(part)),
                "ipo_events": int(part["ipo_id"].nunique()),
            }
            for name, part in splits.items()
        },
        "metrics": {},
    }
    for name in ("validation", "test"):
        part = splits[name]
        actual = pd.to_numeric(part[args.target], errors="coerce")
        predicted = predict_returns(model, part, args.features)
        report["metrics"][name] = regression_metrics(actual, predicted)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "baseline.joblib")
    (output_dir / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ipo-forecast")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a CSV or Parquet dataset")
    validate_parser.add_argument("--dataset", required=True)
    validate_parser.set_defaults(func=_validate_command)

    train_parser = subparsers.add_parser("train-baseline", help="Train a regression baseline")
    train_parser.add_argument("--dataset", required=True)
    train_parser.add_argument("--features", nargs="+", required=True)
    train_parser.add_argument("--target", default="target_return")
    train_parser.add_argument(
        "--model", choices=["median", "ridge", "random_forest"], default="ridge"
    )
    train_parser.add_argument("--train-fraction", type=float, default=0.70)
    train_parser.add_argument("--validation-fraction", type=float, default=0.15)
    train_parser.add_argument("--random-state", type=int, default=42)
    train_parser.add_argument("--output-dir", default="reports/baseline")
    train_parser.set_defaults(func=_train_command)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
