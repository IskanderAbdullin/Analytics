# CHECKPOINT — 2026-11-23 (verified)
Goal: G-001 — independent public GitHub Actions bridge to Cloudflare API.

## Verified
- Existing public IskanderAbdullin/Analytics GitHub runner runs Actions on push
  to chatgpt/cloudflare-control-20261123 without any PC-Agent or VPS access.
- Source Python 3.12 unittest: 5/5 PASS in public Actions,
  commit cb772821f847f87dfa924988beabf99cf466a07f.
- Local exact Git blob tests: 5/5 PASS for cloudflare.py and test_cloudflare.py.
- Full Analytics CI, including Ruff and pytest: SUCCESS on commit
  cb772821f847f87dfa924988beabf99cf466a07f
  (CI run 45239733881).
- GitHub status contexts cloudflare-control-offline-tests=success and
  cloudflare-readonly-audit=failure point to Actions run 45239723887;
  GitHub API tool can follow those run IDs to inspect job logs.
- Logs confirm both CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are
  absent in the *public Analytics repository* environment. The read-only
  Cloudflare step reports secrets_unavailable. NO real Cloudflare API request
  was made, and no Cloudflare resource was modified.
- Repo owns its separate workflow and request.json nonce; repeatable
  owner-controlled push trigger confirmed.

## Blocker
The owner's pre-existing Secrets in private MCP-proxi are repository-scoped.
GitHub Actions cannot read their values from public Analytics.

## Next action
Owner adds a separate, read-only CLOUDFLARE_API_TOKEN and
CLOUDFLARE_ACCOUNT_ID to Analytics / Settings / Secrets and variables /
Actions. Then increment projects/cloudflare-control/request.json nonce and
trigger workflow. Inspect read-only settings/deployments results from GitHub
commit statuses and sanitized logs; never upload private Worker scripts.

Cloudflare deployment/rollback, VPS power, OS shell and broker actions
remain out of scope.


## D177 — actual read-only existing PC tunnel status (2026-11-25T07:49:08Z)
Analytics Secrets authorized for existing bridge; Worker inventory and new fixed named tunnel GET executed in public run 45571035288 / job 139057446085. Exact source a69a445302bfdfee0831515bb10af8925c908c07. Offline unittest 15/15 PASS (0.441 s), live tunnel result at 07:48:49Z: ok, inactive, edge_connected=false. No token endpoint or resource mutation. Do not treat Worker deployment as tunnel connectivity. No private resource IDs or raw responses in logs. Next: owner-side connector/network recovery; do not create duplicate tunnel based on this result. Existing shared Worker remains unchanged. Official Lab CLI not available in chat runtime; event prepared using existing schema.


## D179/D180 — actual isolated Worker TCP22 diagnostic (2026-11-25T08:24:29.737Z)
D179 run 45573469012 attempt 2 job 139067749836: temporary Worker creation and deletion confirmed; HTTP invocation returned 403 before TCP test. D180 source 633b5c9887f65e52a7dc9d2fe10a9495cd9f9f24, run 45575699963 job 139072978827: Python and JavaScript syntax checks passed; one Queue message published at 08:22:36.919Z; actual Worker KV result at 08:23:34.704Z was timeout (8s TCP deadline). All temporary resources (consumer, Worker, queue, KV) deletion confirmed. No public HTTP route used, no Access change, no SSH authentication or Windows modification. No target address or credential in logs. Do not rerun without a new network fact or change. The outcome establishes Cloudflare runtime execution and API resource permissions, not TCP reachability or precise network cause. Source log: https://github.com/IskanderAbdullin/Analytics/actions/runs/45575699963/job/139072978827.


## D183/D184 (2026-11-25T10:46:58.325Z) — connected tunnel, private origin probes
Owner reports cloudflared exclusion from VPN and restart. Live tunnel metadata confirmed connection present/degraded (45581820322 attempt 2). Actual fixed unsigned HTTP /v1/status over existing VPC service result network_error, run 45597758054/job 139148251519, source 33ad716. Actual fixed loopback TCP22 over exact existing tunnel VPC Network binding result connection_failed, run 45597915788/job 139148800308, source 6354beb. Both syntax checks passed, all eight temporary resources cleaned (four per test). No authentication, response bodies, public HTTP or remote commands; no shared Worker or route changes. Exact connector protocol and local listeners remain unknown. Do not rerun without new evidence.


## D186 — private TCP path verified (2026-11-25T11:01:39.755Z)
Owner-provided evidence: local TCP22 listener and established QUIC, TCP8765 absent. Improved fixed-target test uses documented connect promise, checks socket shape and emits sanitized error classes. 8 mock tests and syntax checks passed. Actual run 45600344241/job 139157308232: tcp_open, source cloudflare_vpc_tunnel, port22; cleanup 4/4. Source fabf2ecf30727ab567f208fafb85863c19f5f9f7. No SSH bytes, authentication, commands or persistent endpoint. Exact reason D184 failed is not established. No shared resource or Windows changes. No further identical test absent new evidence. See https://github.com/IskanderAbdullin/Analytics/actions/runs/45600344241/job/139157308232 .


## D190 first runtime fixture (2026-11-25T11:26:44.958Z)
Actual Wrangler 4.50.0 dry-run bundle failed with unresolved optional cpufeatures.node, no runtime test or deploy. Analytics source 86da9a30f1b1a87cb8a5bae2417247a3751e4977, run 45604473969/job 139171624976. Upstream reports same optional native addon error (#1226), plus ssh2 module-load dynamic WASM incompatibility (#1494). Next local-only fixture uses current 4.168.0 reported by Wrangler, current compatibility date and alias for optional native CPU detection only. No crypto change, no real target or credentials.
