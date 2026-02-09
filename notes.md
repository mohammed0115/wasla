You are a senior Django 5 architect, DevOps/SRE, and security engineer.
Implement Phase 5 ONLY in an existing repo.

Repo facts (MUST follow):
- Django root package: wasla_store/
- Architecture: Clean Architecture (domain/application/infrastructure/interfaces)
- Web: Django Templates + Bootstrap RTL
- API: DRF
- Multi-tenant enforced everywhere
- DB: SQLite now; MySQL-compatible later
- Server: Nginx + Gunicorn (assume systemd)
- Custom domains exist partially in code; Phase 5 focuses on OPS-hardening and safe automation.

PHASE 5 GOAL (P1/P2): “SCALE + SECURITY + OPS HARDENING”
Deliver a production-readiness baseline:
1) Security hardening (headers, cookie flags, CSRF, rate limiting, input safety)
2) Observability (structured logging, basic metrics endpoints, health checks, error tracking hooks)
3) Domain mapping operational hardening:
   - domain verification workflow
   - SSL automation (Let’s Encrypt) done safely
   - Nginx config generator + safe reload strategy
4) Runbooks + incident-ready docs
5) No per-request Nginx reload. All changes are async or admin-triggered.

HARD RULES:
1) Never reload Nginx during HTTP request handling.
2) Any Nginx reload must be safe-guarded (config test before reload).
3) SSL issuance must require domain ownership verification.
4) All tenant data remains isolated.
5) Do not store secrets in .env for email; but Phase 5 focuses on infra/security—not email wiring refactor.
6) Keep changes incremental: extend current domain mapping, do not rewrite.

NON-GOALS:
- Multi-region, Kubernetes, advanced autoscaling
- Full enterprise SIEM integration
- Advanced WAF
- Full SOC2 documentation (only baseline controls + runbooks)

============================================================
SECURITY BASELINE (MANDATORY)
============================================================

A) HTTP Security Headers:
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- Referrer-Policy: same-origin
- Permissions-Policy: minimal
- Content-Security-Policy (basic, non-breaking; allow self + static)
- Strict-Transport-Security (ONLY if HTTPS is enabled; guard with setting)

B) Cookie Security:
- SESSION_COOKIE_SECURE (prod)
- CSRF_COOKIE_SECURE (prod)
- SESSION_COOKIE_HTTPONLY True
- CSRF_COOKIE_HTTPONLY False (default, OK)
- SESSION_COOKIE_SAMESITE Lax

C) Rate limiting:
Implement simple rate limiting middleware using cache (locmem now; redis later).
Apply to:
- login
- otp request/verify
- AI endpoints
- webhook endpoints
Return 429 with i18n message_key.

D) Input hardening:
- file upload limits
- allowed extensions
- sanitize filenames
- prevent path traversal

============================================================
OBSERVABILITY (MANDATORY)
============================================================

A) Structured logging (JSON):
- request_id
- tenant_id
- user_id
- path
- status_code
- latency_ms
- error_code
Do not log PII.

B) Health checks:
- GET /healthz (basic: app up)
- GET /readyz (db connectivity, cache)
Return JSON.

C) Metrics (simple):
- GET /metrics (optional; basic counters)
If prometheus not used, at least provide internal counters via cache.

D) Error pages:
Ensure 500 handler does not leak stack traces.
Log exceptions with request_id.

============================================================
DOMAIN MAPPING OPS HARDENING (MANDATORY)
============================================================

Implement a safe, admin-triggered or scheduled domain provisioning pipeline:

States for StoreDomain:
- PENDING_VERIFICATION
- VERIFIED
- SSL_PENDING
- SSL_ACTIVE
- FAILED

Workflow:
1) Merchant adds domain (mystore.com)
2) System issues verification token (TXT record or HTTP well-known)
3) Admin or scheduled job verifies domain ownership
4) If verified -> issue SSL via certbot (Let’s Encrypt)
5) Generate Nginx vhost config from template
6) Validate Nginx config: nginx -t
7) Reload Nginx safely: systemctl reload nginx
8) Update domain status accordingly

Implementation constraints:
- Do NOT call certbot or nginx reload inside request thread.
- Provide a management command:
  - python manage.py provision_domains
that processes pending domains safely.

Nginx config generator:
- Use Jinja2 template file stored in repo:
  infrastructure/nginx/domain.conf.j2

The command will:
- render config for each verified domain
- write to /etc/nginx/conf.d/wasla_domains/<domain>.conf
- run nginx -t
- if ok -> reload nginx
- else -> mark FAILED and keep previous config

SSL issuance:
- Use certbot in non-interactive mode
- If certbot not installed, log and mark FAILED with reason
- Store only paths to certs in DB (no private key in DB)

============================================================
CODE STRUCTURE (REQUIRED)
============================================================

Create/extend modules:

apps/domains/
- domain/types.py
- domain/policies.py
- application/provision_domain.py
- application/verify_domain.py
- infrastructure/dns_verifier.py
- infrastructure/http_verifier.py
- infrastructure/nginx_generator.py
- infrastructure/ssl_manager.py
- interfaces/admin_views.py (thin)
- interfaces/api_views.py (thin) (optional)
- management/commands/provision_domains.py

apps/observability/
- middleware/request_id.py
- middleware/timing.py
- views/health.py
- views/metrics.py
- logging.py

apps/security/
- middleware/rate_limit.py
- headers.py
- settings_helpers.py

Update:
- wasla_store/settings.py (add middleware, logging config, security settings toggles)
- wasla_store/urls.py (add /healthz and /readyz, optionally /metrics)

============================================================
DELIVERABLES
============================================================

A) File-by-file code blocks with full paths
B) Management command: provision_domains
C) Nginx template file
D) Runbook docs:
- docs/ssl.md
- docs/incident.md
- docs/monitoring.md
E) QA checklist:
- nginx reload safety test
- domain verification test
- SSL issuance test
- health endpoints
- rate limiting works
F) Test outline:
- test_rate_limit_middleware
- test_domain_state_transitions
- test_nginx_generator_renders

============================================================
START WORK
============================================================

Step 1: Add request_id + timing middleware and health endpoints.
Step 2: Add security headers and secure cookie settings (guarded by ENV/setting flag).
Step 3: Add rate limiting middleware and apply to sensitive endpoints.
Step 4: Implement domain provisioning pipeline + management command.
Step 5: Add runbooks and operational docs.
Step 6: Provide QA checklist and test outline.

Now implement Phase 5 only, producing code file-by-file with full paths and code blocks.
