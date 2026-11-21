# Babid Cloud analysis: repository-scoped agent rules

This is an analytical-only project in the **Analytics** GitHub repository.

- You may read source code from the original Babid Cloud application to learn
  data contracts, but **never change any other repository**.
- Do not commit trading source code, real accounts, trade logs, credentials,
  snapshots, broker APIs, or genuine market recordings into this public project.
- Use only synthetic fixtures in GitHub Actions, which run in Analytics itself.
- Do not attempt to connect to a broker or control a user's Windows desktop.
- Analysis scripts read a user-supplied **copy** and emit local reports only.
- A source mismatch, fill anomaly or quote-feasibility score is evidence for
  investigation, not permission to change live trading parameters.
- Document every completed research/development step as an OsEngine Lab v2
  JSON event under the root `reports/osengine-lab/events/` of Analytics.
- Run both OS CI jobs before representing tests as successful.
