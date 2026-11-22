# Seven-period scan v1: zero-harmonic false rhythm and explicit v2 correction (2026-11-22)

**Pretest frozen reasoning and invariants:**
[issue #97 comment 7075694957](https://github.com/IskanderAbdullin/Analytics/issues/97#issuecomment-7075694957).
No frozen research protocol was silently rewritten: v1 source remains intact,
and v2 has a separate module and method_version. This is a correction
of an **observable measurement artifact**, not new evidence of a real robot.

## What the legacy scan actually measured

Original v1 returned a hit when
\`min(gap_ms % period_ms, period_ms - gap_ms % period_ms) <= 50ms\`.
For a **1ms** gap and every candidate 5000–60000ms period, this expression
is 1ms and therefore counts as a cadence hit: \`k=0\` is accepted as
a multiple. This makes a dense millisecond burst look like 5s, 10s,
15s, 20s, 30s, 45s and 60s rhythm simultaneously, even though
**none of those periods elapsed between consecutive events**.

The predeclared input \`[1000,1001,1002,1003]\` gives **3/3** v1
hits for all seven periods. v2 explicitly enforces
\`|gap-k*period| <=50ms\` with integer **k>=1**, giving **0/3**
for all seven on the same tape. The former metric should be labelled
legacy/zero-harmonic-sensitive if cited in any old results; no
retrospective reclassification of original source results is justified.

## Remaining scientific negative controls

Unrelated periodic non-target background
\`[1000,21000,41000,61000,81000,101000]\` still gives v2
**5/5** positive-harmonic hits at 5s, 10s and 20s; 0/5
at 15s,30s,45s,60s. A 45s synthetic cadence
\`[0,45000,90000]\` gives 2/2 hits at 5s,15s,45s,
despite a single underlying cadence. Thus positive harmonic
aliases, non-target periodic actors and true owner nonidentifiability
remain, even though the \`k=0\` artifact is corrected.

The same fixed ±50ms tolerance remains; 4950 and 5050ms
are 5s hits, while 4949/5051ms are misses. Exact timestamp
split-fill duplicates do not modify the unique-gap vector.
Reject malformed/unsorted inputs. No best-period/phase selection.

Five new adversarial source-free test groups passed **5/5 on locally
transcribed source-equivalent code**; exact committed GitHub CI
must confirm them. Prior D block-comparator technical checks were
independently verified by
[CI #44996522344](https://github.com/IskanderAbdullin/Analytics/actions/runs/44996522344);
they do not validate a market-timing null.

**Neither v1 nor v2 supplies an exchangeability theorem, probabilistic
market p-value, independent source or owner-ground-truth label.** Real
market FDR remains unknown. No ABIDES source runs were initiated in
this new stage.

**NEXT_ACTION:** confirm the new-HEAD v2 tests; then prospectively
compare the frozen v2 all-period score with existing A/B/C/D constructed
hard negatives, particularly the unrelated 20s background whose
periodicity remains indistinguishable from target cadence. Report
all seven periods and abstentions without selecting the best result.
