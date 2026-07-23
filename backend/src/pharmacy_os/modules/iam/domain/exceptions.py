"""IAM domain exceptions (pure — no framework)."""

from __future__ import annotations


class IamError(Exception):
    """Base for iam domain rule violations."""


class InvalidUserError(IamError):
    """Raised when a :class:`User` is malformed."""


class InvalidRoleError(IamError):
    """Raised when a :class:`Role` is malformed."""


class InvalidTenantError(IamError):
    """Raised when a :class:`Tenant` or :class:`Branch` is malformed."""


class WeakPasswordError(IamError):
    """Raised when a plaintext password fails the strength policy."""


class InvalidCredentialsError(IamError):
    """Raised on a wrong email/password pair.

    Deliberately identical for "no such user" and "wrong password" so the API
    cannot be used to enumerate registered accounts.
    """


class UserLockedError(IamError):
    """Raised when the account is temporarily locked after failed attempts."""


class UserInactiveError(IamError):
    """Raised when a deactivated user tries to authenticate."""


class BranchNotAccessibleError(IamError):
    """Raised when the actor holds no role applying to the requested branch."""


class BranchRequiredError(IamError):
    """Raised when a login could reach several branches and named none."""


class RefreshTokenInvalidError(IamError):
    """Raised when a refresh token is unknown, expired or already rotated."""


class RefreshTokenReusedError(IamError):
    """Raised when an already-revoked refresh token is presented again.

    Signals probable token theft: the caller replayed a token the legitimate
    client had already exchanged. The application layer answers by revoking every
    session of that user, not just this one.
    """
