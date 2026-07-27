# 19 — THIẾT KẾ GIAO DIỆN SPRINT 9: Bảng điều hành & Đề xuất đặt hàng

> **Trạng thái: CHỜ CHAIN DUYỆT.** Không viết dòng mã nào trước khi mục §7 được chốt.
>
> Mọi endpoint trích trong tài liệu này **đã xác nhận tồn tại trên staging đang chạy**
> (`localhost:8001`, đọc trực tiếp từ OpenAPI 2026-07-28). Không màn nào vẽ ra một tính
> năng chưa có backend.
>
> Căn cứ: `docs/16_BRAND_UI_GUIDE.md` · `ROADMAP.md` Sprint 9 · `PROJECT_STATE.md` §7bm–§7br

---

## 1. Cổng kiểm toán & Sprint 9 — đã thoả tới đâu

Chain yêu cầu *"thiết kế nếu đã thoả mãn audit"*. Đây là trạng thái thật, không làm tròn lên.

| Mục chặn | Trạng thái | Bằng chứng |
|---|---|---|
| F-1 cổng + cưỡng chế | ✅ Đóng | hook chạy mọi commit |
| F-2 fail-fast prod (A-02/A-03) | ✅ Đóng | 9 test dựng `Settings` thật |
| F-3 `APP__DEBUG` | ✅ Đóng | `.env.example` = false |
| F-4 nền test Postgres | ✅ Đóng | 10 test đua xanh |
| F-5 khoá hàng tồn kho | ✅ Đóng | 0 dấu `xfail` |
| F-8 runbook mã hoá | ✅ Đóng | chạy hết 8 bước trên staging · 25/25 dòng mã hoá · 0 lỗi giải mã |
| F-9 rate limit | ✅ Đóng | 15 test, gồm kịch bản DoS C-11 |
| F-15 chặn mock ở prod | ✅ Đóng | 13 test, chặn cả 2 điểm nạp |
| F-16 diễn tập restore | ✅ Đóng | khôi phục 2 s · **ứng dụng đọc được** bản khôi phục |
| F-19 quy trình sự cố | 🟡 Thiết kế xong | còn bảng gắn người — chặn *pilot*, **không** chặn thiết kế UI |
| F-17 load test p95 | 🟡 Đạt có điều kiện | 217,6 ms @ 8 luồng · 490,4 ms @ 16 luồng |
| F-6 giấy phép VNPAY | 🔓 Ngoài đường găng | PILOT DECISION LOCK: pilot không có thanh toán online |

**Kết luận:** không còn mục chặn nào thuộc về *mã sản phẩm*. Hai mục còn mở (bảng gắn
người F-19, mức tải mục tiêu F-17) đều chờ **quyết định của Chain** và **không chặn** việc
duyệt bản thiết kế này. ⇒ Đủ điều kiện để thiết kế.

---

## 2. Thiết kế cho ai, trong hoàn cảnh nào

| Người dùng | Câu hỏi thật của họ | Màn chính |
|---|---|---|
| **Quản lý nhà thuốc** | Không phải *"doanh thu bao nhiêu"* mà **"hôm nay có gì cần tôi xử lý không"** | Bảng điều hành |
| **Dược sĩ phụ trách kho** | Lô cận date, thuốc sắp hết. Cần **ra quyết định đặt hàng**, không cần biểu đồ đẹp | Đề xuất đặt hàng |
| **Thu ngân** | — | Không dùng hai màn này. POS **không được đụng** trong Sprint 9 |

⚠️ **Điều kiện vật lý quyết định thiết kế, không phải thẩm mỹ.** Máy POS nhà thuốc thường
là màn rẻ, dưới đèn huỳnh quang, người dùng **đứng và nhìn lướt**. `docs/16` đã cảnh báo
đúng chỗ này: nền kem + chữ xanh nhạt rất dễ rớt chuẩn tương phản. Vì vậy bảng màu dưới
đây **ghi kèm tỉ số tương phản**, không chỉ ghi tên màu.

---

## 3. Hệ thống thiết kế — LẤY TỪ GÓI BÀN GIAO ĐÃ CHỐT

> 🔴 **Đính chính.** Bản nháp đầu của tài liệu này tự đặt một bảng màu mới. **Sai.**
> Đã có gói bàn giao chính thức tại `00-Bookmark/design_handoff_beras/` ghi rõ
> *"Fidelity: **High-fidelity.** Màu, chữ, spacing… là **bản chốt cuối** — dựng pixel-đúng
> bằng token thật, **không tự đổi giá trị**."* Toàn bộ mục này nay chép từ đó.

### 3.1 Token màu — bản chốt

| Token | Hex | Tên | Vai trò |
|---|---|---|---|
| `--beras-text` | `#232920` | Mực Sổ | text chính |
| `--beras-accent` | `#1F3D2B` | Lá Rừng Đậm | primary — nav, chrome tối |
| *(chưa có var riêng)* | `#5B8C51` | Lá Non | accent — nút chính, canopy online |
| `--beras-brown` | `#6B4A32` | Nâu Đất Sổ | secondary — border, icon, canopy offline |
| `--beras-bg` | `#EDEFE7` | Giấy Tái Sinh | nền sáng — **KHÔNG phải kem** |
| `--beras-warning` | `#B98A2D` | Vàng Nghệ | cảnh báo — Rx, cận date |
| `--beras-success` | `#2F7A6B` | Xanh Bạc Hà Trầm | thành công — **tách biệt accent** |
| `--beras-danger` | `#A8452F` | Đỏ Trầm | nguy hiểm; nhãn "chỉ dược sĩ xem được" |

Nguyên tắc **success tách khỏi accent** mà gói bàn giao đã chốt trùng đúng lập luận ở §4–§5
của tài liệu này: nhấn thương hiệu là xanh lá, nên "thành công" phải là màu khác
(`#2F7A6B`) chứ không được mượn màu nhấn.

### 3.2 Chữ — bản chốt

| Vai trò | Font | Cách nạp |
|---|---|---|
| Display | **Be Vietnam Pro** | `next/font/google` — **tự host lúc build** |
| Sans | **Work Sans** | fallback hệ thống, chưa self-host |
| Mono | **IBM Plex Mono** | `next/font/google` — giá / số lượng / mã lô |

**Be Vietnam Pro là lựa chọn đúng cho sản phẩm Việt** — nó được thiết kế cho tiếng Việt,
nên rủi ro "dấu tụt về font thay thế" mà tôi nêu ở bản nháp không còn.

### 3.3 Bo góc

Card 10–16 px tuỳ kích thước · pill/button 8–10 px · badge 4 px.

### 3.4 🔴 BA MÂU THUẪN PHẢI GIẢI TRƯỚC KHI CODE

| # | Mâu thuẫn | Chi tiết |
|---|---|---|
| **M-1** | **Nền: "kem" hay "Giấy Tái Sinh"?** | `docs/16 §2` ghi nền *"Kem / xanh lá nhạt"*. Gói bàn giao ghi `#EDEFE7` và nói thẳng **"KHÔNG phải kem"**. Hai văn bản chính thức nói ngược nhau — **cần Chain chốt văn bản nào thắng** |
| **M-2** | **`frontend/src/styles/tokens.css` đang là giá trị TẠM** | Chính file đó tự ghi *"Giá trị hex dưới đây là TẠM (chưa chốt thiết kế chính thức)"*. Nay đã có bản chốt ⇒ **phải thay** (`#f5f2e8`→`#EDEFE7`, `#2f5233`→`#1F3D2B`, `#7a4a2b`→`#6B4A32`, `#a3312a`→`#A8452F`, thêm `--beras-warning` `--beras-success`). Là việc **code**, không làm trong phiên này |
| **M-3** | **Lý do từ chối `next/font/google` trong `tokens.css` sai về mặt sự kiện** | File đó viết *"tải font từ Google lúc build/dev đòi mạng — ngược tinh thần vận hành khi mất kết nối"*. Nhưng `next/font/google` **tự host lúc build**: runtime **không** gọi mạng. Lý do từ chối không đứng vững, và gói bàn giao đã chốt dùng Be Vietnam Pro |

## 4. Màn hình 1/2 — Bảng điều hành

`GET /api/v1/analytics/dashboard`
→ `branch_id · date_from · date_to · revenue_total · top_drugs · near_expiry_count · low_stock_count · draft_po_count`

Màn này trả lời đúng một câu: **hôm nay có gì cần tôi xử lý không.** Doanh thu là *thông
tin*; ba con số còn lại là *việc* — nên chúng được thiết kế nổi hơn.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ BERAS  Bảng điều hành              [Chi nhánh chính ▾]  [01–28/07 ▾]     │
├──────────────────────────────────────────────────────────────────────────┤
│ ┃ DOANH THU KỲ    ┃ SẮP HẾT HÀNG    ┃ CẬN HẠN DÙNG    │ ĐƠN MUA NHÁP    │
│ ┃ 184.320.000     ┃ 7               ┃ 12              │ 3               │
│ ┃ ₫ · 28 ngày     ┃ dưới điểm đặt   ┃ lô trong 90 ngày│ chờ duyệt       │
│ ↑xanh nhấn         ↑vạch đất nung    ↑vạch hổ phách    ↑không vạch       │
├──────────────────────────────────────────────────────────────────────────┤
│ Thuốc bán chạy                                          [Xuất CSV]       │
│ Paracetamol 500mg   ████████████████  1.240   24.800.000 ₫               │
│ Amoxicillin 500mg   ███████████       842     21.050.000 ₫               │
│ Vitamin C 1000mg    ██████            509     10.180.000 ₫               │
│ Omeprazole 20mg     ███               271      9.485.000 ₫               │
└──────────────────────────────────────────────────────────────────────────┘
```

### Quyết định bố cục, kèm lý do

- **Bốn ô, không phải bốn biểu đồ.** Trường trả về là *số đếm* (`near_expiry_count`,
  `low_stock_count`, `draft_po_count`) — vẽ biểu đồ cho một con số là trang trí, không
  phải thông tin.
- **Vạch màu bên trái ô** mã hoá mức độ. Người nhìn lướt bắt được *"có gì đỏ không"*
  trước khi đọc chữ.
- **Doanh thu dùng màu nhấn, không phải màu cảnh báo** — nó là kết quả, không phải việc cần làm.
- **Thanh ngang cho thuốc bán chạy**, không phải biểu đồ tròn: so sánh độ dài chính xác
  hơn so sánh góc, và đọc được cả khi in đen trắng.
- **Không ô nào bấm ra biểu đồ chi tiết.** Backend chưa có chuỗi thời gian — thiết kế
  không hứa thứ API không trả.

### Trạng thái — phải vẽ đủ, không chỉ vẽ lúc đẹp

| Trạng thái | Hành vi |
|---|---|
| Đang tải | Khung xám từng ô. Ngưỡng hiện **200 ms** — dưới mức đó nháy khung còn khó chịu hơn chờ. Chọn theo p95 đo thật (217 ms) |
| Rỗng thật | *"Chưa có giao dịch nào trong kỳ này."* + nút đổi khoảng ngày. **Không** hiện số 0 to đùng |
| Rỗng tốt | Không mặt hàng nào sắp hết ⇒ ô hiện **0** và **không** vạch màu. Im lặng là tín hiệu tốt |
| Lỗi | *"Không tải được số liệu. Thử lại."* — nút thử lại **tại ô hỏng**, không đánh sập cả trang vì một ô |
| Mất mạng | Dải: **"Đang ngoại tuyến — số liệu tính đến 14:32."** Màn này *không* chạy offline; nói thẳng thay vì hiện số cũ như số mới |
| Không đủ quyền | Thiếu `analytics.read` ⇒ **không hiện mục trong menu**. Không hiện rồi báo lỗi khi bấm |

---

## 5. Màn hình 2/2 — Đề xuất đặt hàng

`GET /api/v1/analytics/reorder/suggestions` · `POST …/run` · `POST …/{id}/dismiss` · `POST …/{id}/materialize`
→ `drug_id · avg_daily_velocity · reorder_point · on_hand_at_calc · suggested_qty · status · supplier_id · po_id · can_materialize · calculated_at`

Đây là màn **ra quyết định**, không phải màn báo cáo. Mỗi dòng kết thúc bằng một trong hai
việc: *tạo đơn mua nháp* hoặc *bỏ qua*.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ BERAS  Đề xuất đặt hàng        Tính lúc 06:15 · 214 thuốc      [Tính lại]    │
├──────────────────────────────────────────────────────────────────────────────┤
│ 7 đề xuất đang mở                              [Đang mở] [Đã bỏ qua]         │
│                                                                              │
│ THUỐC                    TỒN  ĐIỂM ĐẶT  BÁN/NGÀY  ĐỀ XUẤT  NHÀ CUNG CẤP      │
│ Amoxicillin 500mg         48      120      24,0      300   Dược Hậu Giang    │
│   ● Hết trong ~2 ngày                              [Tạo đơn nháp] [Bỏ qua]   │
│ Omeprazole 20mg           96      110      10,5      220   Traphaco          │
│   ● Hết trong ~9 ngày                              [Tạo đơn nháp] [Bỏ qua]   │
│ Cetirizine 10mg           15        —        —         —   chưa có           │
│   ○ Chưa đủ dữ liệu bán                            [Tạo đơn nháp] [Bỏ qua]   │
│                                                     ↑mờ, kèm lý do           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Quyết định thiết kế

- **Hiện đủ cơ sở tính toán** — tồn, điểm đặt lại, tốc độ bán — chứ không chỉ con số đề
  xuất. Dược sĩ phải *kiểm tra được* đề xuất trước khi đồng ý; một con số không giải thích
  được thì hoặc bị làm theo mù quáng, hoặc bị bỏ qua hết.
- **"Hết trong ~N ngày" là dẫn xuất, không phải trường API** — tính từ
  `on_hand_at_calc ÷ avg_daily_velocity` ngay ở giao diện. Nó là thứ người ta thực sự
  nghĩ, khác với "điểm đặt lại" vốn là khái niệm hệ thống.
- **`can_materialize=false` ⇒ nút mờ, không ẩn.** Ẩn nút làm người dùng tưởng chức năng
  không tồn tại; mờ kèm lý do (*"chưa gán nhà cung cấp"*) chỉ đúng chỗ cần sửa.
- **"Chưa đủ dữ liệu bán" là chip trung tính, không phải cảnh báo.** Thuốc mới nhập chưa
  có lịch sử là chuyện bình thường, không phải sự cố.
- **Không có nút "Tạo tất cả".** Đặt hàng là cam kết tiền. Mỗi dòng một quyết định.

### Trạng thái & hệ quả

| Trạng thái | Hành vi |
|---|---|
| Chưa chạy lần nào | *"Chưa tính đề xuất cho chi nhánh này."* + nút **Tính lần đầu** |
| Đang tính | Nút chuyển *"Đang tính…"*, khoá lại. Xong hiện tóm tắt: *đã xét 214 · đề xuất 7 · thiếu dữ liệu 31* (khớp `ReorderRunResponse`) |
| Rỗng tốt | *"Không mặt hàng nào cần đặt thêm."* + giờ tính. Đây là kết quả **tốt**, viết như tin tốt |
| Tạo nháp xong | Dòng rời danh sách + thông báo **"Đã tạo đơn mua nháp #PO-0412"** kèm liên kết. **Hoàn tác trong 10 giây** |
| Bỏ qua | Cần **một lần xác nhận** — đây là hành động che một cảnh báo tồn kho, không phải đóng thông báo |
| Số liệu cũ | Tính > 24 giờ ⇒ dải nhắc *"Số liệu tính từ hôm qua. Tính lại?"* |

---

## 6. Giao diện KHÔNG được nói gì

`docs/16 §4.1` cấm quảng bá tính năng backend chưa chạy thật. Đây là bản áp dụng cho hai màn này.

| Chủ đề | Backend thật | UI được nói | UI CẤM nói |
|---|---|---|---|
| Đề xuất đặt hàng | Công thức **tất định** từ tốc độ bán | "Đề xuất theo tốc độ bán" | 🔴 "AI dự báo nhu cầu" |
| Cảnh báo tương tác | Engine tất định; phần giải thích còn `MockLLMProvider` | "Cảnh báo tương tác & dị ứng" | 🔴 gọi là "AI" |
| Sổ thuốc kiểm soát | Có nghiệp vụ, **chưa mount router** | — không có mục menu nào | 🔴 vẽ màn hình sổ |
| Thanh toán online | Plugin tắt theo quyết định đã khoá | — chỉ tiền mặt | 🔴 hiện "sắp có VNPAY" |

🔴 **Ràng buộc này không phải chuyện chữ nghĩa.** Nhà thuốc mua phần mềm vì tin những gì
màn hình nói. Gọi một công thức chia trung bình là *"AI dự báo"* thì lần đầu đề xuất sai,
thứ mất đi không phải một tính năng — là **lòng tin vào mọi con số còn lại**.

---

## 7. 🔴 BẢY ĐIỂM CHAIN PHẢI CHỐT TRƯỚC KHI CODE

Không điểm nào tôi tự quyết được — mỗi cái đổi thì thiết kế đổi theo.

| # | Câu hỏi | Vì sao cần Chain |
|---|---|---|
| 1 | **Sprint 9 chỉ làm hai màn này?** | ROADMAP ghi *"dashboard + màn duyệt PO nháp"*. Bản này bám đúng vậy. Có thêm màn **đối soát tồn kho** (`GET /inventory/reconciliations` đã có API) không? |
| 2 | **Khoảng thời gian mặc định của bảng điều hành?** | Đề xuất **28 ngày**. "Tháng này" làm đầu tháng luôn trông như sụt doanh thu |
| 3 | **Quản lý xem được số liệu chi nhánh khác không?** | API cho phép chọn chi nhánh. Cho xem chéo là quyết định **quản trị**, không phải kỹ thuật — và nó đổi cả thanh chọn đầu màn |
| 4 | **Mức tải mục tiêu cho p95?** | Đo thật: đạt ở 8 luồng, **không đạt ở 16**. DoD *"p95 < 300 ms"* chưa nói mức tải nào nên **chưa quyết được đạt hay không**. Nhà thuốc pilot có bao nhiêu quầy đồng thời? |
| 5 | **Cột nào bắt buộc mã hoá?** | Diễn tập F-8: `phone` đã mã hoá, **`full_name` vẫn nguyên văn**. Tên người là dữ liệu cá nhân (Luật BVDLCN 91/2025). Chủ đích hay lỗ hổng? Câu trả lời đổi cách màn hình hiển thị tên khách |
| 6 | **Có cần chế độ tương phản cao?** | Bảng màu đã đạt WCAG AA. Nhưng màn rẻ dưới đèn huỳnh quang vẫn có thể khó đọc — thêm công tắc "nền trắng chữ đen" **rẻ nếu quyết ngay, đắt nếu thêm sau** |
| 7 | **Mascot gấu xuất hiện ở đâu?** | Gói bàn giao dùng **avatar mascot 40×40 tròn trong nav** + 22 px trong khu AI, và ghi rõ mascot hiện là **placeholder emoji 🐻**, cần asset thật. Xác nhận vị trí này? |
| 8 | 🔴 **M-1: nền "kem" (`docs/16`) hay `#EDEFE7` "KHÔNG phải kem" (gói bàn giao)?** | Hai văn bản chính thức nói ngược nhau. Mọi màn hình phụ thuộc câu trả lời |
| 9 | 🔴 **Dashboard nào là dashboard?** | Gói bàn giao đã có **`Beras Dashboard.dc.html`** riêng: khu Bán hàng + Tuân thủ + Trợ lý AI + chỉ báo mạng "Tán Cây". Bản thiết kế này là **dashboard analytics** (doanh thu / top thuốc / cảnh báo tồn / PO nháp) theo ROADMAP S9. **Hai màn khác nhau** — gộp làm một, hay là hai mục menu riêng? |
| 10 | 🔴 **Khu "Trợ lý AI" trong gói bàn giao có được dựng không?** | Mockup vẽ box tương tác thuốc và gọi thẳng là **"Trợ lý AI Dược sĩ"**. `docs/16 §4.1` **cấm** gọi engine tất định là AI khi backend còn `MockLLMProvider`. Mockup và quy tắc thương hiệu **đang mâu thuẫn** |

---

## 8. Bản thiết kế này CỐ Ý không làm gì

| Không làm | Vì sao |
|---|---|
| **Không đụng POS** | Trụ cột vững nhất, đang chạy, có e2e. Sửa nó trong sprint pilot là mang rủi ro vào đúng chỗ không được phép hỏng |
| **Không thiết kế màn chưa có API** | Sổ kiểm soát đặc biệt chưa mount router. Vẽ trước là tạo một lời hứa mà lịch không đỡ nổi |
| **Không có biểu đồ chuỗi thời gian** | `DashboardResponse` trả **tổng**, không trả chuỗi theo ngày. Muốn biểu đồ xu hướng phải đổi backend trước — quyết định riêng |
| **Không đặt mã màu cho mascot/đồ hoạ chi tiết** | `docs/16` ghi rõ phần này *"cần người làm thiết kế thật"* |
| **Không dựng lại 2 màn của gói bàn giao** | `Beras Dashboard` và `Beras Health Profile Consent` là **gói riêng, high-fidelity, đã chốt**. Chúng cần một mục công việc riêng, không gộp vào thiết kế S9 analytics này |

---

## 9. Nguồn đã đọc

| Nguồn | Vai trò |
|---|---|
| `00-Bookmark/design_handoff_beras/README.md` | **Bản chốt cuối** về token màu/chữ/spacing — mọi giá trị ở §3 lấy từ đây |
| `00-Bookmark/design_handoff_beras/reference/*.dc.html` | 3 mockup high-fidelity: style tile · dashboard · luồng đồng ý |
| `docs/16_BRAND_UI_GUIDE.md` | Nguyên tắc UI, bảng "được phép nói gì" (§5–§6 của tài liệu này) |
| `frontend/src/styles/tokens.css` | Token **đang chạy trong repo** — còn là giá trị tạm, xem M-2 |
| OpenAPI staging `localhost:8001` | Xác nhận từng endpoint và từng trường schema |
