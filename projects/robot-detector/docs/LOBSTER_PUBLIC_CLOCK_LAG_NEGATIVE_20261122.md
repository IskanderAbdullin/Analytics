# Original LOBSTER AMZN public clock/lag source-capability negative — 2026-11-22

**Evidence type:** *ONE bounded retrospective original public historical source-format/eligibility reanalysis*, **not** a new instrument-day, independent holdout, detector evaluation, market FDR, owner/robot count or proof of exchange completeness.

**Precommitted before source calculation:** [exact Decimal/lag protocol](LOBSTER_PUBLIC_CLOCK_LAG_ELIGIBILITY_PREREG_20261122.md), commit `6b276e26`; source-only code `dc536f54` and corrected source-free controls `79c6053e`. **Original public GitHub workflow [#45040590585](https://github.com/IskanderAbdullin/Analytics/actions/runs/45040590585) SUCCESS**, post-source allowlist/conservation validator SUCCESS; compact **aggregate-only artifact ID 14761716634**, retained 7 days. Source ZIP held only in runner memory, never uploaded or committed. One official historical LOBSTER AMZN 2012-06-21 ten-level demo already used by earlier project source QA. Local previously observed unsigned ZIP SHA256 `5cff62a609b27aef82285382ad646c4c2facc0a692a60bedda633de64c4aa54f` matched again; this remains **not provider-signed**.

## ALL preregistered findings (no omitted unfavorable observations)

| Source-only metric | Original count |
|---|---:|
| Message+post-event book rows aligned | **269,748** |
| Distinct **exact Decimal** exchange event timestamps | **261,265** |
| Adjacent message pairs with exactly equal source timestamp | **8,483** |
| Source rows with **noninteger millisecond** Decimal time | **269,747** (99.99963% of rows) |
| Adjacent **distinct exact** timestamps that would share the **same floor-millisecond bin** | **110,818** (42.41594% of exact timestamp groups) |
| Implied distinct floor-millisecond bins in this monotone source | **150,447** |
| Consecutive original source event gaps strictly longer than 10 seconds | **4** |
| Visible type-4 resting limit-order executions | **8,974** |
| Hidden type-5 executions (kept separate) | **2,445** |
| Visible executions with locally eligible **strictly earlier** post-event BBO after **1-second lag**, age ≤10 seconds | **8,927** (99.47626% of visible) |
| Visible executions ABSTAIN: no prior 1-second-eligible quote | **43** |
| Visible executions ABSTAIN: last quote older than 10 seconds | **4** |
| Visible executions ABSTAIN: invalid prior two-sided BBO | **0** |
| Visible execution coverage conservation | **8,927 + 43 + 4 + 0 = 8,974** |

The millisecond collision statistic counts adjacent *different true Decimal exchange timestamps* that would merge under integer-ms truncation. It is **not** the number of physical parent orders or owners. No raw timestamps/order identifiers/quotes were preserved in output. The exact original 8,483 tied timestamp pairs are distinct from the additional **110,818 false ties introduced by flooring**.

## Negative scientific conclusion

**The current M0/M1-v2/M2 implementation's exact integer-millisecond event representation cannot be declared an information-preserving transformation of this original public LOBSTER sample.** Nearly all raw timestamps have sub-ms components, and blindly flooring to milliseconds would collapse **42.4%** of distinct exact event-time groups. Treating resulting split-fill clusters as original precise source events would create severe measurement pseudoreplication/coarsening; it risks false timing/parent-order conclusions. **Do not round/truncate this sample for M1-v2 or M2 without an independently preregistered, validated lossless clock representation.**

This **does not** mean LOBSTER data lack precise timestamps; the original historical source has *finer* timestamps than the fixed model clock. It means our model's current clock representation is insufficient. A lossless integer-nanosecond or exact Decimal event-time model could preserve the source order, but requires separate unit-contract version and source-specific proof that all source fractions are representable. This audit itself did not fit any detector, test a robot prediction, or join an oracle.

Local 1-second lag +10-second age eligibility is descriptively high (8,927/8,974), but this is **conditional on the reconstructed historical source and its observed event/book rows only**. It does not attest that the feed captured every market event, full depth/MBO, true exchange owner IDs, independent source ground truth or commercial data rights. Original orderbook row k is **post-event** k, and the causal algorithm intentionally excludes it for event k.

**Constraints:** official publicly offered historical demonstration, noncommercial scientific analysis, original ZIP/CSV never redistributed; no new independent market-days, ABIDES seed allocation, p-values, real-market owner/FDR claims. Workflow was switched to **manual-only** after this one successful bounded run to prevent duplicate source downloads.

**NEXT_ACTION:** design and preregister a **lossless nanosecond (or exact Decimal) source-time normalization** plus original-world split/coverage checks before trying real LOBSTER M0/M1-v2/M2 predictive method. Preserve direct 1ms-coercion as a **FAILED source eligibility gate**, not a trigger to loosen model thresholds.
