from __future__ import annotations


class AccountDomainError(ValueError):
    pass


class AccountValidationError(AccountDomainError):
    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.field = field


class FullNameInvalidError(AccountValidationError):
    pass


class PhoneInvalidError(AccountValidationError):
    pass


class EmailInvalidError(AccountValidationError):
    pass


class TermsNotAcceptedError(AccountValidationError):
    pass


class AccountAlreadyExistsError(AccountDomainError):
    def __init__(self, message: str = "Account already exists.", *, field: str | None = None):
        super().__init__(message)
        self.field = field


class InvalidCredentialsError(AccountDomainError):
    pass


class AccountNotFoundError(AccountDomainError):
    pass
