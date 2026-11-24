# BACKLOG — 2026-11-23 UTC 20:07

A-001 DONE — public Analytics GitHub Actions Cloudflare bridge.
A-002 DONE — offline tests and standard Analytics CI verified.
A-003 DONE — owner configured Analytics GitHub Cloudflare Secrets.
A-004 DONE — authenticated read-only Cloudflare REST inventory.
A-005 DONE — direct user-authorized update of babit-vps-bridge with named
             ServerspaceReadOnlyEntrypoint. Active 100% deployment verified
             GH Actions run 45255927652, existing VPS relay preserved.
A-006 NEXT — wire a private Cloudflare Service binding from authorized OAuth
             caller and perform one real sanitized Serverspace list request.
A-007 OPTIONAL — diagnose workers.dev 403 from GH runners if needed;
                 unrelated to actual private entrypoint registration.
A-008 DEFERRED — explicit owner-scoped Serverspace power API actions
                 after proof that read-only private request succeeds.

## 2026-11-23 UTC 21:29 update
A-006 SERVER-SIDE DONE — existing OAuth `t-invest-mcp-proxy` now has private `SERVERSPACE_SERVICE` to dedicated entrypoint, `SERVERSPACE_ENABLED=true` and owner-only `serverspace_list_servers` code. Verified by independent live API audit [45269740240](https://github.com/IskanderAbdullin/Analytics/actions/runs/45269740240). End-to-end tool call still pending.
A-009 NEXT — refresh/discover authenticated `t_invest_IIS` connector's tools, call new `serverspace_list_servers`; validate safe inventory and errors.
A-010 NEXT AFTER A-009 — decide separately permitted Serverspace provider control actions (power/config) and Linux shell path; do not touch live VPS or trades without explicit scoped approval.
A-011 LOW — source map was dropped by Cloudflare settings update; restore only if it impacts debugging. Existing main script verified present.

## 2026-11-23 22:04 UTC priorities
A-012 DONE — restore missing `VpsAdminEntrypoint` named export, independently verified live in 45274182466 attempt 2; `vps_status` still 503 because WSS/agent remains disconnected or unverified.
A-013 DONE — isolate competing GitHub workflow Cron triggers so summary probe is not cleared by old successful diagnostic; existing Worker reused.
A-014 PENDING — collect actual sole-provider server count/on-off aggregate after Cloudflare Cron propagation, no IDs in public logs. Last `summary_v1` was pending around 22:00 UTC.
A-015 DONE (source stage, not deployed) — s2ctl-backed no-execution provider power contract: 6/6 tests in public Analytics; private draft PR #20 with a separate locked entrypoint, no real POST.
A-016 NEXT — check Linux WSS device session after private export fix; determine endpoint/credential mismatch or offline agent without reboot/trade changes.
A-017 NEXT — refresh ChatGPT `t_invest_IIS` OAuth plugin discovery for `serverspace_list_servers`.

A-014 DONE — exact sanitized Serverspace aggregate from [45273824455 attempt 3](https://github.com/IskanderAbdullin/Analytics/actions/runs/45273824455): one VPS, powered on; Cron disabled after success. Continue A-016 Linux WSS and A-017 MCP catalogue; no actual power action.

A-016 PARTIAL SUCCESS 2026-11-24 — root Linux shell command executed through existing owner MCP, exit 0, sudo root. Still highly intermittent: systemd service active/NRestarts=0; observed 579 disconnects vs 4 WSS connects since midnight. Separate private [PR #21](https://github.com/IskanderAbdullin/MCP-proxi/pull/21) stages safe categories, not compiled or deployed. NEXT: build, review, controlled admin-only deployment, diagnose.
A-018 DONE — unsigned private HMAC rejection probe [45276914259](https://github.com/IskanderAbdullin/Analytics/actions/runs/45276914259) returned expected HTTP401, Cron stopped; no credential consumed.
A-017 STILL BLOCKED — ChatGPT MCP tool discovery does not include `serverspace_list_servers`; connected market upstream names do not list local owner-only tool, so do not confuse the two.

A-019 DONE / NEGATIVE RESULT — Cloudflare Observability aggregate-only API [45332379431](https://github.com/IskanderAbdullin/Analytics/actions/runs/45332379431) accepted fixed query but returned zero status-code groups over six hours. No evidence of HTTP 409 distribution. Avoid repeated queries absent a reason to expect telemetry collection has changed.

## 2026-11-24 05:24 UTC — in-place t-invest_IIS plugin release refreshed; same MCP discovery still stale
- Inspected the **owned existing private personal plugin** `plugin_asdk_app_6afc16e32f888191915ccdcd2d04b061`. Its App ID binding `asdk_app_6afc16e32f888191915ccdcd2d04b061` was retained exactly, and its files were only `.app.json` plus `.codex-plugin/plugin.json`.
- Used the official Plugin Creator `update_plugin` on this **same plugin** (no new plugin or reconnection) with only its unchanged presentation and manifest semantic version `1.0.0 → 1.0.1`. Confirmed returned `status=updated`, current release `pluginrel_6b051f1c2e6481918c430c495eac7c4a`, same private USER scope. Plugin link: https://chatgpt.com/plugins/plugin_asdk_app_6afc16e32f888191915ccdcd2d04b061 . OAuth Worker endpoint, auth, Cloudflare and Linux were not modified by the release update.
- **Post-update** this *same chat session* still advertises 18 `mcp__t_invest_IIS__*` methods, **no `serverspace_list_servers`**. Dynamic ChatGPT tool catalog/connection likely pinned for the current conversation. Avoid a second identical release publish; next action is re-discovery of existing app tools in a fresh supported ChatGPT session or user-approved connector refresh if offered, then real owner OAuth read-only call.
