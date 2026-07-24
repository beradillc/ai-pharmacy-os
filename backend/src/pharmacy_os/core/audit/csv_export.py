"""Shaping an audit entry into CSV cells — framework-free and pure.

Kept apart from the query service so the column contract has one home and can be
unit-tested without a database or an HTTP layer. The interface layer feeds these
rows to :mod:`csv` for quoting/escaping; this module only decides *which* fields
appear and *how* each is stringified.

``context`` is emitted as a single JSON column rather than exploded into one column
per key: audit rows carry heterogeneous metadata (a failed login has ``email``, a
sale has ``branch_id``), so a fixed wide schema would be mostly empty and a dynamic
one would make the header depend on the page. One JSON cell keeps the file's shape
stable and loss-free.
"""

from __future__ import annotations

import json

from pharmacy_os.core.audit.entry import AuditEntry

#: Column order for the exported file. Stable: downstream spreadsheets/parsers key
#: on it, so append new columns at the end rather than reordering.
CSV_HEADER: tuple[str, ...] = (
    "id",
    "occurred_at",
    "actor_user_id",
    "action",
    "target_type",
    "target_id",
    "context",
)


def entry_to_row(entry: AuditEntry) -> list[str]:
    """One audit fact as a list of string cells, aligned to :data:`CSV_HEADER`.

    ``None`` becomes an empty cell (not the literal ``"None"``); timestamps are
    ISO 8601 in the UTC they were stored as; ``context`` is compact JSON with sorted
    keys so two exports of the same row are byte-identical.
    """
    return [
        str(entry.id),
        entry.occurred_at.isoformat(),
        str(entry.actor_user_id) if entry.actor_user_id is not None else "",
        entry.action.value,
        entry.target_type,
        entry.target_id if entry.target_id is not None else "",
        json.dumps(entry.context, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    ]
