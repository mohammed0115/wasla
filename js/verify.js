/*
  Wasla OTP Verification (Demo)
  - 6-digit OTP input UX (auto move, backspace, paste)
  - Countdown timer + resend logic
  - Mock verification: accepts 123456
*/

(() => {
  const THEME_KEY = "wasla_theme";
  const REG_KEY = "wasla_reg";
  const OTP_OK = "123456";

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
    const alert = $("otpAlert");
    if (!alert) return;
    alert.className = `alert show ${type}`;
    alert.textContent = message;
  };

  const clearAlert = () => {
    const alert = $("otpAlert");
    if (!alert) return;
    alert.className = "alert";
    alert.textContent = "";
  };

  const setOtpError = (invalid, message) => {
    const field = $("fieldOtp");
    if (!field) return;
    field.dataset.invalid = invalid ? "true" : "false";
    if (message) {
      const err = $("otpError");
      if (err) err.textContent = message;
    }
  };

  const maskPhone = (phoneE164) => {
    const v = String(phoneE164 || "");
    // +9665XXXXXXXX
    const m = v.match(/^\+9665(\d)(\d{2})(\d{2})(\d{3})$/);
    if (!m) return v;
    return `+966 5${m[1]} ${m[2]}${m[3]} ${m[4]}`;
  };

  const getDraft = () => {
    const raw = localStorage.getItem(REG_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  };

  const setDraft = (draft) => {
    localStorage.setItem(REG_KEY, JSON.stringify(draft));
  };

  const getOtpInputs = () => Array.from(document.querySelectorAll("#otpGroup input"));

  const getOtpValue = () => getOtpInputs().map((i) => i.value.trim()).join("");

  const clearOtp = () => {
    getOtpInputs().forEach((i) => (i.value = ""));
    getOtpInputs()[0]?.focus();
  };

  const setLoading = (loading) => {
    const btn = $("verifyBtn");
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle("loading", loading);
  };

  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));

  const formatTime = (seconds) => {
    const s = clamp(seconds, 0, 3600);
    const mm = String(Math.floor(s / 60)).padStart(2, "0");
    const ss = String(s % 60).padStart(2, "0");
    return `${mm}:${ss}`;
  };

  const initOtpUx = () => {
    const inputs = getOtpInputs();
    inputs.forEach((input, idx) => {
      input.addEventListener("input", () => {
        input.value = input.value.replace(/[^\d]/g, "").slice(0, 1);
        setOtpError(false, "");
        if (input.value && idx < inputs.length - 1) inputs[idx + 1].focus();
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Backspace" && !input.value && idx > 0) {
          inputs[idx - 1].focus();
        }
        if (e.key === "ArrowLeft" && idx > 0) inputs[idx - 1].focus();
        if (e.key === "ArrowRight" && idx < inputs.length - 1) inputs[idx + 1].focus();
      });

      input.addEventListener("paste", (e) => {
        const pasted = (e.clipboardData?.getData("text") || "").replace(/[^\d]/g, "").slice(0, 6);
        if (!pasted) return;
        e.preventDefault();
        pasted.split("").forEach((ch, i) => {
          if (inputs[i]) inputs[i].value = ch;
        });
        inputs[Math.min(pasted.length, 6) - 1]?.focus();
      });
    });

    inputs[0]?.focus();
  };

  const initTimer = (draft) => {
    const timerEl = $("timerText");
    const resendBtn = $("resendBtn");
    if (!timerEl || !resendBtn) return () => {};

    const total = 60;
    const startMs = typeof draft.otpSentAtMs === "number" ? draft.otpSentAtMs : Date.now();

    let intervalId = null;

    const tick = () => {
      const elapsed = Math.floor((Date.now() - startMs) / 1000);
      const remaining = total - elapsed;
      timerEl.textContent = formatTime(remaining);

      const canResend = remaining <= 0;
      resendBtn.disabled = !canResend;
      if (canResend && intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    };

    tick();
    intervalId = window.setInterval(tick, 250);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  };

  const init = () => {
    initTheme();

    const draft = getDraft();
    if (!draft || !draft.phoneE164) {
      // No signup draft found.
      window.location.href = "index.html";
      return;
    }

    const masked = $("maskedPhone");
    if (masked) masked.textContent = maskPhone(draft.phoneE164);

    initOtpUx();
    let cleanupTimer = initTimer(draft);

    const resendBtn = $("resendBtn");
    resendBtn?.addEventListener("click", () => {
      clearAlert();
      clearOtp();
      setOtpError(false, "");

      const updated = { ...draft, otpSentAtMs: Date.now() };
      setDraft(updated);

      cleanupTimer();
      cleanupTimer = initTimer(updated);
      showAlert("success", "تم إعادة إرسال الرمز بنجاح.");
    });

    const form = $("verifyForm");
    form?.addEventListener("submit", (e) => {
      e.preventDefault();
      clearAlert();

      const otp = getOtpValue();
      if (!/^\d{6}$/.test(otp)) {
        setOtpError(true, "أدخل رمزًا صحيحًا مكونًا من 6 أرقام.");
        showAlert("error", "الرمز غير مكتمل.");
        return;
      }

      setLoading(true);
      window.setTimeout(() => {
        setLoading(false);
        if (otp !== OTP_OK) {
          setOtpError(true, "رمز التحقق غير صحيح. حاول مرة أخرى.");
          showAlert("error", "رمز التحقق غير صحيح.");
          return;
        }

        setOtpError(false, "");
        const updated = { ...draft, verified: true, verifiedAt: new Date().toISOString() };
        setDraft(updated);
        window.location.href = "success.html";
      }, 650);
    });
  };

  document.addEventListener("DOMContentLoaded", init);
})();
