# Constructed A/B/C timing-null negatives: full-panel diagnostic (2026-11-22)

**Scope:** source-free deterministic method development. Frozen upstream design:
[INTENSITY_CONDITIONED_NULL_PREREG_20261122.md](INTENSITY_CONDITIONED_NULL_PREREG_20261122.md).
Code is in tools/public_abc_report.py and tests_background/test_public_abc_constructed_controls.py.
**This is not a new ABIDES experiment, an exchange dataset, a market p-value,
or a calibrated algorithmic-trading detector.**

## Predeclared configuration and outcome

Three fixed constructed non-target cases, all 64 replicate indices r=0..63,
randomization seed 404, adjacent **unique** public timestamp gaps <=10ms
within UTC-aligned 5s cells. A: resample in 5s cells; B: translate whole
within-cell patterns; C: resample within fixed 500ms subcells. Preserve exact
simultaneous-print multiplicities. No best-model/phase/period selection.

| Constructed negative control | Public prints | Observed short gaps | A min–max; mean | B min–max; mean | C min–max; mean |
|---|---:|---:|---|---|---|
| Quantized exponential-gap Poisson-like | 1541 | 186 | 158–212; 184.0625 | 186–186; 186 | 154–208; 185.453125 |
| Momentum-like 8-event millisecond bursts in 24 cells | 192 | 168 | 0–7; 2.4375 | 168–168; 168 | 17–34; 24.765625 |
| Unrelated 20s periodic sequence (six events) | 6 | 0 | 0–0; 0 | 0–0; 0 | 0–0; 0 |

These numbers were reproduced **locally on a source-equivalent transcription** of
the current GitHub modules and the three existing constructed-control tests
(3/3 pass), plus new report unit tests (3/3 pass). The local run did not use
a checked-out copy of the repository. **Exact committed-code GitHub provenance CI #44995874723 SUCCESS**
ran the entire current-stage source-free test suite (38 explicit tests),
executed the report CLI and uploaded the small full 64-replicate artifact.
This verifies the committed-code technical reproduction, **not** statistical
exchangeability or generalisation to any exchange. The new report CLI emits all 64 replicate counts for every
scenario/model; keep the small aggregate-only JSON, not synthetic raw timestamps.

## Negative interpretation, not significance

1. Candidate C **does not preserve millisecond burst adjacency**:
   168 constructed adjacent short gaps collapse to 17–34, despite preserving
   each 500ms subcell's occupancy and simultaneous-print multiplicities.
   The 500ms conditioning is therefore not sufficient to model this
   hard-negative local dependence. A erases even more of it. Do not call
   either a calibrated null or derive a market p-value.
2. B retains every within-cell gap by construction, including a spurious
   periodic pattern, so its equality to observed does **not** imply
   successful pattern discrimination. It also has strongly restricted support.
3. All three short-gap models output zero for the unrelated 20s cadence:
   this metric cannot test that hard negative's periodicity. A separate
   *predeclared, all-period* periodic scan is necessary, not a posthoc
   favorable-period detector.
4. For the quantized Poisson-like source-free generator, observed 186 is
   inside A and C's 64-replicate ranges. This constructed example is not
   an independently fitted Poisson market model and is not evidence of
   overall calibration.
5. The 64 randomization replicates within each constructed tape are
   dependent views, **not** 64 independent market trials. Real
   owner identities and real-market FDR remain unknown.

## Source provenance, reproducibility and next action

Source at branch baseline \`87b0363690f7517b2e7be77b3486dc91c66be01d\`.
Run from projects/robot-detector at a clean checkout:

\`\`\`sh
PYTHONPATH=tools python -m unittest discover -s tests_background -p 'test_public_abc_constructed_controls.py' -v
PYTHONPATH=tools python -m unittest discover -s tests_background -p 'test_public_abc_report.py' -v
PYTHONPATH=tools python tools/public_abc_report.py --output data/results/abc-constructed-source-free.json
\`\`\`

The provenance workflow now executes the current source-free Python null
tests explicitly, rather than treating unrelated green .NET / ABIDES or
seed-ledger checks as proof of their execution. It uploads **only the small
derived aggregate** for 3 days; private oracle IDs and raw vendor data
are never included.

**NEXT_ACTION:** Check exact new HEAD CI and inspect A/B/C 64-replicate
artifact. If success, mark verified source-free *technical* execution,
not exchangeability; then preregister and run a fresh stronger local
intensity/dependence falsification, including timestamp-precision and
previous-only L2 abstention. Do not refit the 500ms width on these
already inspected development results.
