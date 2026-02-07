from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError

from .models import EmailLog, GlobalEmailSettings, GlobalEmailSettingsAuditLog, TenantEmailSettings
from apps.emails.application.services.crypto import CredentialCrypto


class GlobalEmailSettingsAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave empty to keep existing password/token.",
        label="Password / API Token",
    )

    class Meta:
        model = GlobalEmailSettings
        fields = ("provider", "host", "port", "username", "password", "from_email", "use_tls", "enabled")


@admin.register(TenantEmailSettings)
class TenantEmailSettingsAdmin(admin.ModelAdmin):
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

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied
        super().save_model(request, obj, form, change)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "to_email", "template_key", "status", "provider", "created_at", "sent_at")
    list_filter = ("status", "provider", "template_key")
    search_fields = ("tenant__slug", "to_email", "subject", "idempotency_key", "provider_message_id")
    ordering = ("-created_at",)


@admin.register(GlobalEmailSettings)
class GlobalEmailSettingsAdmin(admin.ModelAdmin):
    form = GlobalEmailSettingsAdminForm
    list_display = ("provider", "from_email", "enabled", "updated_at")
    list_filter = ("provider", "enabled")
    ordering = ("-updated_at",)

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
        return form

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            raise PermissionDenied
        if not obj.pk and GlobalEmailSettings.objects.exists():
            raise ValidationError("Only one GlobalEmailSettings row is allowed.")
        raw_password = form.cleaned_data.get("password") or ""
        if raw_password:
            obj.password_encrypted = CredentialCrypto.encrypt_json({"password": raw_password})
        super().save_model(request, obj, form, change)
        GlobalEmailSettingsAuditLog.objects.create(
            action="updated" if change else "created",
            actor=getattr(request.user, "username", "admin"),
            metadata={"provider": obj.provider},
        )


@admin.register(GlobalEmailSettingsAuditLog)
class GlobalEmailSettingsAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    ordering = ("-created_at",)
