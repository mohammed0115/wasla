# SMS Module (Multi-gateway)

This project includes a tenant-aware SMS module designed for SOLID, clean integration with multiple SMS gateways.

## Structure
- Domain rules/contracts: `apps/sms/domain/`
- Use cases: `apps/sms/application/use_cases/`
- Gateways + routing: `apps/sms/infrastructure/`
- Django models (settings + logs): `apps/sms/models.py`

## Configuration (global)
In `wasla_sore/settings.py`:
- `SMS_DEFAULT_PROVIDER` (default: `console`)
- `SMS_DEFAULT_SENDER_NAME`
- `SMS_DEFAULT_COUNTRY_CODE` (optional)
- `SMS_PROVIDERS` (per-provider config)

### Taqnyat (example)
Set environment variables:
- `SMS_DEFAULT_PROVIDER=taqnyat`
- `SMS_TAQNYAT_BEARER_TOKEN=...`
- `SMS_TAQNYAT_SENDER_NAME=Wasla`

Optional:
- `SMS_TAQNYAT_BASE_URL=https://api.taqnyat.sa`
- `SMS_TAQNYAT_TIMEOUT_SECONDS=10`
- `SMS_TAQNYAT_INCLUDE_QUERY_TOKEN=1` (only if your setup requires `bearerTokens` query param)

## Tenant-level settings
Use Django admin:
- Model: `TenantSmsSettings`
- Fields:
  - `provider` (`console` / `taqnyat`)
  - `is_enabled`
  - `sender_name`
  - `config` (JSON)

Tenant config overrides the global `SMS_PROVIDERS[provider]`.

## Sending SMS (code)
Use the use case:
- `apps/sms/application/use_cases/send_sms.py`

Supports scheduled sending via `scheduled_at`.

## Sending SMS (management command)
Command:
`python manage.py send_sms --to +9665xxxxxxx --body "..." --sender "Wasla"`

Schedule:
`python manage.py send_sms --to +9665xxxxxxx --body "..." --scheduled 2026-02-06T14:26`

Tenant-aware (optional):
`python manage.py send_sms --tenant default --to +9665xxxxxxx --body "..."`

## Adding a new gateway
1) Implement a gateway class in `apps/sms/infrastructure/gateways/` matching the `SmsGateway` protocol.
2) Add it to `apps/sms/infrastructure/router.py` in `_build_gateway()`.
3) Add its config under `SMS_PROVIDERS` in `wasla_sore/settings.py`.

