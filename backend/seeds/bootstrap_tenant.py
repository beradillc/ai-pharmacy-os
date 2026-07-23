"""Stand up a new tenant: its first branch, the system roles and an admin account.

Why a CLI and not an HTTP endpoint (docs/15 §5 Q2, duyệt 2026-07-23): whoever runs
this already holds the database credentials, so it adds no attack surface. A
"first-run" endpoint would be a public path to admin rights whose only guard is a
condition that goes wrong exactly when it matters (an emptied database), and a
password seeded from a migration would live in version control and be identical on
every deployment.

Usage (from ``backend/`` with the venv active and the DB migrated)::

    BOOTSTRAP_ADMIN_PASSWORD='...' python -m seeds.bootstrap_tenant \\
        --tenant-name "Nhà thuốc ABC" \\
        --branch-code HQ --branch-name "Chi nhánh chính" \\
        --admin-email admin@abc.vn --admin-full-name "Nguyễn Văn A"

Omit the environment variable to be prompted (input hidden). There is no default
password and never will be.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

import structlog

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.errors import AppError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.interface import build_repositories

_log = structlog.get_logger("bootstrap")

_PASSWORD_ENV = "BOOTSTRAP_ADMIN_PASSWORD"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a tenant with its first admin user.")
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--branch-code", required=True, help="e.g. HQ, CN01")
    parser.add_argument("--branch-name", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-full-name", required=True)
    return parser.parse_args(argv)


def _read_password() -> str:
    password = os.environ.get(_PASSWORD_ENV)
    if password:
        return password
    first = getpass.getpass("Mật khẩu admin: ")
    if first != getpass.getpass("Nhập lại mật khẩu: "):
        raise SystemExit("Hai lần nhập mật khẩu không khớp")
    return first


async def _run(args: argparse.Namespace, password: str) -> None:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    event_bus = InMemoryEventBus()

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    service = IamService(uow_factory, build_repositories, AuditLogger(session_factory))
    try:
        out = await service.bootstrap_tenant(
            BootstrapTenantInput(
                tenant_name=args.tenant_name,
                branch_code=args.branch_code,
                branch_name=args.branch_name,
                admin_email=args.admin_email,
                admin_full_name=args.admin_full_name,
                admin_password=password,
            )
        )
    finally:
        await engine.dispose()

    _log.info(
        "bootstrap_complete",
        tenant_id=str(out.tenant_id),
        branch_id=str(out.branch_id),
        admin_user_id=str(out.admin_user_id),
        system_roles_created=out.roles_created,
    )
    print(  # noqa: T201 - operator-facing summary, not application logging
        f"Tenant {out.tenant_id} · chi nhánh {out.branch_id} · admin {out.admin_user_id}\n"
        f"Vai trò hệ thống tạo mới: {out.roles_created}\n"
        "Admin phải đổi mật khẩu ở lần đăng nhập đầu."
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        asyncio.run(_run(args, _read_password()))
    except AppError as exc:
        # Duplicate email, weak password, ... — an operator error, not a crash.
        print(f"Lỗi: {exc.detail}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
