# Wasla Store — User Scenarios QA + Web Mapping (MVP + Future‑Ready)

Date: 2026-02-06  
Scope: Multi-tenant e-commerce platform (Saudi/GCC context, SAR, Arabic RTL)  
Stack: Django 5 + DRF, Django templates + Bootstrap RTL, JWT + Django sessions  
Tenancy: subdomain (`<tenant>.domain.com`) OR API header (`X-Tenant: <slug>`)  
Base URLs (target): Storefront `/store/`, Dashboard `/dashboard/`, API `/api/`

---

## 0) Executive summary (QA verdict)

This repository already has a functioning **merchant dashboard** (templates) and a small set of **API endpoints** (DRF). However, for production readiness and strict tenant isolation, the following are the highest‑priority issues to fix:

1) **Tenant isolation is inconsistent in APIs** (some endpoints allow access without tenant scoping; others lack tenant mismatch checks entirely).  
2) **REST API permissions are globally `IsAuthenticated`**, which blocks guest/customer flows; public endpoints are not defined.  
3) **Business logic leaks into some views** (dashboard aggregation, order completion wallet crediting, API view orchestration doing domain validation).  
4) **Storefront UI and shopper flows are mostly missing** (catalog/search/cart/checkout pages and public APIs).  
5) **Operational roles (support, finance, warehouse, delivery) are not implemented**; require explicit RBAC + audit trails.

This document maps all required roles and journeys, identifies current coverage, and proposes a production-grade implementation plan.

---

## 1) User Roles (define)

| Role | Description | Auth | Tenant scope |
|---|---|---|---|
| 1) Guest visitor (shopper) | Browses a single tenant’s store and can checkout as guest | None (public) | Strictly one tenant via subdomain/header |
| 2) Logged-in customer (shopper) | Customer account with addresses, orders, reviews | Customer sessions/JWT (Phase 2) | Strictly one tenant |
| 3) Merchant (store owner) | Owns and configures a tenant store | Django session (dashboard) + JWT (API) | One tenant (owned) |
| 4) Merchant staff | Operates store with limited permissions | Django session + RBAC (Phase 2) | One tenant (assigned) |
| 5) Platform admin | Super admin for platform operations | Django admin session | Cross-tenant (explicit) |
| 6) Support agent | Customer support, refunds, disputes | Session/JWT + RBAC (Phase 2) | Cross-tenant (explicit, audited) |
| 7) Finance/accounting | Payouts, settlements, invoices | Session/JWT + RBAC (Phase 2) | Cross-tenant (explicit, audited) |
| 8) Warehouse/fulfillment operator | Picking/packing/returns | Session/JWT + RBAC (Phase 2) | Usually per-tenant; sometimes 3PL cross-tenant |
| 9) Delivery/shipping operator | Carrier integration, tracking updates | API keys/webhooks (Phase 2) | Cross-tenant by shipment/order reference (audited) |
| 10) Developer/integration user | API consumers, webhooks, integrations | JWT/OAuth/API keys (Phase 2) | Per-tenant tokens; cross-tenant forbidden |

### Global tenant rules (non-negotiable)

- Every request must resolve exactly one tenant context (`tenant_id` / `store_id`) or be rejected (except platform admin endpoints).
- All reads/writes must include tenant scoping at the repository/query layer.
- Tenant mismatch must return **404** (preferred) or **403** consistently.
- No “fallback to first tenant” behavior in production.

---

## 2) Role-based journeys + Web pages + API endpoints

### Common conventions (used across journeys)

- **Tenant**:
  - Web: subdomain (e.g. `acme.domain.com`) and server-side tenant resolution.
  - API: `X-Tenant: <slug>` required (target behavior).
- **Currency/Locale**: SAR, `ar` (RTL), timezone `Asia/Riyadh` (target settings).
- **HTTP errors**:
  - `400` validation error
  - `401` unauthenticated
  - `403` unauthorized / tenant mismatch (if not using 404)
  - `404` not found (including cross-tenant object access)
  - `409` idempotency conflict / state transition conflict (Phase 2)

---

## 2.1) Guest visitor (not logged in) — shopper

#### Journey A — Browse storefront catalog (MVP target; currently missing UI + API)

Steps
1) Open store home  
   - Web: `GET /store/` → `templates/store/home.html` (target)  
   - Output: featured categories/products
2) Browse category  
   - Web: `GET /store/categories/<slug>/` (target)  
   - API: `GET /api/storefront/categories/` (target)  
3) View product details  
   - Web: `GET /store/products/<sku-or-slug>/` (target)  
   - API: `GET /api/storefront/products/<id>/` (target)

Validation rules
- Only products for current tenant (`Product.store_id == tenant.id`).
- Only active/in-stock products shown to guest (configurable).

State changes
- None (read-only).

Edge cases
- Tenant inactive → 404 or “store paused” page (web).
- Product exists but belongs to another tenant → 404.

Current implementation coverage (as-is)
- No storefront URLs exist; only dashboard templates exist.
- Catalog API is not implemented (`apps/catalog/urls.py` is empty).

#### Journey B — Search (Phase 2; planned)

Steps
1) Search query (text)  
   - Web: `GET /store/search?q=...` (target)  
   - API: `GET /api/storefront/search?q=...&category=...&min_price=...` (target)

Validation rules
- Tenant-scoped index/query only.
- Rate-limit to prevent scraping.

State changes
- Optional: store search analytics event.

Edge cases
- Abuse: brute force / enumeration → throttling, bot mitigation.

#### Journey C — Cart + Checkout as guest (Phase 2; planned)

Steps
1) Add to cart  
   - Web: `POST /store/cart/items` (target)  
   - API: `POST /api/storefront/cart/items` (target)
2) View cart  
   - Web: `GET /store/cart/` (target)
3) Checkout  
   - Web: `GET /store/checkout/` and `POST /store/checkout/` (target)  
   - API: `POST /api/storefront/checkout/` (target)
4) Payment  
   - Web: redirect to gateway / show payment status (Phase 2)  
   - API: `POST /api/storefront/orders/<id>/payments/` (target)

Validation rules
- Quantity > 0; product active; enough inventory; pricing recalculated server-side.
- Idempotency key required for checkout/payment (Phase 2).

State changes
- Cart created/updated; order created; payment initiated; inventory reserved/adjusted.

Edge cases
- Race: inventory decreases during checkout → retry/reprice.
- Duplicate submit → idempotency prevents double charge/order creation.

---

## 2.2) Logged-in customer — shopper

This role requires a customer auth model (Phase 2). Current code has a `Customer` table but no customer login/registration.

#### Journey A — Register / Login (Phase 2)

Steps
1) Register  
   - Web: `GET/POST /store/account/register/` (target)  
   - API: `POST /api/storefront/auth/register` (target)
2) Login  
   - Web: `GET/POST /store/account/login/` (target)  
   - API: `POST /api/auth/token/` (existing JWT token endpoint, but must become customer-scoped)

Validation rules
- Email unique per tenant (`Customer(store_id,email)` unique constraint exists).
- MFA/OTP optional (Saudi context: SMS OTP is common).

State changes
- Customer record created; session/JWT created; audit event.

Edge cases
- Same email across different tenants is allowed (by design).

#### Journey B — Manage profile + addresses (Phase 2)

Steps
1) View profile  
   - Web: `GET /store/account/`  
   - API: `GET /api/storefront/me`
2) Add/edit addresses  
   - Web: `/store/account/addresses/`  
   - API: `POST /api/storefront/me/addresses`

Validation rules
- Address belongs to the authenticated customer and tenant.
- One default address max.

State changes
- Address rows created/updated.

#### Journey C — View order history + order details (Phase 2)

Steps
1) List orders  
   - Web: `GET /store/account/orders/`  
   - API: `GET /api/storefront/me/orders`
2) View order details  
   - Web: `GET /store/account/orders/<order_number>/`  
   - API: `GET /api/storefront/me/orders/<id>`

Validation rules
- Orders are tenant-scoped and customer-scoped.

---

## 2.3) Merchant (store owner) — dashboard

Current implementation is closest to this role (dashboard templates exist).

### Web pages (as-is)

Note: Current routes are mounted at site root (`/`). Target is to move them under `/dashboard/`.

- Dashboard
  - `GET /` → `templates/web/dashboard.html` (`wasla_sore/web_urls.py`)
- Products
  - `GET /products/` → `templates/web/products/list.html`
  - `GET/POST /products/new/` → `templates/web/products/form.html`
  - `GET/POST /products/<id>/edit/` → `templates/web/products/form.html`
- Orders
  - `GET /orders/` → `templates/web/orders/list.html`
  - `GET/POST /orders/new/` → `templates/web/orders/create.html`
  - `GET /orders/<id>/` → `templates/web/orders/detail.html`
  - `POST /orders/<id>/status/` (transition) → redirect to detail
  - `POST /orders/<id>/pay/` (dummy pay) → redirect
  - `POST /orders/<id>/ship/` (create shipment) → redirect
- Shipments
  - `GET /shipments/` → `templates/web/shipping/list.html`
- Wallet
  - `GET /wallet/` → `templates/web/wallet/detail.html`
  - `POST /wallet/credit/` and `POST /wallet/debit/` → redirect
- Reviews moderation
  - `GET /reviews/` → `templates/web/reviews/list.html`
  - `POST /reviews/<id>/approve/` and `POST /reviews/<id>/reject/`
- Subscriptions + plans
  - `GET /subscriptions/` → `templates/web/subscriptions/plans.html`
  - `GET/POST /subscriptions/new/` → `templates/web/subscriptions/plan_form.html` (should be platform admin only)
  - `POST /subscriptions/<id>/subscribe/`
- App store / plugins
  - `GET /app-store/` → `templates/web/plugins/store.html`
  - `POST /app-store/<id>/install/`
- Settings
  - `GET /settings/` → `templates/web/settings/index.html`

### APIs (as-is)

All API URLs are under `/api/` and include:
- JWT:
  - `POST /api/auth/token/`
  - `POST /api/auth/token/refresh/`
  - `POST /api/auth/token/verify/`
- Customers:
  - `POST /api/customers/create/`
- Orders:
  - `POST /api/customers/<customer_id>/orders/create/`
- Payments:
  - `POST /api/orders/<order_id>/pay/`
- Shipping:
  - `POST /api/orders/<order_id>/ship/`
- Reviews:
  - `POST /api/reviews/create/`
  - `GET /api/products/<product_id>/reviews/`
- Subscriptions:
  - `GET /api/plans/`
  - `POST /api/stores/<store_id>/subscribe/`
- Wallet:
  - `GET /api/stores/<store_id>/wallet/`
- Plugins:
  - `GET /api/plugins/`
  - `POST /api/stores/<store_id>/plugins/install/`

#### Journey A — Login to dashboard (MVP implemented)

Steps
1) Open login  
   - Web: `GET /accounts/login/` → `templates/registration/login.html` (Django auth)
2) Submit credentials  
   - Web: `POST /accounts/login/`  
   - Output: session cookie; redirect to `LOGIN_REDIRECT_URL` (currently `/`)
3) Open dashboard  
   - Web: `GET /` → shows KPIs

Validation rules
- Merchant user must be authenticated.
- (Phase 2) Merchant user must be authorized for tenant store (RBAC).

State changes
- Session created.

Edge cases
- Tenant missing/inactive → should block dashboard access (Phase 2; currently middleware can fall back).

#### Journey B — Create/update product + inventory (MVP implemented)

Steps
1) Open product list  
   - Web: `GET /products/`
2) Open create form  
   - Web: `GET /products/new/`
3) Submit product  
   - Web: `POST /products/new/`  
   - Inputs: `sku`, `name`, `price`, `quantity`, optional `image`, categories  
   - Output: redirect to list; flash message

Validation rules (current + target)
- `sku` required and unique per tenant (`uq_product_store_sku`).
- `price > 0`.
- `quantity >= 0`; product `is_active` auto toggled based on quantity.
- Categories must belong to same tenant (currently validated in `ProductService._validate_categories`).
- (Phase 2) Validate image type/size; store via storage port (S3, etc).

State changes
- `Product` row created/updated.
- `Inventory` row upserted; `in_stock` toggled.

Edge cases
- Concurrent SKU creation → DB constraint; return friendly error.
- Category cross-tenant selection should be impossible even if user tampers.

#### Journey C — Create order (backoffice) (MVP implemented for dashboard)

Steps
1) Open order create  
   - Web: `GET /orders/new/`  
   - Input: select `Customer` and add items with `Product`, `qty`, `price`
2) Submit order create  
   - Web: `POST /orders/new/`

Validation rules
- At least one item.
- Item product must belong to tenant and be active.
- (Target) Price should be server-calculated for storefront checkouts; for backoffice, allow override with permission.
- Subscription limits: `max_orders_monthly` enforced (implemented in `OrderService.create_order`).

State changes
- `Order` + `OrderItem` created (`status="pending"`).

Edge cases
- Creating orders for inactive customers should be blocked (dashboard form filters `is_active=True`).

#### Journey D — Payment initiation (dummy) (MVP implemented but not production-ready)

Steps
1) From order detail, click “pay”  
   - Web: `POST /orders/<id>/pay/`  
   - API: `POST /api/orders/<id>/pay/` with `{ "method": "card" }`
2) Payment service charges gateway  
   - Current: always success; marks order paid; creates `Payment`

Validation rules
- Order must be `pending` to pay.
- Stock validated before charging (`OrderService.validate_stock`).
- (Phase 2) Idempotency key required, gateway webhooks, and anti-double-charge.

State changes
- `Payment` created; `Payment.status` moves `pending → success/failed`.
- On success: `Order.status` moves `pending → paid`; inventory decremented.

Edge cases
- Repeated pay requests create multiple payments today (must be idempotent).
- Concurrency: two payments racing can double-decrement inventory (must lock/idempotent).

#### Journey E — Order processing → shipment → delivery → completion (MVP implemented for dashboard)

Steps
1) Mark order as processing  
   - Web: `POST /orders/<id>/status/` with `status=processing` (only allowed from `paid`)
2) Create shipment  
   - Web: `POST /orders/<id>/ship/` with carrier  
   - API: `POST /api/orders/<id>/ship/` (note: API currently requires status `processing` but no API transition exists)
3) Mark delivered  
   - Web: `POST /orders/<id>/status/` with `status=delivered` (requires shipment exists)
4) Mark completed  
   - Web: `POST /orders/<id>/status/` with `status=completed`  
   - Side-effect: wallet credited once for completed order (currently done in view)

Validation rules
- Order state machine enforced (`ORDER_TRANSITIONS` in `web_views.py`).
- Shipment allowed only when order is `processing` (`ShippingService`).
- Delivered/completed require at least one shipment.
- Wallet credit must be idempotent (implemented via reference check, but should be a domain policy/use-case).

State changes
- `Order.status` changes across states.
- `Shipment` created and set to shipped with tracking number.
- On delivered: shipment statuses updated.
- On completed: wallet credited + wallet transaction created.

Edge cases
- API cannot progress `paid → processing` today, so API shipping flow is incomplete.
- Wallet crediting in view risks duplicate credits if logic changes; move to use-case.

#### Journey F — Reviews moderation (MVP implemented for dashboard; customer submission is broken)

Steps (merchant)
1) View reviews  
   - Web: `GET /reviews/`
2) Approve/reject  
   - Web: `POST /reviews/<id>/approve/` or `/reject/`

Validation rules
- Review must belong to a product in current tenant.

State changes
- `Review.status` changes `pending → approved/rejected`.

Customer submission (API) problems (as-is)
- `POST /api/reviews/create/` uses `request.user.customer` which is not defined in current auth model.
- No tenant scoping or product ownership checks are enforced in the API view.

---

## 2.4) Merchant staff (limited permissions) — dashboard (Phase 2)

Core requirement: RBAC with tenant-scoped permissions. Do not rely on “if user is staff” flags alone.

#### Journey A — Staff can fulfill orders but cannot manage billing

Steps
1) Login  
   - Web: `/accounts/login/`
2) View orders and shipment list  
   - Web: `/dashboard/orders/`, `/dashboard/shipments/`
3) Transition allowed states and create shipments  
   - Web: `/dashboard/orders/<id>/status/`, `/dashboard/orders/<id>/ship/`

Validation rules
- Staff must have explicit permission set (examples):
  - `orders.view`, `orders.update_status`, `shipping.create_shipment`.
- Forbidden:
  - subscription changes, wallet debit/withdrawal, plugin installation.

State changes
- Same as merchant flows, but constrained actions.

Edge cases
- Staff assigned to tenant A must not access tenant B even if they guess IDs.

Implementation notes
- Add a `StoreMembership(user, store_id, role)` table (Phase 2).
- Add permission policy layer (`apps/<domain>/policies.py`) and enforce in use-cases.

---

## 2.5) Platform admin (super admin / operations)

Platform admin owns cross-tenant operations and must have strict audit logs.

#### Journey A — Manage tenants (MVP partially implemented via Django admin)

Steps
1) Login to Django admin  
   - Web: `GET/POST /admin/`
2) Create/update tenant  
   - Web: `Tenant` model in admin (`apps/tenants/admin.py`)

Validation rules
- `slug` unique.
- `is_active` gates access.
- Domain/subdomain uniqueness (Phase 2 constraints).

State changes
- Tenant row created/updated.

Edge cases
- Changing tenant slug/domain affects routing; require migration/redirect plan.

#### Journey B — Manage subscription plans + plugins (MVP partially implemented)

Steps
- Plans: `/admin/` → `SubscriptionPlan`, `StoreSubscription`
- Plugins: `/admin/` → `Plugin`, `InstalledPlugin`

Validation rules
- Plan changes must be versioned and not break existing stores (Phase 2).

---

## 2.6) Support agent (customer support / refunds) — Phase 2

Key principle: cross-tenant access is allowed only through a **support permission** and must be logged.

#### Journey A — Find an order and assist customer

Steps
1) Search order by order number/email/phone  
   - Web: `/ops/orders/search` (target)  
   - API: `GET /api/ops/orders?query=...` (target)
2) View order timeline, payments, shipments  
   - Web: `/ops/orders/<order_number>/`  
   - API: `GET /api/ops/orders/<id>`
3) Add internal notes and contact log  
   - Web: `/ops/orders/<id>/notes`  
   - API: `POST /api/ops/orders/<id>/notes`

Validation rules
- Must record who accessed what and why (audit log).
- Data minimization (PII visibility only when needed).

State changes
- Notes appended, support ticket status updated.

#### Journey B — Refund / cancel (Phase 2)

Steps
- API: `POST /api/ops/orders/<id>/refunds` with idempotency key

Validation rules
- Refund amounts cannot exceed captured amount.
- State machine constraints (cannot refund if not paid/captured, etc).

---

## 2.7) Finance/admin accounting (payouts, settlements) — Phase 2

#### Journey A — Payout calculation and settlement

Steps
1) Compute eligible balance per tenant  
   - API: `GET /api/finance/tenants/<id>/payouts/preview`
2) Create payout batch  
   - API: `POST /api/finance/payouts` (tenant_id, amount, destination)
3) Mark payout completed and export report  
   - Web: `/finance/payouts/` + exports

Validation rules
- Ledger-based wallet (available vs pending) required; no direct mutable balance.
- Double-entry bookkeeping invariants.
- Approvals (4-eyes) for large payouts.

State changes
- Ledger entries created; payout records created; external transfer references stored.

---

## 2.8) Warehouse / fulfillment operator — Phase 2

#### Journey A — Pick/pack/ship workflow

Steps
1) List orders ready for fulfillment  
   - Web: `/warehouse/orders?status=processing`
2) Pick list + inventory confirmation  
   - Web: `/warehouse/orders/<id>/pick`
3) Pack and request shipment/label  
   - API: `POST /api/warehouse/orders/<id>/shipments`

Validation rules
- Inventory reservation and adjustments must be atomic.
- Partial fulfillment rules if supported.

State changes
- Fulfillment records; shipment creation; order status updates.

---

## 2.9) Delivery / shipping operator (carrier integration) — Phase 2

#### Journey A — Carrier webhook updates shipment tracking

Steps
1) Carrier calls webhook with tracking update  
   - API: `POST /api/webhooks/shipping/<carrier>/tracking`  
   - Input: tracking_number, status, timestamp, signature
2) System validates signature and maps to shipment  
3) Update shipment + potentially order status  
   - State: shipped → delivered, exceptions, etc.

Validation rules
- Signature verification (HMAC) and replay protection.
- Shipment lookup must be tenant-safe.

State changes
- `Shipment.status` updates; `Order.status` transitions (policy).

---

## 2.10) Developer / integration user (API consumers, webhooks) — Phase 2

#### Journey A — Obtain tenant-scoped API credentials

Steps
1) Create integration app (merchant dashboard)  
   - Web: `/dashboard/developers/apps/`  
2) Generate token / rotate secret  
   - API: `POST /api/dev/apps/<id>/tokens`

Validation rules
- Tokens scoped to tenant + permissions (read catalog, write inventory, read orders, etc).

#### Journey B — Integrate order creation / fulfillment

Steps
- Catalog sync: `GET /api/storefront/products` (public or token)
- Create order: `POST /api/storefront/checkout` (public with idempotency)
- Fulfill: `POST /api/orders/<id>/ship` (authorized staff token)

---

## 3) “Flow Validation Layer” design (application layer)

Goal: continuously validate the **end-to-end business flows** (web + API) without embedding business rules in views/templates.

### 3.1 Use-cases (flow validators)

Create an application-layer module such as:

- `apps/tenants/application/flow_validation/` (or `apps/core/application/flow_validation/` if you introduce `core`)
  - `base.py` → `FlowScenario`, `FlowResult`, `FlowIssue`
  - `mvp_catalog.py` → create/update product scenario
  - `mvp_order_lifecycle.py` → create order → pay → processing → ship → deliver → complete
  - `mvp_tenant_isolation.py` → verifies cross-tenant requests return 404/403
  - `phase2_checkout_idempotency.py` → reserved for future

Each `FlowScenario` should:
- Accept a `TenantContext` (`tenant_id`, `currency`, `timezone`, `language`).
- Call *use-cases/services only* (no direct ORM calls from web/API layer).
- Assert invariants (tenant scoping, state transitions, idempotency, limits).

### 3.2 How they are triggered

- Management command:
  - `python manage.py validate_flows --tenant <slug> [--fail-fast]`
- CI job:
  - Seed sample tenant + catalog (`python manage.py seed_sample --tenant ci`)
  - Run `validate_flows`
- Optional: nightly job in production (read-only validations) with alerting.

### 3.3 Architecture impact

- Forces a clear separation between:
  - `interfaces/web` (views/templates): orchestration only
  - `interfaces/api` (DRF views): serialization + orchestration only
  - `application`: use-cases, flow validators, policies
  - `infrastructure`: repositories, gateway adapters
- Makes multi-tenancy testable as a cross-cutting invariant.

---

## 4) Test plan

### 4.1 Unit tests (policies/use-cases)

Tenant isolation
- Any repository query must require `tenant_id` (or use tenant-aware manager).
- Cross-tenant object access returns 404/403.

Catalog
- SKU unique per tenant.
- Price positive, quantity non-negative.
- Categories belong to same tenant.
- Subscription limits `max_products`.

Orders
- State machine: only allowed transitions.
- Stock validation and atomic decrement on pay.
- Subscription limits `max_orders_monthly`.

Shipping
- Shipment allowed only when order is processing.
- Tracking number format/requirements.

Wallet
- Credit/debit invariants (amount > 0, no negative available balance).
- (Phase 2) Ledger reconciliation.

Subscriptions / plugins
- Feature gating and plan enforcement.

### 4.2 Integration tests (API)

For every endpoint:
- Requires tenant header (except platform admin).
- Returns 401/403 for invalid auth; returns 404 for cross-tenant access.
- Validates payloads and returns consistent error schema.

Minimum coverage (MVP)
- `POST /api/customers/create/` (tenant-scoped)
- `POST /api/customers/<id>/orders/create/` (tenant-scoped)
- `POST /api/orders/<id>/pay/` (idempotency planned)
- `POST /api/orders/<id>/ship/` (requires correct state)
- `GET /api/stores/<id>/wallet/` (must enforce tenant mismatch)

### 4.3 E2E tests (optional; Playwright)

Merchant dashboard smoke flow
- Login → create product → create order → pay → set processing → ship → deliver → complete.

Tenant isolation UI smoke
- Two tenants seeded; ensure you cannot see tenant A data under tenant B subdomain.

---

## 5) Production readiness checklist

### 5.1 Security

- Enforce tenant context:
  - No `store_id` query param fallbacks; no “first active tenant” fallback in middleware (prod).
- API permissions:
  - Replace global `IsAuthenticated` with per-endpoint permissions (public storefront vs dashboard vs ops).
- RBAC:
  - Tenant membership model + permissions; deny by default.
- Sensitive operations:
  - Wallet debits, refunds, plan changes require elevated permissions + audit log.
- JWT hardening:
  - Rotation, blacklisting (Phase 2), shorter lifetimes, secure cookie/session configs.
- Input validation:
  - File uploads (images): content-type sniffing, max size, virus scanning (Phase 2).
- Rate limiting + bot protection:
  - Public endpoints and auth endpoints.

### 5.2 Performance

- DB indexes:
  - Already present for orders; add for common tenant filters (e.g., `Product(store_id,is_active)`).
- Pagination:
  - Orders/products/reviews APIs should paginate.
- Query optimization:
  - Use `select_related/prefetch_related` in read models.
- Caching:
  - Storefront catalog pages and category lists.

### 5.3 Monitoring / logging

- Structured logs with request_id + tenant_id + user_id.
- Audit logs for cross-tenant ops, refunds, payouts, role changes.
- Error reporting (Sentry) and metrics (Prometheus/OpenTelemetry).

### 5.4 Data integrity

- Idempotency:
  - Checkout + payment initiation + webhooks (Phase 2).
- Strong invariants:
  - Order state machine in domain layer (not view layer).
  - Prevent cross-tenant M2M contamination (categories/products).
- Migrations:
  - Ensure Postgres compatibility (JSONField, indexes).
- Backups:
  - Regular backups, restore drills, retention.

---

## 6) Implementation plan (phased)

### Phase 0 (Hardening the existing MVP — 1–3 days)

Tenant enforcement
- Make tenant mandatory for all non-admin requests; remove `store_id` GET/session fallback in production settings.
- Add a `TenantRequiredMixin` / DRF permission to enforce `request.tenant` exists.

API security fixes
- For every API endpoint, enforce tenant mismatch checks (404/403) consistently.
- Stop accepting `store_id` from input serializers; derive from tenant.

Move business logic out of views
- Extract dashboard aggregation queries into an application service (read model).
- Extract “order completion credits wallet” into a use-case (idempotent, transactional).

Correctness fixes
- Fix `/api/reviews/create/` (customer identity + tenant check).
- Add an API for `paid → processing` (or unify the state machine use-case).

### Phase 1 (MVP storefront — 1–2 weeks)

- Introduce `/store/` URLs + templates for: home, category, product detail, cart, checkout.
- Add public storefront APIs: list products, product detail, search (basic).
- Customer model integration: allow guest checkout; optional customer accounts.

### Phase 2 (Payments, webhooks, subscriptions billing — 2–6 weeks)

- Payment gateway ports + adapters (PayTabs/Moyasar/HyperPay), webhook verification, idempotency.
- Refunds + partial refunds, reconciliation.
- Subscription billing integration + feature limits enforcement in all flows.

### Phase 3 (Ops roles: support/finance/warehouse/delivery + integrations — ongoing)

- RBAC + audit logs + ops dashboards.
- Payouts/settlements ledger.
- Carrier integrations, shipping labels, tracking webhooks.
- Developer apps, API keys/OAuth, webhooks.

