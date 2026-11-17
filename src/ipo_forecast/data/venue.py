"""Conservative venue classification for cross-broker IPO coverage audits.

Ticker equality alone is not evidence that the issuer and exchange are correct.
Only known exact US primary-exchange MIC aliases earn primary_venue status.
All other broker instruments require explicit issuer/ISIN/venue verification.
"""

from __future__ import annotations

from typing import Any


PRIMARY_VENUE_ALIASES = {
    "NASDAQ": {"NASDAQ", "XNAS"},
    "NYSE": {"NYSE", "XNYS"},
    "NYSE AMERICAN": {"NYSE AMERICAN", "XASE", "AMEX"},
    "NYSE ARCA": {"NYSE ARCA", "ARCX", "XNYS ARCA"},
}
PRIMARY_MIC_CODES = set().union(*PRIMARY_VENUE_ALIASES.values())


def classify_venue(
    listing_exchange: str | None,
    instrument: dict[str, Any],
) -> str:
    """Return primary_venue, alternative_venue or unverified_venue."""
    requested = str(listing_exchange or "").upper().strip()
    reported = str(instrument.get("exchange") or "").upper().strip()
    if not requested:
        return "unverified_venue"
    aliases = PRIMARY_VENUE_ALIASES.get(requested, {requested})
    if reported in aliases:
        return "primary_venue"
    if reported:
        return "alternative_venue"
    return "unverified_venue"


def candidate_priority(
    listing_exchange: str | None,
    instrument: dict[str, Any],
) -> int:
    """Prefer exact primary venue; never infer that a foreign secondary listing matches."""
    classification = classify_venue(listing_exchange, instrument)
    return {
        "primary_venue": 3,
        "unverified_venue": 2,
        "alternative_venue": 1,
    }[classification]
