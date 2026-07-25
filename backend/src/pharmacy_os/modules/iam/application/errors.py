"""HTTP-facing errors specific to iam."""

from __future__ import annotations

from pharmacy_os.core.errors import AppError


class BranchSelectionRequiredError(AppError):
    """The actor may operate in several branches and named none.

    Carries the list of branches as a problem+json extension member so the client
    can render the picker straight from the error, without a second round trip that
    would have to be reachable without a token.
    """

    status_code = 400
    error_type = "https://errors.pharmacy-os/branch-required"
    title = "Cần chọn chi nhánh"


class TwoFactorRequiredError(AppError):
    """The password was correct; the account still owes its second factor.

    Carries ``challenge_token`` as a problem+json extension member, the same technique
    :class:`BranchSelectionRequiredError` uses to hand the client what it needs to
    finish — here, the handle for ``POST /auth/login/2fa``.

    **401, not 200-with-a-body.** The caller has not authenticated yet, and no token
    is issued, so the status has to say so: a client that ignores the body must not
    be able to mistake this for a successful login.
    """

    status_code = 401
    error_type = "https://errors.pharmacy-os/two-factor-required"
    title = "Cần mã xác thực hai lớp"


class TwoFactorEnrollmentRequiredError(AppError):
    """A sensitive action was attempted by an in-scope account with no active 2FA.

    403 rather than 401: the caller *is* authenticated and known — they are simply
    not allowed to perform this particular act until they enrol.
    """

    status_code = 403
    error_type = "https://errors.pharmacy-os/two-factor-enrollment-required"
    title = "Cần đăng ký xác thực hai lớp"
