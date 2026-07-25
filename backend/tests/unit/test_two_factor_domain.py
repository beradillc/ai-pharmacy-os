"""2FA domain rules + the TOTP/backup-code primitives (Sprint 8).

The properties worth pinning here are the ones that make 2FA actually worth having:
a code cannot be replayed, a challenge cannot be brute-forced or reused, and a
pending enrolment has no effect on login.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pyotp
import pytest

from pharmacy_os.core.security.totp import (
    BACKUP_CODE_COUNT,
    TOTP_DIGITS,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    normalize_backup_code,
    timestep_at,
    totp_provisioning_uri,
    verify_totp,
)
from pharmacy_os.modules.iam.domain import (
    MAX_CHALLENGE_ATTEMPTS,
    SYSTEM_ROLES_BY_CODE,
    TWO_FACTOR_PERMISSIONS,
    BackupCode,
    TwoFactorChallenge,
    TwoFactorCodeReusedError,
    TwoFactorNotPendingError,
    TwoFactorStatus,
    UserTwoFactor,
    requires_two_factor,
)

_NOW = datetime(2026, 7, 25, 10, 0, tzinfo=UTC)


def _config(**kw: object) -> UserTwoFactor:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "tenant_id": uuid4(),
        "secret": generate_totp_secret(),
    }
    defaults.update(kw)
    return UserTwoFactor(**defaults)  # type: ignore[arg-type]


# --- scope rule ------------------------------------------------------------


def test_the_three_signing_roles_are_exactly_the_roles_in_scope() -> None:
    """The scope rule must resolve to the roles holding ``compliance.ledger.sign``."""
    in_scope = {
        code for code, spec in SYSTEM_ROLES_BY_CODE.items() if requires_two_factor(spec.permissions)
    }
    assert in_scope == {"system_admin", "chain_pharmacist", "branch_pharmacist"}


def test_counter_and_warehouse_staff_are_out_of_scope() -> None:
    for code in ("cashier", "warehouse"):
        assert not requires_two_factor(SYSTEM_ROLES_BY_CODE[code].permissions)


def test_role_editing_permissions_are_in_scope_because_they_can_grant_signing() -> None:
    assert requires_two_factor(frozenset({"iam.role.write"}))
    assert requires_two_factor(frozenset({"iam.role.assign"}))
    assert "compliance.ledger.sign" in TWO_FACTOR_PERMISSIONS


def test_an_actor_with_no_sensitive_permission_is_out_of_scope() -> None:
    assert not requires_two_factor(frozenset({"sales.create", "catalog.read"}))
    assert not requires_two_factor(frozenset())


# --- enrolment lifecycle ---------------------------------------------------


def test_a_fresh_configuration_is_pending_and_therefore_not_active() -> None:
    cfg = _config()
    assert cfg.status is TwoFactorStatus.PENDING
    assert not cfg.is_active


def test_activation_requires_pending_and_records_the_proving_step() -> None:
    cfg = _config()
    cfg.activate(_NOW, timestep=100)
    assert cfg.is_active
    assert cfg.confirmed_at == _NOW
    assert cfg.last_used_timestep == 100


def test_activating_twice_is_refused() -> None:
    cfg = _config()
    cfg.activate(_NOW, timestep=100)
    with pytest.raises(TwoFactorNotPendingError):
        cfg.activate(_NOW, timestep=101)


# --- replay protection -----------------------------------------------------


def test_a_code_from_an_already_spent_step_is_refused() -> None:
    cfg = _config()
    cfg.activate(_NOW, timestep=100)
    with pytest.raises(TwoFactorCodeReusedError):
        cfg.register_use(100)


def test_an_older_step_is_refused_too() -> None:
    cfg = _config()
    cfg.activate(_NOW, timestep=100)
    with pytest.raises(TwoFactorCodeReusedError):
        cfg.register_use(99)


def test_the_next_step_is_accepted_and_advances_the_watermark() -> None:
    cfg = _config()
    cfg.activate(_NOW, timestep=100)
    cfg.register_use(101)
    assert cfg.last_used_timestep == 101


# --- backup codes ----------------------------------------------------------


def test_backup_codes_are_distinct_and_hash_stably_regardless_of_formatting() -> None:
    codes = generate_backup_codes()
    assert len(codes) == BACKUP_CODE_COUNT
    assert len(set(codes)) == BACKUP_CODE_COUNT

    code = codes[0]
    assert hash_backup_code(code) == hash_backup_code(code.lower().replace("-", ""))
    assert hash_backup_code(code) != code
    assert normalize_backup_code(" ab-cd ") == "ABCD"


def test_a_used_backup_code_is_marked_not_deleted() -> None:
    entry = BackupCode(two_factor_id=uuid4(), code_hash=hash_backup_code("AAAA-BBBB"))
    assert not entry.is_used
    entry.use(_NOW)
    assert entry.is_used
    assert entry.used_at == _NOW


# --- login challenge -------------------------------------------------------


def _challenge(**kw: object) -> TwoFactorChallenge:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "tenant_id": uuid4(),
        "token_hash": "x" * 64,
        "expires_at": _NOW + timedelta(minutes=5),
    }
    defaults.update(kw)
    return TwoFactorChallenge(**defaults)  # type: ignore[arg-type]


def test_a_fresh_challenge_is_usable_and_expires() -> None:
    ch = _challenge()
    assert ch.is_usable(_NOW)
    assert not ch.is_usable(_NOW + timedelta(minutes=6))


def test_a_consumed_challenge_cannot_be_used_again() -> None:
    ch = _challenge()
    ch.consume(_NOW)
    assert ch.is_consumed
    assert not ch.is_usable(_NOW)


def test_a_challenge_is_exhausted_after_the_attempt_cap() -> None:
    ch = _challenge()
    for _ in range(MAX_CHALLENGE_ATTEMPTS - 1):
        assert not ch.register_failure()
    assert ch.register_failure()
    assert ch.attempts == MAX_CHALLENGE_ATTEMPTS


# --- TOTP primitive --------------------------------------------------------


def test_a_generated_code_verifies_and_returns_its_time_step() -> None:
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).at(_NOW)
    assert verify_totp(secret, code, at=_NOW) == timestep_at(_NOW)


def test_clock_drift_of_one_step_either_way_is_tolerated() -> None:
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).at(_NOW)
    assert verify_totp(secret, code, at=_NOW + timedelta(seconds=30)) is not None
    assert verify_totp(secret, code, at=_NOW - timedelta(seconds=30)) is not None


def test_a_code_two_steps_away_is_rejected() -> None:
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).at(_NOW)
    assert verify_totp(secret, code, at=_NOW + timedelta(seconds=90)) is None


def test_malformed_codes_are_rejected_without_raising() -> None:
    secret = generate_totp_secret()
    for bad in ("", "abcdef", "12345", "1234567", "12 34 5a"):
        assert verify_totp(secret, bad, at=_NOW) is None


def test_a_corrupt_secret_rejects_rather_than_crashing() -> None:
    assert verify_totp("not-valid-base32!!", "123456", at=_NOW) is None


def test_a_code_for_a_different_secret_is_rejected() -> None:
    code = pyotp.TOTP(generate_totp_secret()).at(_NOW)
    assert verify_totp(generate_totp_secret(), code, at=_NOW) is None


def test_the_provisioning_uri_carries_the_secret_and_issuer() -> None:
    secret = generate_totp_secret()
    uri = totp_provisioning_uri(secret, account_name="ds@nhathuoc.vn", issuer="AI Pharmacy OS")
    assert uri.startswith("otpauth://totp/")
    assert secret in uri
    assert "issuer=AI%20Pharmacy%20OS" in uri


def test_a_code_built_from_the_provisioning_uri_verifies() -> None:
    """End-to-end of what a real authenticator app does with the QR payload."""
    secret = generate_totp_secret()
    uri = totp_provisioning_uri(secret, account_name="ds@nhathuoc.vn", issuer="AI Pharmacy OS")
    scanned = pyotp.parse_uri(uri)
    assert verify_totp(secret, scanned.at(_NOW), at=_NOW) == timestep_at(_NOW)
    assert scanned.digits == TOTP_DIGITS
