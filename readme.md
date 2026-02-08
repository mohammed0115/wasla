﻿# Waslah (Wasla Store) — Django Multi-Store E‑commerce Platform

هذا المستودع يحتوي مشروع Django هدفه بناء منصة تجارة إلكترونية متعددة المتاجر (Multi‑Store) شبيهة بـ **Salla**، مع تصميم معياري قابل للتوسع وتحويل مواصفات (Magento Open Source) إلى منصة Django نظيفة وقابلة للصيانة.

مصادر المتطلبات الأساسية موجودة في مجلد `Docs/` وتشمل:
- وثيقة SRS لمنصة Waslah: `Docs/SRS Document for Waslah.docx`
- قواعد الأعمال الموحّدة (Platform‑Independent): `Docs/Unified_Business_Rules_SRS_Ready.pdf`
- مخططات ER/Architecture/Use‑Cases/Sequence: ملفات PDF داخل `Docs/`
- سيناريوهات صفحات لوحة التحكم: `Docs/01_dashboard.txt` … `Docs/08_settings.txt`

توثيق المطور (Developer docs):
- دليل التشغيل المحلي: `Docs/DEVELOPER_GUIDE.md`
- البنية التقنية: `Docs/TECHNICAL_ARCHITECTURE.md`
- دليل السيرفر التجريبي + خطوات النشر: `Docs/STAGING_RUNBOOK.md`
- سكربتات النشر (Ubuntu + Gunicorn + Nginx): `deployment/README.md`

---

## 1) الرؤية والنطاق (Scope)

حسب SRS:
- تمكّن المنصة التاجر من **إنشاء وإدارة متجره**، وإدارة **المنتجات** و**الطلبات** و**الدفع** و**الشحن** و**العملاء**.
- العميل يستطيع تصفح عدة متاجر والشراء عبر واجهة موحّدة.
- الدعم المستهدف: **Web + Mobile**.

قيود ومتطلبات عامة:
- الالتزام بأنظمة التجارة الإلكترونية السعودية.
- دعم **العربية (RTL)** والإنجليزية.
- تكامل مع بوابات دفع محلية.
- هدف توفرية: **99.9% uptime**.

---

## 1.1) الهدف النهائي للنظام (Wasla) — ملخص سريع

الهدف النهائي (كما في الرؤية التشغيلية):
- تاجر ينشئ متجر مستقل (Tenant) داخل المنصة.
- يرفع منتجاته وصوره.
- العميل يتصفح/يبحث/يضيف للسلة/يدفع.
- النظام ينشئ الطلب ويدير دورة حياة الطلب + الشحن.
- دعم خصائص “وصلة” لاحقاً: بحث ذكي (بالصورة/النص)، توصيات، عروض، تقارير.

---

## 1.2) اختيار الـ Multi‑tenancy (قرار MVP)

الأفضل كبداية (MVP) ثم توسّع:
- **Single DB + Tenant column** (هنا نستخدم `store_id` كـ tenant id).
- Middleware يحدد `request.tenant` / `store_id`.
- أي Query لازم يفلتر بالـ tenant (Tenant isolation).

ملاحظة عن التنفيذ الحالي في هذا المستودع:
- يوجد `apps/tenants` + `TenantMiddleware` يضبط `request.tenant`.
- تم تطبيق `store_id` في جداول أساسية مثل: Catalog/Customers/Orders (مع فلترة صفحات الـ dashboard بالـ store_id).

---

## 2) الأدوار (Actors / Roles)

من وثائق الـSRS وملفات Use‑Cases:
- **Store Owner**: إدارة المتجر بالكامل (منتجات/طلبات/اشتراك/إعدادات/إضافات).
- **Manager / Staff**: تشغيل يومي حسب الصلاحيات (إدارة منتجات/طلبات…).
- **Admin**: إدارة المنصة على مستوى النظام (اعتماد التجار، الإشراف، التحليلات…).
- **Customer (Registered/Guest)**: التصفح والشراء والتقييم.
- **Payment Gateway** و **Shipping Provider**: أنظمة خارجية لمعالجة الدفع وتتبّع الشحن.

---

## 3) المتطلبات الوظيفية الأساسية (Waslah SRS)

حسب `Docs/SRS Document for Waslah.docx`:

### 3.1 Authentication & User Management
- التسجيل عبر البريد/الجوال + OTP.
- إدارة الأدوار والصلاحيات (RBAC).
- استعادة كلمة المرور + 2FA.

### 3.2 Merchant Store Management
- معالج إنشاء متجر (Wizard).
- دعم نطاق مخصص (Custom Domain).
- تخصيص الثيم والهوية (Theme/Branding).
- حالة المتجر: Active / Paused.
- إعدادات SEO لكل متجر.

### 3.3 Product Management
- CRUD للمنتجات + Variants.
- تتبع المخزون + SKU.
- استيراد/تصدير CSV.
- دعم منتجات رقمية ومادية.

### 3.4 Order Management
- إنشاء الطلب وتتبع حالته.
- حالات الطلب: Pending / Paid / Processing / Shipped / Delivered / Cancelled.
- Partial refunds + ملاحظات داخلية (Order Notes).

### 3.5 Payment System
- تعدد بوابات الدفع.
- Split payments (عمولة المنصة).
- دعم COD.
- إصدار فواتير تلقائي + إدارة الاسترجاع (Refunds).

### 3.6 Shipping & Fulfillment
- مزودين شحن متعددين.
- أسعار شحن لحظية (Real‑time rates).
- روابط تتبع + قواعد شحن حسب المنطقة.
- Fulfillment يدوي عند الحاجة.

### 3.7 Customer Experience
- تصفح المتاجر والمنتجات + Search/Filters.
- Cart & Checkout + سجل الطلبات.
- Wishlist + Reviews/Ratings.

### 3.8 Admin Panel
- اعتماد التجار (Merchant approval).
- إدارة العمولات (Commission management).
- Analytics على مستوى المنصة.
- إيقاف متجر (Store suspension) + إدارة النزاعات (Disputes) + Content moderation.

### 3.9 External Interfaces (مختصر)
- UI: Responsive + دعم RTL/LTR + WCAG AA + صفحات أساسية < 2s.
- API: REST/GraphQL + Webhooks (Orders/Payments/Shipping) + OAuth2.
- Integrations: بوابات دفع + شركات شحن + SMS/Email + Analytics.

---

## 4) المجالات (Domains) وقواعد الأعمال الأساسية

### 3.1 Product & Catalog
- المنتج كيان قابل للبيع وله **SKU فريد**.
- المنتج يجب أن ينتمي إلى **تصنيف واحد على الأقل**.
- حالات المنتج: مفعّل/معطّل/مخفي.

### 3.2 Customer
- العميل إمّا مسجّل أو زائر (Guest).
- العميل المسجّل يملك ملف دائم وسجل طلبات.
- مجموعات العملاء تؤثر على التسعير والعروض (Customer Groups).

### 3.3 Cart / Checkout
- العربة (Cart) تعبر عن نية شراء وليست معاملة قانونية.
- أسعار العربة مؤقتة وتُعاد حسابها.
- العربة تتحول إلى طلب عند تأكيد الدفع/الشراء.

### 3.4 Orders (Sales)
- الطلب سجل بيع قانوني **غير قابل للتعديل** (immutable record).
- دعم جزئي للفواتير/الشحنات/المرتجعات (Partial invoices/shipments/refunds).
- دورة حالات الطلب (State Machine) مذكورة في `Docs/03_orders.txt`:
  - Created → Paid → Processing → Shipped → Delivered → Completed
  - لا يُسمح بانتقالات غير صحيحة.

### 3.5 Payments
- الطلب يصبح “مدفوع” فقط بعد تأكيد الدفع.
- عملية الدفع يجب أن تكون **Idempotent** (منع تكرار الخصم).
- دعم تعدد بوابات الدفع + الدفع عند الاستلام (COD) + الاسترجاع (Refunds).

### 3.6 Shipping / Fulfillment
- إنشاء الشحنة فقط للطلبات المؤكدة/المدفوعة.
- دعم تتبع الشحنة ورابط التتبع ورقم التتبع.
- دعم مزودين متعددين + أسعار شحن لحظية + قواعد حسب المنطقة.

### 3.7 Reviews & Ratings
- تقييمات العملاء تعزّز الثقة وقد تتطلب مراجعة/Moderation.
- دورة مراجعة: Pending → Approve/Reject (`Docs/06_reviews.txt`).

### 3.8 Promotions / Marketing
- الخصومات تُطبق وفق شروط.
- لا يجوز أن ينتج خصم “سعر سلبي”.

### 3.9 Notifications
- الإشعارات مبنية على الأحداث (Event‑Driven).
- منع الرسائل المكررة (No duplicate messages).

### 3.10 Settings / Wallet / Packages (Subscriptions)
- لكل متجر إعدادات معزولة (Store Isolation).
- المحفظة نظام **دفتر أستاذ** (Ledger‑Based) وتحويلات Credit/Debit.
- تمييز Available vs Pending balance (مذكور كسيناريو: `Docs/05_wallet.txt`).
- الاشتراكات وخطط المزايا (Plans & Features) تتحكم في تفعيل خصائص مثل App Store.

### 3.11 Appearance & App Store (Plugins)
- الثيم يؤثر على العرض فقط ولا يغير منطق الأعمال.
- الإضافات يجب أن تكون معزولة وتحتاج صلاحيات (Permission‑Based) وتُقفل حسب الخطة (`Docs/07_app_store.txt`).

---

## 5) سيناريوهات الواجهة (Dashboard / Pages Scenarios)

ملفات TXT داخل `Docs/` تلخّص صفحات لوحة التحكم:
- Dashboard (`Docs/01_dashboard.txt`): أرقام مجمعة (Revenue/Orders/Wallet/Shipments) بدون تعديل بيانات خام.
- Products (`Docs/02_products.txt`): إضافة/تعديل منتجات، السعر/المخزون/الحالة، حالة تلقائية حسب المخزون.
- Orders (`Docs/03_orders.txt`): دورة حياة الطلب (State Machine) وصلاحيات التشغيل.
- Shipping (`Docs/04_shipping.txt`): تعيين شركة الشحن + تتبع الحالات + أرقام التتبع.
- Wallet (`Docs/05_wallet.txt`): Credits من الطلبات المكتملة، Debits للسحب/الرسوم، Owner فقط.
- Reviews (`Docs/06_reviews.txt`): مراجعة تقييمات Pending ثم Approve/Reject.
- App Store (`Docs/07_app_store.txt`): تصفح الإضافات وتثبيتها وتفعيلها، مقيدة بالخطة، Owner فقط.
- Settings (`Docs/08_settings.txt`): ملف المتجر، المستخدمون والصلاحيات، الاشتراك والفوترة، Owner فقط.

---

## 6) Use Cases & Flows (مختصر)

من وثائق Use‑Cases/Diagrams:
- UC‑01 Manage Products (Owner)
- UC‑02 Browse Products (Customer)
- UC‑03 Place Order (Customer Registered/Guest)
- UC‑04 Process Payment (Payment Gateway)
- UC‑05 Ship Order (Owner / Shipping Provider)
- UC‑06 Submit Review (Customer)
- UC‑07 Send Notification (System)
- UC‑08 Install Plugin (Owner)

تسلسلات (Sequence Diagrams) في `Docs/SRS_Sequence_Diagrams.pdf`:
- Order Placement: Cart → Checkout → Pricing → Payment → Gateway → Mark Paid → Notify
- Payment Failure: إبقاء الطلب Pending + إشعار فشل
- Shipping: Create shipment → Carrier → Tracking number → Notify

---

## 7) المعمارية (Architecture) والنشر (Deployment)

### 6.1 طبقات النظام (Logical Architecture)
من `Docs/Architecture_Deployment_UML.pdf` و `Docs/SRS_Items_1_to_4.pdf`:
- Presentation Layer: Web / Mobile
- API Layer: Django REST (و/أو GraphQL حسب SRS)
- Domain Layer: Catalog / Customers / Orders / Payments / Shipping …
- Application Services: Pricing / Promotions / Notifications …
- Infrastructure: Database + External APIs + Messaging

### 6.2 نشر مبدئي (Deployment)
- Client (Browser/App) → Load Balancer → Django App Servers → Database
- تكاملات خارجية: Payment, Shipping (وMessaging)

### 6.3 ملاحظات توسّع (من SRS)
- Multi‑Tenant: “store_id everywhere” لعزل بيانات المتاجر.
- قابلية “Microservice‑Ready” + CDN + Horizontal scaling.
- قاعدة بيانات هجينة (Relational + NoSQL) حسب الوثيقة.

---

## 8) متطلبات غير وظيفية (Non‑Functional)

حسب SRS:
- Performance: 10,000+ مستخدم متزامن، تحميل صفحات < 2s، API متوسط < 500ms.
- Security: تشفير أثناء النقل والتخزين، PCI‑DSS، RBAC، Activity Logs.
- Reliability: 99.9% uptime، نسخ احتياطي آلي، خطة تعافي من الكوارث.
- Localization: عربي/إنجليزي + Multi‑Currency.

---

## 9) ملخص قاعدة البيانات (ER)

من مخططات ER في `Docs/ER_*.pdf` (مختصر):
- Catalog: `Product`, `Category`, `Inventory`
- Customers: `Customer`, `Address` (مذكور ضمن الـSRS)
- Orders: `Order`, `OrderItem`
- Payments: `Payment`
- Shipping: `Shipment`
- Reviews: `Review`
- Wallet: `Wallet`, `WalletTransaction`
- Subscriptions: `SubscriptionPlan`, `StoreSubscription`
- Plugins: `Plugin`, `InstalledPlugin`

---

## 10) كيف يرتبط هذا المستودع بالمواصفات

المستودع الحالي هو بداية تنفيذ Django مع تقسيم “apps” حسب المجالات الأساسية المذكورة في الوثائق.
المراحل التالية عادةً تشمل:
- بناء Cart/Checkout + Pricing + Promotions + Notifications.
- تطبيق RBAC فعلي (Owner/Manager/Staff) وربط Authentication/OTP/2FA.
- تطبيق State Machine للطلبات والتحقق من الانتقالات.
- جعل الدفع Idempotent وربط بوابات دفع حقيقية + Webhooks.
- تكامل شركات شحن حقيقية + تتبع.
- تطبيق Wallet Available/Pending + تسويات.
- بناء واجهات API كاملة + توثيق (OpenAPI/Swagger) + اختبارات.

---

## 11) هيكل المشروع المقترح (Roadmap)

> هذا هيكل تنظيمي مقترح للنسخة “الكاملة” مع فصل Dashboard (واجهة التاجر) عن Storefront (واجهة العميل)، وهو قابل للتطبيق تدريجياً.

```
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
```

---

## 12) Clean Architecture داخل كل App (Roadmap)

مثال على هيكلة داخل `apps/catalog/`:

```
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
  models.py              # ORM (persistence)
```

مبادئ مهمة:
- `models.py` للـ persistence فقط.
- قواعد الأعمال في `domain/policies.py`.
- orchestration في `application/use_cases/`.
- الـ views تكون “thin” قدر الإمكان.

---

## 13) Production readiness checklist (مختصر)

- Tenant isolation tests
- DB indexes: `(tenant_id, sku)`, `(tenant_id, created_at)`
- rate limiting endpoints
- audit logs (orders/payments)
- background jobs (Celery) لاحقاً

---

## 14) Flow validation (QA / CI)

للتحقق من صحة التدفقات الأساسية (MVP) وعزل الـ Tenant بشكل آلي:

- Seed بيانات تجريبية (اختياري):
  - `python manage.py seed_sample --tenant default --create-superuser`
- تشغيل Flow Validators (يناسب CI):
  - `python manage.py validate_flows --tenant store1`

"# wasla" 
