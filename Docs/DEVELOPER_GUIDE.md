# Developer Guide (AR/EN) — Wasla Store (Django)

> **AR:** هذا الملف مخصص للمطورين لتشغيل المشروع محليًا، فهم أهم نقاط الإعداد، وتتبّع الأخطاء بسرعة.  
> **EN:** This file is a developer-oriented guide for running the project locally, understanding configuration, and troubleshooting.

---

## 1) Quick Links | روابط سريعة

- **Modules docs (per app):** `apps/<module>/README.md`
- **Technical architecture:** `Docs/TECHNICAL_ARCHITECTURE.md`
- **Staging runbook (deployment & ops):** `Docs/STAGING_RUNBOOK.md`
- **Deployment scripts:** `deployment/README.md`

---

## 2) Prerequisites | المتطلبات

**AR:**
- Python `3.12+`
- (اختياري) Virtualenv / venv
- SQLite للاختبارات السريعة (المشروع افتراضيًا يستخدم `db.sqlite3`)

**EN:**
- Python `3.12+`
- (Optional) virtual environment
- SQLite for quick local runs (default DB is `db.sqlite3`)

---

## 3) Local Setup | تشغيل محلي

**AR (Windows / PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "Django>=5.1,<5.3" djangorestframework djangorestframework-simplejwt Pillow requests
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**EN (Windows / PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install "Django>=5.1,<5.3" djangorestframework djangorestframework-simplejwt Pillow requests
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

> **Note / ملاحظة:** إن وُجد `requirements.txt` مستقبلاً، استخدمه بدل تثبيت الحزم يدويًا.

---

## 4) Environment Variables | متغيرات البيئة

**AR:**
- `DJANGO_DEBUG` = `1` أو `0`
- `DJANGO_SECRET_KEY` (مهم في الإنتاج)
- `DJANGO_LANGUAGE_CODE` = `ar` أو `en`
- `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_ROOT` (للإنتاج/السيرفر)
- البريد (SMTP): `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
- SMS: راجع `Docs/SMS_Module.md`

**EN:**
- `DJANGO_DEBUG` = `1` or `0`
- `DJANGO_SECRET_KEY` (required in production)
- `DJANGO_LANGUAGE_CODE` = `ar` or `en`
- `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_ROOT` (production/server)
- Email (SMTP): `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
- SMS: see `Docs/SMS_Module.md`

---

## 5) Multi‑Tenancy (How to select a tenant) | تعدد المتاجر (اختيار المتجر)

**AR:**
المشروع يحدد `request.tenant` عبر `TenantMiddleware`. في التطوير يمكنك:
- إرسال هيدر: `X-Tenant: <tenant_id أو slug>`  
- أو (في وضع `DEBUG=1`) تمرير `?store_id=<id>` في الـ URL

**EN:**
The project resolves `request.tenant` via `TenantMiddleware`. In development you can:
- Send header: `X-Tenant: <tenant_id or slug>`
- Or (when `DEBUG=1`) use `?store_id=<id>` in the URL

---

## 6) Tests | الاختبارات

**AR:**
```powershell
python manage.py test
```

**EN:**
```powershell
python manage.py test
```

---

## 7) Useful Commands | أوامر مفيدة

**AR/EN:**
- Seed sample data (optional): `python manage.py seed_sample --tenant default --create-superuser`
- Validate key flows: `python manage.py validate_flows --tenant store1`
- Send SMS (dev): `python manage.py send_sms --tenant default --to +9665xxxxxxx --body "Hello"`

---

## 8) Development conventions | قواعد التطوير

**AR:**
- حاول أن تبقي الـ views “thin” وتضع orchestration داخل use cases.
- قواعد الأعمال والتحقق (validation/policies) مكانها الطبيعي: `domain/` أو `application/policies`.
- أي منطق يتعامل مع “Tenant isolation” يجب أن يفلتر بـ `tenant_id` / `store_id`.

**EN:**
- Keep views thin; orchestrate flows in use-cases/services.
- Business rules and validation belong in `domain/` or `application/policies`.
- Anything that must be tenant-isolated should filter by `tenant_id` / `store_id`.

