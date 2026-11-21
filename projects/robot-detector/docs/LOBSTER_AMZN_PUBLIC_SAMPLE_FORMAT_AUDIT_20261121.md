# Vendor public demo — real NASDAQ 10-level L2 event/book format QA

## Original source and rights gate

The [official historical LOBSTER sample page](https://php.lobsterdata.com/info/DataSamples.php)
**expressly offers downloadable demonstration files** based on
NASDAQ Historical TotalView-ITCH data and includes aligned
**orderbook** and **message** CSVs. We precommitted exactly the
AMZN 10-level **2012-06-21** archive and a **format-only** study in
Git commit `c864b763e3535810e3720c729710fc9ec84e9f0e`
**before its original download**.

[Original successful public GitHub Actions
#44922750898](https://github.com/IskanderAbdullin/Analytics/actions/runs/44922750898)
downloaded the original ZIP, checked bounds/ZIP paths, aligned
the two CSVs event by event, validated strict 6-message/
40-orderbook fields, order and timestamp monotonicity, bid/ask
level hierarchy, event direction and dummy-quote rules,
counted actual historical anomalies without silently cleaning,
and stored only a tiny aggregate JSON (artifact ID
`14713614697`, retention 7 days).

Vendor-sample source:
https://php.lobsterdata.com/info/sample/LOBSTER_SampleFile_AMZN_2012-06-21_10.zip

**Clarification, 2026-11-21:** LOBSTER itself
[offers sample datasets for public download](
https://php.lobsterdata.com/info/DataSamples.php), provides
Matlab/R research examples, and
[states that its academic work is research-oriented](
https://php.lobsterdata.com/info/help_faq_general.php).
Its separate [academic subscription agreement](
https://php.lobsterdata.com/termsAndConditions.php) covers
subscription access; that statement is **not an express
prohibition on noncommercial scientific experiments using
the publicly downloadable demo**. We previously treated
these two distinct matters as one and were over-restrictive.

**Practical project policy:** Continue noncommercial scientific
experiments with the public demo, release independently written
algorithms, methodology, figures and sufficiently aggregated
results with LOBSTER/NASDAQ source attribution. Do not commit
or redistribute the vendor's original event/book CSV or ZIP;
do not infer that it is licensed for commercial exploitation
or that additional subscription data are freely accessible.
The publisher's publicly displayed material does not clearly
specify universal downstream redistribution terms.
Actual licensed-training/redistribution obligations, if
material to a future release, should be resolved separately.
We have **not yet trained or validated a real robot detector
using this sample**; that remains a scientific status, not
a claimed legal prohibition on exploratory research.

The downloaded sample ZIP's **locally observed** byte SHA256:
`5cff62a609b27aef82285382ad646c4c2facc0a692a60bedda633de64c4aa54f`
(4,814,504 compressed bytes). This is **NOT** a checksum
published/signed by LOBSTER. Therefore it verifies local
identity across repetition only, not authenticated original
provider completeness.

## Structural QA observed on real old NASDAQ data

| Observed property | Original value |
|---|---:|
| Exact aligned original event and 10-level book-state rows | **269,748** |
| New visible limit-order submissions, type 1 | 131,954 |
| Partial cancels, type 2 | 2,917 |
| Full deletes, type 3 | 123,458 |
| Executions of visible *resting* limit orders, type 4 | **8,974** |
| Executions of hidden limit orders, type 5 | **2,445** |
| Cross trades, type 6 | 0 |
| Trading halt messages, type 7 | 0 |
| Visible executions with passive **SELL** / aggressive BUY | 4,808 |
| Visible executions with passive **BUY** / aggressive SELL | 4,166 |
| Adjacent messages with identical exchange timestamps | 8,483 |
| Consecutive book snapshots with changed best prices | 27,557 |
| Book states with crossed or locked top quotes | 0 |
| Book states missing either best bid or best ask | 0 |
| Dummy side-level slots (of 20 per row) | 0 |

Official field interpretation:
[LOBSTER output structure](https://php.lobsterdata.com/info/DataStructure.php).
A type-4 event's direction represents the **resting
limit-order side**, which is *opposite* the initiating trade
side. Treating direction=-1 as an aggressive SELL would
invert the aggressor correctly inferred from that execution.

These are event-weighted observations from vendor-provided
reconstruction, not proof of completeness or observed
real physical market-maker/robot identities. The order-book
snapshots are post-event, not pre-event views. The 10-level
sample is **not complete market-by-order depth** and does
not provide individual accounts. The underlying
NASDAQ data are from **2012**, not current microstructure.

## Reproducing format QA

```bash
cd projects/robot-detector
python -m unittest discover -s tests_background \
  -p 'test_lobster_public_sample_format_audit.py' -v

# Explicit public-demo network download for FORMAT QA ONLY:
python tools/lobster_public_sample_format_audit.py \
  --output data/results/lobster-demo-original-format-only.json
```

This tool has zero packages beyond the Python standard library,
bounded ZIP/member sizes/rows, no file extraction and no
order references in any report. The original source fetch Actions
was made **manual-only after the first successful execution**.

## Release scope

**Completed in this stage:** event/book structural format
validation and original aggregate checks.

**Next research stage:** reproducible, noncommercial
exploratory detection-method experiments on the freely
offered demo. The academic subscription agreement does not
by itself make that exploration impermissible. Distinguish
*technical/statistical validation* (still absent because
there is no labelled ground truth) from *data access rights*.
No commercial trading, vendor raw-file republication
or claim of unrestricted third-party reuse. Require
additional source terms if the project later seeks
subscription-only datasets or a commercial product.
