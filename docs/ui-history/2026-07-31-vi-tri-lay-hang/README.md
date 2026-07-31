# Tồn theo vị trí + quầy thấy chỗ lấy — 2026-07-31 (BERAS V2 Phase 2)

Chain hỏi: *"Chọn Kho, Tủ, tầng, ô, sao chưa thấy ghi nhận vị trí đó có thuốc gì, số lượng
bao nhiêu, hạn dùng ra làm sao? sau đó qua lập đơn bán có ngay vị trí lấy thuốc cho dễ."*

Sinh lại: `node scripts/check-vi-tri-lay-hang.mjs` (**nhóm GHI** — cất hàng thật).

## Trọn vòng, đo qua trình duyệt thật

| Bước | desktop | mobile |
|---|---|---|
| Cất hàng xong nói ra **số chưa xếp ô** | ✓ *"Đã cất 2 vào VD35416/O35416. Còn 2.246 chưa xếp ô."* | ✓ |
| Mở ô → thấy đúng lô và hạn dùng | ✓ | ✓ |
| Quầy hiện **📍 ô · lô · HSD · còn** | ✓ | ✓ |
| Lỗi JS | 0 | 0 |

Dòng thật ở quầy:
`📍 VD35416/O35416 · lô MET300-2026 · HSD 13/8/2026 · còn 2 · +3 chỗ khác`

## Ba điều cố ý

- **Quầy chỉ hiện MỘT chỗ**, kèm *"+N chỗ khác"*. Người đứng quầy cần một địa chỉ để đi,
  không cần một bảng để đọc — liệt kê hết là biến thông tin thành nhiễu.
- **Màn hình không sắp lại** danh sách. FEFO là quy tắc nghiệp vụ, máy chủ đã sắp; mỗi màn
  tự sắp lấy là mỗi màn có cơ hội sắp sai một kiểu khác nhau.
- **"Chưa xếp ô" ≠ "hết hàng".** Thuốc còn 100 hộp nhưng chưa ai xếp vào chỗ nào thì quầy
  nói *"chưa xếp ô — hỏi kho"*, KHÔNG nói hết hàng. Nói sai chỗ này là đi từ chối một khách
  còn mua được.

## 🔴 Cổng đỏ ba lần, và lần thứ ba mới là bài học đáng giữ

1. `selectOption` không nhận RegExp cho nhãn — lỗi API của tôi.
2. Hai khổ cùng lấy **một lô**, nên sau lượt desktop thì lô đó nằm ở hai ô; quầy hiện ô của
   lượt trước kèm *"+1 chỗ khác"*. **Sản phẩm đúng.** Tách lô ra cho mỗi khổ.
3. Vẫn đỏ — vì cổng **tự tích luỹ dữ liệu qua các lượt chạy trước**, cùng một lô nay nằm ở
   ba ô của ba lượt. Đến đây mới thấy: khẳng định *"ô của lượt này phải đứng đầu"* là một
   khẳng định **không kiểm chứng được**, vì thứ tự do FEFO quyết chứ không do cổng quyết.

Sửa đúng là đổi khẳng định cho khớp **hợp đồng thật** của màn hình: hiện một đường dẫn thật,
đủ lô/HSD/còn, và **nếu còn chỗ khác thì phải nói ra**. Im lặng cắt bớt danh sách mới là lỗi.

Cổng để lại 6 vị trí + 6 dòng tồn + 14 chuyển động trong `nt650v2` — **đã xoá bằng SQL**,
`stock_movements` về đúng 1499 như trước khi chạy, giữ nguyên "TỦ KÍNH 1" của Chain.
