# Funnel telemetry — Oracle deployment runbook

This service is intentionally separate from the WebAI Bridge commercial runtime.

Public route:

```text
https://webai.140-238-62-74.sslip.io/funnel/*
```

Local service:

```text
127.0.0.1:8766
```

State:

```text
/var/lib/x-ads-funnel/funnel.sqlite3
```

Secrets/config:

```text
/etc/x-ads-funnel/funnel.env
```

## Safety boundary

- Do not place `FUNNEL_AUDIT_TOKEN` or `FUNNEL_HASH_SECRET` in GitHub Pages, JavaScript, URLs, Issues, or logs.
- Browser event ingestion is public and intentionally contains no secret.
- Summary/exclusion endpoints require the audit bearer token.
- The raw browser device ID is not stored in event records; only an HMAC digest is stored.
- Do not log request bodies.
- Keep Uvicorn access logging disabled for this service.
- Stripe, not the browser purchase-complete page, remains purchase authority.

## Install

Adapt paths/user to the existing Oracle host rather than overwriting the WebAI commercial deployment.

```bash
sudo mkdir -p /opt/x-ads-bridge /etc/x-ads-funnel /var/lib/x-ads-funnel
sudo python3 -m venv /opt/x-ads-funnel-venv
sudo /opt/x-ads-funnel-venv/bin/python -m pip install -r /opt/x-ads-bridge/requirements-funnel.txt
```

Place the current repository files under `/opt/x-ads-bridge` using the same controlled deployment method used for the host. Do not put GitHub credentials in the unit or environment file.

Create two independent random values on the host:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Use one only for `FUNNEL_HASH_SECRET` and the other only for `FUNNEL_AUDIT_TOKEN` in `/etc/x-ads-funnel/funnel.env`.

Set restrictive ownership/permissions using the actual unprivileged service account:

```bash
sudo chown -R webai-bridge:webai-bridge /var/lib/x-ads-funnel
sudo chown root:webai-bridge /etc/x-ads-funnel/funnel.env
sudo chmod 640 /etc/x-ads-funnel/funnel.env
sudo chmod 700 /var/lib/x-ads-funnel
```

If the existing host uses a different unprivileged service user, substitute it consistently.

Install the unit from `deploy/x-ads-funnel.service.example`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now x-ads-funnel.service
sudo systemctl status x-ads-funnel.service --no-pager
curl -fsS http://127.0.0.1:8766/health
```

## Caddy

Inside the existing fixed-domain site block, add the contents of `deploy/Caddyfile.funnel.example` **before** the existing catch-all WebAI reverse proxy.

Validate before reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Then verify the public health route:

```bash
curl -fsS https://webai.140-238-62-74.sslip.io/funnel/health
```

## GitHub bridge settings

In `nobutakayamauchi/x-ads-bridge` repository secrets, configure:

```text
FUNNEL_API_BASE_URL=https://webai.140-238-62-74.sslip.io/funnel
FUNNEL_AUDIT_TOKEN=<same audit token held by Oracle service>
```

Do not add the hash secret to GitHub Actions. It is needed only by the Oracle telemetry service.

## Owner smartphone exclusion

On the operator smartphone, open the sales catalog helper:

```text
https://nobutakayamauchi.github.io/sales-catalog/products/webai-bridge/operator-device.html
```

Copy the anonymous device ID. Submit it through the owner-only `[funnel]` GitHub bridge with:

```json
{
  "action": "funnel_exclude_device",
  "device_id": "<copied anonymous device id>",
  "label": "owner-iphone"
}
```

This keeps the operator's events in total/raw counts but removes them from audited counts used for ad decisions.

## Acceptance

1. Public `/funnel/health` returns `status=ok`.
2. Open the WebAI sales LP from the operator phone.
3. Query `funnel_summary` for the current window: total LP count increases.
4. Add the operator device exclusion.
5. Query the same window again: raw total remains, audited LP count drops by the operator device.
6. Tap consultation and purchase CTAs and verify the matching diagnostic events.
7. Do not treat `purchase_complete_client` as revenue. Join actual completed paid Stripe evidence separately.
