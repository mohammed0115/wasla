
1) الهدف النهائي للنظام (Wasla)

تاجر ينشئ متجر مستقل (Tenant)

يرفع منتجاته وصوره

العميل يتصفح/يبحث/يضيف للسلة/يدفع

النظام يرسل طلب + يدير الشحن

دعم خصائص “وصلة”: بحث ذكي (بالصورة/النص)، توصيات، عروض، تقارير

2) اختيار الـ Multi-tenancy

Single DB + Tenant column (الأفضل للـ MVP والتوسع)

كل جدول فيه tenant_id

middleware يحدد request.tenant

أي Query لازم يفلتر بالـ tenant

3) هيكل المشروع (Python/Django)


wassla/
  config/
    settings/
    urls.py
  apps/
    core/            # shared: errors, idempotency, utils
    tenants/         # tenant resolution + tenant model
    accounts/        # users, roles, auth, permissions

    catalog/         # products, categories, tags, media
    search/          # search API + (later AI indexing)
    carts/           # cart + pricing
    orders/          # checkout + payments + order lifecycle
    payments/        # gateway adapters + webhooks
    shipping/        # carriers + labels + tracking
    promotions/      # coupons + discounts rules
    analytics/       # events, reports, dashboards

    dashboard/       # merchant UI (Django templates)
    storefront/      # customer UI (Django templates)
4) Clean Architecture (داخل كل App)
apps/catalog/
  domain/
    entities.py          # (اختياري) قواعد domain
    policies.py          # validation + rules
  application/
    use_cases/
      create_product.py
      update_product.py
      attach_image.py
    ports/
      storage.py         # interface
  infrastructure/
    repositories/
      product_repo.py
    storage/
      local.py / s3.py   # adapters
  interfaces/
    api/                 # DRF views/serializers
    web/                 # Django templates views
  models.py              # ORM

مهم:

الـ models للـ persistence فقط

القواعد في domain/policies.py

orchestration في use_cases/

الـ views “thin”

5) Domain Modules (Wasla core)
A) Tenants

Business rules

slug unique

is_active لازم true للوصول

tenant يحدد:

domain/subdomain

العملة واللغة

خطة الاشتراك

B) Catalog

Entities

Category (اختياري للمنتج)

Tag

Product (SKU إلزامي)

ProductImage (primary image)

Rules

SKU unique per tenant

product belongs to tenant

image types allowed + max size

tags/categories لازم من نفس tenant

C) Search

MVP

text search + filters
Later

Visual similarity + embeddings

Rules

scope = tenant فقط

ranking configurable per tenant

D) Cart

Rules

cart per user per tenant

qty > 0

pricing service يعيد الحساب دائمًا

cart locked أثناء checkout

E) Orders

States

CREATED

PAYMENT_PENDING

CONFIRMED

CANCELLED

SHIPPED

DELIVERED

FAILED

Rules

idempotency-key منع تكرار الطلب

تحويل cart → order atomic

payment adapters قابلة للاستبدال

F) Payments

Gateway adapters

HyperPay / PayTabs / Moyasar

Webhooks للتحقق

ledger لتسجيل عمليات الدفع

G) Subscriptions (للتجار)

Plan: Basic/Pro/Enterprise

Limits:

products_count

orders_monthly

staff_users

6) تدفق البيانات (Data flow)
مثال: Checkout

Client hits /store/checkout

View calls PlaceOrderUseCase

Use case:

validate cart

lock cart

create order

charge payment via PaymentGatewayPort

finalize order

returns order_id + status

7) Mapping “Magento concepts” إلى Django

Magento Module → Django App

Magento Observer → Django Signals / Domain Events (مفضل)

Magento Model → Django ORM model + Repository

Magento Service Contracts → Use-cases / Services

Magento Controller → DRF View / Django Template View

8) Production readiness checklist

Tenant isolation tests

DB indexes: (tenant_id, sku), (tenant_id, created_at)

rate limiting endpoints

audit logs (orders/payments)

background jobs (Celery) لاحقًا


























You are a senior software architect and Django tech lead.

Context:
I’m building “Wassla” (multi-tenant store builder) with Django 5 + DRF + Django Templates (Bootstrap RTL),
Clean Architecture + SOLID, SQLite dev → PostgreSQL prod.
Tenant context is resolved via subdomain + X-Tenant header (request.tenant).

Goal:
Implement a HYBRID authentication flow that combines:
(1) Salla-style OTP-first login/registration
AND
(2) Wassla SRS onboarding flow (country → business → store creation),
without breaking Clean Architecture.

You MUST deliver both flows together and make them work seamlessly.

------------------------------------------------------------
WHAT “1 + 2” MEANS (BUSINESS FLOW)
------------------------------------------------------------

FLOW A — OTP-first (Salla-style):
1) User enters phone OR email on a single screen:
   - If user exists: send OTP and continue
   - If user is new: send OTP and continue
2) Verify OTP:
   - If user exists: log in and continue to next step
   - If user new: create account (minimal fields) then log in
3) After login, continue to Onboarding (Flow B)

FLOW B — Wassla SRS onboarding:
4) Country selection (required)
5) Business type selection (required; 1..5 categories)
6) Store creation (required; store name + unique slug; reserved slugs blocked)
7) After store created → dashboard

Constraints:
- Auth pages must NOT use dashboard layout (no sidebar/nav).
- OTP pages must use auth_base.html layout.
- Dashboard pages use dashboard_base.html.

------------------------------------------------------------
ARCHITECTURE RULES (STRICT)
------------------------------------------------------------

1) No business logic in views/templates.
2) All rules in domain policies.
3) All orchestration in application use-cases.
4) DIP: use-cases depend on ports (interfaces), not concrete providers.
5) OCP: adding a new OTP provider (email/SMS) must not change use-cases.
6) Tenant isolation: onboarding is platform-level (pre-tenant) until store is created.
7) Provide both Web (Templates) and API (DRF) endpoints using the SAME use-cases.

------------------------------------------------------------
REQUIRED FEATURES
------------------------------------------------------------

A) OTP SYSTEM (Provider-agnostic)
- Support OTP delivery by:
  - Email
  - SMS (Phase 2 placeholder)
- OTP validity: 5 minutes
- Max attempts: 5
- Rate limit: 3 OTP per 10 minutes per identifier
- Idempotency: do not send multiple OTPs if a valid one exists recently
- Store hashed OTP code (never store plain code)

B) USER CREATION / LOGIN
- If identifier not found → create user on successful OTP verify
- User fields:
  - email optional (if phone-only)
  - phone optional (if email-only)
  - name optional (Phase 2)
- Session login for web, JWT for API

C) ONBOARDING STATE MACHINE
- OnboardingProfile model per user:
  steps: REGISTERED → COUNTRY → BUSINESS → STORE → DONE
- Prevent skipping steps (e.g., can't create store before choosing country & business)
- Redirect behavior:
  - If authenticated but onboarding not DONE → always redirect to current step

D) STORE CREATION (MVP)
- One store per user (owner)
- Slug rules:
  - lowercase a-z 0-9 hyphen
  - no leading/trailing hyphen
  - unique globally
  - reserved: admin, api, www, dashboard, store
- Default store settings: currency=SAR, language=ar

E) EMAIL SETTINGS SECURITY (GLOBAL SUPERADMIN ONLY)
- Email gateway credentials MUST NOT be in .env
- Store them in DB as GlobalEmailSettings (singleton)
- Only superuser can manage them in Django Admin
- Password encrypted at rest
- OTP Email sender uses Email Gateway which reads config from DB

------------------------------------------------------------
DELIVERABLES (YOU MUST PROVIDE)
------------------------------------------------------------

1) Architecture impact summary
2) Django app structure (folders for domain/application/infrastructure/interfaces)
3) Data models:
   - OnboardingProfile
   - OTPChallenge (hashed code, expiry, attempts, identifier, channel)
   - GlobalEmailSettings (singleton, encrypted)
   - EmailLog (optional but preferred)
4) Domain policies (plain validation functions):
   - validate_identifier (email/phone)
   - validate_otp_rules (rate limit, attempts)
   - validate_onboarding_step_order
   - validate_store_slug
5) Ports (interfaces):
   - OTPProviderPort (send_otp)
   - EmailGatewayPort (send_email)
6) Application use-cases:
   - RequestOtpUseCase
   - VerifyOtpUseCase
   - EnsureOnboardingStepUseCase
   - SelectCountryUseCase
   - SelectBusinessUseCase
   - CreateStoreFromOnboardingUseCase
7) Infrastructure implementations:
   - Email OTP provider using GlobalEmailSettings from DB (no env)
   - SMS provider stub (placeholder)
   - OTP storage (DB)
   - Email gateway (SMTP/SendGrid stubs)
8) Interfaces:
   Web URLs (Templates):
   - /auth/start (enter email/phone)
   - /auth/verify (enter otp)
   - /onboarding/country
   - /onboarding/business
   - /onboarding/store
   API URLs (DRF):
   - POST /api/auth/otp/request
   - POST /api/auth/otp/verify
   - POST /api/onboarding/country
   - POST /api/onboarding/business
   - POST /api/onboarding/store
   - GET  /api/onboarding/status
9) Templates (Bootstrap RTL):
   - layouts/auth_base.html
   - auth/start.html
   - auth/verify.html
   - onboarding/country.html
   - onboarding/business.html
   - onboarding/store.html
   Must be mobile-friendly and must NOT show dashboard sidebar.
10) Middleware/Redirect logic:
   - If user authenticated and onboarding step != DONE → force to that step
   - But allow /auth/verify during pending verification
11) Security checklist + edge cases:
   - replay OTP, brute force, rate limits, idempotency
   - invalid identifiers
   - user tries to skip steps
   - tenant inactive
12) Test checklist:
   - OTP request/verify
   - step enforcement
   - store creation rules
   - superadmin-only email settings

Output format:
- Provide code in production-grade blocks per file path
- Include minimal explanations
- Warn if any part breaks Clean Architecture

Start implementing the combined "1 + 2" flow now.
























































You are a senior cloud architect and Django platform engineer.

Context:
I’m building “Wassla” — a multi-tenant e-commerce platform (store builder).
Each merchant can connect a custom domain to their store (e.g. mystore.com → store.wassla.sa).

Stack:
- Django 5 + DRF
- Nginx + Gunicorn
- Clean Architecture + SOLID
- PostgreSQL (prod)
- Multi-tenancy via subdomain + domain mapping

Goal:
Implement production-grade Custom Domain Mapping for stores.

--------------------------------------------------
BUSINESS FLOW
--------------------------------------------------

1) Merchant enters domain in dashboard:
   Example: mystore.com

2) System generates DNS instructions:
   - A record → server IP
   OR
   - CNAME → stores.wassla.sa

3) Merchant confirms DNS

4) System verifies ownership:
   - DNS lookup
   - HTTP challenge

5) When verified:
   - Domain is activated
   - SSL certificate is issued automatically
   - Domain routes to correct tenant

6) Merchant can:
   - View status
   - Retry verification
   - Disable domain

--------------------------------------------------
ARCHITECTURE RULES
--------------------------------------------------

- No DNS logic in views
- No certbot calls in views
- All orchestration in use-cases
- Use background jobs for verification + SSL
- Domain resolution must be centralized
- Must support millions of domains

--------------------------------------------------
DATA MODEL
--------------------------------------------------

StoreDomain

Fields:
- id
- tenant_id (FK)
- domain (unique)
- status: PENDING | VERIFYING | ACTIVE | FAILED | DISABLED
- verification_token
- verified_at
- ssl_cert_path
- ssl_key_path
- last_check_at
- created_at

--------------------------------------------------
DOMAIN POLICIES
--------------------------------------------------

- validate_domain_format(domain)
- prevent_reserved_domains(domain)
- ensure_domain_not_taken(domain)
- ensure_one_active_domain_per_store (MVP)
- prevent_platform_domain_usage

--------------------------------------------------
USE CASES (APPLICATION)
--------------------------------------------------

1) AddCustomDomainUseCase
2) GetDomainSetupInstructionsUseCase
3) VerifyDomainOwnershipUseCase
4) ActivateDomainUseCase
5) DisableDomainUseCase
6) RefreshSSLCertificateUseCase

Each use-case must be transactional and idempotent.

--------------------------------------------------
INFRASTRUCTURE SERVICES
--------------------------------------------------

A) DNS Resolver Adapter
   - dig / dnspython
   - cached lookups

B) SSL Manager Adapter
   - certbot wrapper
   - supports HTTP-01 + DNS-01

C) Reverse Proxy Adapter
   - Nginx config generator
   - reload safely

D) Background Worker
   - Celery / RQ / Huey

--------------------------------------------------
TENANT RESOLUTION
--------------------------------------------------

Incoming request:
- If Host matches custom domain → resolve tenant
- Else if *.wassla.sa → subdomain tenant
- Else → landing page

Must be implemented as middleware.

--------------------------------------------------
NGINX DESIGN
--------------------------------------------------

Wildcard + dynamic include:

/etc/nginx/sites-enabled/wassla.conf
/etc/nginx/wassla/domains/*.conf

Each domain has separate file.

--------------------------------------------------
SECURITY
--------------------------------------------------

- Block domain takeover
- Prevent wildcard abuse
- Rate-limit verification
- Validate ownership before SSL
- Sanitize Nginx templates
- Atomic reload

--------------------------------------------------
DELIVERABLES
--------------------------------------------------

1) App structure
2) Models + migrations
3) Domain policies
4) Use-cases
5) DNS + SSL adapters
6) Middleware for tenant resolution
7) Celery tasks
8) Nginx template generator
9) Dashboard UI flow
10) Deployment notes
11) Failure recovery plan
12) Test checklist

Rules:
- Never expose cert files to tenants
- Never trust DNS blindly
- Never reload Nginx per request
- Fail safe

Start implementing now.
