# Cài đặt → Lưu trữ + chụp đơn không cần khách — 2026-07-31 (lượt hai)

Chain chốt bốn điều: màn xem nằm trong **Cài đặt → Lưu trữ**, dữ liệu hiện **theo phân
quyền** (chủ chuỗi xem toàn bộ chi nhánh); thời hạn lưu **vĩnh viễn tạm thời**; thông báo
cho khách **bằng miệng** là đủ; **không có SĐT vẫn chụp được đơn**.

Ảnh Firefox thật qua LAN IP, CSDL `nt650v2`.
Sinh lại: `node scripts/check-luu-tru.mjs` · `node scripts/check-pos-rx-photo.mjs`

## Trước / sau

| | Trước | Sau |
|---|---|---|
| Xem lại ảnh đã chụp | ❌ endpoint chạy được nhưng **không màn nào gọi** | Cài đặt → Lưu trữ |
| Phạm vi dữ liệu | — | Chủ chuỗi: **toàn bộ chi nhánh**. Dược sĩ chi nhánh: chi nhánh mình. Thu ngân: **không mở được** |
| Khách vãng lai mua ETC | Không chụp được (bắt gắn khách) | **Chụp được**, cột Khách hiện *"— không để lại số —"* |

## Đo được

| | desktop | mobile |
|---|---|---|
| Lối vào từ Cài đặt | ✓ | ✓ |
| Màn nói rõ phạm vi đang xem | ✓ | ✓ |
| Ảnh **tải sẵn** trong danh sách | **0** ✓ | 0 ✓ |
| Bấm Xem ảnh ⇒ trình duyệt giải mã được (`naturalWidth`) | **8px** ✓ | 8px ✓ |
| Lỗi JS | 0 | 0 |

Kiểm bằng SQL trên `nt650v2` sau lượt chạy thật: `1` đơn · `1` có ảnh · `1` không khách ·
ảnh mã hoá **1167 byte** · audit `RX_IMAGE_ATTACHED=1`, `RX_IMAGE_VIEWED=2`.

## Ba điều màn Lưu trữ cố ý KHÔNG làm

- **Không gửi `branch_id` lên máy chủ.** Phạm vi do máy chủ quyết từ `archive.read.chain`.
  Cho màn hình chọn chi nhánh là mở một đường để máy khách sửa tay đòi xem chi nhánh khác.
- **Không tải sẵn ảnh cho cả danh sách.** Mỗi lượt mở ghi một dòng `RX_IMAGE_VIEWED`; tải
  sẵn sẽ biến sổ audit thành vô nghĩa — ai mở màn cũng thành người đã xem mọi ảnh.
- **Không hiện chẩn đoán trong danh sách.** Nó nằm trong ảnh, và ảnh thì phải bấm mở.

## 🔴 Hai lần cổng xanh/đỏ vì lý do sai, trong cùng một bước

**Một — cổng Lưu trữ xanh với 0 dòng.** Khẳng định quan trọng nhất của nó (*ảnh mở ra và
trình duyệt giải mã được*) **chưa hề chạy**. Một cổng xanh vì không có gì để đo là cổng
xanh vì lý do sai. Đã viết `write-rx-photo.mjs` (nhóm **GHI**) chạy trọn luồng thật —
chọn tệp ở quầy → `canvas` nén → base64 → `POST /prescriptions` → `PUT /image` — rồi mới
đo lại. Bốn lớp đó không lớp nào chứng minh được ba lớp kia.

**Hai — luồng ghi đỏ, và hỏng là ảnh mẫu của tôi.** Màn hình báo đúng và đọc được:
*"Không lưu được ảnh — The image could not be decoded"*. Chuỗi base64 tôi gõ tay vào test
không phải PNG hợp lệ. Sinh PNG thật bằng `zlib` (74 byte) thì luồng chạy trọn ngay.
**Xử lý lỗi của sản phẩm hoạt động đúng** — đó là thứ lần đỏ này chứng minh được.

Và một kỳ vọng cũ phải sửa: `check-pos-rx-photo` vẫn canh *"chưa gắn khách ⇒ chưa cho
chụp"*, đúng thứ Chain vừa bỏ. Sửa kỳ vọng kèm lý do, không xoá khẳng định — thứ còn lại
chặn nút là **tên bác sĩ**, trường duy nhất máy chủ vẫn bắt buộc.
