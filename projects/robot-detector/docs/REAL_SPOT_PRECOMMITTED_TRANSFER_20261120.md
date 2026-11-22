# Prospective public trade-print transfer: LTCUSDT/BCHUSDT 2026-11-20

**Executed on a frozen previously uninspected set of real public trade
archives.** This is an in-scope non-commercial scientific *source
timing* test, not a blind test of an actual labelled trading-robot
detector.

## Freeze and source provenance

Preregistration was committed as
[`research/real_spot_transfer_precommit_20261121.json`](../research/real_spot_transfer_precommit_20261121.json)
at **`ae0d013645e4d7a1ab84757438c69ddff256dfbe`** *before*
the two selected archives were fetched. The frozen sources were:

- LTCUSDT, full **2026-11-20 UTC**, a third chronological public spot
  session following two previously inspected LTCUSDT days.
- BCHUSDT, full **2026-11-20 UTC**, different instrument **on the same
  market date** (not an independent market regime).

Frozen primary metric was: at 0s UTC origin and 30s complete bins,
observed one-sided-public-print bin count exceeds **the maximum of
eight** strong equal-timestamp cluster shuffle controls.
Report success *or failure* for **both** sources. Secondary 10s/20s
origin sensitivity and eight per-print weak shuffle controls.
No parameter search, asset/date substitution, after-the-fact
threshold adjustment or absolute significance/FDR claim.

[The original successful GitHub Actions archive run
#44920626852](https://github.com/IskanderAbdullin/Analytics/actions/runs/44920626852)
downloaded the two official, bounded daily ZIPs and their
published checksums. Python negative controls plus a strict
precommit-reconciliation audit passed before emitting the result.

## Original source integrity

| Symbol and UTC day | Observed public fills | First/last observed trade ID | Source ZIP SHA-256 |
|---|---:|---|---|
| LTCUSDT 2026-11-20 | **195,180** | 608464661 / 608659840 | `98eaafeb4f814f36f1d59de203e5cf74e4e7b3e7dd3cd93f2ca3153d32100a5a` |
| BCHUSDT 2026-11-20 | **73,279** | 296972770 / 297046048 | `553421be8eaf1e339eb0e111a25604ce7d2965e85ad15cea1650ffa0d012e46c` |

No observed trade-ID gaps inside either file. LTCUSDT starts
at **608464661**, exactly one after the previously inspected
2026-11-19 archive ended at **608464660**. This demonstrates
observed provider file continuity, **not proof every exchange
execution is captured**. Spot trades, not synchronized book L2.

## Predeclared results — negative cases included

| Real session | Origin | One-sided bins (observed) | Weak per-print null median | Strong same-time-cluster null median | Maximum of 8 strong shuffles | Observed above maximum? |
|---|---:|---:|---:|---:|---:|---|
| LTCUSDT 2026-11-20 | **0s primary** | **68** | 23 | 49 | 53 | **YES** |
| LTCUSDT 2026-11-20 | 10s sensitivity | 53 | 15 | 44.5 | 47 | Yes |
| LTCUSDT 2026-11-20 | 20s sensitivity | 57 | 16.5 | 43.5 | 50 | Yes |
| BCHUSDT 2026-11-20 | **0s primary** | **511** | 248.5 | 504 | 528 | **NO** |
| BCHUSDT 2026-11-20 | 10s sensitivity | 507 | 223 | 525.5 | 539 | No |
| BCHUSDT 2026-11-20 | 20s sensitivity | 515 | 232.5 | 518 | 538 | No |

Thus the precommitted across-both-instrument endpoint
**FAILED**: the effect persisted for LTCUSDT but not BCHUSDT.
For BCHUSDT the 0s absolute difference vs strong-null median was
just 7 bins, and observed 511 did not exceed its max 528.
In fact for the BCHUSDT 10s and 20s sensitivity views the
observed 507/515 bins are **below the strong-null medians**
525.5/518.

This negative outcome is scientifically useful. The strong
null nullifies most of the one-sided public trade-count apparent
signal in BCHUSDT. Unequal trade activity and single-print
intervals can overwhelm naive comparisons across symbols.

## Important interpretation and limitations

- This is **one market date**, two distinct instruments. The
  0/10/20s clock shifts reuse the exact same event tape and
  cannot be counted as independent trials.
- Both source days and instruments were fixed before
  downloads, but the research metric was developed using the
  earlier inspected Nov18–19 LTCUSDT sessions. This is a
  *prospective descriptive transfer*, **not independently
  labelled bot-actor generalization**.
- The eight shuffles are illustrative controls, not
  exchange-realistic causal randomizations, a p-value or
  a calibrated market false discovery rate.
- In the strong null each **whole vector of equal-timestamp
  trade sides** stays together, but is swapped among
  **equal-size groups within one minute**. The group is not
  necessarily kept at its own original timestamp. Neither
  real parent orders nor book depth can be recovered.
- This study provides **no physical agent count**, no
  execution-based true positive/false positive rate, and
  no trading-release permission.
- Binance Vision research data use is **non-commercial**
  under dataset terms/CC BY-NC-SA 4.0. The source workflows
  retain only small derived aggregate JSON for 7 days and
  have been switched to **manual dispatch only** after success.

Immutable summary-only observations are pinned in
[`fixtures/binance_spot_transfer_20261120_observed.json`](../fixtures/binance_spot_transfer_20261120_observed.json).
The original 7-day artifact is
`robot-detector-frozen-real-print-transfer-20261120` ID
`14713741159`. An exact file copy of that compact artifact
is available in the research session, but the raw provider
ZIP is never committed.

## Next methods stage

Do **not** reinterpret a failure as a detector success by
choosing another time phase or symbol after inspection.
Investigate source clock-interval **trade-count conditioning**:
single-print bins are mechanically one-sided; compare
within frozen occupancy classes (1, 2, 3–4, 5–9, 10+) under
the same side-vector cluster-preserving controls.
Freeze any next-session criteria and source identities
**before** fetching a distinct previously uninspected day.
This is methodological development, not performance tuning.
