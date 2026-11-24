# PLAN

1. Отдельный Python (stdlib) API-клиент и автономные тесты, без реальных ключей.
2. Самостоятельный GitHub Actions workflow с push + manual workflow_dispatch.
3. Проверка первого запуска в публичном Analytics без Secrets.
4. Хранение read-only токена Cloudflare и account ID в Actions Secrets Analytics.
5. Проверка настоящих GET settings и deployments; результат редактируется
   строго по белому списку.
6. Отдельное расширение до управляемого deploy только после проверки
   версии живых Worker, сохранения rollback и согласования прав.

## Post-G-001 active Serverspace stages (2026-11-23)
- DONE: authenticated fixed private Serverspace GET from Cloudflare named entrypoint, via Cron diagnostic Worker; original diagnostic schedule disabled after success.
- DONE: direct production OAuth Worker injection + private Service Binding using code-only and settings-only official Cloudflare API; all original 25 bindings inherited and verified.
- NEXT: registered ChatGPT MCP connector must discover `serverspace_list_servers` and invoke it with owner OAuth; check live allowlisted output. Current session tool catalogue is stale/does not expose it.
- FUTURE: explicitly scoped provider VPS control operations and independent Ubuntu command channel. Trading automation and power changes remain untouched.

## Active continuation update 2026-11-23 22:04 UTC
1. Read-only aggregate-only `summary_v1` result from the existing diagnostic KV after scheduled Cron propagation; record only totals and disable schedule after verified success. Do not mutate the production VPS.
2. Restore Linux WSS device connectivity through existing dedicated route: active admin export has been repaired, bindings and workers.dev are enabled, but `vps_status` still gives HTTP 503. Next diagnosis needs device session / Linux agent environment, not more Cloudflare export uploads.
3. Resolve OAuth MCP tool discovery; no direct ChatGPT `serverspace_list_servers` call confirmed though provider Service binding and code live.
4. Review and test staged draft MCP-proxi PR #20 privately, with control flags disabled and separate targeted owner authorization, before any power API deploy. Real Linux root shell is a distinct channel from Serverspace provider power endpoints.

## 2026-11-24 05:16 UTC — re-prioritized based on real SSH-equivalent root command success
**Proven**: owner OAuth `vps_status` and `vps_exec` can reach live Ubuntu 26.04 as `babit-admin` and `sudo root`. The goal of basic Linux shell access is achieved; **the reliability objective remains open** (579 agent WSS disconnects since 00:00Z against four connects by 05:11Z).
1. Build and review [private PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21) redacted phase/error telemetry without secrets; do not deploy uncompiled C# or restart trading.
2. Controlled and reversible administration-agent-only deployment, followed by bounded classification of real reconnect failures. Correct evidenced cause, not speculative Cloudflare worker fixes.
3. Refresh owner ChatGPT connector tool schema to expose existing server-side `serverspace_list_servers`, or an officially supported tool-discovery mechanism. No extra plugin/worker duplicates.
4. Keep separately staged [provider-power PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20) disabled; only a targeted owner-approved command may ever enable mutation. The actual Serverspace project has one powered-on VPS.

## 2026-11-24 05:24 UTC
- Existing t-invest_IIS **private plugin manifest** updated in place to v1.0.1 with the same App binding. Tool catalogue in the current session remained unchanged (18 tools, no serverspace_list_servers). Do not duplicate or repeatedly republish the plugin; prioritize actually supported re-discovery at a new session boundary.
- Linux root shell proven but WSS stability not achieved; next actionable fix requires compiling and deploying source-only categorized WSS logging in private [PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21). Separate provider-control [PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20) remains disabled and unshipped.

## 2026-11-24 11:30 UTC — agent update installed and authenticated VPS shell restored
- PR #21 exact single-file artifact installed by owner, SHA256 confirmed remotely. Real vps_status and vps_exec succeeded, sudo root confirmed, PID 69813. Eight initial HTTP409 followed by WSS connection; one observed session disconnect recovered in 2s. Long-term stability and cause of 409 not yet proven. No Cloudflare or trading changes.
- VPS direct public GitHub reachable, private repository access not verified; Git installed, dotnet unavailable. GitHub-first mandated in MCP-proxi AGENTS. Next delivery should use authorized private direct fetch/build or release rather than home PC SCP.
- Provider API PR #20 still staged, not deployed; separate full build and connector discovery work remains.

## 2026-11-24 11:50 UTC — VPS-local builds and real MCP protocol tests
- Existing production agent remains active, with recovered root shell; journal observed unchanged counters through 11:41 UTC after reconnect at 11:29:44. Long-run reliability and provider-side HTTP409 cause remain open.
- Found existing VPS-local .NET SDK 10.0.404/runtime 10.0.15; previous PATH-only dotnet check was incomplete. Actual inherited-pipe deadline bug reproduced in production read-only command and fixed in candidate [PR #23](https://github.com/IskanderAbdullin/MCP-proxi/pull/23). Native acceptance 12/12 including graceful TCP WebSocket shutdown; Linux x64 self-contained artifact published locally, SHA256 906bbc4a30ddd19cc5cf468ab74d01678ef2aa73fe2c5e17c48b0f64eaae46f9. Not deployed; separately authorize agent-only rollout via independent SSH.
- [PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20): verified Node 24.11.1 and pnpm 10.20.0 installed in isolated VPS home directory; exact derived dependency closure from original lock, real MCP SDK JSON-RPC tests 6/6, native Node tests 211/211 and targeted strict TS6 passed. No live provider request, full repository build or Wrangler dry-run yet. Mutation stays disabled.
- GitHub-first: both GitHub SSH endpoints reachable with pinned host keys. Dedicated read-only deploy key generated on VPS; owner must register public half in private repository Settings -> Deploy keys. No private key leaves VPS. Then fetch exact pinned commits and run full frozen build in bounded single-worker environment. Do not rerun private Actions.
- Existing connector schema refresh and real owner read-only Serverspace invocation remain pending. No duplicate plugin creation. No Cloudflare production deploy or provider mutation in this continuation.
- Immutable lab events saved on PR #23 (1e2a1057d013a43a1a1878aa1e769dbe432a4eec) and PR #20 (08d0063eb999087e0228dbfbce2af332a662a3dc). Next: owner read-only deploy key registration, pinned checkout/full build; separately approve new local agent candidate if desired.

## 2026-11-24 12:08 UTC — coordination with parallel PC Agent
The owner explicitly requests bidirectional coordination between PC Agent and VPS Agent. Both projects use private MCP-proxi; shared branch-independent coordination mailbox: https://github.com/IskanderAbdullin/MCP-proxi/issues/25. At each continuation read latest comments; before changing shared t-invest-mcp-proxy announce planned scope, verify fresh active baseline, preserve PC/VPS/broker/OAuth/Serverspace bindings, and avoid concurrent deployments. Record actual changes, tested commit/version, cross-agent effects and rollback. Independent Windows PC-Agent and Linux VPS-agent/bridge work may proceed in parallel. PC Agent's current active branch is not yet confirmed; requested its checkpoint in issue #25. Do not modify its active branch or local service. Existing production authorization gates remain unchanged.

## 2026-11-24 12:14 UTC — full build and real local service routing verified
- VPS Agent remains active (PID 69813); journal 11:19:29–12:13:30 UTC: 2 connect, 9 disconnect markers, 8 HTTP409; no new connect/disconnect markers after 11:29:44. About 44 minutes of observed unchanged WSS counters, not long-term stability proof. New PR #23 single-file candidate is local only, not deployed. Existing agent and trading unchanged.
- PR #20: original frozen lockfile installed 265 platform packages with lifecycle scripts disabled; complete package test script 356 passed; full TypeScript check after narrow entrypoint type fix; both official Wrangler 4.165.0 dry-runs exit 0. Exact 75-file relevant input projection (Git blob verification), not genuine complete clean checkout or release verifier execution. Real pinned workerd with actual named bridge entrypoints and caller helpers passed synthetic legacy/catalog reads and redaction, offline plan, public 404 and mutation-disabled 403. Source fix 35ca612eac4c9c8d7f4f966898377a734bf9e805; offline harness 675fd4fdc6501dde209e06c7cf7d11d5314e1c30; journal commits 7022ce5afbfbad8d8d1f06f26b0394e503ff8883 and 3e45ff137696730d8088587ae5eafaf14b95125d.
- Independent PR #24 implements atomic expiring one-shot approval via dedicated SQLite ledger. Native 219/219 plus real SDK 6/6; actual workerd two-process persistence test passes; full TypeScript and both official Wrangler dry-runs pass, with ledger enabled only in explicit CI test config and mutation flags false. Journal 9ff101e8af48a41ec2dcab7d0bb58f36780e043b. No live namespace or mutation. Do not make this future mutation path a prerequisite for read-only rollout.
- Critical next actions requiring owner interaction: register already-generated public read-only deploy key in private MCP-proxi; authorize exact read-only production rollout after shared caller coordination and live baseline/rollback validation; refresh existing ChatGPT connector and perform actual authenticated live provider read. Independently approve new Linux agent release only if wanted; use independent SSH for safe rollback. No production deployment or provider mutation in this continuation. Coordination mailbox issue #25; no parallel agent launched by this run.
- This run began 11:32:26 UTC, before this checkpoint 12:14 UTC; stop on actionable external prerequisites rather than fabricate nine hours. Continue after owner action; remaining live acceptance and operational goals are open.
