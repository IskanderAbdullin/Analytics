"""Finam Trade API adapter for instrument discovery and historical bars."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ipo_forecast.data.sources.http import HttpTransport, MarketDataApiError
from ipo_forecast.data.sources.market_data import normalize_finam_bar

FINAM_TIMEFRAMES = {
    "1m": "TIME_FRAME_M1",
    "5m": "TIME_FRAME_M5",
    "15m": "TIME_FRAME_M15",
    "30m": "TIME_FRAME_M30",
    "1h": "TIME_FRAME_H1",
    "2h": "TIME_FRAME_H2",
    "4h": "TIME_FRAME_H4",
    "8h": "TIME_FRAME_H8",
    "1d": "TIME_FRAME_D",
    "1w": "TIME_FRAME_W",
    "1mo": "TIME_FRAME_MN",
}
FINAM_LOOKBACK_DAYS = {
    "1m": 7,
    "5m": 30,
    "15m": 30,
    "30m": 30,
    "1h": 30,
    "2h": 30,
    "4h": 30,
    "8h": 30,
    "1d": 365,
    "1w": 365 * 5,
    "1mo": 365 * 5,
}


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Finam request timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class FinamClient:
    """Finam adapter. API secret is exchanged for a short-lived JWT session token."""

    provider_name = "finam"

    def __init__(
        self,
        api_secret: str | None = None,
        *,
        session_token: str | None = None,
        source_app_id: str | None = None,
        cache_dir: str | Path = "data/raw/market_data/cache/finam",
        transport: HttpTransport | None = None,
    ) -> None:
        self.transport = transport or HttpTransport(
            provider=self.provider_name,
            base_url="https://api.finam.ru",
            cache_dir=cache_dir,
            min_interval_seconds=0.31,
        )
        if session_token is None:
            secret = api_secret or os.getenv("FINAM_API_SECRET") or os.getenv("FINAM_TOKEN")
            if not secret:
                raise ValueError(
                    "Set FINAM_API_SECRET to the Finam Trade API secret; "
                    "do not paste credentials into the repository"
                )
            body: dict[str, Any] = {"secret": secret}
            app_id = source_app_id or os.getenv("FINAM_SOURCE_APP_ID")
            if app_id:
                body["source_app_id"] = app_id
            session = self.transport.request_json(
                "POST",
                "/v1/sessions",
                json_body=body,
                cache=False,
            )
            session_token = next(
                (
                    str(session[key])
                    for key in ("token", "accessToken", "access_token", "sessionToken")
                    if session.get(key)
                ),
                None,
            )
            if not session_token:
                raise MarketDataApiError(
                    self.provider_name,
                    "session response did not contain a JWT token",
                )
        self.transport.set_header("Authorization", session_token)

    @staticmethod
    def max_history_days(interval: str) -> int:
        if interval not in FINAM_LOOKBACK_DAYS:
            raise ValueError(f"Unsupported Finam interval: {interval}")
        return FINAM_LOOKBACK_DAYS[interval]

    def list_instruments(self) -> list[dict[str, Any]]:
        """Read all instruments, including archived ones, using cursor pagination."""
        instruments: list[dict[str, Any]] = []
        cursor = 0
        seen_cursors: set[int] = set()

        for _ in range(10000):
            page = self.transport.request_json(
                "GET",
                "/v1/assets/all",
                params={
                    "cursor": cursor,
                    "only_active": False,
                    "only_disabled": False,
                },
            )
            assets = page.get("assets", [])
            for asset in assets:
                symbol = str(asset.get("symbol") or "")
                ticker = str(asset.get("ticker") or symbol.split("@", maxsplit=1)[0])
                instruments.append(
                    {
                        "provider": self.provider_name,
                        "ticker": ticker.upper(),
                        "symbol": symbol,
                        "instrument_id": asset.get("id"),
                        "name": asset.get("name"),
                        "exchange": asset.get("mic")
                        or (symbol.split("@", maxsplit=1)[1] if "@" in symbol else None),
                        "isin": asset.get("isin"),
                        "is_archived": bool(
                            asset.get("isArchived", asset.get("is_archived", False))
                        ),
                        "api_trade_available": None,
                        "first_daily_candle_date": None,
                        "first_minute_candle_date": None,
                    }
                )

            next_cursor = int(page.get("nextCursor", page.get("next_cursor", 0)) or 0)
            if not next_cursor or next_cursor in seen_cursors or not assets:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        else:
            raise MarketDataApiError(
                self.provider_name, "instrument pagination exceeded 10000 pages"
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
    ) -> list[Any]:
        if interval not in FINAM_TIMEFRAMES:
            raise ValueError(f"Unsupported Finam interval: {interval}")
        if start >= end:
            raise ValueError("start must be earlier than end")
        symbol = (
            instrument
            if isinstance(instrument, str)
            else str(instrument.get("symbol") or "")
        )
        if not symbol:
            raise ValueError("Finam instrument must include symbol")

        encoded_symbol = quote(symbol, safe="@._-")
        response = self.transport.request_json(
            "GET",
            f"/v1/instruments/{encoded_symbol}/bars",
            params={
                "timeframe": FINAM_TIMEFRAMES[interval],
                "interval.start_time": _utc_iso(start),
                "interval.end_time": _utc_iso(end),
            },
            refresh=refresh,
        )
        return [
            candle
            for bar in response.get("bars", [])
            if (
                candle := normalize_finam_bar(
                    bar, symbol=symbol, interval=interval
                )
            )
            is not None
        ]
