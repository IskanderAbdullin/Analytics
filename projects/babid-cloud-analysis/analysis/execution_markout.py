#!/usr/bin/env python3
"""Per-fill offline markout in ticks, using only PREVIOUSLY received book data.

Not a P&L backtest. Fills have broker trade time, books have receipt time.
The mapping between state and instrument is supplied explicitly by the user.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from report_safety import validate_report_output
from tape_integrity import good_book

MSK = timezone(timedelta(hours=3))
HORIZONS = {"h5": 5000, "h30": 30000}
COLUMNS = (
    "time_msk", "state", "instrument", "order", "trade_id", "side", "lots",
    "fill_price", "synthetic", "reference_age_ms", "spread_ticks",
    "entry_edge_ticks", "markout_5s_ticks", "markout_30s_ticks",
    "mid_move_5s_ticks", "mid_move_30s_ticks", "entry_status", "h5_status", "h30_status",
)


def dec(raw):
    result = Decimal(str(raw))
    if not result.is_finite():
        raise InvalidOperation("non-finite number")
    return result


def time_msk(raw):
    dt = datetime.fromisoformat(raw.strip().replace(" ", "T"))
    if dt.tzinfo is not None:
        raise ValueError("time_msk must be naive")
    return round(dt.replace(tzinfo=MSK).timestamp() * 1000)


def read_fills(path: Path, day: str) -> tuple[list[dict], int]:
    rows, skipped, seen = [], 0, set()
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        fields = {"time_msk", "order", "trade_id", "side", "lots", "price", "synthetic"}
        if not reader.fieldnames or not fields.issubset(reader.fieldnames):
            raise ValueError("fills.csv schema is incomplete")
        for line, row in enumerate(reader, 2):
            if not (row.get("time_msk") or "").startswith(day):
                continue
            try:
                t = time_msk(row["time_msk"])
                side = row["side"]
                lots = int(row["lots"])
                price = dec(row["price"])
                if side not in ("Buy", "Sell") or lots < 1 or price <= 0:
                    raise ValueError("invalid execution")
                trade_id = row.get("trade_id", "")
                key = (row.get("exchange_id", ""), trade_id)
                if trade_id and key in seen:
                    skipped += 1
                    continue
                if trade_id:
                    seen.add(key)
                rows.append(dict(t=t, line=line, time_msk=row["time_msk"],
                                 order=row.get("order", ""), trade_id=trade_id,
                                 side=side, lots=lots, fill_price=price,
                                 synthetic=row.get("synthetic") == "1"))
                if len(rows) > 250000:
                    raise ValueError("too many fills for one day; no silent truncation")
            except (ValueError, InvalidOperation, TypeError, KeyError, OverflowError):
                skipped += 1
    rows.sort(key=lambda x: (x["t"], x["line"]))
    return rows, skipped


def analyze(root: Path, state: str, instrument: str, day: str,
            max_book_age_ms: int = 2000, verified_tick: str | None = None):
    root = root.resolve(strict=True)
    date.fromisoformat(day)
    if not re.fullmatch(r"state[\w.-]*", state) or "/" in state or "\\" in state:
        raise ValueError("state must be one state* folder")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", instrument):
        raise ValueError("invalid instrument folder")
    if max_book_age_ms < 1:
        raise ValueError("max_book_age_ms must be positive")
    folder = (root / state).resolve()
    if not folder.is_relative_to(root) or not folder.is_dir():
        raise ValueError("state folder outside root or missing")
    path = folder / "fills.csv"
    if not path.is_file():
        raise ValueError("fills.csv is missing")
    market_dir = (root / "recordings" / instrument).resolve()
    if not market_dir.is_relative_to(root):
        raise ValueError("recording folder escapes root")
    filename = f"{instrument}_{day}.tsv"
    paths = [p for p in (market_dir / filename, market_dir / (filename + ".gz")) if p.is_file()]
    if len(paths) != 1:
        raise ValueError("expected one matching TSV or TSV.GZ recording")
    tape = paths[0]
    tick = dec(verified_tick) if verified_tick is not None else None
    if tick is not None and tick <= 0:
        raise ValueError("tick must be positive")
    fills, skipped = read_fills(path, day)
    milestones = []
    for index, row in enumerate(fills):
        row.update(state=state, instrument=instrument, entry_status="pending",
                   h5_status="pending", h30_status="pending")
        for field in ("reference_age_ms", "spread_ticks", "entry_edge_ticks",
                      "markout_5s_ticks", "markout_30s_ticks",
                      "mid_move_5s_ticks", "mid_move_30s_ticks"):
            row[field] = ""
        for kind, horizon in (("entry", 0), ("h5", 5000), ("h30", 30000)):
            milestones.append((row["t"] + horizon, index, kind))
    heapq.heapify(milestones)

    last_book = None
    last_received = None
    epoch = 0
    down = False
    good, bad = 0, 0

    def sample(at, index, kind):
        row = fills[index]
        field = kind + "_status"
        if kind != "entry" and row["entry_status"] != "ok":
            row[field] = "entry_unavailable"
            return
        if tick is None or tick <= 0:
            row[field] = "missing_tick"
            return
        if down or last_book is None:
            row[field] = "no_current_book"
            return
        book_time, mid, spread, book_epoch = last_book
        age = at - book_time
        if age <= 0 or age > max_book_age_ms:
            row[field] = "stale_or_same_millisecond"
            return
        if kind != "entry" and row.get("_epoch") != book_epoch:
            row[field] = "stream_reset"
            return
        direction = 1 if row["side"] == "Buy" else -1
        if kind == "entry":
            row["_epoch"] = book_epoch
            row["_mid"] = mid
            row["reference_age_ms"] = age
            row["spread_ticks"] = str(spread / tick)
            row["entry_edge_ticks"] = str(direction * (mid - row["fill_price"]) / tick)
        else:
            suffix = "5s" if kind == "h5" else "30s"
            row["markout_" + suffix + "_ticks"] = str(direction * (mid - row["fill_price"]) / tick)
            row["mid_move_" + suffix + "_ticks"] = str(direction * (mid - row["_mid"]) / tick)
        row[field] = "ok"

    opener = gzip.open if tape.suffix == ".gz" else open
    with opener(tape, "rt", encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            if not raw.strip() or raw.startswith("#"):
                continue
            parts = raw.rstrip("\r\n").split("\t")
            kind = parts[0]
            if kind == "I":
                try:
                    meta = json.loads(parts[1])
                    name = str(meta.get("Ticker") or "")
                    if name and name.casefold() != instrument.casefold():
                        raise ValueError("instrument name mismatch")
                    if verified_tick is None and meta.get("PriceStep") is not None:
                        candidate = dec(meta["PriceStep"])
                        if candidate > 0:
                            tick = candidate
                except (IndexError, TypeError, InvalidOperation) as error:
                    raise ValueError("bad instrument header") from error
                continue
            if kind not in ("B", "T", "G", "D", "U", "S"):
                continue
            try:
                received = int(parts[1])
            except (IndexError, ValueError) as error:
                raise ValueError("bad market receipt timestamp") from error
            if last_received is not None and received < last_received:
                raise ValueError("non-monotonic tape: no causal alignment is possible")
            last_received = received
            # Process sample BEFORE equal-timestamp book/reset events.
            while milestones and milestones[0][0] <= received:
                at, index, sample_kind = heapq.heappop(milestones)
                sample(at, index, sample_kind)
            if kind in ("D", "U"):
                down = kind == "D"
                epoch += 1
                last_book = None
            if kind == "B":
                try:
                    if len(parts) < 5 or not good_book(parts[3], parts[4]):
                        raise ValueError("invalid/crossed market book")
                    bid = dec(parts[3].split(";", 1)[0].split("@", 1)[0])
                    ask = dec(parts[4].split(";", 1)[0].split("@", 1)[0])
                    if not down:
                        last_book = (received, (bid + ask) / 2, ask - bid, epoch)
                        good += 1
                except (ValueError, InvalidOperation, TypeError):
                    bad += 1
                    last_book = None
    # No continuation can be inferred beyond the last observed tape event.
    while milestones:
        _, index, kind = heapq.heappop(milestones)
        fills[index][kind + "_status"] = "outside_recording"

    real = [x for x in fills if not x["synthetic"]]
    means = {}
    for suffix in ("5s", "30s"):
        vals = [dec(row["markout_" + suffix + "_ticks"]) for row in real
                if row["markout_" + suffix + "_ticks"] != ""]
        means["real_samples_" + suffix] = len(vals)
        means["mean_real_markout_" + suffix + "_ticks"] = (
            str(sum(vals) / len(vals)) if vals else "")
    summary = dict(
        state=state, instrument=instrument, day=day, recording=tape.name,
        fills=len(fills), real_fills=len(real), synthetic_fills=len(fills) - len(real),
        invalid_or_duplicate_fills=skipped, valid_books=good, invalid_books=bad,
        book_age_cap_ms=max_book_age_ms, tick=str(tick) if tick else "",
        entry_valid=sum(x["entry_status"] == "ok" for x in fills),
        h5_valid=sum(x["h5_status"] == "ok" for x in fills),
        h30_valid=sum(x["h30_status"] == "ok" for x in fills),
        **means,
        warnings=[
            "The specified state/instrument identity is not independently proven by historical config epochs.",
            "Fills have broker trade timestamps; tape books have local receipt timestamps.",
            "Equal-timestamp data is ignored, stale books and stream resets invalidate samples.",
            "This is a conditional sample of eligible fills; selection bias can be material.",
            "A markout is signed price movement in ticks, NOT net P&L or a trading signal.",
        ],
    )
    return fills, summary


def run(root: Path, output: Path, state: str, instrument: str,
        day: str, max_book_age_ms: int = 2000, verified_tick: str | None = None):
    root, output = validate_report_output(root, output)
    rows, summary = analyze(root, state, instrument, day, max_book_age_ms, verified_tick)
    output.mkdir(parents=True, exist_ok=False)
    with (output / "fill_markouts.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--instrument", required=True)
    p.add_argument("--day", required=True)
    p.add_argument("--max-book-age-ms", type=int, default=2000)
    p.add_argument("--tick", help="verified PriceStep if missing from recording")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    root = args.root.resolve()
    try:
        result = run(root, args.output or root / "reports" / ("markout-" + args.day),
                     args.state, args.instrument, args.day, args.max_book_age_ms, args.tick)
    except (OSError, ValueError, InvalidOperation) as error:
        print("Markout analysis refused:", error, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
