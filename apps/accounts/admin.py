from django.contrib import admin

from .models import AccountAuditLog, AccountProfile


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone", "full_name", "country", "accepted_terms_at", "created_at")
    search_fields = ("phone", "full_name", "user__username", "user__email")
    list_select_related = ("user",)


@admin.register(AccountAuditLog)
class AccountAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "user", "ip_address", "created_at")
    search_fields = ("action", "user__username", "user__email", "ip_address")
    list_filter = ("action",)
    list_select_related = ("user",)
