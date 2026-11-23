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
