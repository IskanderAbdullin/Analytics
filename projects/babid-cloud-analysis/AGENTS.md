# Babid Cloud analysis: repository-scoped agent rules

This is an analytical-only project in the **Analytics** GitHub repository.

- You may read source code from the original Babid Cloud application to learn
  data contracts, but **never change any other repository**.
- Do not commit trading source code, real accounts, trade logs, credentials,
  snapshots, broker APIs, or genuine market recordings into this public project.
- Use only synthetic fixtures in GitHub Actions, which run in Analytics itself.
- Do not connect to a broker or access/control the user's Windows computer without separately explicit user authorization for the specific purpose. Even with approval, this analytical project is limited to read-only inspection of a frozen local copy or authorized read-only broker evidence; no GUI trading, order entry, position changes or edits to a running robot.
- Analysis scripts read a user-supplied **copy** and emit local reports only.
- A source mismatch, fill anomaly or quote-feasibility score is evidence for
  investigation, not permission to change live trading parameters.
- Document every completed research/development step as an OsEngine Lab v2
  JSON event under the root `reports/osengine-lab/events/` of Analytics.
- Run both OS CI jobs before representing tests as successful.


## Continuous research and recovery (required)

The terminal goal is evidence-backed resolution of the real Babid Cloud incident
and assessment of historical trading — NOT green CI, a PR, or a code commit.

Every session MUST read GOAL.md, STATE.json, NEXT_ACTION.json, EVIDENCE.md,
BACKLOG.md and PROTOCOL.md, and run the state validator before choosing work.
Continue the highest-priority feasible task after each milestone. Prefer the
action that most reduces uncertainty about the incident, not easy extra tests.

Before EVERY commit, update evidence, hypothesis status, current action and
next executable action in the same commit. Commit/push only to Analytics,
without force-push. If blocked on real files or authorization, retain
goal_status=in_progress, mark the next action blocked_external, record exact
missing inputs and a resumption command. Never say root cause was proven from
synthetic tests.

No private data in public GitHub, no live broker action, no bot changes.
Computer Use / PC Agent requires separately explicit user authorization.
GitHub Actions may run synthetic-only tests and a deterministic state checker.
A scheduled CI run is NOT an autonomous researcher and cannot wake ChatGPT Work.

## Source-fix specification and concurrent evidence merges

Whenever a verified source-code weakness is relevant to G-001, maintain
`SOURCE_FIX_SPEC.md` with exact source member, confidence, limitations,
corrective design and offline synthetic acceptance tests. Never edit or
operate the original trading robot as part of Analytics research.

Before merging another research branch, compare all E- and M-IDs with
CURRENT main; preserve both independent evidence sets with unique IDs.
The checkpoint validator must reject duplicate evidence and milestone IDs.
Real observed data always take precedence over older speculative checkpoints,
and green CI is not evidence of the historical root cause.

## Evidence coverage units

Always distinguish (state,calendar-day) aggregate report rows from unique calendar dates. `error_events` includes WRN+ERR log messages; it is never the number of unique failing broker orders. Do not infer strategy performance from short overlapping historical windows or from unsynchronized broker statements. Preserve private financial aggregates only in private local project reports.
