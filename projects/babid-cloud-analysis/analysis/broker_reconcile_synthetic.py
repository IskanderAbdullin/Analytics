"""Conservative offline matching of normalized synthetic trade facts.

No token, broker calls, CSV import, account identifiers, or live trading.
This candidate classifier alone cannot establish broker-side truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class TradeFact:
    account: str
    instrument: str
    side: str
    lots: int
    price: Decimal
    executed_utc: datetime
    trade_id_namespace: str
    trade_id: str

    def __post_init__(self) -> None:
        if not self.account or not self.instrument or not self.trade_id_namespace:
            raise ValueError("missing identity namespace")
        if self.side not in ("Buy", "Sell") or self.lots <= 0 or self.price <= 0:
            raise ValueError("invalid trade")
        if self.executed_utc.tzinfo is None or self.executed_utc.utcoffset() != timedelta(0):
            raise ValueError("execution timestamp must be timezone-aware UTC")


@dataclass(frozen=True)
class Decision:
    local_index: int
    status: str  # confirmed_id / candidate / ambiguous / unmatched
    broker_index: int | None
    reason: str


def reconcile_facts(local: list[TradeFact], broker: list[TradeFact],
                    tolerance_ms: int = 1000) -> list[Decision]:
    """Never turn a different ID namespace or ambiguous pair into proof.

    Same declared namespace and trade ID, identity, side, lots, price and a near
    UTC execution time is necessary for confirmed_id. Different namespaces
    yield candidates only. Broker records may be linked at most once.
    """
    if tolerance_ms < 0:
        raise ValueError("negative timestamp tolerance")
    if len({id(x) for x in local}) != len(local):
        raise ValueError("duplicate local object, deduplicate input explicitly")
    candidates: list[list[int]] = []
    for a in local:
        possible = []
        for j, b in enumerate(broker):
            if not (a.account == b.account and a.instrument == b.instrument and
                    a.side == b.side and a.lots == b.lots and a.price == b.price):
                continue
            time_delta = abs(a.executed_utc - b.executed_utc)
            if time_delta > timedelta(milliseconds=tolerance_ms):
                continue
            if (a.trade_id_namespace == b.trade_id_namespace and
                    a.trade_id and b.trade_id and a.trade_id != b.trade_id):
                continue
            possible.append(j)
        candidates.append(possible)
    broker_occurrences = [sum(j in row for row in candidates) for j in range(len(broker))]
    output = []
    for i, js in enumerate(candidates):
        if len(js) == 0:
            output.append(Decision(i, "unmatched", None, "no compatible broker execution"))
            continue
        if len(js) > 1 or broker_occurrences[js[0]] != 1:
            output.append(Decision(i, "ambiguous", None, "multiple compatible executions"))
            continue
        j = js[0]
        a, b = local[i], broker[j]
        if (a.trade_id_namespace == b.trade_id_namespace and
                a.trade_id and a.trade_id == b.trade_id):
            output.append(Decision(i, "confirmed_id", j, "same declared ID namespace and trade ID"))
        else:
            output.append(Decision(i, "candidate", j, "ID namespace differs or ID is missing; not proof"))
    return output
