# Kho — nhãn, tên thuốc, gộp menu (P2, 2026-08-01)

Ba lệnh Chain giao 01/08: `#3` nhãn *Sắp xếp* · `#4` tên thuốc thay số lô · `#5 #6` gộp menu.

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Nút cất hàng | "Cất vào ô" · xác nhận "Đã cất N vào…" | **"Sắp xếp"** · "Đã sắp xếp N vào…" |
| `/kiem-ke` cột đầu | `Số lô` — `KK75193` | **`Thuốc` — `Alaxan`**, dòng phụ `Lô KK75193` |
| `/so-do-kho` xem trong ô | `Số lô` | **`Thuốc`**, dòng phụ `Lô …` |
| Menu Kho | 5 mục: Kho · Danh mục · Nhập hàng nhanh · Khởi tạo tồn kho · Kiểm kê · Sơ đồ kho | 4 mục: Kho · Danh mục · **Nhập hàng** · **Sơ đồ & Kiểm kê** |
| Đi lại giữa hai màn gộp | không có | dải tab ngay dưới tiêu đề |

Menu tổng: **15 → 13 mục**.

## Gộp menu KHÔNG đổi một URL nào

Kỷ luật #17 cấm đổi tên route cũ, và bốn đường dẫn đang nằm trong dấu trang, tài liệu và
**tám cổng trình duyệt**. Gộp là việc của *menu*: hai màn vẫn là hai màn, chỉ vào chung một
cửa qua `NavItem.alsoActiveFor` và dải tab `TabManGop`.

| URL | Sau P2 |
|---|---|
| `/nhap-nhanh` · `/khoi-tao-ton` · `/kiem-ke` · `/so-do-kho` | **200 cả bốn** (kiểm bằng curl) |

## Ảnh

| Tệp | Cảnh |
|---|---|
| `*-menu.png` | menu sau khi gộp |
| `*-so-do-kho.png` · `*-kiem-ke.png` | dải tab + tên thuốc |
| `*-nhap-nhanh.png` | dải tab nhóm Nhập hàng |
| `*-ton-kho.png` | nhãn "Sắp xếp" |

Hai khổ: 390×844 và 1440×900, `deviceScaleFactor: 2`.

## Một cổng đỏ KHÔNG phải hồi quy — và cách chứng minh

`check-vi-tri-lay-hang` đỏ ở khổ desktop. Thay vì đoán, chạy lại trên cây **trước P2**
(`git stash push --include-untracked`): `BASELINE_EXIT=1`, hỏng y hệt.

Nguyên nhân: cổng chọn dòng bằng `nth(0)` mù. Trên CSDL đã chạy vài lượt, dòng đầu là lô
**đã xếp hết vào ô** — FEFO đẩy lô sắp hết hạn lên đầu, mà lô đó chính là lô các lượt trước
vừa cất. Máy chủ từ chối **đúng**; cổng đỏ vì **kỳ vọng sai**. Nay chọn theo tên mặt hàng,
mỗi khổ một mặt hàng riêng.
