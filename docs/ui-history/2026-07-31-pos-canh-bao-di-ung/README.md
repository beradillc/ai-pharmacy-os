# Cảnh báo dị ứng ở quầy (POS) — 2026-07-31

**Trước:** màn POS không có chữ "dị ứng" nào. Cổng cưỡng chế đã có ở máy chủ từ 30/07,
nhưng quầy vẫn là *"bấm hoàn tất rồi mới biết"* — đo được: 0 kết quả khi tìm chuỗi "dị ứng"
trong DOM ở cả hai khổ.

**Sau:** cảnh báo hiện ngay khi gắn khách + thêm thuốc, **trên** tổng tiền và nút Thanh toán.

Ảnh chụp Firefox thật qua LAN IP, dữ liệu thật trên `nt650v2`: khách **Jenny** khai dị ứng
Acid clavulanic, thuốc **Augmentin 625mg** chứa hoạt chất đó — tên thuốc không hề nhắc tới
nó, nên đây đúng là ca mà đọc tên không bắt được.

Sinh lại: `cd frontend && node scripts/check-pos-allergy.mjs`

## Bốn trạng thái phải phân biệt được

| Tình huống | Hiện gì | Vì sao không gộp |
|---|---|---|
| Chưa gắn khách | *không hiện gì* | bán vãng lai là ca thường, không có gì để đối chiếu |
| Đã kiểm, không xung đột | ✓ xanh, **mờ** | ca chạy nhiều nhất; tô đậm thì người bán quen mắt rồi thôi nhìn kỹ lúc nó đổi |
| **Chưa được phép kiểm** | ⚠️ vàng, "**chưa kiểm được**" | 🔴 trả `conflict_count = 0` **y hệt** ca sạch — gộp lại là nói dối người bán |
| Có xung đột | 🔴 đỏ + số lượng + mức nặng nhất + ô ghi lý do | |

## Đo được

| | desktop | mobile |
|---|---|---|
| Chưa gắn khách → không hiện cảnh báo | ✓ | ✓ |
| Khách dị ứng + Augmentin → hiện cảnh báo | ✓ | ✓ |
| Nút đổi thành "Ghi lý do để bán", **tắt** | ✓ | ✓ |
| Ghi lý do → nút bật lại "Thanh toán" | ✓ | ✓ |

Mức độ hiện **tiếng Việt** ("nặng nhất: Vừa"), dùng lại `severityLabel` của màn Sức khoẻ —
thu ngân không phải tự dịch "MODERATE" đúng lúc cần quyết nhanh nhất.

Màu cảnh báo dùng `--beras-warning-ink` chứ không `--beras-warning`: kiểm tương phản trong
`tokens.css` đo được cặp gốc trên nền vàng nhạt chỉ đạt **2,82** (trượt AA). Đây là cảnh báo
an toàn thuốc đọc dưới đèn huỳnh quang ở quầy.

## 🔴 Nút này KHÔNG phải cổng

Cưỡng chế thật vẫn ở máy chủ (`complete_sale` → 422), quyết lại từ chính đơn đang lưu. Nút
tắt ở đây chỉ để đỡ một lượt đi mạng chắc chắn bị từ chối. Giỏ có thể đổi sau lượt kiểm, và
một client hoàn toàn có thể không gọi.
