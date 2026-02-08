# SMS Module (Multi-gateway) | موديول الرسائل SMS (بوابات متعددة)

**AR:** يحتوي المشروع على موديول SMS داعم لتعدد المتاجر (Tenant-aware) ومصمم بطريقة قابلة للتوسعة لإضافة أكثر من مزود (Gateway) بسهولة.  
**EN:** This project includes a tenant-aware SMS module designed for clean extensibility and multi-gateway integration.

## Structure | الهيكل

- Domain rules/contracts: `apps/sms/domain/`
- Use cases: `apps/sms/application/use_cases/`
- Gateways + routing: `apps/sms/infrastructure/`
- Django models (settings + logs): `apps/sms/models.py`

## Global configuration | الإعدادات العامة

In `wasla_sore/settings.py`:
- `SMS_DEFAULT_PROVIDER` (default: `console`) | المزود الافتراضي
- `SMS_DEFAULT_SENDER_NAME` | اسم المرسل الافتراضي
- `SMS_DEFAULT_COUNTRY_CODE` (optional) | كود الدولة (اختياري)
- `SMS_PROVIDERS` | إعدادات كل مزود

### Taqnyat (example) | مثال: تقنيات (Taqnyat)

**Env vars | متغيرات البيئة:**
- `SMS_DEFAULT_PROVIDER=taqnyat`
- `SMS_TAQNYAT_BEARER_TOKEN=...`
- `SMS_TAQNYAT_SENDER_NAME=Wasla`

**Optional | اختياري:**
- `SMS_TAQNYAT_BASE_URL=https://api.taqnyat.sa`
- `SMS_TAQNYAT_TIMEOUT_SECONDS=10`
- `SMS_TAQNYAT_INCLUDE_QUERY_TOKEN=1` (only if required) | فقط إذا كان مطلوبًا

## Tenant-level settings | إعدادات على مستوى المتجر

Use Django admin | عبر لوحة Django admin:
- Model: `TenantSmsSettings`
- Fields:
  - `provider` (`console` / `taqnyat`)
  - `is_enabled`
  - `sender_name`
  - `config` (JSON)

**AR:** إعدادات الـ tenant تقوم بعمل override على الإعدادات العامة داخل `SMS_PROVIDERS[provider]`.  
**EN:** Tenant config overrides the global `SMS_PROVIDERS[provider]`.

## Sending SMS (code) | إرسال SMS (في الكود)

Use the use case | استخدم الـ use case:
- `apps/sms/application/use_cases/send_sms.py`

Supports scheduling via `scheduled_at` | يدعم الجدولة عبر `scheduled_at`.

## Sending SMS (management command) | إرسال SMS (عبر أمر إداري)

**Command | الأمر:**
`python manage.py send_sms --to +9665xxxxxxx --body "..." --sender "Wasla"`

**Schedule | جدولة:**
`python manage.py send_sms --to +9665xxxxxxx --body "..." --scheduled 2026-02-06T14:26`

**Tenant-aware (optional) | مع تحديد المتجر (اختياري):**
`python manage.py send_sms --tenant default --to +9665xxxxxxx --body "..."`

## Adding a new gateway | إضافة مزود جديد

1) Implement a gateway in `apps/sms/infrastructure/gateways/` matching the `SmsGateway` protocol.  
2) Register it in `apps/sms/infrastructure/router.py` in `_build_gateway()`.  
3) Add provider config under `SMS_PROVIDERS` in `wasla_sore/settings.py`.
