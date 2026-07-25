"""Break-glass: clear a user's two-factor configuration from the server.

**Why this exists.** ``POST /users/{id}/2fa/reset`` covers the ordinary case — an
administrator helps a member of staff who lost their phone. It cannot cover the case
that actually locks a pharmacy out: the deployment has a **single** ``system_admin``
(the normal shape for a small pharmacy) and that person loses both their authenticator
and their printed backup codes. Nobody can reset them, including themselves, and
``system_admin`` is the only role holding ``iam.user.write``. Without this command,
switching enforcement on would risk locking the pharmacy out of its own system
permanently — the one outcome the 2FA design was explicitly required to avoid
(PROJECT_STATE §7bb).

**Why a CLI is not a new hole.** Whoever can run this already holds the database
credentials, and therefore already has total control of the deployment: the command
adds no privilege that its operator did not already possess. That is the same argument
``seeds.bootstrap_tenant`` records for creating the first admin (docs/15 §5 Q2), and
the reason there is deliberately no HTTP equivalent.

The reset is logged to ``audit_logs`` like any other 2FA transition, attributed to the
user themselves — no administrator was involved, and inventing one would put a false
actor in a legal record.

Usage (from ``backend/`` with the venv active)::

    python -m seeds.reset_two_factor --email admin@abc.vn

Add ``--yes`` to skip the confirmation prompt (for a scripted recovery).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.iam.interface import build_repositories

_log = structlog.get_logger("reset_two_factor")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Xoá cấu hình 2FA của một người dùng (khôi phục khi mất thiết bị)."
    )
    parser.add_argument("--email", required=True, help="Email của người dùng cần khôi phục")
    parser.add_argument(
        "--yes", action="store_true", help="Bỏ qua bước xác nhận (dùng cho kịch bản tự động)"
    )
    return parser.parse_args(argv)


async def _run(email: str, *, assume_yes: bool) -> int:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    event_bus = InMemoryEventBus()

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    audit = AuditLogger(session_factory)
    try:
        async with uow_factory() as uow:
            repos = build_repositories(uow)
            user = await repos.users.find_by_email(email)
            if user is None:
                print(f"Không tìm thấy người dùng '{email}'", file=sys.stderr)  # noqa: T201
                return 1

            config = await repos.two_factor.find_for_user(user.id)
            if config is None:
                # Not an error: the goal state is "this user has no second factor".
                print(f"'{email}' vốn chưa bật 2FA — không có gì để xoá.")  # noqa: T201
                return 0

            if not assume_yes:
                print(  # noqa: T201
                    f"Sắp XOÁ 2FA của '{email}' (trạng thái: {config.status.value}).\n"
                    "Người này sẽ đăng nhập chỉ bằng mật khẩu cho tới khi đăng ký lại."
                )
                if input("Gõ 'xoa' để xác nhận: ").strip().lower() != "xoa":
                    print("Đã huỷ.")  # noqa: T201
                    return 1

            await repos.two_factor.delete_for_user(user.id)
            await uow.commit()

        await audit.record(
            AuditEntry(
                actor_user_id=user.id,
                tenant_id=user.tenant_id,
                action=AuditAction.TWO_FACTOR_RESET,
                target_type="user",
                target_id=str(user.id),
            ).with_context(via="cli_break_glass")
        )
    finally:
        await engine.dispose()

    _log.info("two_factor_reset_via_cli", user_id=str(user.id), email=email)
    print(  # noqa: T201
        f"Đã xoá 2FA của '{email}'. Người này nên đăng ký lại ngay sau khi đăng nhập được."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args.email, assume_yes=args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
