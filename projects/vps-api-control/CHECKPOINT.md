# VPS API control — checkpoint 2026-11-23 UTC

## Goal

Establish full owner-controlled VPS provider API operations via existing
Cloudflare infrastructure, independent of the flaky Ubuntu WSS agent, and
restore reliable Linux OS command execution via a separately authenticated
channel. This repo is public: do not commit tokens, Cloudflare account IDs,
server IDs, Worker sources fetched from Cloudflare, hostnames or raw replies.

## Completed and independently evidenced

1. Original public Analytics GitHub Actions Cloudflare API bridge works:
   https://github.com/IskanderAbdullin/Analytics/actions/runs/45251925905
2. Dedicated existing `babit-vps-bridge` has declared and deployed private
   `ServerspaceReadOnlyEntrypoint` with `SERVERSPACE_API_KEY` Secret:
   https://github.com/IskanderAbdullin/Analytics/actions/runs/45255927652
3. **Live production change succeeded**: `SERVERSPACE_API_ENABLED=true`
   via full version upload and 100% activation, inheriting existing
   secrets/DO/bindings/export metadata and preserving VPS relay:
   https://github.com/IskanderAbdullin/Analytics/actions/runs/45263676970
4. A separate diagnostic Worker `babit-ss-diagnostic-1123`, KV namespace
   and private same-account Service binding to the dedicated entrypoint
   exist. Binding ownership verified. The Cloudflare Cron Triggers API
   accepted a one-minute schedule. Active Worker deployment, 2 bindings
   and 1 Cron schedule independently verified:
   https://github.com/IskanderAbdullin/Analytics/actions/runs/45264909723
5. `projects/vps-api-control/canary.py` now uses top-level array Cron
   JSON as specified by Cloudflare API, treats KV HTTP404/10009 as
   pending, retains results across workflows, and disables Cron only
   after genuine successful private inventory.

## NOT VERIFIED — never claim otherwise

- Real authenticated `GET https://api.serverspace.ru/api/v1/servers`
  through private Cloudflare Service binding has **not yet returned a
  confirmed outcome** to GitHub. Earlier runs returned
  `pending_cron_propagation` and `pending_no_result`, consistent with
  delayed Cron propagation, not proof of provider API success/failure.
- The existing OAuth `t-invest-mcp-proxy` is **not yet connected** to
  the Serverspace private Service binding; private MCP-proxi PR #18
  prepares the read-only caller but is still draft:
  https://github.com/IskanderAbdullin/MCP-proxi/pull/18
- `mcp__t_invest_IIS__vps_status` returned one genuine Ubuntu Agent
  status; subsequent status and shell execution returned HTTP503/504.
  Cloud provider control-plane API does not itself provide Ubuntu root
  shell or establish a working SSH session.
- Provider power/create/delete/configure APIs are supported by
  Serverspace but have **not been integrated or exercised**. Do not
  power-cycle a VPS just to test remote access.

## Next work, in order

1. **Do not clear stored KV result or replace the diagnostic Worker**.
   Use `projects/vps-api-control/read_outcome.py` through
   `.github/workflows/vps-api-read-result.yml` to query the existing
   result; use CI run's sanitized `outcome`.
   Existing Cron schedule can take up to ~15 minutes to propagate.
2. If `serverspace_inventory_ok`, stop diagnostic Cron and add the
   owner-scoped caller with strict private Service binding. If other
   outcome, fix exactly that provider/Service issue without leaking data.
3. Implement **specific documented** Serverspace power/VM operations in
   dedicated Worker and authenticated caller, one exact API endpoint at
   a time, with clear target constraints, feedback and error handling.
   Keep Linux OS command access separate. Avoid modifying OAuth
   production Worker until all existing live secret, KV, DO, route and
   provider dependencies are audited.
4. Restore existing Linux agent WSS/SSH admin reliability, preserving
   running trading service and source-pinned deployment state.
5. Record actual test evidence (not just source assertions), official
   OsEngine Lab v2 event and checkpoint. GitHub Actions for this public
   Analytics project can run without Computer Use.

## Workflow evidence

- Source updates and diagnostic workflow in this folder.
- `vps-private-serverspace-proof` status on commit
  `dc5f2ff62fee35ff8f4c088afa08a7e9bdac19f6`:
  https://github.com/IskanderAbdullin/Analytics/actions/runs/45264198197
  — Cron setup succeeded; run exited 5 on pending propagation.
- Independent read result:
  https://github.com/IskanderAbdullin/Analytics/actions/runs/45264731073
  — `pending_no_result` at 2026-11-23 20:58 UTC.
- Live Cloudflare diagnostic metadata:
  https://github.com/IskanderAbdullin/Analytics/actions/runs/45264909723
  — `active=true`, `schedule_count=1`, `binding_count=2`.

The ChatGPT Automations attempt to schedule a 20-minute recheck was
rejected by plan limit (5 active tasks); no automation was created.
Do not claim that this chat continues asynchronously.
