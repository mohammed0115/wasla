from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser

from apps.tenants.application.policies.ownership import EnsureTenantOwnershipPolicy
from apps.tenants.domain.policies import validate_custom_domain
from apps.tenants.models import Tenant


@dataclass(frozen=True)
class ValidateCustomDomainCommand:
    user: AbstractBaseUser
    tenant: Tenant
    custom_domain: str


@dataclass(frozen=True)
class ValidateCustomDomainResult:
    normalized_domain: str
    is_conflict: bool


class ValidateCustomDomainUseCase:
    @staticmethod
    def execute(cmd: ValidateCustomDomainCommand) -> ValidateCustomDomainResult:
        EnsureTenantOwnershipPolicy.ensure_is_owner(user=cmd.user, tenant=cmd.tenant)

        normalized = validate_custom_domain(cmd.custom_domain)
        if not normalized:
            return ValidateCustomDomainResult(normalized_domain="", is_conflict=False)

        conflict = (
            Tenant.objects.filter(domain=normalized)
            .exclude(id=cmd.tenant.id)
            .exists()
        )
        return ValidateCustomDomainResult(normalized_domain=normalized, is_conflict=conflict)

