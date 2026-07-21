"""Export mapper: domain ``NationalDrugRecord`` → 23-field QĐ540 Bảng 1 payload.

Applies the converter helpers (docs/13_COMPLIANCE_SPEC.md mục A) at the boundary, exactly
where the spec says they must run — never earlier, keeping the domain's internal ``date``/
``datetime`` types ISO-pure. ``NationalDrugRecordExport`` enforces the size limits from Bảng 1
("Kích thước tối đa" column) since it represents the literal wire contract sent to the
CSDL Dược Quốc gia gateway (docs/13 mục D.3 — currently only a ``MockAdapter``, no real
endpoint wired yet).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from pharmacy_os.modules.compliance.domain import (
    NationalDrugRecord,
    to_qld_code,
    to_qld_date,
    to_qld_datetime,
)


class NationalDrugRecordExport(BaseModel):
    ma_thuoc: str = Field(max_length=50)
    ten_thuoc: str = Field(max_length=50)
    so_dang_ky: str = Field(max_length=20)
    ten_hoat_chat: str = Field(max_length=50)
    nong_do_ham_luong: str = Field(max_length=20)
    nha_san_xuat: str = Field(max_length=100)
    nuoc_san_xuat: str = Field(max_length=20)
    nha_nhap_khau: str = Field(max_length=100)
    quy_cach_dong_goi: str = Field(max_length=20)
    dang_bao_che: str = Field(max_length=20)
    don_vi_dong_goi_nn: str = Field(max_length=20)
    gia_ban_le: Decimal
    so_lo: str = Field(max_length=20)
    han_dung: int
    so_luong_nhap: Decimal
    so_luong_ban: Decimal
    so_luong_ton: Decimal
    don_vi_bthuoc_cho_csbl: str = Field(max_length=100)
    so_hoa_don_mthuoc: str = Field(max_length=20)
    ngay_nhap: int
    ngay_ban: int
    ma_co_so_ban_le: str = Field(max_length=12)
    ma_co_so_ban_buon: str = Field(max_length=12)


def to_national_drug_record_export(record: NationalDrugRecord) -> NationalDrugRecordExport:
    """Đẩy lên CSDL Dược Quốc gia: mã hóa ``ma_thuoc`` và chuyển ngày/giờ theo mục A."""
    return NationalDrugRecordExport(
        ma_thuoc=to_qld_code(record.ma_thuoc),
        ten_thuoc=record.ten_thuoc,
        so_dang_ky=record.so_dang_ky,
        ten_hoat_chat=record.ten_hoat_chat,
        nong_do_ham_luong=record.nong_do_ham_luong,
        nha_san_xuat=record.nha_san_xuat,
        nuoc_san_xuat=record.nuoc_san_xuat,
        nha_nhap_khau=record.nha_nhap_khau,
        quy_cach_dong_goi=record.quy_cach_dong_goi,
        dang_bao_che=record.dang_bao_che,
        don_vi_dong_goi_nn=record.don_vi_dong_goi_nn,
        gia_ban_le=record.gia_ban_le,
        so_lo=record.so_lo,
        han_dung=to_qld_date(record.han_dung),
        so_luong_nhap=record.so_luong_nhap,
        so_luong_ban=record.so_luong_ban,
        so_luong_ton=record.so_luong_ton,
        don_vi_bthuoc_cho_csbl=record.don_vi_bthuoc_cho_csbl,
        so_hoa_don_mthuoc=record.so_hoa_don_mthuoc,
        ngay_nhap=to_qld_datetime(record.ngay_nhap),
        ngay_ban=to_qld_datetime(record.ngay_ban),
        ma_co_so_ban_le=record.ma_co_so_ban_le,
        ma_co_so_ban_buon=record.ma_co_so_ban_buon,
    )
