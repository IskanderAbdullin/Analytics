from datetime import date

import pytest

from ipo_forecast.data.sources.sec_edgar import (
    SecEdgarClient,
    extract_ipo_filings,
    filing_document_url,
)


def test_filing_document_url_normalises_cik_and_accession():
    url = filing_document_url("0001234567", "0001234567-26-000123", "final.htm")
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/1234567/"
        "000123456726000123/final.htm"
    )


def test_extract_ipo_filings_filters_forms_and_date_range():
    table = {
        "form": ["S-1", "10-K", "424B4", "F-1/A"],
        "filingDate": ["2026-01-01", "2026-01-02", "2026-01-03", "2025-12-31"],
        "acceptanceDateTime": [
            "2026-01-01T14:00:00Z",
            "2026-01-02T14:00:00Z",
            "2026-01-03T14:00:00Z",
            "2025-12-31T14:00:00Z",
        ],
        "accessionNumber": [
            "0001234567-26-000001",
            "0001234567-26-000002",
            "0001234567-26-000003",
            "0001234567-25-000004",
        ],
        "primaryDocument": ["s1.htm", "10k.htm", "424b4.htm", "f1a.htm"],
    }

    rows = extract_ipo_filings(
        1234567, [table], start_date=date(2026, 1, 1), end_date=date(2026, 1, 3)
    )

    assert [row["form"] for row in rows] == ["S-1", "424B4"]
    assert rows[0]["document_url"].endswith("/000123456726000001/s1.htm")
    assert rows[1]["is_amendment"] is False


def test_sec_client_requires_contactable_user_agent(tmp_path):
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        SecEdgarClient(user_agent="IPOAnalytics", cache_dir=tmp_path)
