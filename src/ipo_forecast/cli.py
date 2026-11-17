"""Command-line entry points."""

import argparse
import json
import os
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ipo_forecast.data.coverage import run_coverage_audit
from ipo_forecast.data.io import load_modeling_dataset
from ipo_forecast.data.sources.finam import FinamClient
from ipo_forecast.data.sources.sec_edgar import SecEdgarClient
from ipo_forecast.data.sources.tinvest import TInvestClient
from ipo_forecast.data.validate import select_forecast_task
from ipo_forecast.evaluation.metrics import regression_metrics
from ipo_forecast.models.baseline import fit_regression_baseline, predict_returns
from ipo_forecast.validation.maturity import purge_unmatured_training_labels
from ipo_forecast.validation.split import chronological_event_split


def _validate_command(args: argparse.Namespace) -> int:
    frame = load_modeling_dataset(args.dataset)
    print(f"Valid dataset: {len(frame)} forecast rows, {frame['ipo_id'].nunique()} IPO events")
    return 0


def _train_command(args: argparse.Namespace) -> int:
    frame = load_modeling_dataset(args.dataset)
    frame = select_forecast_task(
        frame,
        forecast_origin=args.forecast_origin,
        target_horizon=args.target_horizon,
    )
    splits = chronological_event_split(
        frame,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    purged_train, maturity_report = purge_unmatured_training_labels(
        splits["train"],
        splits["validation"],
        embargo_days=args.embargo_days,
    )
    splits["train"] = purged_train
    model = fit_regression_baseline(
        splits["train"],
        args.features,
        target_column=args.target,
        model_kind=args.model,
        random_state=args.random_state,
    )
    train_median = float(pd.to_numeric(splits["train"][args.target]).median())

    report = {
        "model": args.model,
        "target": args.target,
        "forecast_origin": args.forecast_origin,
        "target_horizon": args.target_horizon,
        "features": args.features,
        "label_maturity": maturity_report,
        "counts": {
            name: {
                "rows": int(len(part)),
                "ipo_events": int(part["ipo_id"].nunique()),
            }
            for name, part in splits.items()
        },
        "metrics": {},
        "baseline_metrics": {},
    }
    for name in ("validation", "test"):
        part = splits[name]
        actual = pd.to_numeric(part[args.target], errors="coerce")
        predicted = predict_returns(model, part, args.features)
        report["metrics"][name] = regression_metrics(actual, predicted)
        report["baseline_metrics"][name] = {
            "zero_return": regression_metrics(actual, np.zeros(len(part))),
            "train_median": regression_metrics(
                actual, np.full(len(part), train_median)
            ),
        }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "baseline.joblib")
    (output_dir / "metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


def _sec_search_command(args: argparse.Namespace) -> int:
    client = SecEdgarClient(cache_dir=args.cache_dir)
    matches = client.resolve_company(args.query)
    print(json.dumps(matches, indent=2))
    return 0 if matches else 1


def _sec_filings_command(args: argparse.Namespace) -> int:
    client = SecEdgarClient(cache_dir=args.cache_dir)
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    rows = client.list_ipo_filings(
        args.cik,
        start_date=start_date,
        end_date=end_date,
        include_historical=not args.no_historical,
        refresh=args.refresh,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Saved {len(rows)} SEC IPO-related filing candidates to {output_path}")
    return 0


def _sec_index_command(args: argparse.Namespace) -> int:
    client = SecEdgarClient(cache_dir=args.cache_dir)
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    rows = client.list_ipo_filing_index(
        args.start_year,
        args.end_year,
        start_date=start_date,
        end_date=end_date,
        refresh=args.refresh,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    print(f"Saved {len(rows)} SEC filing candidates to {output_path}")
    return 0


def _market_data_audit_command(args: argparse.Namespace) -> int:
    providers = {}
    cache_root = Path(args.cache_dir)
    selected = set(args.providers)

    if "finam" in selected:
        secret = os.getenv("FINAM_API_SECRET") or os.getenv("FINAM_TOKEN")
        if secret:
            providers["finam"] = FinamClient(
                api_secret=secret,
                source_app_id=os.getenv("FINAM_SOURCE_APP_ID"),
                cache_dir=cache_root / "finam",
            )
        else:
            raise ValueError(
                "Finam selected but FINAM_API_SECRET is not set. "
                "Set it in the local environment; do not commit it."
            )

    if "tinvest" in selected:
        token = os.getenv("TINVEST_TOKEN") or os.getenv("TINKOFF_INVEST_TOKEN")
        if token:
            providers["tinvest"] = TInvestClient(
                token=token,
                cache_dir=cache_root / "tinvest",
            )
        else:
            raise ValueError(
                "T-Invest selected but TINVEST_TOKEN is not set. "
                "Set it in the local environment; do not commit it."
            )

    rows, summary = run_coverage_audit(
        args.universe,
        providers,
        daily_window_days=args.daily_window_days,
        include_minute_archives=args.minute_archives,
        refresh=args.refresh,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Coverage detail: {output_path}")
    print(f"Coverage summary: {summary_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ipo-forecast")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a CSV or Parquet dataset")
    validate_parser.add_argument("--dataset", required=True)
    validate_parser.set_defaults(func=_validate_command)

    train_parser = subparsers.add_parser("train-baseline", help="Train one IPO forecast task")
    train_parser.add_argument("--dataset", required=True)
    train_parser.add_argument("--features", nargs="+", required=True)
    train_parser.add_argument(
        "--forecast-origin",
        choices=["preliminary_filing", "after_pricing_pre_open", "post_open"],
        required=True,
    )
    train_parser.add_argument(
        "--target-horizon",
        choices=[
            "first_trade",
            "day1_close",
            "day5_close",
            "day20_close",
            "day60_close",
            "day180_close",
        ],
        required=True,
    )
    train_parser.add_argument("--target", default="target_return")
    train_parser.add_argument("--embargo-days", type=int, default=0)
    train_parser.add_argument(
        "--model", choices=["median", "ridge", "random_forest"], default="ridge"
    )
    train_parser.add_argument("--train-fraction", type=float, default=0.70)
    train_parser.add_argument("--validation-fraction", type=float, default=0.15)
    train_parser.add_argument("--random-state", type=int, default=42)
    train_parser.add_argument("--output-dir", default="reports/baseline")
    train_parser.set_defaults(func=_train_command)

    sec_search_parser = subparsers.add_parser(
        "sec-search", help="Resolve a company name or ticker using SEC's public mapping"
    )
    sec_search_parser.add_argument("--query", required=True)
    sec_search_parser.add_argument("--cache-dir", default="data/raw/sec_edgar/cache")
    sec_search_parser.set_defaults(func=_sec_search_command)

    sec_filings_parser = subparsers.add_parser(
        "sec-filings", help="Collect a company's SEC IPO-related filing candidates"
    )
    sec_filings_parser.add_argument("--cik", required=True)
    sec_filings_parser.add_argument("--start-date")
    sec_filings_parser.add_argument("--end-date")
    sec_filings_parser.add_argument("--no-historical", action="store_true")
    sec_filings_parser.add_argument("--refresh", action="store_true")
    sec_filings_parser.add_argument("--cache-dir", default="data/raw/sec_edgar/cache")
    sec_filings_parser.add_argument("--output", default="data/interim/sec_ipo_filings.csv")
    sec_filings_parser.set_defaults(func=_sec_filings_command)

    sec_index_parser = subparsers.add_parser(
        "sec-index", help="Scan SEC quarterly master indexes for IPO-related filing candidates"
    )
    sec_index_parser.add_argument("--start-year", type=int, default=2000)
    sec_index_parser.add_argument("--end-year", type=int, default=date.today().year)
    sec_index_parser.add_argument("--start-date")
    sec_index_parser.add_argument("--end-date")
    sec_index_parser.add_argument("--refresh", action="store_true")
    sec_index_parser.add_argument("--cache-dir", default="data/raw/sec_edgar/cache")
    sec_index_parser.add_argument("--output", default="data/interim/sec_ipo_filing_index.csv")
    sec_index_parser.set_defaults(func=_sec_index_command)

    market_data_parser = subparsers.add_parser(
        "market-data-audit",
        help="Audit Finam and T-Invest historical price coverage for an IPO universe",
    )
    market_data_parser.add_argument(
        "--universe", default="data/templates/us_ipo_coverage_sample.csv"
    )
    market_data_parser.add_argument(
        "--output", default="data/interim/market_data_coverage.csv"
    )
    market_data_parser.add_argument(
        "--providers", nargs="+", choices=["finam", "tinvest"], default=["finam", "tinvest"]
    )
    market_data_parser.add_argument("--daily-window-days", type=int, default=180)
    market_data_parser.add_argument(
        "--minute-archives",
        action="store_true",
        help="Opt in to potentially large T-Invest annual minute archive downloads",
    )
    market_data_parser.add_argument("--refresh", action="store_true")
    market_data_parser.add_argument(
        "--cache-dir", default="data/raw/market_data/cache"
    )
    market_data_parser.set_defaults(func=_market_data_audit_command)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
