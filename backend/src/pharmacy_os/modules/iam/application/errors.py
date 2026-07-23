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
