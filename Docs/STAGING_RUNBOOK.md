# Staging Runbook (AR/EN) — Deployment & Operations

**AR:** هذا الملف يشرح تشغيل النظام وإدارته على سيرفر تجريبي (Staging): إعداد أول مرة، تحديثات، مراقبة، واستكشاف أخطاء.  
**EN:** This runbook explains how to deploy and operate the system on a staging server: initial setup, updates, monitoring, and troubleshooting.

> Source of truth for scripts: `deployment/README.md` and `deployment/*.sh`.

---

## 1) Server prerequisites | متطلبات السيرفر

**AR:**
- Ubuntu `20.04+`
- فتح المنافذ: `80` و (اختياري) `443`
- (اختياري) دومين حقيقي إذا تريد SSL عبر Let's Encrypt

**EN:**
- Ubuntu `20.04+`
- Open ports: `80` and (optional) `443`
- (Optional) real domain if you want Let's Encrypt SSL

---

## 2) One‑time install (recommended path) | إعداد أول مرة (المسار الموصى به)

**AR/EN (run as root):**
```bash
export PROJECT_NAME=wasla
export PROJECT_ROOT=/opt/wasla
export BACKEND_PATH=/opt/wasla/app
export GIT_REPO_URL="https://github.com/<you>/<repo>.git"
export GIT_BRANCH=main
export DOMAIN_NAME="yourdomain.com"   # أو IP عند HTTP فقط

bash deployment/00_env_check.sh
bash deployment/01_git_sync.sh
bash deployment/02_system_setup.sh
bash deployment/04_gunicorn_service.sh
bash deployment/05_nginx_setup.sh

# SSL فقط عند وجود domain حقيقي:
bash deployment/06_ssl_setup.sh
```

**AR:** إذا تستخدم IP فقط، لا تشغّل `06_ssl_setup.sh`.  
**EN:** If using IP-only, do not run `06_ssl_setup.sh`.

---

## 3) Environment files | ملفات البيئة

**AR:**
السكريبتات تضع متغيرات Django عادةً في:
- `/etc/<project>/django.env`

أهم متغيرات مقترحة:
- `DJANGO_SECRET_KEY=...`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS=...` (إذا تم دعمها في settings)
- `DJANGO_SECURE_SSL_REDIRECT=1` (عند HTTPS)
- إعدادات SMTP/SMS حسب الحاجة

**EN:**
Scripts typically write Django env vars to:
- `/etc/<project>/django.env`

Common variables:
- `DJANGO_SECRET_KEY=...`
- `DJANGO_DEBUG=0`
- `DJANGO_SECURE_SSL_REDIRECT=1` (when HTTPS)
- SMTP/SMS settings as needed

> **Note / ملاحظة:** راجع `wasla_sore/settings.py` لمعرفة أسماء المتغيرات المعتمدة فعليًا.

---

## 4) Deploy updates (pull + migrate + restart) | تحديثات النشر

**AR/EN:**
```bash
cd /opt/wasla/app
git pull

source /opt/wasla/venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

systemctl restart gunicorn-wasla
systemctl reload nginx
```

---

## 5) Health checks & logs | فحص الحالة والسجلات

**AR/EN:**
```bash
systemctl status gunicorn-wasla --no-pager
journalctl -u gunicorn-wasla -n 200 --no-pager
nginx -t
tail -n 200 /var/log/nginx/wasla.*.log
```

---

## 6) Troubleshooting | حل المشاكل الشائعة

**AR:**
- 502 من Nginx: تحقق من gunicorn service + socket path + صلاحيات.
- مشاكل static: تأكد من `collectstatic` و `STATIC_ROOT`.
- مشاكل CSRF: راجع `CSRF_TRUSTED_ORIGINS` و HTTPS.

**EN:**
- Nginx 502: check gunicorn service, socket path, and permissions.
- Static issues: verify `collectstatic` and `STATIC_ROOT`.
- CSRF problems: check `CSRF_TRUSTED_ORIGINS` and HTTPS.

