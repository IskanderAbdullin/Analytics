# Source-free microsecond-only timestamp cluster uncertainty set, preimplementation 2026-11-22

**NOT a probability interval, market calibration, independent source experiment or new original ABIDES run.** A lossy exporter maps distinct exact nanosecond source times into a single observed microsecond timestamp. The number of distinct source-time event clusters within that one observed microsecond is NOT identifiable from the coarse timestamps alone, even with perfectly known fixed public quote/exposure and model rates.

## Frozen mathematical identification contract

Consider exactly ONE coarse microsecond bucket with k public executed fills (1<=k<=100000), no original individual nanosecond timestamps available. Within that fixed 1000-nanosecond bucket, the unknown number d of distinct true source-nanosecond event time clusters must satisfy 1<=d<=min(k,1000). (This counts each ns tick only once; fills may share true timestamp.) Without further source information every integer d in this range can be constructed. Different physical owner partitions cannot be inferred from d.

Assume BOTH fixed known M0 and conditional model rates are strictly positive finite and **constant over that entire microsecond bucket**; otherwise ABSTAIN instead of crossing a causal BBO boundary. Original complete observation interval and model-specific compensators are FIXED and asserted source-free; the difference c = M0 integral minus M1 integral is a finite deterministic scalar. Then the exact public source-time-cluster M1-minus-M0 full-window likelihood gain is:
    delta(d) = d * ln(rate_M1/rate_M0) + c.
The **identification interval** (not confidence/credible interval) for unknown exact-ns identity is [min(delta(1), delta(min(k,1000))), max(...)]. If rate ratio=1 the range collapses. The interval is about unknown number of distinct **observable time clusters** only; no claim about real robot ownership or population error.

## Prospective numeric source-free falsifiers
Re-use already frozen one-bucket [34222.5] toy and trained M1v4-low=.75/s, M0=.625/s; integral difference c=2.5-2.875=-.375. For k=2 coarse identical microsecond strings, d could be 1 (true exact split fill) or 2 (true 1ns-separated events):
- d1 delta=-.1926784432060451.
- d2 delta=-.010356886412090205.
- Width=+ln(.75/.625)=+0.1823215567939549.
Existing source-free exact-ns and lossy-old-CSV panel must bracket these two values. No single point estimate is justified from microsecond-only event text.
For high regime rate_M1=.5/s vs .625/s, ln(.8)<0 and the interval endpoint ordering REVERSES; no model can choose favorable bound after seeing a heldout tape.
With k>1000, d<=1000 (not k) because a microsecond has 1000 discrete original ns slots. No giant/allocation or confidence interpretation.

## Hard negative tests and handling
- Wrong/boolean/zero/negative/noninteger k, k>100000, nonfinite, zero/negative or absurd rates, nonfinite compensator, missing/unknown clock precision and rate constant-regime assertion -> strict Abstain; no fallback to one guessed true timestamp cluster.
- Existing original source timestamps provided exactly ns do not need a bound; the bound applies only when microsecond strings have destroyed original ns distinctions. Never feed this envelope to a claim of original ABIDES study performance without actual source profiles.
- Strict aggregate output: bounds and possible cluster count range, public-only source-free flag, no source timestamp list/price/agent/order IDs, no estimated physical owners/FDR, no actual source jobs/seeds.
- Do not alter original old CSV exporter or original 160-source in-memory path. This is a new restricted source-free mathematical negative result.

NEXT_ACTION: implement pure microsecond one-bucket identification set and adversarial tests with exact cheap GitHub Python CI; reconcile new interval with prior 3-case constructed LL panel and report all limitations.
