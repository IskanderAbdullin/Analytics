# VPS API control plane — independent private canary

Goal: prove real Serverspace RU API access via the existing Cloudflare
`babit-vps-bridge/ServerspaceReadOnlyEntrypoint`, even when BabitVpsAgent
WSS is disconnected.

The public GitHub Actions runner uses only the already configured
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` Secrets. It never
prints their values or reads the Serverspace API key. The dedicated
`babit-vps-bridge` Worker and the OAuth `t-invest-mcp-proxy` Worker
are inspected but **never overwritten** by this canary.

`canary.py` creates an independent `babit-ss-diagnostic-1123` Worker
with **no functional public HTTP route** and a separate KV namespace. Its
same-account Service binding calls only the existing named private
entrypoint and reduces the response to an allowlisted outcome code.
No VPS names, IDs, credentials, server locations, provider API responses,
tokens, Worker source or cloud account identifiers enter public CI logs.

The Worker starts a once-per-minute Cron Trigger and writes a single,
expiring sanitized outcome to KV. The Actions job polls it and disables
Cron after receipt. Cron propagation can take up to 15 minutes, so a
pending result is not proof of failure. Existing diagnostic resources are
never overwritten by reruns. This canary neither executes shell commands
nor performs provider power mutations; it proves the prerequisite
private Cloudflare-to-Serverspace API hop.

For follow-up work: connect the existing private OAuth caller Service
binding and expose owner-scoped inventory; then separately add reviewed
provider power/VM management operations. OS shell access must use the
independent authenticated VPS relay or another privileged Linux channel;
provider cloud API permissions alone do not imply SSH/root access.

Do not turn the public Analytics workflow into a generic request-to-API
or shell executor. Production credentials remain GitHub Secrets.
