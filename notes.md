
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