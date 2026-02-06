from django.contrib import admin

from .models import EmailLog, TenantEmailSettings


@admin.register(TenantEmailSettings)
class TenantEmailSettingsAdmin(admin.ModelAdmin):
    list_display = ("tenant", "provider", "from_email", "is_enabled", "updated_at")
    list_filter = ("provider", "is_enabled")
    search_fields = ("tenant__slug", "tenant__name", "from_email")
    ordering = ("tenant_id",)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "to_email", "template_key", "status", "provider", "created_at", "sent_at")
    list_filter = ("status", "provider", "template_key")
    search_fields = ("tenant__slug", "to_email", "subject", "idempotency_key", "provider_message_id")
    ordering = ("-created_at",)
