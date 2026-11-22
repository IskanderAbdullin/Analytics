# Scientific source-readiness audit: nanosecond visible-type4 detector (2026-11-22)

**DECISION: NO-GO for new independent original-market experiments or scientific detector release; GO for bounded source-free method development.** This is an evidence synthesis, NOT a new empirical validation, prediction, source acquisition, owner/FDR result or legal opinion.

## Technical result verified

Existing public Python source-free CI https://github.com/IskanderAbdullin/Analytics/actions/runs/45056270305 on commit 3462d88c passed **257/257**. Complete *source-free constructed* chain now exists:
- exact Decimal seconds after exchange-local midnight to typed integer nanoseconds, without truncation;
- event-type-aware public source projection, where **only type4 visible executions** create trade timestamps, type5 hidden executions are separately counted, and all public orderbook-changing message types contribute POST-event BBO to future exposure;
- source-bound public SHA256, original run label and replay guards (structural, NOT provider authentication);
- M1-v3 train-only spread-rate model fitted to the same visible-type4 event process later evaluated, with strictly 1-second-lagged post-event quotes and maximum 10-second quote age;
- complete-window held-out predictive log likelihood, with independent train/eval source labels, duplicate same-time execution cluster collapsing, and 1-nanosecond distinctness.

Fifteen source-free training/model methods and other negative cases passed on frozen toy source tapes. Synthetic positive algebra includes low .75/s and high .5/s, a five-public-message evaluation source with two visible type4 rows at one original timestamp, one hidden type5 and two nontrades. This yields one visible type4 timestamp, total causal integral 2.875 and heldout LL = log(.75)-2.875. Those are **constructed mathematical unit fixtures**, not real trading patterns or successful classification. Earlier malformed adversarial test inserted a later 1-ns event before an earlier public row; the correct UNSORTED rejection caused a CI failure at https://github.com/IskanderAbdullin/Analytics/actions/runs/45056210929; the test was reordered without changing any source/model/threshold.

## Independent source readiness matrix

| Necessary gate | Evidence and limitation | Decision |
|---|---|---|
| Public-only same event process for train/evaluation | Current source-free code uses type4 visible events for both. All post-event book messages affect causal future rates. | **PASS: engineering only** |
| Historical source timestamp precision | Original LOBSTER AMZN 2012 sample had 269,748 public message+book rows, 269,747 sub-ms timestamp rows; flooring to integer milliseconds merges 110,818 distinct original timestamps among 261,265 exact groups. Current typed ns code is lossless for representable Decimal test values but actual complete original file was **not** checked for exact ns representability. | **NOT PROVEN on original source** |
| Trade-only vs all-message time precision | 110,818 and 42.4% refer to **ALL LOBSTER message types**, NOT the 8,974 historical visible type4 execution rows. Historical type4-only distinct timestamp count and its ms coarsening remain UNKNOWN. | **BLOCKED for trade-only original source** |
| Book causality and full event coverage | LOBSTER official output specifies message row k transforms book k−1 into **POST-event** book k; model uses +1sec lag. But LOBSTER documentation notes non-book-changing NASDAQ messages can be skipped; a reconstructed book-aligned source does NOT independently attest every actual exchange execution or a full source feed. Source completeness is only asserted by caller. | **NO real feed completeness certification** |
| Original source provenance and independent units | Internal public source SHA and duplicate run-ID guards reject certain replays/mismatched public events, but the LOBSTER ZIP checksum was observed locally, not vendor-signed. Source-free toy labels are not independently generated market worlds. ABIDES 3301–3340 original seeds were previously inspected and later replays are not fresh. | **BLOCKED for new blinded study** |
| Statistical power / coverage | Frozen 4-way Bonferroni exact binomial hypothetical panel shows n=100 evaluation original worlds at positive alarm p=.90 and negative p=.01 have **joint power upper bound .3660**, at p=.02 **upper bound .1326**; true within-seed dependence unspecified. Old synthetic grouped false alarm 6/40 Poisson and 7/40 momentum already exceeds these hypothetical rates. | **NO-GO on proposed n=100 release plan** |
| License, true market owner labels, commercial use | Official LOBSTER provides historical AMZN academic demo, but no universal commercial/raw redistribution right established. Coinbase Market Data Terms last updated 2026-08-07 restrict algorithm/AI research/development without express permission, including derived work dissemination. MOEX non-display use also unverified. No independent market physical owner labels. | **BLOCKED** |
| Independent predictive performance of current M1-v3 | New code tested on constructed synthetic public tapes only; no independent original source validation. On older constructed negative tapes, M2 train chose excitation 0 and exactly equaled M0 LL -3, while M1-v2 scored worse on all three. | **UNKNOWN real source accuracy/FDR** |

## Source evidence and negative interpretation

The official LOBSTER output structure (https://php.lobsterdata.com/info/DataStructure.php) explicitly distinguishes event type 1 submissions, 2 cancellations, 3 deletions, 4 executions of visible limit orders, 5 hidden executions, 6 cross trades and 7 halts. A resting sell limit order execution corresponds to buyer-initiated trade and vice versa. Book row k is AFTER corresponding event k. Those constraints substantiate the source-free type4/trade distinction but do not make each full-source message a trade. Official public demo list: https://php.lobsterdata.com/info/DataSamples.php.

Prior one original sample source-only report: [LOBSTER clock and quote negative](LOBSTER_PUBLIC_CLOCK_LAG_NEGATIVE_20261122.md) and successful bounded aggregate-only workflow https://github.com/IskanderAbdullin/Analytics/actions/runs/45040590585. Historical type4 quote locally eligible after frozen 1sec post-event lag for 8,927/8,974, 43 ABSTAIN no prior, 4 stale; **local reconstructed source eligibility, NOT proof of exchange completeness or owner accuracy**. The workflow is now manual-only; do not redownload raw vendor ZIP.

Negative source-free model result: [constructed three-tape heldout LL](CROSSMODEL_HELDOUT_LL_NEGATIVE_20261122.md). Sample size: [power feasibility negative](INDEPENDENT_POWER_FEASIBILITY_AUDIT_20261122.md). Rights: [source licenses](REAL_SOURCE_LICENSE_GATES.md). Coinbase source terms: https://www.coinbase.com/legal/market_data, 2026-08-07 section 3(5).

## Decision / future evidence obligations

Before allocating original simulation/source evaluation seeds or seeking real feed data, freeze ALL:
1. Source rights/pinning and provider checksum/authenticity or explicit unsigned limitation; public output must remain aggregate-only.
2. Exactly which exchange event type defines the predictable process, including type5 hidden/cross type6/missing channels, and consistent train/calibration/evaluation treatment.
3. Source-specific exact integer-nanosecond representability, true tied-event ordering, per-type timestamp collision diagnostics, independent clock precision and complete event/L2 capture evidence. Do not silently round source times.
4. Original independent world split into disjoint train/calibration/evaluation with paired four-background complete cohorts, spent seed register and matching engine revision, frozen classifier/hyperparameters, coverage and ABSTAIN rules.
5. Familywise confidence intervals, power/resource/cost plan and predeclared scientific rejection gates not retrofitted after negative outcomes.
6. Distinction between source-free mathematical correctness, controlled-source synthetic oracle evaluation and unavailable real-market physical owner/FDR.

**At this checkpoint: no new original vendor data, simulator seeds, trades, physical-identity claim or actual market FDR.** Master scientific release issue #72 stays OPEN. A well-supported impossibility/uncertainty boundary is acceptable scientific research progress.


## Observable identical-timestamp multiplicity is deliberately lost for this intensity estimand

**Additional scientific identifiability bound, 2026-11-22; no new experiment:** M1-v3 is a **unique-public-timestamp cluster** event-intensity model, not a model of each executed order or market participant. If one observable source contains a single type4 execution at source time t and another contains two or more type4 executions at EXACTLY t, the model inputs use the same unique timestamp set (assuming all other source timestamps and its causal quote exposure are fixed). Consequently the source-free full-window point-process LL is mathematically identical: sum over unique t of log rate minus the same full exposure integral. This remains true whether the extra same-time execution arose from a split fill of one order or independent unrelated counterparties. The safe source aggregate still reports the **number of raw visible type4 executions separately**, so the model does NOT silently assert that multiplicity was absent, but its fitted cluster rate and LL do not infer the number of underlying parent orders.

This is a many-to-one **feature projection**, not a proof that two physically different market histories are fully observationally identical across *all* public fields. It is a model-specific identifiability limitation, and same-time individual executions may carry additional public information (side, size, price, within-tick order) intentionally excluded from this minimal timestamp-only estimand. A later richer count/mark model would require separate pre-registration, independent data and simultaneous-event chronology controls. Existing source-free split-fill/1ns-distinctness tests are integrity checks of this declared estimand, not evidence of physical bots. No new claim of market FDR, unique robot count or original source quality is made.
