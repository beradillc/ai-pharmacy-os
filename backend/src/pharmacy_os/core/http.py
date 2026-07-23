"""Small adapters between the HTTP framework and the kernel.

Lives in ``core`` so both the ``api`` layer and a module's interface layer can use
it: putting it in ``api`` would force modules to import upwards, which the
``layers`` contract forbids (and did catch).
"""

from __future__ import annotations

from fastapi import Request


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
