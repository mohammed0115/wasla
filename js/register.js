/*
  Wasla Registration (Demo)
  - Pure HTML/CSS/JS
  - Client-side validation + mocked API call
  - Stores draft in localStorage and redirects to verify.html
*/

(() => {
  const THEME_KEY = "wasla_theme";
  const REG_KEY = "wasla_reg";

  const $ = (id) => document.getElementById(id);

  const themeIconSvg = (theme) => {
    if (theme === "dark") {
      return `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z" stroke="currentColor" stroke-width="2"/>
          <path d="M12 2v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M12 20v2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M4.93 4.93l1.41 1.41" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M17.66 17.66l1.41 1.41" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M2 12h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M20 12h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M4.93 19.07l1.41-1.41" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M17.66 6.34l1.41-1.41" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      `;
    }
    return `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M21 14.5A8.5 8.5 0 1 1 9.5 3a6.7 6.7 0 0 0 11.5 11.5Z"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    `;
  };

  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    const icon = $("themeIcon");
    if (icon) icon.innerHTML = themeIconSvg(theme);
  };

  const initTheme = () => {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") applyTheme(saved);

    const toggle = $("themeToggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "light";
        const next = current === "dark" ? "light" : "dark";
        localStorage.setItem(THEME_KEY, next);
        applyTheme(next);
      });
    }
  };

  const showAlert = (type, message) => {
    const alert = $("formAlert");
    if (!alert) return;
    alert.className = `alert show ${type}`;
    alert.textContent = message;
  };

  const clearAlert = () => {
    const alert = $("formAlert");
    if (!alert) return;
    alert.className = "alert";
    alert.textContent = "";
  };

  const setFieldError = (fieldId, message, invalid) => {
    const field = $(fieldId);
    if (!field) return;
    field.dataset.invalid = invalid ? "true" : "false";

    // Optional: update error text if provided.
    const errorEl = field.querySelector(".error");
    if (errorEl && message) errorEl.textContent = message;
  };

  const normalizeSaudiPhoneToE164 = (raw) => {
    const value = String(raw || "").trim().replace(/\s+/g, "");
    if (!value) return null;

    // Accept patterns:
    //  - 05XXXXXXXX
    //  - 5XXXXXXXX
    //  - +9665XXXXXXXX
    //  - 9665XXXXXXXX
    const v = value.replace(/[-().]/g, "");
    const m = v.match(/^(\+?966)?0?5(\d{8})$/);
    if (!m) return null;
    return `+9665${m[2]}`;
  };

  const isValidEmail = (email) => {
    const v = String(email || "").trim().toLowerCase();
    if (!v) return true; // optional
    // Simple email regex for UI validation (server should validate strictly).
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
  };

  const passwordScore = (password) => {
    const v = String(password || "");
    let score = 0;
    if (v.length >= 10) score += 1;
    if (/[a-zA-Z]/.test(v)) score += 1;
    if (/\d/.test(v)) score += 1;
    if (/[^a-zA-Z0-9]/.test(v)) score += 1;
    return score; // 0..4
  };

  const updatePasswordMeter = (password) => {
    const meter = $("passwordMeter");
    if (!meter) return;
    const score = passwordScore(password);
    const pct = (score / 4) * 100;
    meter.style.width = `${pct}%`;
    if (score <= 1) meter.style.background = "var(--danger)";
    else if (score === 2) meter.style.background = "var(--warning)";
    else meter.style.background = "var(--success)";
  };

  const getSelectedRole = () => {
    const selected = document.querySelector('input[name="role"]:checked');
    return selected ? selected.value : "";
  };

  const syncRoleCards = () => {
    const selectedRole = getSelectedRole();
    document.querySelectorAll(".role-card").forEach((card) => {
      const role = card.getAttribute("data-role");
      card.dataset.selected = role === selectedRole ? "true" : "false";
    });
  };

  const validateForm = () => {
    const fullName = $("fullName")?.value || "";
    const phone = $("phone")?.value || "";
    const email = $("email")?.value || "";
    const password = $("password")?.value || "";
    const role = getSelectedRole();
    const terms = Boolean($("terms")?.checked);

    clearAlert();

    // Full name
    const nameOk = fullName.trim().length >= 2 && fullName.trim().length <= 200;
    setFieldError("fieldFullName", "الاسم مطلوب (على الأقل حرفين).", !nameOk);

    // Phone
    const phoneE164 = normalizeSaudiPhoneToE164(phone);
    const phoneOk = Boolean(phoneE164);
    setFieldError("fieldPhone", "أدخل رقم جوال سعودي صحيح (مثل 05XXXXXXXX).", !phoneOk);

    // Email (optional)
    const emailOk = isValidEmail(email);
    setFieldError("fieldEmail", "أدخل بريدًا إلكترونيًا صحيحًا.", !emailOk);

    // Password
    const score = passwordScore(password);
    updatePasswordMeter(password);
    const passOk = score >= 3; // length + letter + number (and ideally symbol)
    setFieldError("fieldPassword", "كلمة المرور ضعيفة. جرّب إضافة أرقام/رموز أكثر.", !passOk);

    // Role
    const roleOk = Boolean(role);
    setFieldError("fieldRole", "اختر نوع الحساب للمتابعة.", !roleOk);

    // Terms
    const termsOk = terms;
    setFieldError("fieldTerms", "لازم توافق على الشروط والخصوصية لإكمال التسجيل.", !termsOk);

    const ok = nameOk && phoneOk && emailOk && passOk && roleOk && termsOk;
    return { ok, fullName: fullName.trim(), phoneE164, email: email.trim().toLowerCase(), role };
  };

  const setLoading = (loading) => {
    const btn = $("submitBtn");
    const text = $("submitText");
    if (!btn || !text) return;
    btn.disabled = loading;
    btn.classList.toggle("loading", loading);
    text.textContent = loading ? "جاري إنشاء الحساب..." : "إنشاء الحساب";
  };

  const init = () => {
    initTheme();

    // Restore draft if exists
    try {
      const raw = localStorage.getItem(REG_KEY);
      const draft = raw ? JSON.parse(raw) : null;
      if (draft && typeof draft === "object") {
        if ($("fullName")) $("fullName").value = draft.fullName || "";
        if ($("phone")) $("phone").value = draft.phoneRaw || draft.phoneE164 || "";
        if ($("email")) $("email").value = draft.email || "";
        if (draft.role) {
          const radio = document.querySelector(`input[name="role"][value="${draft.role}"]`);
          if (radio) radio.checked = true;
        }
        syncRoleCards();
      }
    } catch (_) {
      // ignore
    }

    // Role cards
    document.querySelectorAll(".role-card input").forEach((input) => {
      input.addEventListener("change", () => {
        syncRoleCards();
        setFieldError("fieldRole", "", false);
      });
    });
    syncRoleCards();

    // Inline validation
    $("fullName")?.addEventListener("blur", () => validateForm());
    $("phone")?.addEventListener("blur", () => validateForm());
    $("email")?.addEventListener("blur", () => validateForm());
    $("password")?.addEventListener("input", (e) => updatePasswordMeter(e.target.value));
    $("password")?.addEventListener("blur", () => validateForm());
    $("terms")?.addEventListener("change", () => validateForm());

    const form = $("registerForm");
    if (!form) return;

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const result = validateForm();
      if (!result.ok) {
        showAlert("error", "تحقق من الحقول المطلوبة قبل المتابعة.");
        return;
      }

      // Save draft + simulate backend response
      setLoading(true);

      const payload = {
        fullName: result.fullName,
        phoneRaw: $("phone")?.value || "",
        phoneE164: result.phoneE164,
        email: result.email || "",
        role: result.role,
        termsAccepted: true,
        createdAt: new Date().toISOString(),
        verificationId: `ver_${Math.random().toString(16).slice(2)}`,
        otpSentAtMs: Date.now(),
      };
      localStorage.setItem(REG_KEY, JSON.stringify(payload));

      // Mock API request
      window.setTimeout(() => {
        setLoading(false);
        // Redirect to OTP page
        window.location.href = "verify.html";
      }, 900);
    });
  };

  document.addEventListener("DOMContentLoaded", init);
})();
