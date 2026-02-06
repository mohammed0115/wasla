from __future__ import annotations


class StoreDomainError(ValueError):
    pass


class StoreValidationError(StoreDomainError):
    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.field = field


class StoreNameInvalidError(StoreDomainError):
    pass


class StoreSlugReservedError(StoreDomainError):
    pass


class StoreSlugInvalidError(StoreDomainError):
    pass


class StoreSlugAlreadyTakenError(StoreDomainError):
    pass


class StoreAlreadyOwnedByUserError(StoreDomainError):
    pass


class StoreAccessDeniedError(StoreDomainError):
    pass


class StoreInactiveError(StoreDomainError):
    pass


class StoreNotReadyError(StoreDomainError):
    def __init__(self, message: str = "Store is not ready.", *, reasons: list[str] | None = None):
        super().__init__(message)
        self.reasons = reasons or []
