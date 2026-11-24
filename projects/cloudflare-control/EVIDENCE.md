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

## 2026-11-23 — live private entrypoint deployment evidence
- User explicitly authorized editing/testing existing `babit-vps-bridge` Worker.
- First code-only Cloudflare update via public Analytics GH Actions 45254233185 reported `stage=patch,result=updated`, but **was not yet active**; later updated with explicit `exports` metadata via full script upload.
- Active earlier version inspection reported `private_serverspace_export=false`; the code-only patch lacked named export registration (run 45255330134).
- Full script + inherited bindings publisher was checked in as `projects/cloudflare-control/serverspace_rebuild.py` and workflow `.github/workflows/serverspace-full-deploy.yml` under commit `a744e6c61975d4f744c6cff05165a4356329320d`; Actions run `45255927652`, job `137977600334`, exit success.
- Its sanitized output: `{"stage":"full_upload","result":"accepted"}`; `{"stage":"activation","result":"live","serverspace_private_entrypoint":true,"vps_relay_preserved":true}`.
- The private `ServerspaceReadOnlyEntrypoint` uses fixed authenticated Serverspace RU GET, responds with allowlisted metadata (ID/name/state/power) and is available only via same-account private Service binding. Source API key value never read or logged. No real trade or VPS changes.
- All public workers.dev probes from GH runner were `HTTP 403`, including existing `babit-vps-bridge` and `t-invest-mcp-proxy`, source run `45254882866`, job `137973964681`. Ephemeral canary script(s) were deleted, not left enabled.
- **Unverified:** actual Serverspace network/API response, OAuth caller Service binding/MCP tool. Requires separate private caller wiring; do not claim fully end-to-end ready.

## 2026-11-23 UTC 21:29 — independent Serverspace provider + OAuth deployment evidence
- Provider list: run [45265270517](https://github.com/IskanderAbdullin/Analytics/actions/runs/45265270517), `cloudflare_private_call=serverspace_inventory_ok`, valid allowlisted schema, diagnostic Cron disabled.
- OAuth production preflight: run [45268781717](https://github.com/IskanderAbdullin/Analytics/actions/runs/45268781717): 25 existing bindings, PC/VPS true, no Serverspace tool/binding, 2 original modules.
- Dry-run syntax and target checks passed: [45269497666](https://github.com/IskanderAbdullin/Analytics/actions/runs/45269497666).
- Deploy attempt: [45269625921](https://github.com/IskanderAbdullin/Analytics/actions/runs/45269625921), two API mutation calls accepted; workflow error `MODULE_LAYOUT_UNEXPECTED` only in final verifier after source-map normalization.
- Independent live caller audit: [45269740240](https://github.com/IskanderAbdullin/Analytics/actions/runs/45269740240) confirmed active main JS has owner-only MCP tool, `SERVERSPACE_SERVICE` is a Service binding and `SERVERSPACE_ENABLED=true`, all original PC/VPS/OAuth/broker bindings present; 27 total. JS source map was dropped by Cloudflare during setting update.
- Post-deploy no-write idempotence check: [45269882505](https://github.com/IskanderAbdullin/Analytics/actions/runs/45269882505), success with patch_needed=false, binding_needed=false, 27 bindings.
- Owner OAuth call to existing `list_allowed_market_tools` via connected `t_invest_IIS` returned success. New `serverspace_list_servers` was not advertised among this session's callable connector tools; **no ChatGPT MCP end-to-end proof yet**.
- Code: `projects/cloudflare-control/oauth_rollout.py`, `oauth_rollout_request.json`, `caller_audit.py` and corresponding Actions workflows. Secrets and Cloudflare script content never committed.

## 2026-11-23 22:04 UTC — private entrypoint restoration, Cron collision isolation, provider control staging
- Before fix: [Cloudflare audit 45274001199](https://github.com/IskanderAbdullin/Analytics/actions/runs/45274001199) `vps_admin_entrypoint_live=false`, `serverspace_entrypoint_live=true`, `vps_relay_export_live=true`; [45274182466](https://github.com/IskanderAbdullin/Analytics/actions/runs/45274182466) source confirmed admin class/handler present.
- Offline preflight [45274414567](https://github.com/IskanderAbdullin/Analytics/actions/runs/45274414567) passed, code-only existing Worker source & 7 bindings preserved. Live export upload accepted in [45274491529](https://github.com/IskanderAbdullin/Analytics/actions/runs/45274491529), but exit 3 on unexpected auto-activation; [independent audit attempt 2 of 45274182466](https://github.com/IskanderAbdullin/Analytics/actions/runs/45274182466) confirmed admin entrypoint active with other exports and bindings. WSS `vps_status` still returned `VPS_AGENT_HTTP_503` (observed via connected MCP, not a public network log).
- Dedicated/legacy flags and credentials binding *names* verified in [45272780237](https://github.com/IskanderAbdullin/Analytics/actions/runs/45272780237) and [45272679520](https://github.com/IskanderAbdullin/Analytics/actions/runs/45272679520); workers.dev enabled [45275564611](https://github.com/IskanderAbdullin/Analytics/actions/runs/45275564611).
- Aggregate Cron staged in [45271842598](https://github.com/IskanderAbdullin/Analytics/actions/runs/45271842598), active scheduled version verified [45273266350](https://github.com/IskanderAbdullin/Analytics/actions/runs/45273266350), broad competing private-proof trigger fixed by `b86170849da41bac373e30165b89ac2498c09fe8`, rearm [45273731893](https://github.com/IskanderAbdullin/Analytics/actions/runs/45273731893) success. KV summary remained pending at last read [45273824455 attempt 2](https://github.com/IskanderAbdullin/Analytics/actions/runs/45273824455) around 22:00:47 UTC.
- Pure planning contract 6/6 tests [45272478653](https://github.com/IskanderAbdullin/Analytics/actions/runs/45272478653). Private dependent draft [PR #20](https://github.com/IskanderAbdullin/MCP-proxi/pull/20) not deployed and its TS mocks not executed. No VPS power or shell call conducted.

## 2026-11-23 UTC 22:06 — confirmed single live VPS, aggregate Cron stopped
- After isolating the old conflicting proof workflow and allowing the existing Cloudflare Cron to propagate, the **third attempt** of read-only summary workflow [45273824455](https://github.com/IskanderAbdullin/Analytics/actions/runs/45273824455), job `138048671720`, completed SUCCESS at 22:05 UTC.
- Sanitized result: `{"count":1,"outcome":"summary_ok","power_unknown":0,"powered_off":0,"powered_on":1}`. **Exactly one VPS exists in this Serverspace RU project and it is powered on** at measurement time. No server IDs, network addresses, names, passwords or API response were logged.
- Same run then reported `cron_disabled_after_success`; the existing `babit-ss-diagnostic-1123` Cron was stopped. No new Worker, VPS operation, power action, shell or broker change.
- This meets the sole-target prerequisite for the *nonexecuting* power planner; it does **not** authorize submitting power operations. The approved scope is to build owner-only API capability, not reboot a running trading VPS just to validate access.
- NEXT_ACTION: prefer a read-only remote console/session inventory or Linux WSS signal; refresh the owner MCP plugin catalogue for `serverspace_list_servers`. Only later promote separately feature-locked power-control code with explicit owner approval for any execution.

## 2026-11-24 05:16 UTC — ROOT ADMINISTRATIVE SHELL NOW DEMONSTRATED (intermittent)
- Direct **authenticated** `t_invest_IIS.vps_status` at 2026-11-24T05:11:00Z confirmed live `BabitVpsAgent` version 0.1.0 on Ubuntu 26.04 LTS under `babit-admin`. This is a genuine device reply, unlike previous Cloudflare-only source checks.
- A harmless real `t_invest_IIS.vps_exec` at 2026-11-24T05:11:06Z returned exit code **0**: `id -un => babit-admin`, `sudo -n id -un => root`, `systemctl is-active babit-vps-agent => active`. **This proves actual Linux command execution and noninteractive root access via existing OAuth → private Worker → Linux WSS agent, without Computer Use or additional tools.** No trading or server power changes.
- The channel is **NOT reliable**: an adjacent previous exec got `VPS_AGENT_HTTP_503`; follow-up read-only commands succeeded and verified the agent never restarted (`systemd NRestarts=0`, process started 2026-11-23T16:43Z). Sanitized journal counts since UTC midnight, observed at 05:11Z: `VPS_AGENT_DISCONNECTED=579` vs `VPS_AGENT_WSS_CONNECTED=4`. Dedicated pinned endpoint confirmed, three unauthenticated HTTPS requests returned HTTP400 (expected without WebSocket upgrade). Latest successful WS connection at 05:10:27Z. These logs establish material recurrent WSS instability but **do not determine the precise cause**.
- A proposed diagnostic handshake that would access the Linux device bearer secret was rejected by the OpenAI tool safety layer before execution; **no retry or workaround was attempted**. Do not inspect or disclose any credential.
- Independent read-only Cloudflare probe via the existing diagnostic Worker [45276914259](https://github.com/IskanderAbdullin/Analytics/actions/runs/45276914259) returned expected HTTP401 with intentionally unsigned admin request, then stopped Cron. This confirms live private route requires HMAC; no signed command was sent by that probe.
- Existing upstream OAuth market list still works; ChatGPT's `t_invest_IIS` connected tool catalog still does NOT advertise new `serverspace_list_servers` even though its server-side source is live; a connector/tool schema refresh remains separate.
- A **source-only** safe telemetry patch for Ubuntu admin agent was staged in private `IskanderAbdullin/MCP-proxi` branch `chatgpt/vps-wss-telemetry-20261124`, [draft PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21), latest commit `57d5cf18565d15e6ed8c39be080a3f99bb39810a`: classify WSS disconnects by phase and fixed error categories, never log exception messages/URI/credentials. C# build is **NOT RUN**, live agent not updated/restarted, no trading changes.
- **NEXT_ACTION**: verify compile of PR #21 using .NET 10 SDK and exact GitHub source in a trusted environment, then controlled admin-only deployment with rollback; observe sanitized WSS categories to identify and fix actual reconnect root cause. Do NOT claim stable remote shell until repeated responses over time are proven. Keep Serverspace power-control PR #20 staged/locked (not deployed); sole live provider server confirmed powered on; no power action justified by WSS instability.
