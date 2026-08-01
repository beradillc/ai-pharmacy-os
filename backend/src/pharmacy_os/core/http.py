"""Small adapters between the HTTP framework and the kernel.

Lives in ``core`` so both the ``api`` layer and a module's interface layer can use
it: putting it in ``api`` would force modules to import upwards, which the
``layers`` contract forbids (and did catch).
"""

from __future__ import annotations

import csv
import io
from collections.abc import AsyncIterator, Sequence

from fastapi import Request


async def csv_stream_body(
    header: Sequence[str], rows: AsyncIterator[Sequence[str]]
) -> AsyncIterator[str]:
    """Header once, then one CSV line per row, using :mod:`csv` for quoting so a
    comma/newline inside a cell cannot break the file. A single reused buffer keeps
    the whole response flat in memory regardless of row count.

    Lives in ``core`` (not a module's interface layer) so every CSV export in the
    project shares one streaming body rather than re-implementing it — first used
    by the audit dashboard (PROJECT_STATE §7al), reused as-is by the Sprint 7
    revenue/stock reports (§7an). Callers build ``rows`` from their own paged
    query; this function only owns the CSV-writer/StreamingResponse glue.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def _drain() -> str:
        line = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return line

    writer.writerow(header)
    yield _drain()
    async for row in rows:
        writer.writerow(row)
        yield _drain()


def client_ip_of(request: Request) -> str | None:
    """Origin of the request, recorded on audit entries and nothing else.

    Reads the socket peer, **not** ``X-Forwarded-For``: that header is
    client-supplied, so trusting it unconditionally would let anyone write whatever
    origin they like into the audit trail — the one place that must not be
    forgeable. Behind a reverse proxy this records the proxy, which is correct but
    not useful; honouring a *trusted-proxy* allowlist is the follow-up, not
    spoofable header parsing today.
    """
    return request.client.host if request.client else None


#: Cắt User-Agent ở 200 ký tự. Không phải để tiết kiệm chỗ (``context`` là JSONB) mà vì
#: chuỗi này **do client gửi** và không có giới hạn nào cả: một client cố tình có thể
#: nhồi hàng megabyte vào mỗi request và sổ audit — thứ **không xoá được** — sẽ nuốt hết.
#: 200 dư cho mọi UA thật (UA dài nhất trong bộ chụp màn hình là 138).
_USER_AGENT_MAX = 200


def user_agent_of(request: Request) -> str | None:
    """Chuỗi ``User-Agent`` của request, ghi vào sổ audit và không dùng vào việc gì khác.

    Trả ``None`` khi không có header hoặc header rỗng, để ``with_context`` bỏ hẳn khoá
    thay vì lưu một chuỗi rỗng — một dòng audit mang ``user_agent=""`` đọc như *"máy
    không khai"*, còn không có khoá đọc đúng như *"không biết"*.

    **Không phân tích, không chuẩn hoá ở đây.** Lưu nguyên chuỗi thô rồi để màn hình tự
    rút ra nhãn dễ đọc: nếu server đoán sẵn *"iPhone"* thì cái đoán sai sẽ nằm vĩnh viễn
    trong một bảng chỉ-ghi-thêm, còn đoán ở màn hình thì sửa lại lúc nào cũng được.
    """
    raw = request.headers.get("User-Agent")
    if not raw:
        return None
    return raw[:_USER_AGENT_MAX]
