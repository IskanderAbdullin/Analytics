#!/usr/bin/env python3
"""ABIDES-NG market-execution exporter with strict public/private separation.

Runs an actual ABIDES-NG matching-engine simulation (no broker access).
Emits an anonymous T-Invest-shaped CSV and a *separate* private manifest.
Do not expose --truth outside the trusted evaluation job.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

UPSTREAM_COMMIT = "ac7a2a7bf6e406cd2bbed887e22c5a5a790bb242"
FIELDS = (
    "TRADE_TS", "INSTRUMENT_UID", "DIRECTION", "PRICE", "QUANTITY",
    "TRADE_SOURCE", "EVENT_ID", "TICKER", "TRADING_MODE", "SESSION_ID",
    "DATA_KIND",
)


def _date_utc(ns: int) -> str:
    sec, nanosecond = divmod(int(ns), 1_000_000_000)
    return (datetime.fromtimestamp(sec, tz=timezone.utc)
            .replace(microsecond=nanosecond // 1000)
            .isoformat(timespec="microseconds").replace("+00:00", "Z"))


def project_executions(
    trades: list[Any], *, seed: int, ticker: str,
    controlled_agent_ids: list[int], revision: str = UPSTREAM_COMMIT
) -> tuple[bytes, dict[str, Any]]:
    """Return public bytes and private truth; never pass truth to a detector."""
    if seed < 0 or not ticker or len(set(controlled_agent_ids)) != len(controlled_agent_ids):
        raise ValueError("Invalid simulator seed, symbol, or controlled agent set")
    if any(not isinstance(x, int) or x < 0 for x in controlled_agent_ids):
        raise ValueError("Invalid controlled agent identifier")
    if not revision:
        raise ValueError("Missing simulator revision")

    public = io.StringIO(newline="")
    writer = csv.DictWriter(public, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    truth: list[dict[str, Any]] = []
    # Stable within one engine-produced execution history, including same-time
    # partial fills. Execution ordering is not parent-order identity.
    ordered = sorted(enumerate(trades), key=lambda pair: (int(pair[1].time_ns), pair[0]))
    for index, (_, trade) in enumerate(ordered):
        time_ns = int(trade.time_ns)
        price_cents = int(trade.price_cents)
        quantity = int(trade.quantity)
        passive = int(trade.passive_agent_id)
        aggressive = int(trade.aggressive_agent_id)
        side = str(trade.side).upper()
        if time_ns < 0 or price_cents <= 0 or quantity <= 0 or min(passive, aggressive) < 0:
            raise ValueError("ABIDES execution has invalid time/price/size/agent IDs")
        # ABIDES TradeAttribution.side denotes the PASSIVE order side.
        # Export the aggressive direction, not a claim about T-Invest semantics.
        if side not in ("BUY", "SELL"):
            raise ValueError(f"Unsupported ABIDES passive order side: {side}")
        aggressive_direction = "SELL" if side == "BUY" else "BUY"
        event_id = hashlib.sha256(
            f"abides-exec-v1|{seed}|{index}|{time_ns}|{price_cents}|{quantity}".encode()
        ).hexdigest()[:32]
        writer.writerow({
            "TRADE_TS": _date_utc(time_ns),
            "INSTRUMENT_UID": f"ABIDES-{ticker}",
            "DIRECTION": aggressive_direction,
            "PRICE": str(Decimal(price_cents) / 100),
            "QUANTITY": quantity,
            "TRADE_SOURCE": "EXCHANGE",
            "EVENT_ID": event_id,
            "TICKER": ticker,
            "TRADING_MODE": "SIM-LOB",
            "SESSION_ID": _date_utc(time_ns)[:10],
            "DATA_KIND": "SIMULATED_ABIDES_NG",
        })
        truth.append({
            "event_id": event_id,
            "passive_agent_id": passive,
            "aggressive_agent_id": aggressive,
        })
    csv_bytes = public.getvalue().encode("utf-8")
    manifest = {
        "schema_version": "abides-blind-v1",
        "seed": seed,
        "simulator": "abides-ng",
        "simulator_revision": revision,
        "instrument_uid": f"ABIDES-{ticker}",
        "public_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "complete_execution_attribution": True,
        "controlled_agent_ids": sorted(controlled_agent_ids),
        "events": truth,
    }
    return csv_bytes, manifest


def simulate(seed: int, *, mode: str = "twap") -> tuple[bytes, dict[str, Any]]:
    """Use the genuine ABIDES-NG exchange/limit-book matching pipeline."""
    from abides_markets.config_system import SimulationBuilder
    from abides_markets.config_system.agent_configs import (
        NoiseAgentConfig, POVExecutionAgentConfig,
        TWAPExecutionAgentConfig, VWAPExecutionAgentConfig,
    )
    from abides_markets.simulation import ResultProfile, run_simulation

    if mode not in ("twap", "vwap", "pov", "null"):
        raise ValueError("mode must be twap, vwap, pov or null")
    ticker = "ABM"
    builder = (
        SimulationBuilder().apply_template("liquid_market")
        .ticker(ticker).start_time("09:30:00").end_time("10:00:00")
        .enable_agent(
            NoiseAgentConfig(multi_wake=True, wake_up_freq="20s",
                             noise_mkt_close_time="10:00:00"), count=60
        ).seed(seed)
    )
    execution_window = dict(
        start_time_offset="00:01:00", end_time_offset="00:01:00",
        freq="45s", direction="BID", quantity=1_200, trade=True,
    )
    if mode == "twap":
        builder = builder.enable_agent(
            TWAPExecutionAgentConfig(**execution_window, order_style="market"), count=1
        )
    elif mode == "vwap":
        builder = builder.enable_agent(
            VWAPExecutionAgentConfig(**execution_window, order_style="market"), count=1
        )
    elif mode == "pov":
        builder = builder.enable_agent(
            POVExecutionAgentConfig(**execution_window, pov=0.25), count=1
        )
    # Trade attribution is sufficient: no raw agent logs, no account data.
    result = run_simulation(builder.build(),
                            profile=ResultProfile.SUMMARY | ResultProfile.TRADE_ATTRIBUTION)
    market = result.markets[ticker]
    if market.trades is None:
        raise RuntimeError("ABIDES did not expose complete trade attribution")
    expected_prefix = mode.upper() + "_EXECUTION_AGENT_"
    controlled = sorted(
        int(agent.agent_id) for agent in result.agents
        if str(agent.agent_name).startswith(expected_prefix)
    )
    if (mode != "null" and len(controlled) != 1) or (mode == "null" and controlled):
        raise RuntimeError("Controlled agent identity is ambiguous")
    output, private = project_executions(
        list(market.trades), seed=seed, ticker=ticker,
        controlled_agent_ids=controlled,
    )
    if not private["events"]:
        raise RuntimeError("No ABIDES matching-engine executions: cannot validate")
    # A controlled agent must actually execute: missing fills are a failed
    # experimental scenario, NOT proof that the detector missed a robot.
    if mode != "null" and not any(
        e["passive_agent_id"] in controlled or
        e["aggressive_agent_id"] in controlled
        for e in private["events"]
    ):
        raise RuntimeError(f"Controlled {mode} had zero matched fills")
    return output, private


def _create_once(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as target:
        target.write(contents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--mode", choices=("twap", "vwap", "pov", "null"), default="twap")
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    args = parser.parse_args()
    if args.public.resolve() == args.truth.resolve() or args.public.exists() or args.truth.exists():
        parser.error("Public and private paths must differ and must not exist")
    if args.seed < 0:
        parser.error("Seed must be nonnegative")
    public, truth = simulate(args.seed, mode=args.mode)
    _create_once(args.public, public)
    _create_once(args.truth, (json.dumps(truth, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({
        "mode": args.mode, "seed": args.seed,
        "public_prints": len(truth["events"]),
        "configured_controlled_agents": len(truth["controlled_agent_ids"]),
        "public_sha256": truth["public_sha256"],
        "simulator_commit": UPSTREAM_COMMIT,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
