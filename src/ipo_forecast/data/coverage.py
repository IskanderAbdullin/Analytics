"""Audit Finam and T-Invest coverage of a representative IPO universe."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from ipo_forecast.data.sources.market_data import Candle, parse_timestamp


def load_coverage_universe(path: str | Path) -> list[dict[str, Any]]:
    """Load a ticker universe; listing_date may be blank for pending/control rows."""
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"ticker", "issuer_name"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Coverage universe is missing columns: {sorted(missing)}")

        rows = []
        seen: set[str] = set()
        for row in reader:
            ticker = str(row.get("ticker") or "").strip().upper()
            issuer_name = str(row.get("issuer_name") or "").strip()
            if not ticker or not issuer_name:
                continue
            if ticker in seen:
                raise ValueError(f"Duplicate ticker in coverage universe: {ticker}")
            seen.add(ticker)
            listing_text = str(row.get("listing_date") or "").strip()
            try:
                listing_date = date.fromisoformat(listing_text) if listing_text else None
            except ValueError as error:
                raise ValueError(
                    f"Invalid listing_date for {ticker}: {listing_text}"
                ) from error
            probe_text = str(row.get("probe_days_ago") or "").strip()
            try:
                probe_days_ago = int(probe_text) if probe_text else None
            except ValueError as error:
                raise ValueError(
                    f"Invalid probe_days_ago for {ticker}: {probe_text}"
                ) from error
            if probe_days_ago is not None and probe_days_ago < 1:
                raise ValueError(f"probe_days_ago must be positive for {ticker}")
            rows.append(
                {
                    "ticker": ticker,
                    "issuer_name": issuer_name,
                    "exchange": str(row.get("exchange") or "").strip() or None,
                    "listing_date": listing_date,
                    "event_type": str(row.get("event_type") or "ipo").strip(),
                    "training_eligible": str(
                        row.get("training_eligible") or "true"
                    ).strip().lower()
                    in {"1", "true", "yes", "y"},
                    "probe_days_ago": probe_days_ago,
                    "notes": str(row.get("notes") or "").strip() or None,
                }
            )

    if not rows:
        raise ValueError("Coverage universe contains no valid tickers")
    return rows


def _date_from_metadata(value: Any) -> date | None:
    if value is None or value == "":
        return None
    timestamp = parse_timestamp(value)
    if timestamp:
        return date.fromisoformat(timestamp[:10])
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _utc_midnight(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _candle_date(candle: Candle) -> date:
    return date.fromisoformat(candle.timestamp[:10])


def _daily_limit_days(provider_name: str) -> int:
    return 365 if provider_name == "finam" else 365 * 6


def _previous_weekday(value: date) -> date:
    candidate = value
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def _evaluate_candidate(
    provider_name: str,
    provider: Any,
    candidate: dict[str, Any],
    target: dict[str, Any],
    *,
    today: date,
    daily_window_days: int,
    include_minute_archives: bool,
    refresh: bool,
) -> dict[str, Any]:
    listing_date = target["listing_date"]
    is_control = listing_date is None and target["event_type"] == "active_data_control"
    event_date = listing_date
    if is_control:
        probe_days = target.get("probe_days_ago") or 1
        event_date = _previous_weekday(today - timedelta(days=probe_days))

    result: dict[str, Any] = {
        "instrument_id": candidate.get("instrument_id"),
        "instrument_symbol": str(candidate.get("symbol") or target["ticker"]),
        "instrument_exchange": candidate.get("exchange"),
        "instrument_name": candidate.get("name"),
        "is_archived": candidate.get("is_archived"),
        "api_trade_available": candidate.get("api_trade_available"),
        "first_daily_candle_date": _date_from_metadata(
            candidate.get("first_daily_candle_date")
        ),
        "first_minute_candle_date": _date_from_metadata(
            candidate.get("first_minute_candle_date")
        ),
        "probe_date": event_date if is_control else None,
        "daily_status": "not_applicable",
        "daily_candle_count": 0,
        "daily_first_timestamp": None,
        "daily_last_timestamp": None,
        "daily_error": None,
        "minute_getcandles_status": "not_applicable",
        "minute_getcandles_count": 0,
        "minute_archive_status": "not_applicable",
        "minute_archive_candle_count": 0,
        "minute_archive_listing_day_count": 0,
        "minute_archive_first_timestamp": None,
        "minute_archive_last_timestamp": None,
        "minute_error": None,
    }

    if event_date is None:
        result["daily_status"] = "no_listing_date"
        result["minute_getcandles_status"] = "no_listing_date"
        result["minute_archive_status"] = "no_listing_date"
        return result

    age_days = (today - event_date).days
    if age_days < 0:
        result["daily_status"] = "event_date_in_future"
        result["minute_getcandles_status"] = "event_date_in_future"
        result["minute_archive_status"] = "event_date_in_future"
        return result

    daily_limit = _daily_limit_days(provider_name)
    if age_days > daily_limit:
        result["daily_status"] = "outside_documented_lookback"
    else:
        start = _utc_midnight(event_date)
        end = min(
            _utc_midnight(event_date + timedelta(days=daily_window_days + 1)),
            _utc_midnight(today + timedelta(days=1)),
        )
        try:
            daily = provider.get_candles(
                candidate,
                interval="1d",
                start=start,
                end=end,
                refresh=refresh,
            )
            daily = sorted(daily, key=lambda candle: candle.timestamp)
            result["daily_candle_count"] = len(daily)
            result["daily_status"] = "available" if daily else "no_candles_returned"
            if daily:
                result["daily_first_timestamp"] = daily[0].timestamp
                result["daily_last_timestamp"] = daily[-1].timestamp
        except Exception as error:  # Provider errors should not abort the whole audit.
            result["daily_status"] = "request_error"
            result["daily_error"] = str(error)

    if provider_name == "finam":
        if age_days > 7:
            result["minute_getcandles_status"] = "outside_documented_lookback"
        else:
            try:
                minute = provider.get_candles(
                    candidate,
                    interval="1m",
                    start=_utc_midnight(event_date),
                    end=_utc_midnight(event_date + timedelta(days=1)),
                    refresh=refresh,
                )
                result["minute_getcandles_count"] = len(minute)
                result["minute_getcandles_status"] = (
                    "available" if minute else "no_candles_returned"
                )
            except Exception as error:
                result["minute_getcandles_status"] = "request_error"
                result["minute_error"] = str(error)
        result["minute_archive_status"] = "not_supported_by_trade_api"

    elif is_control:
        try:
            minute = provider.get_candles(
                candidate,
                interval="1m",
                start=_utc_midnight(event_date),
                end=_utc_midnight(event_date + timedelta(days=1)),
                refresh=refresh,
            )
            result["minute_getcandles_count"] = len(minute)
            result["minute_getcandles_status"] = (
                "available" if minute else "no_candles_returned"
            )
        except Exception as error:
            result["minute_getcandles_status"] = "request_error"
            result["minute_error"] = str(error)
        result["minute_archive_status"] = "not_applicable_control"

    elif include_minute_archives:
        try:
            minute = provider.get_candles(
                candidate,
                interval="1m",
                start=_utc_midnight(event_date),
                end=_utc_midnight(event_date + timedelta(days=1)),
                refresh=refresh,
            )
            result["minute_getcandles_count"] = len(minute)
            result["minute_getcandles_status"] = (
                "available" if minute else "no_candles_returned"
            )
        except Exception as error:
            result["minute_getcandles_status"] = "request_error"
            result["minute_error"] = str(error)

        try:
            archive_bytes = provider.get_history_archive(
                candidate,
                year=event_date.year,
                refresh=refresh,
            )
            archive_candles = provider.parse_history_archive(
                archive_bytes,
                symbol=result["instrument_symbol"],
            )
            day_candles = [
                candle
                for candle in archive_candles
                if _candle_date(candle) == event_date
            ]
            result["minute_archive_candle_count"] = len(archive_candles)
            result["minute_archive_listing_day_count"] = len(day_candles)
            result["minute_archive_status"] = (
                "listing_day_available" if day_candles else "archive_without_listing_day"
            )
            if archive_candles:
                result["minute_archive_first_timestamp"] = archive_candles[0].timestamp
                result["minute_archive_last_timestamp"] = archive_candles[-1].timestamp
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            result["minute_archive_status"] = (
                "archive_not_found" if status_code == 404 else "request_error"
            )
            previous = result["minute_error"]
            result["minute_error"] = "; ".join(
                item for item in (previous, str(error)) if item
            )
    else:
        result["minute_getcandles_status"] = "skipped_by_option"
        result["minute_archive_status"] = "skipped_by_option"

    first_daily = result["first_daily_candle_date"]
    if listing_date and first_daily and first_daily > listing_date:
        result["first_daily_candle_after_listing_days"] = (
            first_daily - listing_date
        ).days
    else:
        result["first_daily_candle_after_listing_days"] = 0
    first_minute = result["first_minute_candle_date"]
    if listing_date and first_minute and first_minute > listing_date:
        result["first_minute_candle_after_listing_days"] = (
            first_minute - listing_date
        ).days
    else:
        result["first_minute_candle_after_listing_days"] = 0

    return result


def run_coverage_audit(
    universe_path: str | Path,
    providers: dict[str, Any],
    *,
    daily_window_days: int = 180,
    include_minute_archives: bool = True,
    refresh: bool = False,
    today: date | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compare provider instrument catalogues and IPO-date candle availability."""
    if daily_window_days < 1:
        raise ValueError("daily_window_days must be positive")
    audit_date = today or datetime.now(UTC).date()
    universe = load_coverage_universe(universe_path)
    rows: list[dict[str, Any]] = []

    for provider_name, provider in providers.items():
        try:
            instruments = provider.list_instruments()
        except Exception as error:
            for target in universe:
                rows.append(
                    {
                        "provider": provider_name,
                        "ticker": target["ticker"],
                        "issuer_name": target["issuer_name"],
                        "exchange": target["exchange"],
                        "listing_date": target["listing_date"],
                        "event_type": target["event_type"],
                        "training_eligible": target["training_eligible"],
                        "instrument_status": "catalog_error",
                        "matching_instruments": 0,
                        "instrument_ids": "",
                        "daily_status": "not_checked",
                        "daily_candle_count": 0,
                        "minute_getcandles_status": "not_checked",
                        "minute_archive_status": "not_checked",
                        "error": str(error),
                    }
                )
            continue

        ticker_map: dict[str, list[dict[str, Any]]] = {}
        for instrument in instruments:
            ticker = str(instrument.get("ticker") or "").upper()
            if ticker:
                ticker_map.setdefault(ticker, []).append(instrument)

        for target in universe:
            matches = ticker_map.get(target["ticker"], [])
            base = {
                "provider": provider_name,
                "ticker": target["ticker"],
                "issuer_name": target["issuer_name"],
                "exchange": target["exchange"],
                "listing_date": target["listing_date"],
                "event_type": target["event_type"],
                "training_eligible": target["training_eligible"],
                "probe_days_ago": target["probe_days_ago"],
                "notes": target["notes"],
                "matching_instruments": len(matches),
                "instrument_ids": ";".join(
                    str(item.get("instrument_id") or "") for item in matches
                ),
            }
            if not matches:
                rows.append(
                    {
                        **base,
                        "instrument_status": "not_found_in_catalog",
                        "daily_status": "not_applicable",
                        "daily_candle_count": 0,
                        "minute_getcandles_status": "not_applicable",
                        "minute_archive_status": "not_applicable",
                        "error": None,
                    }
                )
                continue

            candidate_results = [
                _evaluate_candidate(
                    provider_name,
                    provider,
                    candidate,
                    target,
                    today=audit_date,
                    daily_window_days=daily_window_days,
                    include_minute_archives=include_minute_archives,
                    refresh=refresh,
                )
                for candidate in matches
            ]
            best = max(
                candidate_results,
                key=lambda item: (
                    item.get("daily_candle_count", 0),
                    item.get("minute_archive_listing_day_count", 0),
                    item.get("minute_getcandles_count", 0),
                ),
            )
            errors = [
                value
                for key, value in best.items()
                if key.endswith("_error") and value
            ]
            rows.append(
                {
                    **base,
                    **best,
                    "instrument_status": "found",
                    "error": "; ".join(errors) if errors else None,
                }
            )

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "audit_date": audit_date.isoformat(),
        "universe_count": len(universe),
        "daily_window_days": daily_window_days,
        "minute_archives_checked": include_minute_archives,
        "providers": {},
    }
    for provider_name in providers:
        provider_rows = [row for row in rows if row["provider"] == provider_name]
        ipo_rows = [
            row for row in provider_rows if row.get("training_eligible") is True
        ]
        control_rows = [
            row
            for row in provider_rows
            if row.get("event_type") == "active_data_control"
        ]
        summary["providers"][provider_name] = {
            "tickers_checked": len(provider_rows),
            "instruments_found": sum(
                row.get("instrument_status") == "found" for row in provider_rows
            ),
            "ipo_daily_windows_with_data": sum(
                row.get("daily_status") == "available" for row in ipo_rows
            ),
            "ipo_minute_listing_days_with_data": sum(
                row.get("minute_archive_status") == "listing_day_available"
                or (
                    row.get("minute_archive_status") == "not_supported_by_trade_api"
                    and row.get("minute_getcandles_status") == "available"
                )
                for row in ipo_rows
            ),
            "active_control_daily_smoke_tests_with_data": sum(
                row.get("daily_status") == "available" for row in control_rows
            ),
            "active_control_minute_smoke_tests_with_data": sum(
                row.get("minute_getcandles_status") == "available"
                for row in control_rows
            ),
            "catalog_errors": sum(
                row.get("instrument_status") == "catalog_error"
                for row in provider_rows
            ),
        }
    return rows, summary
