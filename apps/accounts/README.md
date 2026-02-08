# Accounts Module | موديول الحسابات (Accounts)

**AR:** هذا الموديول مسؤول عن تسجيل/دخول التاجر، إدارة ملفه الشخصي، وإدارة خطوات الـ onboarding بعد تسجيل الدخول.  
**EN:** This module handles merchant authentication, profile management, and post-auth onboarding steps.

---

## What lives here? | ماذا يوجد هنا؟

- **Use cases (Application):** `apps/accounts/application/use_cases/`
- **Domain rules & state machine:** `apps/accounts/domain/`
- **Auth backends + OTP providers (Infrastructure):** `apps/accounts/infrastructure/`
- **API (DRF):** `apps/accounts/interfaces/api/`
- **Web views (Django templates):** `apps/accounts/interfaces/web/`
- **Middleware:** `apps/accounts/middleware.py`

---

## Key models | أهم الجداول (Models)

**AR/EN:**
- `AccountProfile`: بيانات التاجر الإضافية (الاسم/الهاتف/الدولة/أنواع النشاط…).
- `AccountAuditLog`: سجل عمليات الدخول/التسجيل (للتتبع).
- `OnboardingProfile`: تتبع خطوة onboarding الحالية.
- `AccountEmailOtp`, `OTPChallenge`, `OTPLog`: دعم OTP وتسجيل التحقق.

---

## Main flows | أهم التدفقات

**AR:**
- تسجيل جديد → إنشاء المستخدم + `AccountProfile` + ضبط خطوة onboarding.
- دخول بكلمة مرور أو OTP → حساب `MerchantNextStep` ثم توجيه المستخدم للخطوة المطلوبة.
- Onboarding (مبسّط): Country → Business Types → Store Create → Done.

**EN:**
- Register → create user + `AccountProfile` + set onboarding step.
- Login (password or OTP) → compute `MerchantNextStep` and redirect accordingly.
- Onboarding (simplified): Country → Business Types → Store Create → Done.

---

## Protection / Redirects | الحماية والتحويلات

**AR:** `OnboardingRedirectMiddleware` يمنع الوصول للـ dashboard قبل إكمال خطوات onboarding.  
**EN:** `OnboardingRedirectMiddleware` blocks dashboard access until onboarding is completed.

---

## Configuration | الإعدادات

**AR/EN (see `wasla_sore/settings.py`):**
- `TEST_OTP_CODE` (dev/testing)
- `OTP_PROVIDER_REGISTRY`
- DRF throttles: `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`

---

## Tests | الاختبارات

Run:
`python manage.py test apps.accounts`

