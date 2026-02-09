# Technical Architecture (AR/EN) — Wasla Store (Django)

**AR:** هذا الملف يشرح البنية التقنية للمشروع من منظور المطور: كيف قُسِّمت الموديولات، كيف يعمل الـ multi‑tenancy، وما هي نقاط التوسعة.  
**EN:** This document describes the technical architecture from a developer perspective: module boundaries, multi-tenancy, and extension points.

---

## 1) System overview | نظرة عامة

**AR:**
- Backend: Django + Django REST Framework.
- واجهة Web: Django templates (لوحة تحكم + صفحات أساسية).
- API: تحت المسار `api/` ويجمع URLs من عدة Apps.

**EN:**
- Backend: Django + Django REST Framework.
- Web UI: Django templates (dashboard + basic pages).
- API: under `api/` aggregating URLs from multiple apps.

Key entrypoints:
- Django project: `wasla_sore/`
- Apps: `apps/`
- Templates: `templates/`
- Deployment scripts: `deployment/`

---

## 2) Code organization (Apps) | تنظيم الكود (التطبيقات)

**AR:**
كل موديول (App) يمثل نطاق وظيفي مستقل (Bounded Context) مثل: `accounts`, `tenants`, `orders`, `payments`…  
بعض الموديولات تتبع أسلوب Clean Architecture داخلها:

- `domain/`: قواعد الأعمال + الأخطاء + السياسات (Policies) وواجهات الـ ports.
- `application/`: use cases (سيناريوهات) تربط بين domain و persistence/gateways.
- `infrastructure/`: adapters/gateways (SMTP, SMS providers, …) وتنفيذ الـ ports.
- `interfaces/`: طبقة الدخول (Django/DRF views/serializers/urls) + HTML views.

**EN:**
Each app is a bounded context (e.g., `accounts`, `tenants`, `orders`, `payments`).  
Some apps follow a Clean Architecture split:

- `domain/`: business rules, errors, policies, ports/contracts.
- `application/`: use cases orchestrating domain + persistence/gateways.
- `infrastructure/`: adapters (SMTP/SMS/etc) implementing ports.
- `interfaces/`: entrypoints (DRF + Django views/urls/templates).

Per-module documentation lives inside each module: `apps/<module>/README.md`.

---

## 3) Multi‑tenancy model | نموذج تعدد المتاجر

**AR:**
- `apps/tenants/models.py` يحتوي `Tenant` (المتجر/الـ tenant) وعضويات/إعدادات المتجر.
- ربط الدومينات الخاصة يتم عبر `StoreDomain` + تحقق DNS/HTTP + إصدار SSL.
- `apps/tenants/middleware.py::TenantMiddleware` يحدد `request.tenant` باستخدام:
  1) Headers (`X-Tenant`, `X-Tenant-Id`)
  2) Session (`store_id`)
  3) Custom domain (StoreDomain) أو legacy `Tenant.domain`
  4) Subdomain under `WASSLA_BASE_DOMAIN`
  5) (في DEBUG) querystring مثل `?store_id=1`
- قاعدة مهمة: أي بيانات تخص متجرًا يجب أن تكون معزولة (Tenant Isolation) عبر `tenant_id` أو `store_id`.

**EN:**
- `apps/tenants/models.py` defines `Tenant` (store/tenant) and store settings/memberships.
- Custom domains are mapped via `StoreDomain` with DNS/HTTP verification + SSL issuance.
- `apps/tenants/middleware.py::TenantMiddleware` resolves `request.tenant` using:
  1) Headers (`X-Tenant`, `X-Tenant-Id`)
  2) Session (`store_id`)
  3) Custom domain (StoreDomain) or legacy `Tenant.domain`
  4) Subdomain under `WASSLA_BASE_DOMAIN`
  5) (In DEBUG) querystring `?store_id=1`
- Rule: store-owned data must be tenant-isolated via `tenant_id` / `store_id`.

---

## 4) Authentication + Onboarding | الدخول + الإعداد الأولي

**AR:**
- `apps/accounts/` مسؤول عن التسجيل/تسجيل الدخول (كلمة مرور أو OTP) + متابعة خطوات onboarding.
- يوجد “state machine” لتحديد الخطوة التالية للتاجر بعد الدخول (`MerchantNextStep`).
- Middleware: `apps/accounts/middleware.py::OnboardingRedirectMiddleware` يمنع الدخول للوحة التحكم قبل إكمال الخطوات.

**EN:**
- `apps/accounts/` handles auth (password or OTP) and merchant onboarding steps.
- A post-auth state-machine computes the next required step (`MerchantNextStep`).
- Middleware `OnboardingRedirectMiddleware` protects the dashboard until onboarding completes.

---

## 5) Notifications / Emails / SMS | الإشعارات / البريد / الرسائل

**AR:**
- `apps/notifications/`: توجيه إرسال الإيميلات (بوابة SMTP حاليًا).
- `apps/emails/`: طبقة بريد أكثر مرونة (providers + logs + optional async via Celery).
- `apps/sms/`: بوابات SMS متعددة (مثل console و Taqnyat) مع إعدادات عامة + إعدادات لكل Tenant.

**EN:**
- `apps/notifications/`: routing for outbound email notifications (SMTP gateway currently).
- `apps/emails/`: richer email layer (providers + logs + optional Celery async).
- `apps/sms/`: multi-gateway SMS with global + per-tenant settings.

---

## 6) Deployment architecture | بنية النشر

**AR:**
ملفات `deployment/` توفر نشر على Ubuntu باستخدام:
- `gunicorn` عبر `systemd`
- `nginx` reverse proxy
- ملفات env في `/etc/<project>/`

**EN:**
`deployment/` scripts deploy on Ubuntu using:
- `gunicorn` + `systemd`
- `nginx` reverse proxy
- env files in `/etc/<project>/`

See: `Docs/STAGING_RUNBOOK.md` and `deployment/README.md`.
