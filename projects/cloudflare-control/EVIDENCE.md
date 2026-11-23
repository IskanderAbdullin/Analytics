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

## Main deployment and repeat trigger
- PR #101 merged: https://github.com/IskanderAbdullin/Analytics/pull/101
- main repository workflow is enabled and branch-filtered, read-only.
- Main repeat trigger: commit 637a016429788d20fb0b71c74aac18ee9e9560c3,
  Action run https://github.com/IskanderAbdullin/Analytics/actions/runs/45240223355
  returned offline success, Cloudflare missing-secrets failure.
- Direct authenticated Cloudflare API still not called; all cloud resources
  untouched; public logs reveal no token or raw Cloudflare responses.

## Authenticated production Cloudflare GET proof — 2026-11-23T19:43:52Z
- Source commit: `5e176e37404cf4c2fdf437a3d5010606be2d44e1`.
- GitHub run: `45251925905`, job `137963545927` success.
- Public-safe JSON:
  `{"connected":true,"mode":"read_only","schema_version":1,"workers":[{"binding_present":true,"deployed":true,"expected_binding":"SERVERSPACE_API_KEY","settings_ok":true,"worker":"babit-vps-bridge"},{"binding_present":true,"deployed":true,"expected_binding":"VPS_AGENT_ENABLED","settings_ok":true,"worker":"t-invest-mcp-proxy"}]}`.
- Scripts made two fixed GET requests per Worker, one for settings and one for
  deployments. No writing to Cloudflare or VPS; no broker orders.
- `cloudflare-control-offline-tests` and `cloudflare-readonly-audit`
  both `success` with Actions URL in GitHub commit statuses.
- `SERVERSPACE_API_KEY` binding presence does not prove the Serverspace API
  itself works or that the staged PR #18 code is deployed.
