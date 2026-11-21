# Public L2 and executed-print exact integer source semantics

**2026-11-21 — input-integrity stage only.** The exchange tape provides discrete nanoseconds, price ticks and integer lot counts; quietly converting `100.9` to `100` creates fictional order-book/trade observations. The research pipeline must reject such inputs before any apparent statistical correlation is computed.

## Change

`tools/public_numeric.py` defines `exact_nonnegative_integer(value, name, positive=False)`, using Python `operator.index` rather than `int()`. This allows exact integer scalars with the standard `__index__` protocol (including compatible NumPy integer types) while rejecting:

- Floating-point values even when numerically integral (`100.0`), because the upstream field should be declared as an integer type;
- Fractional floats (`100.9`), decimal values, strings and booleans;
- Negative timestamps and nonpositive prices, sizes and bounded settings.

The validator is used by `l2_probe.audit_l2_public`, `l2_trade_context.public_projection`, `l2_trade_context.audit_public_join` and `lagged_l2_bin.summarize_lagged_book`. No public market scalar is silently truncated in these ingestion paths. Source timestamps retain the existing no-deduplication policy; ambiguous exact-time quote/execution matches still abstain.

This change does **not** claim protection from every type of real-world timestamp parsing error: a provider adapter may already have rounded data **before** it reaches this function. Authenticating source representations still requires separately documented provider parsing and feed coverage.

## Regression checks

Eight no-NuGet/non-ABIDES Python unit tests in `tests_l2/test_public_numeric.py` check the exact `__index__` protocol, rejection of floats/bools/strings/Decimals/negatives, no silent truncation of quote times, L2 prices/lots/depth, public trade timestamps/price/lots, configuration parameters, plus an unchanged known integer fixture.

The existing pinned-ABIDES public L2 workflow runs the expanded `tests_l2` collection before any real matching-engine simulation; the new stage does not add its own expensive simulation job.

## Scientific limits

Type-correctness is a **necessary source quality invariant**, not a proof that the data is complete, that exchange event timing is causally ordered, that physical robot identities are known, or that a signal is predictive. The strict previous-bin study remains retrospective. Real-account orders, token access, GUI changes and trading remain out of scope. Scientific release gate CLOSED.
