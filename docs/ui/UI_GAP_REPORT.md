# UI_GAP_REPORT — Khoảng cách giữa hiện trạng và yêu cầu

> PHASE 1. Xếp theo **mức chặn**, không theo thứ tự mục trong yêu cầu.
> Cột "Chi phí" là ước lượng của tôi, đơn vị nửa ngày làm việc.

## Bảng khoảng cách

| # | Khoảng cách | Mức | Chi phí | Ghi chú |
|---|---|---|---|---|
| **G-01** | Không khai báo `viewport` | 🟡 VỪA *(hạ từ CHẶN)* | 0,1 | **Đã đo lại:** Next 16 tự phát `width=device-width, initial-scale=1`, nên mobile KHÔNG hỏng — xem đính chính `UI_CURRENT_STATE.md` §6.1. Khai báo tường minh chỉ thêm `viewport-fit=cover` (cần cho bottom nav trên iPhone) + `theme-color` |
| **G-02** | Hai hệ điều hướng rời nhau (`(pos)` vs `(app)`) | 🔴 CHẶN | 2 | Yêu cầu mục 6 cấm thẳng. Phải gộp về một shell trước khi thêm bottom nav |
| **G-03** | Không có tầng component | 🔴 CHẶN | 3 | 17 component yêu cầu, 0 tồn tại. Mọi mục khác đều phụ thuộc mục này |
| **G-04** | Thiếu 5/6 nhóm token (spacing, radius-scale, shadow, typography, motion) | 🟠 CAO | 1 | Có màu rồi; phần còn lại là viết ra thang, không phải phát minh |
| **G-05** | Vùng chạm < 44px ở ≥10 chỗ | 🟠 CAO | 0,5 | Sửa ở tầng token + `Button`, không phải sửa từng chỗ |
| **G-06** | Không có Quick Actions | 🟠 CAO | 1 | 8 hành động, 4 cột mobile |
| **G-07** | KPI card không tái dùng được, thiếu `trend`/`comparison`/`status` | 🟠 CAO | 1 | Backend **chưa có số liệu so sánh kỳ trước** — xem G-14 |
| **G-08** | Không có Compliance Center | 🟠 CAO | 2 | 12 endpoint `compliance` chưa có màn nào |
| **G-09** | Không có Revenue Chart theo thời gian | 🟠 CAO | 2 | Backend **chưa có endpoint doanh thu theo ngày dạng JSON** — xem G-15 |
| **G-10** | Không có transition / `prefers-reduced-motion` | 🟡 VỪA | 1 | 0 lần xuất hiện trong CSS hiện tại |
| **G-11** | Không có `AI Assist` UI | 🟡 VỪA | 2 | 5 endpoint `clinical` sẵn; luồng accept/reject đã có ở backend |
| **G-12** | Không có Recent Transactions trên dashboard | 🟡 VỪA | 0,5 | `GET /sales` đã có (Sprint 10) — chỉ là màn |
| **G-13** | Không có focus state, không kiểm keyboard | 🟡 VỪA | 0,5 | |
| **G-14** | **KPI "so với hôm qua" chưa có nguồn dữ liệu** | 🟠 CAO | — | Xem §"Khoảng trống backend" |
| **G-15** | **Doanh thu theo ngày chưa có endpoint JSON** | 🟠 CAO | — | Nt |
| **G-16** | Không có dark mode | ⚪ THẤP | — | Yêu cầu **không** đòi. Ghi lại để không ai tưởng đã có |
| **G-17** | 2 chỗ hard-code `#fff` | ⚪ THẤP | 0,1 | |
| **G-18** | 0 test frontend | 🟠 CAO | 2 | Không nằm trong yêu cầu, nhưng DoD nói *"không kết luận hoàn thành nếu build/test chưa pass"* — hiện **không có test nào để pass** |

## 🔴 Khoảng trống BACKEND mà yêu cầu UI đang giả định là có

Đây là phần quan trọng nhất của báo cáo này. Ba mục dưới đây **không sửa được bằng
CSS**; nếu bỏ qua, giao diện sẽ phải bịa số hoặc hiện ô trống.

| Mã | Yêu cầu UI đòi | Backend có gì | Cách xử lý đề xuất |
|---|---|---|---|
| **B-01** | `KpiCard.comparison` + `trend` ("so với hôm qua ↑12%") | `GET /analytics/dashboard` trả **một** `revenue_total` cho **một** khoảng ngày. Không có kỳ đối chiếu | **Gọi hai lần** (kỳ này / kỳ trước) từ FE và tự tính chênh lệch. Không đổi backend, không đổi code sprint. Nếu sau này thấy tốn, mới thêm `compare_to` ở API |
| **B-02** | `RevenueChart` — doanh thu **theo ngày** | Chỉ có `GET /reports/revenue/export` trả **CSV** (đã có `granularity=DAY`), không có JSON | 🔴 **Cần một endpoint JSON mới** hoặc FE parse CSV. Parse CSV ở FE là nợ kỹ thuật xấu. **Đề xuất: thêm `GET /reports/revenue` (JSON) dùng lại y nguyên `revenue_report_rows` đã có** — không đụng nghiệp vụ, chỉ thêm một lớp trình bày |
| **B-03** | `ComplianceCard` — "cần xử lý" gộp nhiều loại | 12 endpoint compliance nhưng **không có endpoint tổng hợp việc-cần-làm**; cảnh báo cận hạn nằm ở `inventory`, tồn thấp nằm ở `analytics` | **Gộp ở FE từ 3 lời gọi đã có** (`/inventory/alerts/near-expiry`, `/analytics/dashboard`, `/analytics/reorder/suggestions`). Không tạo endpoint tổng hợp vội — gộp ở backend là quyết định kiến trúc, cần biết hình dạng thật trước |

**Nguyên tắc tôi đề nghị Chain chốt:** trong đợt UI này, **ưu tiên tuyệt đối là
không đổi nghiệp vụ**. B-01 và B-03 giải quyết hoàn toàn ở FE. Chỉ **B-02** cần
thêm một endpoint đọc — và nó là lớp trình bày của một hàm đã tồn tại và đã có test,
không phải nghiệp vụ mới.

## Cái yêu cầu đòi mà hệ thống ĐÃ có sẵn (không mất công)

| Yêu cầu | Đã có |
|---|---|
| Mục 13 — UI không quyết định authorization | ✅ Menu lọc theo `session.permissions`; mọi endpoint `require_permission` ở service. Không đổi gì |
| Mục 12 — skeleton loading | ✅ 6/8 màn đã có |
| Mục 12 — không tải toàn bộ data khi mở | ✅ Mỗi hook một endpoint, có `staleTime`, phân trang 50 dòng |
| Mục 11 — không chỉ dùng màu để biểu thị trạng thái | ✅ Chip luôn có chữ kèm màu |
| Mục 10 — không tràn ngang | ⚠️ `body { overflow-x: hidden }` + bảng cuộn trong khung. Chưa ai nhìn ở 390px thật — nhưng KHÔNG phải vì G-01 (xem đính chính) |

## Thứ tự làm đề nghị

```
G-04 (token)  →  G-01 (viewport, đi kèm)  →  G-03 (component nền: Button/Card/DataTable/States)
   →  G-02 (gộp shell + Sidebar/BottomNav)  →  G-06 (quick actions)  →  G-07+B-01 (KPI)
   →  G-12 (recent transactions)  →  G-08+B-03 (compliance card)  →  B-02 + G-09 (chart)
   →  G-10 (transition)  →  G-11 (AI assist)  →  G-05/G-13 (chạm + a11y quét lại)
```

Lý do thứ tự: G-04→G-03 là nền của tất cả; G-01 đi kèm vì nó rẻ và cần cho vùng an
toàn iPhone của bottom nav; chart để sau vì nó là mục duy nhất chạm tới backend.
