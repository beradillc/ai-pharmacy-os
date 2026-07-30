# Nguồn chính thức danh mục thuốc → hoạt chất (Bộ Y tế)

> Rà 2026-07-30 theo yêu cầu của Chain. Mục đích: nối `drug_ingredients` cho seeder —
> xem khiếm khuyết §7ce trong `PROJECT_STATE.md` (trên `nt650v2` bảng này **rỗng 0 dòng**
> nên cảnh báo dị ứng không bao giờ kích hoạt).
>
> 🔴 **Chưa lấy được danh mục đầy đủ.** Đọc mục 3 trước khi dùng.

## 1. Hai nguồn chính thức, đã xác minh

| Nguồn | Cơ quan | Trạng thái từ máy này |
|---|---|---|
| `dichvucong.dav.gov.vn/congbothuoc` | Cục Quản lý Dược — cổng tra cứu **toàn bộ** giấy ĐKLH | ⚠️ **SPA JavaScript** — tải về chỉ ra khung, biến `{{totalRow}}` chưa render. **Có nút xuất Excel** nhưng phải bấm bằng trình duyệt thật |
| `dav.gov.vn` — các Quyết định `QĐ-QLD` | Cục Quản lý Dược — công bố **theo đợt** | ✅ **Tải được, đọc được.** PDF có dấu ký số |
| `drugbank.vn` | Ngân hàng dữ liệu ngành Dược (Cục QLD) | ❌ **DNS không phân giải** từ môi trường này |

## 2. Đã kiểm chứng bằng một văn bản thật

**Quyết định số 132/QĐ-QLD ngày 10/3/2026** — *Ban hành Danh mục 30 thuốc sản xuất trong
nước được gia hạn giấy đăng ký lưu hành tại Việt Nam — Đợt 220 thuốc hóa dược.*
Ký thay Cục trưởng: Phó Cục trưởng **Nguyễn Thành Lâm**, có dấu ký số Cục Quản lý Dược
ngày 10/03/2026. Căn cứ gồm Luật Dược 2016 (sửa đổi 21/11/2024), NĐ 163/2025/NĐ-CP,
TT 12/2025/TT-BYT.

**Phụ lục I có đúng cột cần dùng:**

| STT | Tên thuốc | **Hoạt chất chính – Hàm lượng** | Dạng bào chế | Quy cách đóng gói | Tiêu chuẩn | Tuổi thọ | Số đăng ký | Số lần gia hạn |
|---|---|---|---|---|---|---|---|---|

Ba dòng mẫu đọc được từ Phụ lục I:

| Tên thuốc | Hoạt chất chính – Hàm lượng |
|---|---|
| Flu-cold children's | Guaifenesin 100 mg; Phenylephrin hydroclorid 2,5 mg; **Dextromethorphan hydrobromid 5 mg** |
| Oraptic 20 | **Omeprazol** (dưới dạng pellet Omeprazol 8,5 %) 20 mg |
| Cetirizin 10mg | **Cetirizin dihydroclorid** 10 mg |
| Eurdogel | **Nhôm phosphat** gel 20 % 12,38 mg |

⇒ Định dạng nguồn **khớp đúng** thứ ta cần: một cột tên thương mại, một cột hoạt chất.
Và nó cho thấy luôn hai điều phải xử lý khi nối dữ liệu:
- Hoạt chất ghi ở **dạng muối/ester** (`Cetirizin dihydroclorid`, `Dextromethorphan
  hydrobromid`) chứ không phải gốc (`Cetirizin`, `Dextromethorphan`). Dị ứng khoá theo
  **gốc**, nên phải chuẩn hoá tên trước khi khớp.
- Thuốc **phối hợp** có nhiều hoạt chất trong một ô, phân tách bằng `;` — đúng ca
  `AllergyConflict` được thiết kế để báo từng hoạt chất một.

## 3. 🔴 Vì sao vẫn CHƯA đủ để nối seeder

Các `QĐ-QLD` là **công bố theo đợt**, mỗi quyết định chỉ 30–50 thuốc. Muốn tra 16 mã đang
thiếu của seeder thì phải quét hàng trăm quyết định — không phải cách làm.

Nặng hơn: **phần lớn 16 mã đó là thuốc nước ngoài hoặc biệt dược nhập** (Efferalgan,
Panadol Extra, Augmentin, Smecta, Phosphalugel, Prospan) nên nằm ở **chuỗi quyết định
khác** với đợt thuốc sản xuất trong nước ở trên. Không suy ra được từ một văn bản.

⇒ Đường đúng là **cổng tra cứu toàn bộ** (`dichvucong.dav.gov.vn/congbothuoc`) — nó có
tra theo tên thuốc và **nút xuất Excel**. Nhưng là SPA nên cần trình duyệt thật.

## 4. ✅ ĐÃ TRA ĐƯỢC — Firefox 153 + Selenium, cổng chính thức

Chain chọn đường B nhưng dùng **Firefox** (công cụ `claude-in-chrome` sẵn có là Chrome-only).
Cách làm: `selenium 4.46` trong venv **riêng ở scratchpad** (không đụng `backend/.venv`),
điều khiển `/usr/bin/firefox` chế độ headless, gõ vào ô *"Nhập từ khóa tìm kiếm theo Số
GPLH và Tên thuốc"* (`ng-model="vm.filterAll"`) rồi đọc bảng kết quả.

Cột đọc được: `[5]` Tên thuốc · `[9]` Hoạt chất · `[3]` Số GPLH · `[11]` Số QĐ.

### Kết quả 13 mã (3 vật tư không tra: băng gạc, khẩu trang, nhiệt kế — không có hoạt chất)

| Thuốc trong seeder | Hoạt chất theo Cục QLD | Có trong 26 hoạt chất? | Dẫn chứng |
|---|---|---|---|
| **Efferalgan 500mg** | Paracetamol | ✅ Paracetamol | SĐK 300100523924 · 407/QĐ-QLD |
| **Panadol Extra** | Paracetamol + Cafein | ✅ cả hai | SĐK 539100184523 · 489/QĐ-QLD |
| **Alaxan** | Ibuprofen 200mg + Paracetamol 325mg | ✅ cả hai | SĐK 893100099624 · 90/QĐ-QLD |
| **Smecta** | Diosmectite | ✅ Diosmectit | 593/QĐ-QLD |
| **Phosphalugel** | Aluminium phosphate 20% gel | ✅ Nhôm phosphat | SĐK 300100006024 · 03/QĐ-QLD |
| **Augmentin 625mg** | Amoxicillin 500mg + Acid clavulanic 125mg | ✅ cả hai | 698/QĐ-QLD (625 = 500+125) |
| **Oresol** | Glucose khan + Natri clorid + Kali clorid + Natri citrat | 🟡 chỉ có **Natri clorid** | SĐK 893100276125 · 285/QĐ-QLD |
| **Vitamin 3B** | Vitamin B1 + B6 + B12 (thiamin/pyridoxin/cyanocobalamin) | 🟡 chỉ có **Vitamin B1** | SĐK 893100059625 · 124/QĐ-QLD |
| **Prospan** | Cao khô lá thường xuân (*Hederae helicis*) | ❌ chưa có | VN-22331-19 · 653/QĐ-QLD |
| **Men vi sinh Enterogermina** | Bào tử *Bacillus clausii* | ❌ chưa có | SĐK 800400108124 · 94/QĐ-QLD |
| **Dầu gió xanh** | Menthol · methyl salicylat · tinh dầu tràm/long não | ❌ chưa có | 230/QĐ-QLD |
| **Bổ phế Nam Hà** | Cao dược liệu (bạch linh, cát cánh, tỳ bà diệp, tang bạch bì, ma hoàng…) | ❌ chưa có | VD-28674-18 · 28/QĐ-QLD |
| **Canxi D3** | **0 kết quả** — không có giấy ĐKLH thuốc | 🟡 có Calci carbonat | không tra được |

### 🔴 Ba điều phải cẩn thận, không được nhắm mắt lấy dòng đầu

1. **Tra theo tên trả về khớp mờ.** `Prospan` trả về một dòng **Betamethasone** (sản phẩm
   khác hoàn toàn); `Smecta` trả về `Smectago` (thuốc generic cùng hoạt chất, **không phải**
   Smecta); `Efferalgan` trả về cả `Efferalgan Codeine` (có thêm codein). Phải đọc **tên
   thuốc** ở cột `[5]`, không chỉ đọc hoạt chất.
2. **Hoạt chất ghi ở dạng muối.** `Cetirizin dihydroclorid`, `Amoxicillin trihydrate`,
   `Pyridoxin hydroclorid`. Dị ứng khoá theo **gốc** ⇒ phải chuẩn hoá trước khi khớp.
3. **Cùng biệt dược, nhiều công thức theo dạng bào chế.** Efferalgan có 150mg/250mg/500mg;
   Augmentin có 500+125, 875+125, 600+42,9. Chọn công thức nào là quyết định, không phải
   phép tra.

### Đề nghị: nối 6 mã CHẮC CHẮN, để 7 mã còn lại chờ Chain

**Nối được ngay** (hoạt chất đã có trong danh mục, dữ liệu Cục QLD rõ ràng, không mơ hồ):
Efferalgan → Paracetamol · Panadol Extra → Paracetamol + Cafein · Alaxan → Ibuprofen +
Paracetamol · Smecta → Diosmectit · Phosphalugel → Nhôm phosphat · Augmentin →
Amoxicillin + Acid clavulanic.

⇒ Sáu mã này là **6/6 thuốc tân dược biệt dược** trong nhóm thiếu — đúng nhóm nguy hiểm
nhất mà §7ce nêu (khách dị ứng Paracetamol mua Efferalgan thì tên thuốc không nhắc
Paracetamol). Nối 6 mã này là đóng được phần rủi ro thật.

**Chờ Chain quyết** 7 mã còn lại, vì mỗi mã cần một quyết định chứ không phải một phép tra:
- `Oresol`, `Vitamin 3B` — nối **một phần** (chỉ hoạt chất đã có) hay **thêm hoạt chất mới**?
- `Prospan`, `Enterogermina`, `Dầu gió xanh`, `Bổ phế Nam Hà` — thêm 4 hoạt chất mới, hay
  để trống vì gần như không ai khai dị ứng với chúng?
- `Canxi D3` — không có ĐKLH thuốc. Đây có phải **thực phẩm bổ sung** chứ không phải thuốc?
  Nếu vậy thì để trống là **đúng**, không phải thiếu.

## 5. Ba đường đi (đã chọn B — giữ lại để tham chiếu)

| # | Cách | Ưu | Nhược |
|---|---|---|---|
| A | Chain mở cổng tra cứu, tra 16 tên, **bấm xuất Excel**, để file vào `00-Bookmark/` | Chính thức, một lần xong, tôi khớp máy móc không phải đoán | Chain mất ~15 phút |
| B | Tôi điều khiển Chrome của Chain tự tra + xuất (có công cụ `claude-in-chrome`) | Chain không phải làm tay | Cần Chain cấp quyền cho site trong extension; tôi chưa thử site này |
| C | Chain đọc bao bì/tự khai 16 mã | Nhanh nhất, Chain là người bán thuốc | Không có vết nguồn chính thức trong hồ sơ |

**Khuyến nghị: A hoặc B.** Lý do không chọn C dù nhanh: đây là dữ liệu để **cảnh báo dị
ứng cho người thật**, nên gốc dữ liệu cần truy được về Cục Quản lý Dược, không phải về
trí nhớ của ai — kể cả trí nhớ đúng.

**Và tôi KHÔNG tự điền từ kiến thức của mình.** Tôi biết Efferalgan là paracetamol, nhưng
"tôi biết" không phải nguồn dẫn được trong hồ sơ một hệ thống cảnh báo dị ứng. Theo tinh
thần **R-10**: thiếu văn bản thì ghi *"chưa lấy được"*, không tự lấp bằng suy luận.

## Nguồn

- Cổng tra cứu Cục Quản lý Dược: https://dichvucong.dav.gov.vn/congbothuoc/index
- Trang Cục Quản lý Dược: https://dav.gov.vn/
- QĐ 132/QĐ-QLD ngày 10/3/2026: https://dav.gov.vn/upload_images/files/132_QD_QLD%202026_signed.pdf
- QĐ 145/QĐ-QLD năm 2026: https://dav.gov.vn/upload_images/files/145_QD_QLD%202026_signed.pdf
- Bộ Y tế hướng dẫn tra cứu GĐKLH thuốc: https://moh.gov.vn/en/tin-lien-quan/-/asset_publisher/vjYyM7O9aWnX/content/cuc-quan-ly-duoc-bo-y-te-huong-dan-nguoi-dan-doanh-nghiep-tra-cuu-thong-tin-giay-ang-ky-luu-hanh-thuoc
