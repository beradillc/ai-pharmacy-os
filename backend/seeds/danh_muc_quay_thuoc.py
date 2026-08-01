"""Danh mục thuốc cho **Quầy thuốc 650** — CSDL chạy thử thật (Chain giao 2026-08-01).

Khác `demo_pharmacy` ở đúng một điểm, và điểm đó là lý do tệp này tồn tại: seeder kia dựng
một nhà thuốc **giả** đầy đủ (tồn kho, đơn bán lùi ngày, khách hàng) để đưa khách xem trong
mười phút. Tệp này dựng **chỉ danh mục** cho một quầy thuốc **thật** sắp chạy một tuần ở
xã Thạnh Trị — kho, khách hàng, tồn, đơn hàng đều **trống**, vì chúng sẽ được nhập bằng tay
trong quá trình thử và đó chính là thứ cần thử.

🔴 Trộn hai thứ đó là sai lầm tốn kém nhất có thể xảy ra ở đây: một dòng tồn kho giả nằm
lẫn trong kho thật sẽ được đối chiếu, được báo cáo, và không ai nhớ nó từ đâu ra.

Cách chạy (từ ``backend/``, venv đã kích hoạt, CSDL đã migrate và đã bootstrap tenant)::

    DB__URL='postgresql+asyncpg://…/qt650' python -m seeds.danh_muc_quay_thuoc \\
        --tenant-id <uuid> --branch-id <uuid> --user-id <uuid>

Chạy lại **an toàn**: mã đã có thì bỏ qua, không ghi đè. Kỷ luật #7 — một lệnh seed âm thầm
sửa dữ liệu đang có là đúng loại rủi ro quy tắc đó sinh ra để chặn.

## Danh mục này gồm gì, và vì sao

Phủ các nhóm điều trị một quầy thuốc xã bán hằng ngày: giảm đau hạ sốt · kháng sinh · tiêu
hoá · hô hấp · dị ứng · tim mạch – tiểu đường · mắt – tai mũi họng · da liễu · vitamin –
khoáng · vật tư y tế. Không phủ: thuốc gây nghiện/hướng thần (cần giấy phép riêng), thuốc
tiêm truyền, thuốc chuyên khoa sâu.

**Mọi thuốc đều được nối hoạt chất.** Không nối thì cảnh báo dị ứng **im lặng vĩnh viễn**
trên đúng những mã bị bỏ sót — đo thật ngày 30/07 trên CSDL cũ: `drug_ingredients` **0
dòng** dù đã có 26 hoạt chất và 36 thuốc (§7ce).

**Giá bán là giá tham khảo**, dược sĩ phải sửa lại theo giá nhập thật của quầy. Để trống thì
mỗi lần bán phần mềm lại hỏi giá — cản trở đúng thứ đang muốn thử.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import suppress
from decimal import Decimal
from uuid import UUID

import structlog

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.errors import AppError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugIngredientInput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.application.dto import CreateIngredientInput
from pharmacy_os.modules.catalog.domain import RxClass
from pharmacy_os.modules.catalog.infrastructure import (
    SqlAlchemyActiveIngredientRepository,
    SqlAlchemyDrugRepository,
)

_log = structlog.get_logger("seed-quay-thuoc")

#: Hoạt chất — `(tên tiếng Việt, tên quốc tế)`. Tên quốc tế để đối chiếu với cổng Cục Quản
#: lý Dược; tên tiếng Việt là thứ dược sĩ gõ khi khai dị ứng cho khách.
_HOAT_CHAT: list[tuple[str, str]] = [
    ("Paracetamol", "Paracetamol"),
    ("Ibuprofen", "Ibuprofen"),
    ("Diclofenac", "Diclofenac"),
    ("Meloxicam", "Meloxicam"),
    ("Cafein", "Caffeine"),
    ("Amoxicillin", "Amoxicillin"),
    ("Acid clavulanic", "Clavulanic acid"),
    ("Cefixim", "Cefixime"),
    ("Cefuroxim", "Cefuroxime"),
    ("Cephalexin", "Cefalexin"),
    ("Azithromycin", "Azithromycin"),
    ("Clarithromycin", "Clarithromycin"),
    ("Ciprofloxacin", "Ciprofloxacin"),
    ("Metronidazol", "Metronidazole"),
    ("Omeprazol", "Omeprazole"),
    ("Esomeprazol", "Esomeprazole"),
    ("Domperidon", "Domperidone"),
    ("Berberin", "Berberine"),
    ("Diosmectit", "Diosmectite"),
    ("Nhôm phosphat", "Aluminium phosphate"),
    ("Oresol", "Oral rehydration salts"),
    ("Loperamid", "Loperamide"),
    ("Bisacodyl", "Bisacodyl"),
    ("Loratadin", "Loratadine"),
    ("Cetirizin", "Cetirizine"),
    ("Clorpheniramin", "Chlorphenamine"),
    ("Dextromethorphan", "Dextromethorphan"),
    ("Acetylcystein", "Acetylcysteine"),
    ("Bromhexin", "Bromhexine"),
    ("Salbutamol", "Salbutamol"),
    ("Prednisolon", "Prednisolone"),
    ("Methylprednisolon", "Methylprednisolone"),
    ("Amlodipin", "Amlodipine"),
    ("Losartan", "Losartan"),
    ("Enalapril", "Enalapril"),
    ("Bisoprolol", "Bisoprolol"),
    ("Atorvastatin", "Atorvastatin"),
    ("Rosuvastatin", "Rosuvastatin"),
    ("Metformin", "Metformin"),
    ("Gliclazid", "Gliclazide"),
    ("Aspirin", "Acetylsalicylic acid"),
    ("Natri clorid", "Sodium chloride"),
    ("Povidon iod", "Povidone-iodine"),
    ("Cồn 70 độ", "Ethanol"),
    ("Oxy già", "Hydrogen peroxide"),
    ("Ketoconazol", "Ketoconazole"),
    ("Clotrimazol", "Clotrimazole"),
    ("Acyclovir", "Aciclovir"),
    ("Vitamin C", "Ascorbic acid"),
    ("Vitamin B1", "Thiamine"),
    ("Vitamin B6", "Pyridoxine"),
    ("Vitamin B12", "Cyanocobalamin"),
    ("Vitamin D3", "Cholecalciferol"),
    ("Calci carbonat", "Calcium carbonate"),
    ("Kẽm gluconat", "Zinc gluconate"),
    ("Sắt fumarat", "Ferrous fumarate"),
    ("Acid folic", "Folic acid"),
    ("Men vi sinh", "Probiotics"),
    ("Xylometazolin", "Xylometazoline"),
    ("Cao lá thường xuân", "Hedera helix leaf extract"),
    ("Dược liệu Bổ phế", "Herbal expectorant blend"),
]

#: `(tên, nhóm, phân loại kê đơn, dạng bào chế, hàm lượng, đơn vị lẻ, giá bán tham khảo)`
#:
#: `RxClass.ETC` = thuốc kê đơn. Phân loại này quyết định quầy có bị chặn khi bán mà chưa
#: có đơn thuốc hay không — đặt sai ở đây là dạy sai luật cho người dùng phần mềm.
_DANH_MUC: list[tuple[str, str, RxClass, str, str, str, int]] = [
    # ── Giảm đau · hạ sốt · kháng viêm ────────────────────────────────────────
    ("Paracetamol 500mg", "Giảm đau hạ sốt", RxClass.OTC, "Viên nén", "500mg", "viên", 1200),
    ("Efferalgan 500mg", "Giảm đau hạ sốt", RxClass.OTC, "Viên sủi", "500mg", "viên", 4500),
    ("Panadol Extra", "Giảm đau hạ sốt", RxClass.OTC, "Viên nén", "500mg+65mg", "viên", 2500),
    ("Hapacol 250mg (gói)", "Giảm đau hạ sốt", RxClass.OTC, "Bột pha", "250mg", "gói", 2500),
    ("Ibuprofen 400mg", "Giảm đau hạ sốt", RxClass.OTC, "Viên nén", "400mg", "viên", 1500),
    ("Alaxan", "Giảm đau hạ sốt", RxClass.OTC, "Viên nén", "325mg+200mg", "viên", 2200),
    ("Diclofenac 50mg", "Giảm đau hạ sốt", RxClass.ETC, "Viên nén", "50mg", "viên", 1000),
    ("Meloxicam 7,5mg", "Giảm đau hạ sốt", RxClass.ETC, "Viên nén", "7,5mg", "viên", 2000),
    ("Aspirin 81mg", "Tim mạch", RxClass.OTC, "Viên nén", "81mg", "viên", 700),
    # ── Kháng sinh (ETC — bán phải có đơn) ────────────────────────────────────
    ("Amoxicillin 500mg", "Kháng sinh", RxClass.ETC, "Viên nang", "500mg", "viên", 2000),
    ("Augmentin 625mg", "Kháng sinh", RxClass.ETC, "Viên nén", "500mg+125mg", "viên", 12000),
    ("Cephalexin 500mg", "Kháng sinh", RxClass.ETC, "Viên nang", "500mg", "viên", 2500),
    ("Cefuroxim 500mg", "Kháng sinh", RxClass.ETC, "Viên nén", "500mg", "viên", 7000),
    ("Cefixim 200mg", "Kháng sinh", RxClass.ETC, "Viên nang", "200mg", "viên", 6500),
    ("Azithromycin 500mg", "Kháng sinh", RxClass.ETC, "Viên nén", "500mg", "viên", 9000),
    ("Clarithromycin 500mg", "Kháng sinh", RxClass.ETC, "Viên nén", "500mg", "viên", 11000),
    ("Ciprofloxacin 500mg", "Kháng sinh", RxClass.ETC, "Viên nén", "500mg", "viên", 3000),
    ("Metronidazol 250mg", "Kháng sinh", RxClass.ETC, "Viên nén", "250mg", "viên", 800),
    # ── Tiêu hoá ──────────────────────────────────────────────────────────────
    ("Omeprazol 20mg", "Tiêu hoá", RxClass.ETC, "Viên nang", "20mg", "viên", 1500),
    ("Nexium 20mg", "Tiêu hoá", RxClass.ETC, "Viên nén", "20mg", "viên", 15000),
    ("Domperidon 10mg", "Tiêu hoá", RxClass.OTC, "Viên nén", "10mg", "viên", 900),
    ("Berberin 100mg", "Tiêu hoá", RxClass.OTC, "Viên nén", "100mg", "viên", 500),
    ("Smecta (gói)", "Tiêu hoá", RxClass.OTC, "Bột pha", "3g", "gói", 5500),
    ("Phosphalugel (gói)", "Tiêu hoá", RxClass.OTC, "Hỗn dịch", "20%", "gói", 6000),
    ("Oresol (gói)", "Tiêu hoá", RxClass.OTC, "Bột pha", "—", "gói", 3500),
    ("Loperamid 2mg", "Tiêu hoá", RxClass.OTC, "Viên nang", "2mg", "viên", 800),
    ("Bisacodyl 5mg", "Tiêu hoá", RxClass.OTC, "Viên bao", "5mg", "viên", 1000),
    ("Men vi sinh Enterogermina", "Tiêu hoá", RxClass.OTC, "Ống uống", "2 tỷ", "ống", 8000),
    # ── Hô hấp · dị ứng ───────────────────────────────────────────────────────
    ("Loratadin 10mg", "Dị ứng", RxClass.OTC, "Viên nén", "10mg", "viên", 1000),
    ("Cetirizin 10mg", "Dị ứng", RxClass.OTC, "Viên nén", "10mg", "viên", 1000),
    ("Clorpheniramin 4mg", "Dị ứng", RxClass.OTC, "Viên nén", "4mg", "viên", 300),
    ("Dextromethorphan 15mg", "Hô hấp", RxClass.OTC, "Viên nén", "15mg", "viên", 1200),
    ("Acetylcystein 200mg", "Hô hấp", RxClass.OTC, "Bột pha", "200mg", "gói", 2500),
    ("Bromhexin 8mg", "Hô hấp", RxClass.OTC, "Viên nén", "8mg", "viên", 800),
    ("Salbutamol xịt", "Hô hấp", RxClass.ETC, "Bình xịt", "100mcg", "bình", 78000),
    ("Prednisolon 5mg", "Hô hấp", RxClass.ETC, "Viên nén", "5mg", "viên", 700),
    ("Methylprednisolon 16mg", "Hô hấp", RxClass.ETC, "Viên nén", "16mg", "viên", 3000),
    ("Bổ phế Nam Hà", "Hô hấp", RxClass.OTC, "Siro", "125ml", "chai", 32000),
    ("Prospan", "Hô hấp", RxClass.OTC, "Siro", "100ml", "chai", 95000),
    # ── Tim mạch · tiểu đường · mỡ máu (ETC — bệnh mạn tính) ──────────────────
    ("Amlodipin 5mg", "Tim mạch", RxClass.ETC, "Viên nén", "5mg", "viên", 1000),
    ("Losartan 50mg", "Tim mạch", RxClass.ETC, "Viên nén", "50mg", "viên", 2400),
    ("Enalapril 5mg", "Tim mạch", RxClass.ETC, "Viên nén", "5mg", "viên", 1200),
    ("Bisoprolol 2,5mg", "Tim mạch", RxClass.ETC, "Viên nén", "2,5mg", "viên", 2000),
    ("Atorvastatin 20mg", "Mỡ máu", RxClass.ETC, "Viên nén", "20mg", "viên", 3200),
    ("Rosuvastatin 10mg", "Mỡ máu", RxClass.ETC, "Viên nén", "10mg", "viên", 4500),
    ("Metformin 500mg", "Tiểu đường", RxClass.ETC, "Viên nén", "500mg", "viên", 1100),
    ("Gliclazid 30mg", "Tiểu đường", RxClass.ETC, "Viên phóng thích chậm", "30mg", "viên", 2200),
    # ── Mắt · tai mũi họng ────────────────────────────────────────────────────
    ("Natri clorid 0,9% nhỏ mắt", "Mắt – TMH", RxClass.OTC, "Dung dịch", "10ml", "lọ", 6000),
    ("Nước muối sinh lý 500ml", "Mắt – TMH", RxClass.OTC, "Dung dịch", "500ml", "chai", 12000),
    ("Otrivin 0,05%", "Mắt – TMH", RxClass.OTC, "Dung dịch xịt", "10ml", "lọ", 42000),
    ("Tobradex nhỏ mắt", "Mắt – TMH", RxClass.ETC, "Hỗn dịch", "5ml", "lọ", 55000),
    # ── Da liễu · sát khuẩn ───────────────────────────────────────────────────
    ("Povidon iod 10%", "Sát khuẩn", RxClass.OTC, "Dung dịch", "20ml", "lọ", 12000),
    ("Cồn 70 độ 60ml", "Sát khuẩn", RxClass.OTC, "Dung dịch", "60ml", "chai", 8000),
    ("Oxy già 3%", "Sát khuẩn", RxClass.OTC, "Dung dịch", "60ml", "chai", 9000),
    ("Ketoconazol 2% (kem)", "Da liễu", RxClass.OTC, "Kem bôi", "10g", "tuýp", 18000),
    ("Clotrimazol 1% (kem)", "Da liễu", RxClass.OTC, "Kem bôi", "10g", "tuýp", 15000),
    ("Acyclovir 5% (kem)", "Da liễu", RxClass.OTC, "Kem bôi", "5g", "tuýp", 16000),
    # ── Vitamin · khoáng chất ─────────────────────────────────────────────────
    ("Vitamin C 500mg", "Vitamin", RxClass.OTC, "Viên nén", "500mg", "viên", 800),
    ("Vitamin 3B", "Vitamin", RxClass.OTC, "Viên nang", "B1+B6+B12", "viên", 1500),
    ("Vitamin D3 1000UI", "Vitamin", RxClass.OTC, "Viên nang", "1000UI", "viên", 2000),
    ("Calci D3", "Vitamin", RxClass.OTC, "Viên sủi", "500mg+D3", "viên", 3500),
    ("Kẽm gluconat 10mg", "Vitamin", RxClass.OTC, "Viên nén", "10mg", "viên", 1500),
    ("Sắt fumarat + acid folic", "Vitamin", RxClass.OTC, "Viên nang", "—", "viên", 2000),
    # ── Vật tư y tế (không có hoạt chất — đúng, không phải thiếu sót) ─────────
    ("Khẩu trang y tế 4 lớp", "Vật tư", RxClass.OTC, "—", "—", "cái", 1500),
    ("Băng gạc y tế", "Vật tư", RxClass.OTC, "—", "—", "gói", 5000),
    ("Băng keo cá nhân", "Vật tư", RxClass.OTC, "—", "—", "hộp", 12000),
    ("Bông y tế 50g", "Vật tư", RxClass.OTC, "—", "50g", "gói", 8000),
    ("Nhiệt kế điện tử", "Vật tư", RxClass.OTC, "—", "—", "cái", 85000),
    ("Găng tay y tế", "Vật tư", RxClass.OTC, "—", "—", "đôi", 2000),
    ("Kim tiêm dùng một lần", "Vật tư", RxClass.OTC, "—", "—", "cái", 1500),
]

#: Tên thuốc → hoạt chất. Mã **vật tư y tế cố ý không có** — băng gạc không có hoạt chất, và
#: một mã trống ở đây là **đúng**, không phải bỏ sót. Xem `docs/inventory` và §7ce: thiếu
#: dòng nối làm cảnh báo dị ứng **im lặng** chứ không kêu lỗi.
_THANH_PHAN: dict[str, list[str]] = {
    "Paracetamol 500mg": ["Paracetamol"],
    "Efferalgan 500mg": ["Paracetamol"],
    "Panadol Extra": ["Paracetamol", "Cafein"],
    "Hapacol 250mg (gói)": ["Paracetamol"],
    "Ibuprofen 400mg": ["Ibuprofen"],
    "Alaxan": ["Paracetamol", "Ibuprofen"],
    "Diclofenac 50mg": ["Diclofenac"],
    "Meloxicam 7,5mg": ["Meloxicam"],
    "Aspirin 81mg": ["Aspirin"],
    "Amoxicillin 500mg": ["Amoxicillin"],
    "Augmentin 625mg": ["Amoxicillin", "Acid clavulanic"],
    "Cephalexin 500mg": ["Cephalexin"],
    "Cefuroxim 500mg": ["Cefuroxim"],
    "Cefixim 200mg": ["Cefixim"],
    "Azithromycin 500mg": ["Azithromycin"],
    "Clarithromycin 500mg": ["Clarithromycin"],
    "Ciprofloxacin 500mg": ["Ciprofloxacin"],
    "Metronidazol 250mg": ["Metronidazol"],
    "Omeprazol 20mg": ["Omeprazol"],
    "Nexium 20mg": ["Esomeprazol"],
    "Domperidon 10mg": ["Domperidon"],
    "Berberin 100mg": ["Berberin"],
    "Smecta (gói)": ["Diosmectit"],
    "Phosphalugel (gói)": ["Nhôm phosphat"],
    "Oresol (gói)": ["Oresol"],
    "Loperamid 2mg": ["Loperamid"],
    "Bisacodyl 5mg": ["Bisacodyl"],
    "Men vi sinh Enterogermina": ["Men vi sinh"],
    "Loratadin 10mg": ["Loratadin"],
    "Cetirizin 10mg": ["Cetirizin"],
    "Clorpheniramin 4mg": ["Clorpheniramin"],
    "Dextromethorphan 15mg": ["Dextromethorphan"],
    "Acetylcystein 200mg": ["Acetylcystein"],
    "Bromhexin 8mg": ["Bromhexin"],
    "Salbutamol xịt": ["Salbutamol"],
    "Prednisolon 5mg": ["Prednisolon"],
    "Methylprednisolon 16mg": ["Methylprednisolon"],
    "Prospan": ["Cao lá thường xuân"],
    "Amlodipin 5mg": ["Amlodipin"],
    "Losartan 50mg": ["Losartan"],
    "Enalapril 5mg": ["Enalapril"],
    "Bisoprolol 2,5mg": ["Bisoprolol"],
    "Atorvastatin 20mg": ["Atorvastatin"],
    "Rosuvastatin 10mg": ["Rosuvastatin"],
    "Metformin 500mg": ["Metformin"],
    "Gliclazid 30mg": ["Gliclazid"],
    "Natri clorid 0,9% nhỏ mắt": ["Natri clorid"],
    "Nước muối sinh lý 500ml": ["Natri clorid"],
    "Tobradex nhỏ mắt": ["Methylprednisolon"],
    "Povidon iod 10%": ["Povidon iod"],
    "Cồn 70 độ 60ml": ["Cồn 70 độ"],
    "Oxy già 3%": ["Oxy già"],
    "Ketoconazol 2% (kem)": ["Ketoconazol"],
    "Clotrimazol 1% (kem)": ["Clotrimazol"],
    "Acyclovir 5% (kem)": ["Acyclovir"],
    "Vitamin C 500mg": ["Vitamin C"],
    "Vitamin 3B": ["Vitamin B1", "Vitamin B6", "Vitamin B12"],
    "Vitamin D3 1000UI": ["Vitamin D3"],
    "Calci D3": ["Calci carbonat", "Vitamin D3"],
    "Kẽm gluconat 10mg": ["Kẽm gluconat"],
    "Sắt fumarat + acid folic": ["Sắt fumarat", "Acid folic"],
    "Otrivin 0,05%": ["Xylometazolin"],
    # Thuốc đông dược: hoạt chất khai theo **nhóm dược liệu**, không tách từng vị. Khai
    # nhóm vẫn tốt hơn để trống — khách dị ứng dược liệu vẫn được cảnh báo, dù thô.
    "Bổ phế Nam Hà": ["Dược liệu Bổ phế"],
}

#: Đơn vị bán lẻ có đóng gói lớn hơn. Quầy nhập theo hộp, bán theo viên — thiếu quy đổi thì
#: mỗi lần nhập phải nhân tay, và nhân tay là chỗ sai số vào sổ.
_QUY_DOI: dict[str, tuple[str, int]] = {
    "viên": ("hộp", 100),
    "gói": ("hộp", 30),
    "ống": ("hộp", 20),
    "cái": ("hộp", 50),
    "đôi": ("hộp", 50),
}


def _don_vi(don_vi_le: str) -> list[DrugUnitInput]:
    goi = _QUY_DOI.get(don_vi_le)
    if goi is None:
        return []
    ten, he_so = goi
    return [DrugUnitInput(unit_name=ten, factor=Decimal(he_so))]


async def _chay(tenant_id: UUID, branch_id: UUID, user_id: UUID) -> None:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    sessionmaker = build_sessionmaker(engine)
    bus = InMemoryEventBus()

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(sessionmaker, bus)

    catalog = CatalogService(
        uow_factory,
        lambda uow, c: SqlAlchemyDrugRepository(uow.session, c),
        lambda uow: SqlAlchemyActiveIngredientRepository(uow.session),
        AuditLogger(sessionmaker),
    )
    ctx = RequestContext(
        tenant_id=tenant_id,
        branch_id=branch_id,
        user_id=user_id,
        permissions=frozenset({"catalog.read", "catalog.create", "catalog.update"}),
    )

    them_hc = 0
    for ten, ten_en in _HOAT_CHAT:
        # Hoạt chất là danh mục dùng chung toàn hệ thống, không thuộc tenant nào ⇒ trùng là
        # chuyện bình thường khi chạy lại.
        with suppress(AppError):
            await catalog.create_ingredient(CreateIngredientInput(name=ten, name_en=ten_en), ctx)
            them_hc += 1

    # Đọc lại từ CSDL: lượt trên bọc trong `suppress` nên khi chạy lại nó không trả về gì.
    ma_hc = {i.name: i.id for i in await catalog.list_ingredients(ctx)}

    them_thuoc = 0
    bo_qua = 0
    thieu_hc: list[str] = []
    # `_nhom` chưa dùng: nhóm điều trị là thông tin CHO NGƯỜI ĐỌC bảng `_DANH_MUC` (biết
    # danh mục phủ đủ chưa), chưa phải trường của `Drug`. Giữ trong bảng chứ không xoá —
    # xoá đi thì lần bổ sung sau không ai biết mã mới thuộc nhóm nào.
    for i, (ten, _nhom, rx, dang, ham_luong, don_vi, gia) in enumerate(_DANH_MUC):
        ten_hc = _THANH_PHAN.get(ten, [])
        thieu = [h for h in ten_hc if h not in ma_hc]
        if thieu:
            thieu_hc.extend(f"{ten}→{h}" for h in thieu)
        thanh_phan = [
            DrugIngredientInput(ingredient_id=ma_hc[h], amount=Decimal("1"), unit=don_vi)
            for h in ten_hc
            if h in ma_hc
        ]
        try:
            await catalog.create_drug(
                CreateDrugInput(
                    name=ten,
                    rx_class=rx,
                    base_unit=don_vi,
                    form=dang,
                    strength=ham_luong,
                    # EAN-13 đúng hình dạng, tiền tố 893 (Việt Nam). Mã **nội bộ của quầy**
                    # — không phải mã nhà sản xuất; quét mã thật sẽ không khớp cho tới khi
                    # dược sĩ quét lại và sửa. Ghi ra đây để không ai tưởng nó là mã chuẩn.
                    barcode=f"893{6500000000 + i:010d}",
                    sale_price=Decimal(gia),
                    units=_don_vi(don_vi),
                    ingredients=thanh_phan,
                ),
                ctx,
            )
            them_thuoc += 1
        except AppError:
            bo_qua += 1  # đã có — chạy lại seeder, không ghi đè

    await engine.dispose()
    _log.info(
        "seed_danh_muc_xong",
        hoat_chat_them=them_hc,
        thuoc_them=them_thuoc,
        thuoc_bo_qua=bo_qua,
        thieu_hoat_chat=thieu_hc or None,
    )
    print(f"Hoạt chất: +{them_hc} · Thuốc: +{them_thuoc}, bỏ qua {bo_qua} (đã có)")
    if thieu_hc:
        print(f"⚠️  Thiếu hoạt chất, cảnh báo dị ứng sẽ IM LẶNG cho: {', '.join(thieu_hc)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Seed danh mục thuốc cho một quầy thuốc thật.")
    p.add_argument("--tenant-id", required=True)
    p.add_argument("--branch-id", required=True)
    p.add_argument("--user-id", required=True)
    a = p.parse_args(argv)
    asyncio.run(_chay(UUID(a.tenant_id), UUID(a.branch_id), UUID(a.user_id)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
