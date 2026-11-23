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
