"""T-Invest API adapter for shares, GetCandles, and annual minute archives."""

from __future__ import annotations

import csv
import io
import os
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ipo_forecast.data.sources.http import HttpTransport
from ipo_forecast.data.sources.market_data import (
    Candle,
    first_value,
    normalize_tinvest_candle,
    normalize_tinvest_history_row,
)

TINVEST_REST_PREFIX = "/rest/tinkoff.public.invest.api.contract.v1"
TINVEST_INTERVALS = {
    "1m": ("CANDLE_INTERVAL_1_MIN", 2400, 1),
    "5m": ("CANDLE_INTERVAL_5_MIN", 2400, 7),
    "15m": ("CANDLE_INTERVAL_15_MIN", 2400, 21),
    "1h": ("CANDLE_INTERVAL_HOUR", 2400, 90),
    "1d": ("CANDLE_INTERVAL_DAY", 2400, 365 * 6),
    "1w": ("CANDLE_INTERVAL_WEEK", 300, 365 * 5),
    "1mo": ("CANDLE_INTERVAL_MONTH", 120, 365 * 10),
}


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("T-Invest request timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class TInvestClient:
    """T-Invest REST adapter. Historical instrument enumeration includes ALL status."""

    provider_name = "tinvest"

    def __init__(
        self,
        token: str | None = None,
        *,
        cache_dir: str | Path = "data/raw/market_data/cache/tinvest",
        transport: HttpTransport | None = None,
    ) -> None:
        access_token = token or os.getenv("TINVEST_TOKEN") or os.getenv(
            "TINKOFF_INVEST_TOKEN"
        )
        if not access_token:
            raise ValueError(
                "Set TINVEST_TOKEN to your T-Invest API token; "
                "do not paste credentials into the repository"
            )
        self.transport = transport or HttpTransport(
            provider=self.provider_name,
            base_url="https://invest-public-api.tbank.ru",
            cache_dir=cache_dir,
            default_headers={"Authorization": f"Bearer {access_token}"},
            min_interval_seconds=0.4,
        )

    def list_instruments(self) -> list[dict[str, Any]]:
        """Return all shares, not only the base list currently tradable via API."""
        response = self.transport.request_json(
            "POST",
            f"{TINVEST_REST_PREFIX}/InstrumentsService/Shares",
            json_body={"instrumentStatus": "INSTRUMENT_STATUS_ALL"},
        )
        instruments = []
        for item in response.get("instruments", []):
            instruments.append(
                {
                    "provider": self.provider_name,
                    "ticker": str(item.get("ticker") or "").upper(),
                    "symbol": (
                        f"{item.get('ticker', '')}_{item.get('classCode', '')}"
                    ),
                    "instrument_id": item.get("uid") or item.get("figi"),
                    "uid": item.get("uid"),
                    "figi": item.get("figi"),
                    "name": item.get("name"),
                    "exchange": item.get("exchange") or item.get("classCode"),
                    "class_code": item.get("classCode"),
                    "isin": item.get("isin"),
                    "is_archived": None,
                    "api_trade_available": item.get("apiTradeAvailableFlag"),
                    "first_daily_candle_date": first_value(
                        item, "first1dayCandleDate", "first_1day_candle_date"
                    ),
                    "first_minute_candle_date": first_value(
                        item, "first1minCandleDate", "first_1min_candle_date"
                    ),
                }
            )
        return instruments

    def get_candles(
        self,
        instrument: dict[str, Any] | str,
        *,
        interval: str,
        start: datetime,
        end: datetime,
        refresh: bool = False,
    ) -> list[Candle]:
        if interval not in TINVEST_INTERVALS:
            raise ValueError(f"Unsupported T-Invest interval: {interval}")
        if start >= end:
            raise ValueError("start must be earlier than end")
        if end - start > timedelta(days=TINVEST_INTERVALS[interval][2]):
            raise ValueError(
                f"Requested {interval} range exceeds the documented single-request window"
            )
        instrument_id = (
            instrument
            if isinstance(instrument, str)
            else str(instrument.get("uid") or instrument.get("instrument_id") or "")
        )
        if not instrument_id:
            raise ValueError("T-Invest instrument must include uid or instrument_id")

        api_interval, _, _ = TINVEST_INTERVALS[interval]
        response = self.transport.request_json(
            "POST",
            f"{TINVEST_REST_PREFIX}/MarketDataService/GetCandles",
            json_body={
                "from": _utc_iso(start),
                "to": _utc_iso(end),
                "interval": api_interval,
                "instrumentId": instrument_id,
                "candleSourceType": "CANDLE_SOURCE_EXCHANGE",
            },
            refresh=refresh,
        )
        return [
            candle
            for item in response.get("candles", [])
            if (
                candle := normalize_tinvest_candle(
                    item,
                    symbol=instrument_id,
                    interval=interval,
                )
            )
            is not None
        ]

    def get_history_archive(
        self,
        instrument: dict[str, Any] | str,
        *,
        year: int,
        refresh: bool = False,
    ) -> bytes:
        """Download one annual ZIP archive of minute candles for a single instrument."""
        instrument_id = (
            instrument
            if isinstance(instrument, str)
            else str(instrument.get("uid") or instrument.get("instrument_id") or "")
        )
        if not instrument_id:
            raise ValueError("T-Invest instrument must include uid or instrument_id")
        if year < 1990 or year > datetime.now(UTC).year:
            raise ValueError("year is outside the supported calendar range")
        return self.transport.request_bytes(
            "GET",
            "/history-data",
            params={"instrument_id": instrument_id, "year": year},
            response_kind="zip",
            refresh=refresh,
        )

    @staticmethod
    def parse_history_archive(
        payload: bytes,
        *,
        symbol: str,
    ) -> list[Candle]:
        """Parse the documented headerless semicolon-separated CSV files in a ZIP."""
        candles: list[Candle] = []
        try:
            archive = zipfile.ZipFile(io.BytesIO(payload))
        except zipfile.BadZipFile as error:
            raise ValueError("T-Invest history response is not a valid ZIP archive") from error

        with archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".csv"):
                    continue
                with archive.open(info) as stream:
                    text_stream = io.TextIOWrapper(stream, encoding="utf-8-sig")
                    for row in csv.reader(text_stream, delimiter=";"):
                        candle = normalize_tinvest_history_row(row, symbol=symbol)
                        if candle is not None:
                            candles.append(candle)

        return sorted(candles, key=lambda candle: candle.timestamp)
