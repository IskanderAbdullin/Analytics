# EVIDENCE — Cloudflare Control

2026-11-23 UTC: Independent public GitHub Actions workflow created on
branch chatgpt/cloudflare-control-20261123 in IskanderAbdullin/Analytics.

## Read-only workflow execution
- Commit bfa5b0387b0b44231f43c69e1d58818a6d7f6556 created workflow
  .github/workflows/cloudflare-api-bridge.yml and Python module/tests.
- First execution proved Actions starts in public repo; initial unit fixture
  failed due to Python unittest mock not accepting timeout keyword.
- Commit 0f67f10978bbf7bad599dcf88c6a6e60f4101084 fixed the fixture:
  five offline tests passed; read-only API not yet connected.
- Ruff CI import-order findings in standard Analytics CI were corrected;
  full CI on commit cb772821f847f87dfa924988beabf99cf466a07f:
  run 45239733881 completed success.
- Read-only workflow run 45239723887 on same commit:
  offline tests 5/5 PASS, status published; Cloudflare audit
  secrets_unavailable (both Analytics Secrets empty), with no HTTP request
  to Cloudflare. Separate status linked to exact run URL.
- No GitHub Secrets were printed; code only accepts two fixed Worker names,
  GET /settings or GET /deployments, never Cloudflare mutations.
- No VPS, broker, trading or PC-Agent interactions occurred in this project.

## Limits
- Real Cloudflare authentication, verified binding metadata and deployment
  state still untested because Analytics-repository Secrets are not present.
- GitHub Actions token only posts safe commit status; logs remain public.
- Full static/CI testing is evidence of code validity, not live API access.
