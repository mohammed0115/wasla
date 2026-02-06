from django.contrib import admin

from .models import (
    StorePaymentSettings,
    StoreProfile,
    StoreShippingSettings,
    Tenant,
    TenantAuditLog,
    TenantMembership,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "slug",
        "name",
        "is_active",
        "is_published",
        "currency",
        "language",
        "setup_completed",
        "setup_step",
        "activated_at",
        "deactivated_at",
    )
    list_filter = ("is_active", "currency", "language")
    search_fields = ("slug", "name", "domain", "subdomain")
    ordering = ("id",)
    exclude = ("setup_step", "setup_completed", "setup_completed_at")


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("tenant__slug", "tenant__name", "user__username", "user__email")
    ordering = ("-id",)


@admin.register(StoreProfile)
class StoreProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "owner",
        "store_info_completed",
        "setup_step",
        "is_setup_complete",
        "created_at",
    )
    list_filter = ("store_info_completed", "setup_step", "is_setup_complete")
    search_fields = ("tenant__slug", "tenant__name", "owner__username", "owner__email")
    ordering = ("-id",)


@admin.register(StorePaymentSettings)
class StorePaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "mode", "provider_name", "is_enabled", "updated_at")
    list_filter = ("mode", "is_enabled")
    search_fields = ("tenant__slug", "tenant__name", "provider_name")
    ordering = ("-id",)


@admin.register(StoreShippingSettings)
class StoreShippingSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "fulfillment_mode", "origin_city", "is_enabled", "updated_at")
    list_filter = ("fulfillment_mode", "is_enabled")
    search_fields = ("tenant__slug", "tenant__name", "origin_city")
    ordering = ("-id",)


@admin.register(TenantAuditLog)
class TenantAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("tenant__slug", "actor", "details")
    ordering = ("-created_at",)
