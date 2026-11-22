# Candidate D: burst-block relocation diagnostic, not a calibrated null (2026-11-22)

**Prospective frozen source-free plan:** [issue #97 comment 7075675938](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075675938).
This is exploratory work **after** examining A/B/C's 10ms burst results,
not an unseen market/source confirmatory trial. It does not alter the
preexisting 500ms candidate C, spend ABIDES seeds, create new market data,
or justify p-values / ownership / real-market FDR.

## Fixed construction

From the strictly sorted public exact-timestamp groups, partition each
UTC-aligned 5s cell into maximal adjacent blocks linked by unique gaps
<=10ms. Keep all relative within-block millisecond offsets, original
split-fill multiplicity and block order. Leave at least 10 unoccupied
millisecond slots between distinct blocks, guaranteeing their adjacent
unique timestamp gap is >10ms. Randomize remaining slack across before,
between and after blocks using uniform weak compositions (stars and bars).
64 replicates, seed 404 namespace \`rd-microburst-block-v1\`.
Counts in each 5s cell and total prints never change.
This is a **construction-specific randomization**, not an exchangeable
distribution independently justified on markets.

## Frozen adversarial tests and negative interpretation

Four source-free test groups:
- Tied two-block tape: all 64 replicates preserve UTC-cell occupancy,
  print multiplicities, and within-cell <=10ms gap count.
- Tape of two eight-event 1ms bursts at 1000..1007 and 3000..3007:
  observed **14** short gaps, retained by both B (rigid whole-cell
  shift) and D; original between-block boundary gap **1993ms**
  remains fixed under B, while D produces **more than one distinct**
  between-block gap across 64 replicates. So D's support is broader
  for inter-block timing than B's, but not proven calibrated.
- Unrelated 20s periodic stream: no injected target, short-gap count
  zero across 64 replicates. Its clock regularity is a strong hard
  negative for ownership claims; a short-gap metric cannot assess it.
- Empty and bad timestamps, booleans, noninteger seeds and negative
  replicates fail closed.

On the already inspected constructed A/B/C background tapes (development
only, same source-free sample), a supplementary D analysis gave the
**exactly conserved** <=10ms gap count in all 64 replicates:
Poisson-like 186/186, momentum-like 168/168, unrelated periodic 0/0.
This invariance is an **important negative result**: D is
*mathematically powerless* for a test statistic it directly conditions on.
It is only a possible diagnostic of longer-scale features and cannot
distinguish an external periodic actor from a targeted robot by itself.

The four new tests passed locally on source-equivalent transcribed code
(4/4), **not an exact repository checkout**. The cheap GitHub CI suite
must independently confirm the committed code.
A real fitted Hawkes model, source precision validation and owner labels
have not been tested.

**NEXT_ACTION:** verify committed D negative tests and workflow status.
Prospectively define a *distinct* long-period descriptive statistic,
multiple-testing policy and non-target periodic negative control to test
D's long-range discrimination; do NOT silently use the fixed short-gap
statistic (already conditioned away) or claim market significance.
