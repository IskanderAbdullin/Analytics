"""Shared market-data models and provider response normalisation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def first_value(payload: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in payload and payload[name] is not None:
            return payload[name]
    return default


def parse_decimal(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if "units" in value:
            units = Decimal(str(value.get("units", 0)))
            nano = Decimal(str(value.get("nano", 0)))
            return float(units + nano / Decimal("1000000000"))
        for key in ("value", "decimal"):
            if value.get(key) is not None:
                return parse_decimal(value[key])
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not parsed.is_finite():
        return None
    return float(parsed)


def parse_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, dict) and "seconds" in value:
        seconds = int(value.get("seconds", 0))
        nanos = int(value.get("nanos", 0))
        parsed = datetime.fromtimestamp(seconds + nanos / 1_000_000_000, tz=UTC)
    elif isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(float(value), tz=UTC)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    volume_unit: str
    provider: str
    symbol: str
    interval: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalise_candle(
    payload: dict[str, Any],
    *,
    provider: str,
    symbol: str,
    interval: str,
    timestamp_names: tuple[str, ...],
    volume_unit: str,
) -> Candle | None:
    timestamp = parse_timestamp(first_value(payload, *timestamp_names))
    values = {
        name: parse_decimal(payload.get(name))
        for name in ("open", "high", "low", "close", "volume")
    }
    if timestamp is None or any(value is None for value in values.values()):
        return None
    return Candle(
        timestamp=timestamp,
        open=float(values["open"]),
        high=float(values["high"]),
        low=float(values["low"]),
        close=float(values["close"]),
        volume=float(values["volume"]),
        volume_unit=volume_unit,
        provider=provider,
        symbol=symbol,
        interval=interval,
    )


def normalize_finam_bar(
    payload: dict[str, Any], *, symbol: str, interval: str
) -> Candle | None:
    return _normalise_candle(
        payload,
        provider="finam",
        symbol=symbol,
        interval=interval,
        timestamp_names=("timestamp", "time", "date"),
        volume_unit="shares",
    )


def normalize_tinvest_candle(
    payload: dict[str, Any], *, symbol: str, interval: str
) -> Candle | None:
    return _normalise_candle(
        payload,
        provider="tinvest",
        symbol=symbol,
        interval=interval,
        timestamp_names=("time", "timestamp"),
        volume_unit="lots",
    )


def normalize_tinvest_history_row(
    row: list[str], *, symbol: str
) -> Candle | None:
    if len(row) < 7:
        return None
    payload = {
        "time": row[1],
        "open": row[2],
        "close": row[3],
        "high": row[4],
        "low": row[5],
        "volume": row[6],
    }
    return _normalise_candle(
        payload,
        provider="tinvest",
        symbol=symbol,
        interval="1m_archive",
        timestamp_names=("time",),
        volume_unit="lots",
    )
