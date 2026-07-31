# Màn Sơ đồ kho — 2026-07-31 (BERAS V2 Phase 1)

**Trước:** không có khái niệm vị trí nào. Đơn vị không gian nhỏ nhất hệ thống biết là
**chi nhánh**. `grep "shelf|bin|zone|location"` toàn repo = 0.

**Sau:** dựng được cây Kho → Khu → Kệ → Ô, đặt thứ tự đi lấy hàng.

Sinh lại: `node scripts/check-so-do-kho.mjs` (**nhóm GHI** — tạo vị trí thật).

## Đo được

| | desktop | mobile |
|---|---|---|
| Bỏ tầng Khu (Kho → Kệ thẳng) | ✓ | ✓ |
| Ô "01" dưới **hai kệ khác nhau** | 2/2 ✓ | 2/2 ✓ |
| Thứ tự **đi lấy hàng**, không phải bảng chữ cái | AA1(đi thứ 1) trước ZZ9(đi thứ 9) ✓ | ✓ |
| Ngừng kệ còn ô con ⇒ bị từ chối | ✓ | ✓ |
| Lỗi JS | 0 | 0 |

## Ba điều màn này cố ý làm khác thói quen

- **Không có ô sửa MÃ.** Mã bất biến — đổi mã buộc viết lại đường dẫn cả cây con. Hiện một
  ô rồi từ chối lưu còn tệ hơn không hiện.
- **Ô "thứ tự lấy hàng" đứng ngang hàng với mã**, không giấu trong trang con: nếu khó tìm
  thì không ai điền, và Pick List sau đó chỉ còn cách sắp theo bảng chữ cái.
- **Danh sách tầng con lọc theo tầng cha.** Bỏ tầng thì được, đảo tầng thì không.

## 🔴 Cổng đỏ hai lần, cả hai lần là lỗi PHÉP ĐO

1. `.first()` trên `li` lồng nhau lấy trúng **nhánh gốc**, nên hai lượt bấm "+ Thêm Ô" rơi
   vào cùng một kệ và lượt hai bị 409.
2. Sửa thành `.last()` vẫn sai: **dữ liệu lượt chạy trước còn sót** cũng có kệ "AA1"/"ZZ9",
   nên tìm toàn trang là tìm nhầm sang cây khác.

Vá đúng: **khoanh mọi locator trong đúng cây của lượt chạy này**. Bài học ghi lại thành
bình luận trong chính tệp cổng: *cổng phải tự cô lập khỏi dữ liệu nó để lại lần trước, đừng
giả định CSDL sạch.*

Cổng để lại 32 dòng kho thử trong `nt650v2` — **đã xoá bằng SQL**, giữ nguyên "TỦ KÍNH 1"
Chain tự tạo. Nay đã đăng ký vào **nhóm GHI** của `ui-gates.sh` nên không chạy mặc định.
