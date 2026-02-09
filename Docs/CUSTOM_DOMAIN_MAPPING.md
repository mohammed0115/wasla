# Custom Domain Mapping (AR/EN) — Wasla Store

**AR:** هذا الملف يشرح ربط الدومينات الخاصة للمتاجر (Custom Domains) وكيفية التحقق والـ SSL والربط مع Nginx.  
**EN:** This document explains custom domain mapping: verification, SSL, and Nginx routing.

---

## 1) Business Flow | سير العمل

**AR:**
1) التاجر يضيف الدومين من لوحة التحكم.
2) النظام يعرض تعليمات DNS (A أو CNAME).
3) التاجر يضبط DNS.
4) التحقق: DNS + HTTP challenge.
5) عند النجاح: تفعيل الدومين + إصدار SSL + توجيه للمتجر.
6) التاجر يستطيع رؤية الحالة / إعادة التحقق / تعطيل الدومين.

**EN:**
1) Merchant adds domain in dashboard.
2) System shows DNS instructions (A or CNAME).
3) Merchant updates DNS.
4) Verify ownership (DNS + HTTP challenge).
5) On success: activate domain + issue SSL + route to tenant.
6) Merchant can view status / retry / disable domain.

---

## 2) Data Model | نموذج البيانات

**Model:** `apps/tenants/models.py::StoreDomain`

Fields:
- `tenant` (FK)
- `domain` (unique)
- `status`: `PENDING | VERIFYING | ACTIVE | FAILED | DISABLED`
- `verification_token`
- `verified_at`
- `ssl_cert_path`
- `ssl_key_path`
- `last_check_at`
- `created_at`

---

## 3) Use Cases | الحالات الاستخدامية

**Location:** `apps/tenants/application/use_cases/`

1) `AddCustomDomainUseCase`
2) `GetDomainSetupInstructionsUseCase`
3) `VerifyDomainOwnershipUseCase`
4) `ActivateDomainUseCase`
5) `DisableDomainUseCase`
6) `RefreshSSLCertificateUseCase`

All are transactional + idempotent, with ownership checks in the use-case layer.

---

## 4) Verification | التحقق من الملكية

**DNS:**
- A record → `CUSTOM_DOMAIN_SERVER_IP`
- CNAME → `CUSTOM_DOMAIN_CNAME_TARGET` (fallback: `stores.<WASSLA_BASE_DOMAIN>`)

**HTTP challenge:**
- Path: `/.well-known/wassla-domain-verification/<token>`
- Endpoint served by Django view.

Verification runs via background task and updates status.

---

## 5) Adapters (Infrastructure) | المحولات

**DNS Resolver:** `apps/tenants/infrastructure/dns_resolver.py`  
**SSL Manager:** `apps/tenants/infrastructure/ssl_manager.py`  
**Reverse Proxy (Nginx):** `apps/tenants/infrastructure/reverse_proxy.py`  
**HTTP Challenge:** `apps/tenants/infrastructure/http_challenge.py`  
**Background tasks:** `apps/tenants/tasks.py`

---

## 6) Tenant Resolution | تحديد المتجر حسب الدومين

**AR:** يتم حل الدومين عبر `apps/tenants/services/domain_resolution.py` ويُستخدم داخل `TenantMiddleware`.  
**EN:** Domain-to-tenant resolution is centralized in `apps/tenants/services/domain_resolution.py` and used by `TenantMiddleware`.

Resolution priority:
1) Custom domain (`StoreDomain` where status = ACTIVE)
2) Legacy `Tenant.domain`
3) Subdomain under `WASSLA_BASE_DOMAIN`

---

## 7) Deployment Notes | ملاحظات النشر

**Key env vars:**
- `WASSLA_BASE_DOMAIN`
- `CUSTOM_DOMAIN_SERVER_IP`
- `CUSTOM_DOMAIN_CNAME_TARGET`
- `CUSTOM_DOMAIN_VERIFICATION_PATH_PREFIX`
- `CUSTOM_DOMAIN_SSL_ENABLED`
- `CUSTOM_DOMAIN_CERTBOT_*`
- `CUSTOM_DOMAIN_NGINX_*`

**Nginx include:**
```
/etc/nginx/wassla/domains/*.conf
```

**ALLOWED_HOSTS:**
For large-scale custom domains set:
```
DJANGO_ALLOWED_HOSTS=*
```
or manage a wildcard policy at your reverse proxy.

**Upstream example:**
- `CUSTOM_DOMAIN_NGINX_UPSTREAM=http://127.0.0.1:8000`
- or unix socket: `CUSTOM_DOMAIN_NGINX_UPSTREAM=http://unix:/run/gunicorn-wasla.sock:`

---

## 8) Failure Recovery Plan | خطة التعافي

**AR (مختصر):**
- `FAILED`: تحقق من DNS وملف التحقق HTTP ثم أعد المحاولة.
- فشل SSL: افحص certbot والـ webroot وأعد إصدار الشهادة.
- فشل Nginx: راجع `nginx -t` وسجل الأخطاء، ثم أعد التحميل.
- `DISABLED`: يمكن إعادة إضافة الدومين أو إعادة تفعيله.

**EN (Summary):**
- `FAILED`: check DNS + HTTP challenge, then retry verify.
- SSL failures: inspect certbot, webroot, and re-issue cert.
- Nginx failures: run `nginx -t`, check logs, then reload.
- `DISABLED`: re-add or re-verify the domain.

---

## 9) Test Checklist | قائمة الاختبار

1) Add domain from dashboard.
2) Configure A record or CNAME.
3) Verify domain (DNS + HTTP challenge).
4) Confirm SSL issuance (if enabled).
5) Confirm Nginx config created.
6) Visit domain and ensure correct tenant.
7) Disable domain and confirm routing stops.
