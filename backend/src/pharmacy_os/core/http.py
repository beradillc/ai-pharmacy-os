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
