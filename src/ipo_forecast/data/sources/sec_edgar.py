"""Small, cached SEC EDGAR client for filing discovery and company facts.

Set SEC_USER_AGENT to a descriptive application name and a real contact email.
The client defaults to five requests per second, below the SEC's published
maximum automated access rate.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

IPO_FORMS = {"S-1", "S-1/A", "F-1", "F-1/A", "424B4", "424B3", "424B5"}
SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


def filing_document_url(cik: int | str, accession_number: str, primary_document: str) -> str:
    """Build the canonical EDGAR archive URL for a filing's primary document."""
    if not primary_document:
        raise ValueError("primary_document is required")
    cik_path = str(int(cik))
    accession_path = accession_number.replace("-", "")
    document_path = quote(primary_document, safe="/._-")
    return f"{SEC_ARCHIVES_BASE}/{cik_path}/{accession_path}/{document_path}"


def _table_value(table: dict[str, Any], index: int, name: str, default: str = "") -> str:
    values = table.get(name, [])
    return values[index] if index < len(values) else default


def _in_date_range(
    filing_date: str,
    start_date: date | None,
    end_date: date | None,
) -> bool:
    parsed = date.fromisoformat(filing_date)
    return not (
        (start_date is not None and parsed < start_date)
        or (end_date is not None and parsed > end_date)
    )


def extract_ipo_filings(
    cik: int | str,
    filing_tables: list[dict[str, Any]],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Extract IPO-related filing candidates from SEC submissions table payloads."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for table in filing_tables:
        forms = table.get("form", [])
        for index, form in enumerate(forms):
            if form not in IPO_FORMS:
                continue

            filing_date = _table_value(table, index, "filingDate")
            if not filing_date or not _in_date_range(filing_date, start_date, end_date):
                continue

            accession = _table_value(table, index, "accessionNumber")
            if not accession or accession in seen:
                continue
            seen.add(accession)

            primary_document = _table_value(table, index, "primaryDocument")
            rows.append(
                {
                    "cik": str(int(cik)),
                    "form": form,
                    "filing_date": filing_date,
                    "acceptance_datetime": (
                        _table_value(table, index, "acceptanceDateTime") or None
                    ),
                    "report_date": _table_value(table, index, "reportDate") or None,
                    "accession_number": accession,
                    "file_number": _table_value(table, index, "fileNumber") or None,
                    "primary_document": primary_document or None,
                    "document_url": (
                        filing_document_url(cik, accession, primary_document)
                        if primary_document
                        else None
                    ),
                    "is_amendment": form.endswith("/A"),
                }
            )

    return sorted(rows, key=lambda row: (row["filing_date"], row["accession_number"]))


class SecEdgarClient:
    """SEC data.sec.gov client with explicit identity, throttling, retries, and cache."""

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        cache_dir: str | Path = "data/raw/sec_edgar/cache",
        min_interval_seconds: float = 0.2,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
    ) -> None:
        self.user_agent = user_agent or os.getenv("SEC_USER_AGENT", "")
        if "@" not in self.user_agent:
            raise ValueError(
                "Set SEC_USER_AGENT to an application name and contact email, "
                "for example 'IPOAnalytics contact@example.com'"
            )
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must not be negative")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._last_request_at = 0.0

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_for = self.min_interval_seconds - elapsed
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_request_at = time.monotonic()

    def _get_bytes(self, url: str, *, refresh: bool = False) -> bytes:
        cache_path = self._cache_path(url)
        if cache_path.exists() and not refresh:
            return cache_path.read_bytes()

        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/html, */*",
            },
        )
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = response.read()
                cache_path.write_bytes(payload)
                return payload
            except HTTPError as error:
                last_error = error
                if error.code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    raise
                retry_after = error.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else min(2**attempt, 30)
                except ValueError:
                    retry_time = parsedate_to_datetime(retry_after)
                    delay = max(0.0, retry_time.timestamp() - time.time())
                time.sleep(min(delay, 60))
            except URLError as error:
                last_error = error
                if attempt >= self.max_retries:
                    raise
                time.sleep(min(2**attempt, 30))

        raise RuntimeError(f"SEC request failed after retries: {last_error}")

    def _get_json(self, url: str, *, refresh: bool = False) -> dict[str, Any]:
        return json.loads(self._get_bytes(url, refresh=refresh))

    def get_company_tickers(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        """Return SEC's public ticker/CIK/company-name mapping."""
        payload = self._get_json(
            "https://www.sec.gov/files/company_tickers.json", refresh=refresh
        )
        return list(payload.values())

    def resolve_company(self, query: str) -> list[dict[str, Any]]:
        """Find ticker/CIK candidates by exact or partial ticker/company-name match."""
        needle = query.strip().casefold()
        if not needle:
            raise ValueError("query must not be empty")

        matches = []
        for company in self.get_company_tickers():
            ticker = str(company.get("ticker", ""))
            title = str(company.get("title", ""))
            if needle == ticker.casefold() or needle == title.casefold():
                rank = 0
            elif needle in ticker.casefold() or needle in title.casefold():
                rank = 1
            else:
                continue
            matches.append({**company, "match_rank": rank})

        return sorted(
            matches,
            key=lambda row: (row["match_rank"], str(row.get("title", "")).casefold()),
        )

    def get_submissions(self, cik: int | str, *, refresh: bool = False) -> dict[str, Any]:
        """Fetch the submissions history for a company CIK."""
        cik_number = int(cik)
        url = f"{SEC_DATA_BASE}/submissions/CIK{cik_number:010d}.json"
        return self._get_json(url, refresh=refresh)

    def get_company_facts(self, cik: int | str, *, refresh: bool = False) -> dict[str, Any]:
        """Fetch the SEC XBRL company-facts payload for a company CIK."""
        cik_number = int(cik)
        url = f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik_number:010d}.json"
        return self._get_json(url, refresh=refresh)

    def list_ipo_filings(
        self,
        cik: int | str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        include_historical: bool = True,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """List S-1/F-1 and prospectus filing candidates, including older SEC shards."""
        submissions = self.get_submissions(cik, refresh=refresh)
        filings = submissions.get("filings", {})
        tables = [filings.get("recent", {})]

        if include_historical:
            for shard in filings.get("files", []):
                shard_from = shard.get("filingFrom")
                shard_to = shard.get("filingTo")
                if start_date and shard_to and date.fromisoformat(shard_to) < start_date:
                    continue
                if end_date and shard_from and date.fromisoformat(shard_from) > end_date:
                    continue
                shard_name = shard.get("name")
                if shard_name:
                    tables.append(
                        self._get_json(f"{SEC_DATA_BASE}/submissions/{shard_name}", refresh=refresh)
                    )

        return extract_ipo_filings(
            cik, tables, start_date=start_date, end_date=end_date
        )
