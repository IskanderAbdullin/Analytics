#!/usr/bin/env python3
"""Research-only Binance Vision SPOT raw public trades: verified compact audit.

License for the *data*: CC BY-NC-SA 4.0 and Binance Vision Dataset Terms
(2026-08-26). NON-COMMERCIAL research only. No live or commercial trading,
raw archive redistribution, private owner recovery, or trading endpoints.
The script fetches ONLY public date-scoped immutable static archives.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen
import zipfile

PROTOCOL = "public-binance-spot-execution-archive-audit-v1"
SOURCE = "https://data.binance.vision"
TERMS = "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md"
MAX_ZIP_BYTES = 60_000_000
MAX_CSV_BYTES = 400_000_000
MAX_TRADES = 3_000_000
HEADERS = ("id", "price", "qty", "quoteqty", "time", "isbuyermaker", "isbestmatch")
FLAG = {"true": True, "false": False}


def frozen_source(symbol: str, day: str) -> tuple[str, date, str, str]:
    if type(symbol) is not str or not re.fullmatch(r"[A-Z0-9]{5,16}", symbol):
        raise ValueError("Invalid fixed spot instrument")
    if type(day) is not str or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", day):
        raise ValueError("Invalid UTC session date")
    trading_day = date.fromisoformat(day)
    if trading_day >= datetime.now(timezone.utc).date():
        raise ValueError("Only previously completed UTC daily archives are allowed")
    name = f"{symbol}-trades-{day}.zip"
    url = f"{SOURCE}/data/spot/daily/trades/{symbol}/{name}"
    return name, trading_day, url, url + ".CHECKSUM"


def verify_checksum(raw_zip: bytes, checksum_text: str, expected_name: str) -> str:
    if type(raw_zip) is not bytes or not 0 < len(raw_zip) <= MAX_ZIP_BYTES:
        raise ValueError("Empty, oversized or malformed ZIP download")
    if type(checksum_text) is not str:
        raise ValueError("Missing provider checksum")
    match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\s/]+)\s*", checksum_text)
    if match is None or match.group(2) != expected_name:
        raise ValueError("No exact source file checksum attestation")
    actual = sha256(raw_zip).hexdigest()
    if actual.lower() != match.group(1).lower():
        raise ValueError("Official ZIP checksum mismatch")
    return actual


def _decimal(value: str, label: str, *, positive: bool = False) -> Decimal:
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
        raise ValueError(f"Noncanonical {label}")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Bad decimal {label}") from exc
    if not number.is_finite() or (positive and number <= 0) or number < 0:
        raise ValueError(f"Invalid positive {label}")
    return number


def analyze_verified_zip(
    raw_zip: bytes, checksum_text: str, *, symbol: str, day: str
) -> dict:
    """Process bounded real or synthetic ZIP entirely in memory; no raw export.

    File SHA verifies byte-level identity with provider published CHECKSUM,
    NOT whether exchange captured all trades or timestamps accurately.
    """
    name, trading_day, url, checksum_url = frozen_source(symbol, day)
    digest = verify_checksum(raw_zip, checksum_text, name)
    min_us = int(datetime.combine(trading_day,time(),timezone.utc).timestamp()) * 1_000_000
    max_us = min_us + 86_400_000_000
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        files = archive.infolist()
        expected_csv = name[:-4] + ".csv"
        if (len(files) != 1 or files[0].filename != expected_csv
                or files[0].is_dir() or files[0].file_size > MAX_CSV_BYTES
                or files[0].file_size == 0 or files[0].flag_bits & 0x1):
            raise ValueError("Unexpected ZIP member, size or encryption")
        count = buyer_taker_count = seller_taker_count = 0
        buy_qty = sell_qty = Decimal(0)
        previous_id = previous_time = None
        id_gaps = 0
        first_id = first_time = last_id = last_time = None
        minutes = [0] * 1440
        first_row = True
        with archive.open(files[0]) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8", newline=""))
            for line in reader:
                if first_row:
                    first_row = False
                    if tuple(x.lower() for x in line) == HEADERS:
                        continue
                if len(line) != 7:
                    raise ValueError("Expected exactly 7 raw spot trade columns")
                trade_id, price, quantity, quoted, stamp, buyer_maker, best = line
                if not re.fullmatch(r"[0-9]+", trade_id):
                    raise ValueError("Bad trade ID")
                tid = int(trade_id)
                if not re.fullmatch(r"[0-9]{16}", stamp):
                    raise ValueError("Spot 2025+ must use 16-digit microsecond UTC timestamps")
                ts = int(stamp)
                if ts < min_us or ts >= max_us:
                    raise ValueError("Trade outside frozen UTC day")
                if previous_time is not None and ts < previous_time:
                    raise ValueError("Time reversal in exchange trade file")
                if previous_id is not None:
                    if tid <= previous_id:
                        raise ValueError("Duplicate or unordered exchange trade IDs")
                    id_gaps += tid - previous_id - 1
                p = _decimal(price, "price", positive=True)
                q = _decimal(quantity, "quantity", positive=True)
                _decimal(quoted, "quote quantity")
                maker = FLAG.get(buyer_maker.lower())
                matched = FLAG.get(best.lower())
                if maker is None or matched is None:
                    raise ValueError("Invalid public spot trade flags")
                # Binance isBuyerMaker=True implies aggressive SELL.
                if maker:
                    seller_taker_count += 1
                    sell_qty += q
                else:
                    buyer_taker_count += 1
                    buy_qty += q
                minutes[(ts-min_us)//60_000_000] += 1
                count += 1
                if count > MAX_TRADES:
                    raise ValueError("Archive exceeds approved bounded research sample")
                if count == 1:
                    first_id, first_time = tid, ts
                last_id, last_time = tid, ts
                previous_id, previous_time = tid, ts
    if not count or buyer_taker_count + seller_taker_count != count:
        raise ValueError("Empty or nonconserved official execution archive")
    active = [x for x in minutes if x]
    ordered = sorted(active)
    return {
        "schema_version": PROTOCOL,
        "source": "Binance Vision, official daily SPOT raw trades",
        "source_url": url, "checksum_url": checksum_url,
        "dataset_license": "CC BY-NC-SA 4.0; Binance Vision Dataset Terms 2026-08-26",
        "terms_url": TERMS, "commercial_use_allowed_without_license": False,
        "symbol": symbol, "utc_date": day, "time_unit": "microseconds",
        "source_zip_sha256": digest, "provider_published_checksum_matched": True,
        "source_zip_bytes": len(raw_zip),
        "public_trade_count": count,
        "first_trade_id": first_id, "last_trade_id": last_id,
        "missing_ids_inside_observed_range": id_gaps,
        "trade_ids_strictly_increasing": True,
        "exchange_event_timestamps_monotonic": True,
        "first_public_timestamp_us": first_time,
        "last_public_timestamp_us": last_time,
        "aggressive_buy_prints": buyer_taker_count,
        "aggressive_sell_prints": seller_taker_count,
        "aggressive_buy_base_quantity": str(buy_qty),
        "aggressive_sell_base_quantity": str(sell_qty),
        "minute_bins_in_complete_utc_day": 1440,
        "minute_bins_with_observed_trades": len(active),
        "max_trades_in_utc_minute": max(active),
        "median_trades_per_nonempty_minute": (
            ordered[len(ordered)//2] if len(ordered)%2 else
            (ordered[len(ordered)//2-1]+ordered[len(ordered)//2])/2
        ),
        "raw_trades_or_ids_exported": False,
        "l2_orderbook_present": False,
        "all_exchange_trades_independently_verified": False,
        "market_specific_false_alarm_rate_estimated": False,
        "real_world_owner_count_known": False,
        "tuned_detector_or_threshold": False,
        "live_or_commercial_trading_enabled": False,
        "limitations": [
            "Provider SHA-256 proves file integrity against published checksum, not market completeness.",
            "Binance spot public prints are neither MOEX trades nor order book L2.",
            "isBuyerMaker determines aggressor side; not physical buyer/seller owner identity.",
            "Archive may contain provider omissions even when IDs are sequential.",
            "This is new *descriptive* real-market evidence; no calibrated robot detection accuracy.",
            "Dataset license restricts use to non-commercial research absent separate license.",
        ],
    }


def _download_bounded(url: str, limit: int) -> bytes:
    with urlopen(Request(url,headers={"User-Agent":"MarketRobotDetector-research/1.0"}),
                 timeout=25) as response:
        raw = response.read(limit+1)
    if len(raw)>limit or not raw:
        raise ValueError("Unavailable, empty or oversized official archive")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol",default="LTCUSDT")
    parser.add_argument("--date",default="2026-11-18")
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    name, _, url, checksum_url = frozen_source(args.symbol,args.date)
    if args.output.exists():
        parser.error("Never overwrite prior read-only research evidence")
    checksum = _download_bounded(checksum_url, 250).decode("ascii")
    raw = _download_bounded(url, MAX_ZIP_BYTES)
    summary = analyze_verified_zip(raw,checksum,symbol=args.symbol,day=args.date)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as file:
        json.dump(summary,file,sort_keys=True,indent=2,allow_nan=False)
        file.write("\n")
    print("PUBLIC_EXCHANGE_TRADE_ARCHIVE", json.dumps({
        "symbol":summary["symbol"], "utc_date":summary["utc_date"],
        "source_zip_sha256":summary["source_zip_sha256"],
        "trades":summary["public_trade_count"],
        "id_gaps":summary["missing_ids_inside_observed_range"],
        "provider_checksum_matched":True,
        "physical_owner_count_known":False,
        "market_accuracy_estimated":False,
    },sort_keys=True))


if __name__ == "__main__":
    main()
