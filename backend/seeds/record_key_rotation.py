"""Ghi vết kiểm toán cho một lần xoay khoá mã hoá at-rest (D-SEC-01).

**Vì sao phải có lệnh riêng.** Xoay khoá là thao tác **vận hành**, không phải một
request: người vận hành thêm khoá mới vào ``ENCRYPTION__KEYS`` rồi trỏ
``ENCRYPTION__CURRENT_VERSION`` sang nó. Không có endpoint nào để móc audit vào, nên nếu
không có lệnh này thì D-SEC-01 (*"rotation phải có audit trail"*) **không có gì thực
hiện** — và `docs/18` §B.6 đã ghi đúng điều đó là nợ.

**Vì sao nó không phải một cuốn sổ tay.** Lệnh **đọc cấu hình đang chạy** và từ chối ghi
nếu việc xoay chưa thực sự xảy ra:

* ``--to-version`` phải **đúng bằng** ``current_version`` hiện tại — không cho ghi trước
  một lần xoay chưa làm;
* cả ``--from-version`` lẫn ``--to-version`` phải **có mặt trong keyring** — khoá cũ bị
  xoá khỏi cấu hình trong khi vẫn còn dòng mang thẻ đó là sự cố, không phải chuyện để
  ghi nhận rồi đi tiếp;
* hai phiên bản phải **khác nhau**.

Một dòng audit khẳng định điều gì đó *không* kiểm chứng được thì tệ hơn không có dòng
nào: nó biến một câu hỏi mở thành một câu trả lời sai có dấu.

Cách chạy (từ ``backend/``, venv đã kích hoạt, ``ENCRYPTION__*`` đã trỏ sang khoá mới)::

    python -m seeds.record_key_rotation \\
        --from-version 1 --to-version 2 \\
        --operator-email admin@nhathuoc.vn \\
        --reason "Xoay định kỳ 90 ngày (D-SEC-01)"

Chạy **ngay sau** khi khởi động lại ứng dụng với khoá mới, **trước** khi chạy
``encrypt_backfill`` để mã hoá lại dữ liệu cũ.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

import structlog
from sqlalchemy import select

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import build_engine, build_sessionmaker
from pharmacy_os.modules.iam.infrastructure.models import UserORM

_log = structlog.get_logger("record_key_rotation")


class RotationNotProven(Exception):
    """Cấu hình đang chạy không xác nhận được lần xoay đang muốn ghi."""


def _check_against_live_config(from_version: int, to_version: int) -> None:
    settings = get_settings()
    enc = settings.encryption

    if from_version == to_version:
        raise RotationNotProven(
            f"--from-version và --to-version cùng là {to_version}: không có lần xoay nào ở đây"
        )
    if enc.current_version != to_version:
        raise RotationNotProven(
            f"ENCRYPTION__CURRENT_VERSION đang là {enc.current_version}, không phải "
            f"{to_version}. Xoay khoá TRƯỚC rồi mới ghi vết — lệnh này ghi nhận việc đã "
            f"xảy ra, không phải việc định làm."
        )
    missing = [v for v in (from_version, to_version) if v not in enc.keys]
    if missing:
        raise RotationNotProven(
            f"Thiếu khoá phiên bản {missing} trong ENCRYPTION__KEYS. Khoá cũ phải còn "
            f"trong cấu hình chừng nào còn dòng mang thẻ đó — xoá sớm là mất dữ liệu, "
            f"không phải dọn dẹp."
        )


async def _run(*, from_version: int, to_version: int, operator_email: str, reason: str) -> int:
    _check_against_live_config(from_version, to_version)

    settings = get_settings()
    engine = build_engine(settings.db.url)
    session_factory = build_sessionmaker(engine)
    try:
        async with session_factory() as session:
            row = (
                await session.execute(select(UserORM).where(UserORM.email == operator_email))
            ).scalar_one_or_none()
            if row is None:
                raise RotationNotProven(
                    f"Không tìm thấy người dùng {operator_email!r}. Vết kiểm toán phải gắn "
                    f"vào một người có thật, không phải một chuỗi tự do."
                )
            tenant_id: UUID = row.tenant_id
            actor_id: UUID = row.id

        await AuditLogger(session_factory).record(
            AuditEntry(
                actor_user_id=actor_id,
                tenant_id=tenant_id,
                action=AuditAction.ENCRYPTION_KEY_ROTATED,
                target_type="encryption_key",
                target_id=f"v{to_version}",
            ).with_context(
                from_version=f"v{from_version}",
                to_version=f"v{to_version}",
                reason=reason,
                # Ghi luôn số khoá còn sống: đây là con số trả lời được câu "còn bao
                # nhiêu phiên bản đang chồng lấn" mà D-SEC-01 giới hạn ở 7 ngày.
                keys_in_ring=str(len(settings.encryption.keys)),
            )
        )
    finally:
        await engine.dispose()

    _log.info(
        "key_rotation_recorded",
        from_version=from_version,
        to_version=to_version,
        operator=operator_email,
    )
    print(  # noqa: T201
        f"✅ Đã ghi vết xoay khoá v{from_version} → v{to_version} "
        f"(người thực hiện: {operator_email}).\n"
        f"   Keyring đang giữ {len(settings.encryption.keys)} phiên bản. "
        f"D-SEC-01 giới hạn chồng lấn tối đa 7 ngày — chạy "
        f"`python -m seeds.encrypt_backfill` để mã hoá lại dữ liệu cũ, rồi `--verify`."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ghi vết kiểm toán cho một lần xoay khoá mã hoá at-rest (D-SEC-01)."
    )
    parser.add_argument("--from-version", type=int, required=True)
    parser.add_argument("--to-version", type=int, required=True)
    parser.add_argument(
        "--operator-email", required=True, help="Người thực hiện — phải tồn tại trong CSDL"
    )
    parser.add_argument("--reason", required=True, help='VD: "Xoay định kỳ 90 ngày (D-SEC-01)"')
    args = parser.parse_args(argv)
    try:
        return asyncio.run(
            _run(
                from_version=args.from_version,
                to_version=args.to_version,
                operator_email=args.operator_email,
                reason=args.reason,
            )
        )
    except RotationNotProven as exc:
        print(f"🔴 Từ chối ghi vết: {exc}", file=sys.stderr)  # noqa: T201
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
