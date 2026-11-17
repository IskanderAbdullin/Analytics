from datetime import date
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from ipo_forecast.data.coverage import load_coverage_universe, run_coverage_audit
from ipo_forecast.data.sources.http import HttpTransport, MarketDataApiError
from ipo_forecast.data.sources.market_data import (
    normalize_finam_bar,
    normalize_tinvest_candle,
    parse_decimal,
    parse_timestamp,
)
from ipo_forecast.data.sources.tinvest import TInvestClient


def test_decimal_and_timestamp_normalisation():
    assert parse_decimal({"units": "12", "nano": 500000000}) == 12.5
    assert parse_decimal("1.25") == 1.25
    assert parse_timestamp("2025-01-02T04:00:00Z") == "2025-01-02T04:00:00Z"
    assert parse_timestamp({"seconds": 1735790400, "nanos": 0}) is not None


def test_finam_and_tinvest_candles_use_explicit_volume_units():
    finam = normalize_finam_bar(
        {
            "timestamp": "2025-01-02T14:30:00Z",
            "open": "10.1",
            "high": "10.5",
            "low": "10.0",
            "close": "10.4",
            "volume": "1500",
        },
        symbol="TEST@XNAS",
        interval="1d",
    )
    tinvest = normalize_tinvest_candle(
        {
            "time": "2025-01-02T14:30:00Z",
            "open": {"units": "10", "nano": 100000000},
            "high": {"units": "10", "nano": 500000000},
            "low": {"units": "10", "nano": 0},
            "close": {"units": "10", "nano": 400000000},
            "volume": "15",
        },
        symbol="uid-1",
        interval="1d",
    )
    assert finam is not None and finam.volume_unit == "shares"
    assert tinvest is not None and tinvest.volume_unit == "lots"
    assert tinvest.open == 10.1


def test_tinvest_history_archive_parser_reads_headerless_semicolon_csv():
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "2025-01-02.csv",
            "uid-1;2025-01-02T14:30:00Z;10.1;10.4;10.5;10.0;15;\n",
        )
    candles = TInvestClient.parse_history_archive(buffer.getvalue(), symbol="uid-1")
    assert len(candles) == 1
    assert candles[0].open == 10.1
    assert candles[0].close == 10.4
    assert candles[0].volume_unit == "lots"


def test_tinvest_archive_parser_rejects_non_zip_payload():
    with pytest.raises(ValueError, match="not a valid ZIP"):
        TInvestClient.parse_history_archive(b"not a zip", symbol="uid-1")


def test_http_transport_caches_successful_response(tmp_path):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"ok":true}'

    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response()

    transport = HttpTransport(
        provider="test",
        base_url="https://example.test",
        cache_dir=tmp_path,
        opener=opener,
    )
    first = transport.request_json("GET", "/health")
    second = transport.request_json("GET", "/health")
    assert first == second == {"ok": True}
    assert len(calls) == 1


def test_http_transport_does_not_retry_client_errors(tmp_path):
    from urllib.error import HTTPError

    def opener(_request, timeout):
        raise HTTPError("https://example.test", 401, "unauthorized", {}, None)

    transport = HttpTransport(
        provider="test",
        base_url="https://example.test",
        cache_dir=tmp_path,
        opener=opener,
        sleeper=lambda _seconds: None,
    )
    with pytest.raises(MarketDataApiError) as error:
        transport.request_json("GET", "/private")
    assert error.value.status_code == 401


def test_coverage_universe_allows_pending_and_rejects_duplicate_tickers(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text(
        "ticker,issuer_name,listing_date\n"
        "ANT,Anthropic,\n"
        "SNOW,Snowflake,2020-09-16\n",
        encoding="utf-8",
    )
    rows = load_coverage_universe(path)
    assert rows[0]["listing_date"] is None
    assert rows[1]["listing_date"] == date(2020, 9, 16)

    path.write_text(
        "ticker,issuer_name\nSNOW,Snowflake\nSNOW,Snowflake duplicate\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate ticker"):
        load_coverage_universe(path)


def test_coverage_audit_records_provider_lookup_and_candle_statuses(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text(
        "ticker,issuer_name,listing_date,exchange,event_type\n"
        "TEST,Test Corp,2025-01-02,XNAS,ipo\n"
        "MISS,Missing Corp,2025-01-02,XNAS,ipo\n",
        encoding="utf-8",
    )

    class FakeProvider:
        provider_name = "finam"

        def list_instruments(self):
            return [
                {
                    "ticker": "TEST",
                    "symbol": "TEST@XNAS",
                    "instrument_id": "asset-1",
                    "exchange": "XNAS",
                }
            ]

        def get_candles(self, instrument, *, interval, start, end, refresh=False):
            from ipo_forecast.data.sources.market_data import Candle

            return [
                Candle(
                    timestamp="2025-01-02T14:30:00Z",
                    open=10,
                    high=11,
                    low=9,
                    close=10.5,
                    volume=100,
                    volume_unit="shares",
                    provider="finam",
                    symbol=instrument["symbol"],
                    interval=interval,
                )
            ]

    rows, summary = run_coverage_audit(
        path,
        {"finam": FakeProvider()},
        today=date(2025, 1, 10),
        daily_window_days=5,
    )
    assert rows[0]["instrument_status"] == "found"
    assert rows[0]["daily_status"] == "available"
    assert rows[0]["daily_candle_count"] == 1
    assert rows[1]["instrument_status"] == "not_found_in_catalog"
    assert summary["providers"]["finam"]["ipo_daily_windows_with_data"] == 1


def test_coverage_audit_supports_recent_active_data_control(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text(
        "ticker,issuer_name,listing_date,event_type,training_eligible,probe_days_ago\n"
        "AAPL,Apple,,active_data_control,false,1\n",
        encoding="utf-8",
    )

    class FakeProvider:
        provider_name = "finam"

        def list_instruments(self):
            return [
                {
                    "ticker": "AAPL",
                    "symbol": "AAPL@XNAS",
                    "instrument_id": "asset-aapl",
                }
            ]

        def get_candles(self, instrument, *, interval, start, end, refresh=False):
            from ipo_forecast.data.sources.market_data import Candle

            return [
                Candle(
                    timestamp="2025-01-09T14:30:00Z",
                    open=200,
                    high=201,
                    low=199,
                    close=200.5,
                    volume=1000,
                    volume_unit="shares",
                    provider="finam",
                    symbol=instrument["symbol"],
                    interval=interval,
                )
            ]

    rows, summary = run_coverage_audit(
        path,
        {"finam": FakeProvider()},
        today=date(2025, 1, 10),
        daily_window_days=2,
    )
    assert rows[0]["probe_date"] == date(2025, 1, 9)
    assert summary["providers"]["finam"]["active_control_daily_smoke_tests_with_data"] == 1
