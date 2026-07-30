"""Ánh xạ tên thuốc → tên hoạt chất, dùng chung cho seeder và lệnh backfill.

**Vì sao là file riêng, không nằm trong `demo_pharmacy.py`.** Hai lệnh cần đúng cùng một
bảng này: `seeds.demo_pharmacy` (seed mới) và `seeds.backfill_drug_ingredients` (vá CSDL
đã có). Để hai bản là bảo đảm chúng sẽ lệch — và lệch ở đây không kêu, nó chỉ làm cảnh
báo dị ứng im lặng trên đúng những mã bị bỏ sót. Thêm nữa, `demo_pharmacy` nạp gần như
toàn bộ ứng dụng, nên lệnh backfill nhập từ đó là kéo theo cả thứ nó không cần.

**Không nối bảng này thì cảnh báo dị ứng không bao giờ kích hoạt** — đo thật 30/07 trên
`nt650v2`: `drug_ingredients` **0 dòng** dù đã có 26 hoạt chất và 36 thuốc, vì seeder tạo
cả hai rồi không nối (khiếm khuyết PROJECT_STATE §7ce).

Hai nhóm, khác nhau về **mức chắc chắn** — chia ra để về sau còn biết dòng nào tra được,
dòng nào chỉ là tên trùng:

1. **Tên thuốc CHỨA THẲNG tên hoạt chất** (`Paracetamol 500mg` → Paracetamol). Không phải
   suy đoán — tên generic chính là tên hoạt chất.
2. **Biệt dược**, tra ở cổng Cục Quản lý Dược (`dichvucong.dav.gov.vn/congbothuoc`) ngày
   30/07/2026, có SĐK và số QĐ làm dẫn chứng — xem
   `docs/features/ho-so-suc-khoe-khach-hang/02_NGUON_DANH_MUC_THUOC.md`.
   🔴 Đây mới là nhóm quan trọng: khách dị ứng Paracetamol mua **Efferalgan** thì tên
   thuốc không hề nhắc tới Paracetamol, nên chỉ ánh xạ theo hoạt chất mới bắt được.

Ba vật tư (băng gạc, khẩu trang, nhiệt kế) **cố ý không có** hoạt chất — chúng vắng mặt ở
đây là đúng, không phải sót.

Bảy mã còn để trống vì **cần Chain quyết**, không phải vì tra không ra: Vitamin 3B, Oresol,
Bổ phế Nam Hà, Prospan, Men vi sinh Enterogermina, Canxi D3, Dầu gió xanh — chi tiết và
câu hỏi cho từng mã ở tài liệu nói trên, mục 4.
"""

from __future__ import annotations

DRUG_INGREDIENTS: dict[str, list[str]] = {
    # --- nhóm 1: tên thuốc = tên hoạt chất ---
    "Paracetamol 500mg": ["Paracetamol"],
    "Ibuprofen 400mg": ["Ibuprofen"],
    "Vitamin C 500mg": ["Vitamin C"],
    "Berberin 100mg": ["Berberin"],
    "Loratadin 10mg": ["Loratadin"],
    "Cetirizin 10mg": ["Cetirizin"],
    "Dextromethorphan 15mg": ["Dextromethorphan"],
    "Domperidon 10mg": ["Domperidon"],
    "Omeprazol 20mg": ["Omeprazol"],
    "Natri clorid 0,9% nhỏ mắt": ["Natri clorid"],
    "Povidon iod 10%": ["Povidon iod"],
    "Amoxicillin 500mg": ["Amoxicillin"],
    "Cefixim 200mg": ["Cefixim"],
    "Azithromycin 500mg": ["Azithromycin"],
    "Metformin 500mg": ["Metformin"],
    "Amlodipin 5mg": ["Amlodipin"],
    "Losartan 50mg": ["Losartan"],
    "Atorvastatin 20mg": ["Atorvastatin"],
    "Prednisolon 5mg": ["Prednisolon"],
    "Salbutamol xịt": ["Salbutamol"],
    # --- nhóm 2: biệt dược, tra cổng Cục QLD 30/07/2026 ---
    # SĐK 300100523924 · 407/QĐ-QLD
    "Efferalgan 500mg": ["Paracetamol"],
    # SĐK 539100184523 · 489/QĐ-QLD — Paracetamol 500mg + Cafein 65mg
    "Panadol Extra": ["Paracetamol", "Cafein"],
    # SĐK 893100099624 · 90/QĐ-QLD — Ibuprofen 200mg + Paracetamol 325mg
    "Alaxan": ["Ibuprofen", "Paracetamol"],
    # 593/QĐ-QLD — Diosmectite 3g
    "Smecta": ["Diosmectit"],
    # SĐK 300100006024 · 03/QĐ-QLD — Aluminium phosphate 20% gel
    "Phosphalugel": ["Nhôm phosphat"],
    # 698/QĐ-QLD — Amoxicillin 500mg + Acid clavulanic 125mg (625 = 500 + 125)
    "Augmentin 625mg": ["Amoxicillin", "Acid clavulanic"],
}
