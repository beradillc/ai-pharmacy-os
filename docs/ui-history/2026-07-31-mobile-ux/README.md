# Giao diện điện thoại — 2026-07-31

Chain báo bốn việc: *ô nhập nằm cuối trang kéo rất lâu · cần xác nhận khi chốt đơn (hoặc
cho sửa trong 10 giây) · nút Giá và nút hoạt chất mất cân đối · GĐ chụp lại, phân tích, tối
ưu giúp.*

Đo lại: `node scripts/measure-mobile-ux.mjs` (chẩn đoán, đọc thuần).

## 🔴 Đo trước khi sửa — "kéo rất lâu" thành con số

| Màn | Cao trang | Số màn | **Phải kéo tới việc chính** |
|---|---|---|---|
| **Quầy** | 3465 | 4,1 | 🔴 **3,9 màn** ← nút Thanh toán |
| Danh mục | 2976 | 3,5 | 0,2 màn |
| Khách hàng | 1095 | 1,3 | 0,2 màn |
| Tồn kho | 3957 | 4,7 | 0,2 màn |
| Sơ đồ kho | 844 | 1,0 | 0,2 màn |

Phép đo khoanh vùng gọn hơn Chain mô tả: **chỉ màn quầy hỏng**, và hỏng nặng. Các màn khác
đã có ô nhập ở đầu trang. Nếu tin cảm giác "màn nào cũng vậy" thì đã sửa cả năm màn, trong
đó bốn màn không hỏng.

## Ba việc đã sửa

### 1. Quầy: **3,9 màn → 0 màn**

`position: sticky` cho giỏ hàng **đã có từ 29/07 và không làm gì cả** — sticky cần khoảng
trống trong container để trượt, mà lưới một cột cho mỗi ô một hàng cao đúng bằng chính nó.
Thay bằng **thanh đáy cố định**: `N món · tổng tiền · [Xem giỏ]`. Bấm mới mở giỏ thành tấm
phủ 85% màn.

### 2. Xác nhận hai bước khi chốt đơn

Chain cho chọn *hỏi lại xác nhận* hoặc *cho sửa trong 10 giây sau khi chốt*. **GĐ chọn hỏi
lại**: hoàn tác sau khi chốt là **huỷ một đơn đã trừ tồn kho và đã ghi doanh thu** — thao
tác đụng tiền và hàng, không phải mẹo giao diện, và làm nửa vời còn tệ hơn hỏi một câu.

Bấm *Thanh toán* → hiện khối tóm tắt (số món · tổng tiền · tiền thối) + *Sửa lại đơn*; bấm
lần hai mới gọi máy chủ. Khối tóm tắt đặt **ngay trên nút**, không phải hộp thoại che màn:
che mất thứ đang được xác nhận là bắt người ta xác nhận từ trí nhớ.

### 3. Danh mục thuốc: bảng → thẻ

Ảnh chụp cho thấy **nặng hơn "mất cân đối"**: cột "Giá niêm yết" bị cắt thành `GI`, hai nút
bị đẩy hẳn ra ngoài mép phải. Cổng cũ bỏ sót vì nó đo *trang có cuộn ngang không* — trang
thì không, nhưng bảng bên trong `overflow-x: auto` thì có, **và một nút chỉ với tới được
bằng cách cuộn ngang trong bảng là một nút không tồn tại với người dùng**.

Nay dưới 720px mỗi thuốc là một thẻ, hai nút chia đôi bề ngang. Nhãn đổi `Giá`→`Sửa giá`,
`Sửa`→`Hoạt chất` — nhãn cũ chỉ đọc được nhờ tiêu đề cột, mà thẻ thì không có tiêu đề cột.

**Cổng có phép kiểm mới**: `nút NẰM TRONG khung nhìn`, không phải "có trong DOM".

## 🔴 Phép đo sai ba lần trước khi đúng — và đó là phần đáng giữ

| Lần | Báo | Sự thật |
|---|---|---|
| 1 | quầy 2,0 màn | Đo nút "Thanh toán" trong giỏ **đang ẩn** |
| 2 | quầy 2,9 màn | Kiểm `position` của **chính cái nút** — nút `static`, chỉ **thanh chứa** mới `fixed` |
| 3 | ✓ 0 màn | Đi ngược lên cây cha tìm `fixed` |

Giữa lần 1 và 2 tôi còn vá CSS theo con số mà **chưa nhìn ảnh**. Ảnh cho thấy thanh đáy đã
chạy đúng từ đầu. Bài học: khi số và ảnh nói ngược nhau, **dừng lại xem ảnh** — kỷ luật #20
đã ghi đúng điều này, và tôi vẫn đi vòng ba lượt mới làm theo.

## Còn nợ, đo được

**Danh mục thuốc dài 11,4 màn** (trước là 3,5) — thẻ cao hơn hàng bảng. Sửa được chỗ bấm,
làm dài chỗ tìm. Chấp nhận được vì ô tìm nằm ở 0,2 màn nên **không ai duyệt bằng cách kéo**,
nhưng vẫn là một con số nên tiếp tục nén.
