import json

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied

from .models import EmailLog, TenantEmailSettings
from apps.emails.application.services.crypto import CredentialCrypto


class TenantEmailSettingsAdminForm(forms.ModelForm):
    credentials_json = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "spellcheck": "false"}),
        help_text="JSON credentials stored encrypted. Examples: "
        "SMTP {host,port,username,password,use_tls,use_ssl}. "
        "SendGrid {api_key}. Mailgun {api_key,domain,base_url}.",
        label="Credentials (JSON)",
    )

    class Meta:
        model = TenantEmailSettings
        fields = ("tenant", "provider", "from_email", "from_name", "is_enabled", "credentials_json")

    def clean_credentials_json(self):
        raw = (self.cleaned_data.get("credentials_json") or "").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception as exc:
            raise forms.ValidationError("Invalid JSON.") from exc
        if not isinstance(data, dict):
            raise forms.ValidationError("Credentials JSON must be an object.")
        return data


@admin.register(TenantEmailSettings)
class TenantEmailSettingsAdmin(admin.ModelAdmin):
    form = TenantEmailSettingsAdminForm
    list_display = ("tenant", "provider", "from_email", "is_enabled", "updated_at")
    list_filter = ("provider", "is_enabled")
    search_fields = ("tenant__slug", "tenant__name", "from_email")
    ordering = ("tenant_id",)

    def has_module_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_superuser)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            try:
                creds = CredentialCrypto.decrypt_json(obj.credentials_encrypted)
            except Exception:
                creds = {}
            form.base_fields["credentials_json"].initial = json.dumps(creds, indent=2, ensure_ascii=False)
        return form

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied
        creds = form.cleaned_data.get("credentials_json") or {}
        obj.credentials_encrypted = CredentialCrypto.encrypt_json(creds) if creds else ""
        super().save_model(request, obj, form, change)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "to_email", "template_key", "status", "provider", "created_at", "sent_at")
    list_filter = ("status", "provider", "template_key")
    search_fields = ("tenant__slug", "to_email", "subject", "idempotency_key", "provider_message_id")
    ordering = ("-created_at",)
