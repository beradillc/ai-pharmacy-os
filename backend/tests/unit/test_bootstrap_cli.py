"""Argument and password handling of ``seeds.bootstrap_tenant``.

The bootstrap use-case itself is covered against a real database in
``tests/integration/test_iam_flow.py``; what matters here is that the CLI never
invents a password.
"""

from __future__ import annotations

import pytest
from seeds.bootstrap_tenant import _PASSWORD_ENV, _parse_args, _read_password

_ARGV = [
    "--tenant-name",
    "Nhà thuốc ABC",
    "--branch-code",
    "HQ",
    "--branch-name",
    "Chi nhánh chính",
    "--admin-email",
    "admin@abc.vn",
    "--admin-full-name",
    "Nguyễn Văn A",
]


def test_all_arguments_are_required() -> None:
    for drop in range(0, len(_ARGV), 2):
        partial = _ARGV[:drop] + _ARGV[drop + 2 :]
        with pytest.raises(SystemExit):
            _parse_args(partial)


def test_arguments_are_parsed() -> None:
    args = _parse_args(_ARGV)
    assert args.tenant_name == "Nhà thuốc ABC"
    assert args.branch_code == "HQ"
    assert args.admin_email == "admin@abc.vn"


def test_password_comes_from_the_environment_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_PASSWORD_ENV, "MatKhauAdmin2026")
    assert _read_password() == "MatKhauAdmin2026"


def test_password_is_prompted_twice_when_the_environment_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(_PASSWORD_ENV, raising=False)
    prompts = iter(["MatKhauAdmin2026", "MatKhauAdmin2026"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(prompts))
    assert _read_password() == "MatKhauAdmin2026"


def test_mismatched_prompts_abort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_PASSWORD_ENV, raising=False)
    prompts = iter(["MatKhauAdmin2026", "GoNhamRoi2026"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(prompts))
    with pytest.raises(SystemExit):
        _read_password()
