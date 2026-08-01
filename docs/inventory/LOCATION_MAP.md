# Sơ đồ kho trực quan (BERAS V2 Phase 12)

> Trạng thái: **MỨC 1 ĐÃ CHẠY** (2026-08-01) — lưới ô trên `/so-do-kho`, xếp theo thứ tự đi
> lấy, bốn trạng thái phân biệt bằng cả màu lẫn viền. **Mức 2 (mặt bằng thật) CHƯA LÀM** và
> có điều kiện chặn, đọc kỹ mục "Cảnh báo" dưới.

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
| **1 — lưới theo `pick_order`** ✅ | thêm đúng một endpoint tổng hợp | Nhìn một lượt thấy toàn bộ ô, ô nào trống/có hàng/cận hạn/đã ngừng. Thứ tự trái→phải đúng thứ tự đi lấy |
| **2 — mặt bằng thật** 🚧 | thêm `x`, `y`, `rong`, `cao` cho mỗi ô **và có người đo** | Bản đồ đúng tỉ lệ phòng |

Mức 1 dùng lại **toàn bộ** dữ liệu đang có và trả lời được câu hỏi hay dùng nhất: *"chỗ nào
đang trống để xếp hàng mới"*.

## Ràng buộc kế thừa

- Không đổi route `/so-do-kho` (kỷ luật #17) — sơ đồ trực quan là **một tab** cạnh cây hiện
  tại, không thay thế nó. Cây vẫn là chỗ duy nhất **sửa** cấu trúc.
- Quyền: `location.read` để xem, `location.write` để sửa — không tạo quyền mới.
- Cổng: kỷ luật #21 — ô phải **nhìn thấy được** ở khổ 390px, không chỉ có trong DOM. Một
  lưới 200 ô trên màn điện thoại cần cuộn hai chiều, và cuộn hai chiều là chỗ dễ làm mất
  thứ người ta đang tìm.


---

## Mức 1 — đã chạy, làm gì

`GET /api/v1/inventory/locations/summary` — **một** lượt gọi trả tóm tắt **mọi ô đang giữ
hàng**: `so_lo`, `tong_so_luong`, `hsd_gan_nhat`.

🔴 Vì sao là một endpoint riêng chứ không gọi `/locations/{id}/stock` cho từng ô: một kho
vài trăm ô nghĩa là vài trăm lượt đi-về cho **một** màn hình đang có người đứng chờ. Gộp ở
tầng CSDL (`GROUP BY location_id`) là chỗ duy nhất làm được rẻ.

Ô **trống không có dòng**. Màn hình biết chúng trống bằng cách đối chiếu với `GET /locations`
— *"không có dòng"* rẻ hơn *"dòng với số 0"* cho một kho mà phần lớn ô trống.

### Ba thứ cố ý KHÔNG có

| Không có | Vì sao |
|---|---|
| **Phần trăm đầy** | Kho chưa khai sức chứa của ô nào. Một phần trăm tính từ con số không có thật thì **tệ hơn không hiện gì** — người ta tin vào nó |
| **Toạ độ mặt bằng** | Xem cảnh báo ở trên: toạ độ phải có người **đo và nhập** |
| **Thay thế cây danh sách** | Lưới trả lời *"chỗ nào trống"*; cây trả lời *"ô A01 nằm đâu trong cấu trúc"*. Hai câu khác nhau. Cây vẫn là chỗ **duy nhất sửa** cấu trúc |

### Ngưỡng cận hạn

**90 ngày** — cùng con số màn Tồn kho đang dùng. Hai màn hai ngưỡng nghĩa là hai câu trả lời
cho một câu hỏi, và người dùng sẽ tin cái nào tiện hơn.

### Tiếp cận người khiếm thị

Bốn trạng thái phân biệt bằng **cả màu nền lẫn viền** (nét liền/đậm/đứt) — người mù màu đọc
được viền. Mỗi ô có `aria-label` nói ra bằng chữ: *"TỦ KÍNH 1/A01 — 2 lô, còn 270, cận hạn
20 ngày"*. Màu là thứ trình đọc màn hình không nghe được.
