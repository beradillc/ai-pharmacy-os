"""``GET /privacy/processing-record`` — the technical half of a tenant's DPIA.

Kernel infrastructure like ``health`` and ``audit``: it describes personal-data
processing across the deployment, which is nobody's business module in particular.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pharmacy_os.api.deps import get_context
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.privacy import DataCategory, ProcessingRecord, processing_record
from pharmacy_os.core.security import require_permission

DPIA_READ = "privacy.dpia.read"


class DataCategoryResponse(BaseModel):
    name: str
    examples: list[str]
    sensitive: bool
    legal_basis: str
    purposes: list[str]
    guarded_by: list[str]
    retention: str

    @classmethod
    def of(cls, category: DataCategory) -> DataCategoryResponse:
        return cls(
            name=category.name,
            examples=category.examples,
            sensitive=category.sensitive,
            legal_basis=category.legal_basis,
            purposes=category.purposes,
            guarded_by=category.guarded_by,
            retention=category.retention,
        )


class ProcessingRecordResponse(BaseModel):
    categories: list[DataCategoryResponse]
    audited_actions: list[str]
    audit_storage: str
    cross_border_transfers: list[str]
    subject_rights: dict[str, str]
    known_gaps: list[str]

    @classmethod
    def of(cls, record: ProcessingRecord) -> ProcessingRecordResponse:
        return cls(
            categories=[DataCategoryResponse.of(c) for c in record.categories],
            audited_actions=record.audited_actions,
            audit_storage=record.audit_storage,
            cross_border_transfers=record.cross_border_transfers,
            subject_rights=record.subject_rights,
            known_gaps=record.known_gaps,
        )


router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/processing-record", response_model=ProcessingRecordResponse)
async def get_processing_record(
    ctx: RequestContext = Depends(get_context),
) -> ProcessingRecordResponse:
    """What personal data this deployment processes, on what basis, guarded by what.

    Feeds the tenant's own đánh giá tác động xử lý DLCN (Luật 91/2025 Điều 21 · NĐ356
    Điều 19), which every tenant owes once health data is involved — the small-business
    exemption does not apply to sensitive data (NĐ356 Điều 41.2). Requires
    ``privacy.dpia.read``.

    ``known_gaps`` is part of the response on purpose. A processing record that lists
    only what works would be a worse document to hand a regulator than one that says
    plainly what is still missing.
    """
    require_permission(ctx, DPIA_READ)
    return ProcessingRecordResponse.of(processing_record())
