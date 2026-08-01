# Sơ đồ kho trực quan (BERAS V2 Phase 12)

> Trạng thái: **CHƯA LÀM.** Tệp này là *thiết kế*, không phải mô tả thứ đang chạy. Viết
> 2026-08-01 để Phase 12 không phải bắt đầu từ trang trắng.

## Hiện có gì

`/so-do-kho` hiện sơ đồ dạng **cây danh sách**: Kho → Khu → Kệ → Ô, mỗi cấp một `<li>` lồng
nhau. Dựng được, sửa được, xem được hàng trong ô. Đủ dùng cho một nhà thuốc vài chục ô.

## Thiếu gì

Cây danh sách trả lời *"ô A01 ở đâu trong cấu trúc"* nhưng không trả lời **"ô A01 ở đâu
trong phòng"**. Với một kho vài trăm ô, người mới vào làm cần cái thứ hai.

## Đề xuất — và một cảnh báo trước

**Cảnh báo:** một sơ đồ mặt bằng thật đòi **toạ độ**, mà toạ độ thì phải có người **đo và
nhập**. Nếu không ai nhập, tính năng sẽ hiện một lưới ô vuông xếp theo thứ tự bảng chữ cái —
trông như bản đồ nhưng không phải bản đồ, và đó **tệ hơn không có**: người ta tin vào nó.

Vậy nên đề xuất chia hai mức, làm mức 1 trước và chỉ làm mức 2 khi có người thật sự đo:

| Mức | Cần dữ liệu gì | Cho được gì |
|---|---|---|
| **1 — lưới theo `pick_order`** | không cần gì thêm (đã có) | Nhìn một lượt thấy toàn bộ ô, ô nào trống/đầy/cận hạn tô màu khác nhau. Thứ tự trái→phải đúng thứ tự đi lấy |
| **2 — mặt bằng thật** | thêm `x`, `y`, `rong`, `cao` cho mỗi ô | Bản đồ đúng tỉ lệ phòng |

Mức 1 dùng lại **toàn bộ** dữ liệu đang có và trả lời được câu hỏi hay dùng nhất: *"chỗ nào
đang trống để xếp hàng mới"*.

## Ràng buộc kế thừa

- Không đổi route `/so-do-kho` (kỷ luật #17) — sơ đồ trực quan là **một tab** cạnh cây hiện
  tại, không thay thế nó. Cây vẫn là chỗ duy nhất **sửa** cấu trúc.
- Quyền: `location.read` để xem, `location.write` để sửa — không tạo quyền mới.
- Cổng: kỷ luật #21 — ô phải **nhìn thấy được** ở khổ 390px, không chỉ có trong DOM. Một
  lưới 200 ô trên màn điện thoại cần cuộn hai chiều, và cuộn hai chiều là chỗ dễ làm mất
  thứ người ta đang tìm.
