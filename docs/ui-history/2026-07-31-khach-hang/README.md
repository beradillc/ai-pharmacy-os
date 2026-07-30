# Màn Khách hàng — 2026-07-31

Ảnh chụp **Firefox thật**, qua LAN IP, trên `nt650v2` (595 hoá đơn, dữ liệu thật).
Khổ: desktop 1440×900 · điện thoại 390×844, `deviceScaleFactor: 2`.

Sinh lại bằng: `cd frontend && node scripts/shot-desktop-mobile.mjs`

## Đo được, không phải cảm nhận

| Chỉ số | Trước | Sau |
|---|---|---|
| Bảng khách tràn ngang (mobile) | **322px** | **0px** |
| Số cột | 5 (có cột nút) | **4** — Họ tên · Điện thoại · Điểm · Dữ liệu |
| Dấu ✓/✗ lệch tâm ô | 48px desktop · 21px mobile | **0px** |
| Ô chọn "Mức độ" tràn | **95px** | không còn `<select>` |
| Bảng chọn hoạt chất chiếm màn | 100% (bộ chọn hệ điều hành) | **57–61%**, 3 lối đóng |
| Bệnh nền chọn cùng lúc | 1 | **nhiều** |
| Khoảng trắng dọc thừa (bảng Đồng ý) | khối chữ cao 260px | **12px** |
| Tiêu đề/ô bị cắt chữ | `DỮ LIỆU` cắt 4px | **0** |

## 🔴 Hai lần ảnh và phép đo nói ngược nhau

1. **Ảnh nói sai:** thanh điều hướng trông như đè lên giữa bảng. Đo ra thì không che gì —
   ảnh `fullPage` vẽ phần tử `position: fixed` đúng một lần ở vị trí cố định của nó.
2. **Phép đo nói sai:** "bảng không tràn khung" báo ✓, nhưng mắt thấy `DỮ LIỆU` bị cắt.
   Tràn ở mức **ô** khác tràn ở mức **bảng**, và phép đo khi ấy chỉ biết cái sau.

Cả hai đều đúng họ với kỷ luật #15: ảnh là cổng, nhưng **sau khi nhìn vẫn phải đo** — và
**phải đo cả chính phép đo**.
