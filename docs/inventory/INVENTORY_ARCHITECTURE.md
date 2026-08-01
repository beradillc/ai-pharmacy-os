# Kiến trúc kho — hai sổ, một sự thật

> Tệp này giải thích **vì sao** tồn kho có hai bảng, và đâu là bất biến giữa chúng. Viết
> 2026-08-01, sau khi BERAS V2 chạy được đầu-cuối.

## Hai sổ

| Sổ | Bảng | Câu hỏi nó trả lời |
|---|---|---|
| Sổ **lô** | `stock_balances` | *"Còn bao nhiêu của lô này?"* — nguồn của FEFO, báo cáo, đề xuất nhập |
| Sổ **vị trí** | `stock_at_location` | *"Lô này nằm ở ô nào, bao nhiêu?"* — nguồn của lấy hàng, kiểm kê theo ô |

🔴 **Vì sao không gộp thành một cột `location_id` trong `stock_balances`** (quyết định
2026-08-01, §7cu #2): thêm cột đó làm vỡ khoá `uq_balance_batch`, và vỡ nó thì **phá FEFO,
báo cáo và đề xuất nhập cùng lúc**. Một lô nằm ở ba ô là chuyện bình thường; một lô có ba
dòng số dư thì không.

## Bất biến

**Tổng đã xếp ô của một lô ≤ tồn của lô đó.** Vỡ bất biến này nghĩa là màn lấy hàng chỉ
người ta tới một ô không có hàng. Cưỡng chế ở `ensure_can_put_away`, có test đơn và test
đầu-cuối qua HTTP.

Phần chênh gọi là **chưa xếp ô** (`chua_xep_o`) — **hiện ra được, không bị giấu**. Hàng nhận
về mà chưa ai xếp lên kệ là trạng thái có thật của mọi nhà thuốc; giấu nó đi thì người ta
mất niềm tin vào con số tồn.

## Ranh giới module

`inventory` **không** import `location`. Sơ đồ ô đi qua port `LocationInfoProvider`, cài đặt
ở `api/v1/cross_module.py`. Đây là ràng buộc do `import-linter` canh, không phải quy ước.

## Loại chuyển động

`MovementType` **không** thêm giá trị mới cho khởi tạo tồn kho hay kiểm kê — chúng dùng
`ref_type` (`INIT`, `COUNT`). Vì sao: thêm một loại buộc **mọi chỗ đang phân nhánh theo
`type`** phải biết về nó; cái khác nhau giữa chúng là *ý nghĩa*, không phải *tác động lên
số dư*.

## Bản đồ tệp

| Tính năng | Tài liệu |
|---|---|
| Sơ đồ Kho→Khu→Kệ→Ô | [STORAGE_LOCATION.md](STORAGE_LOCATION.md) |
| Nhận hàng gắn ô ngay | [SHELF_FIRST_ENTRY.md](SHELF_FIRST_ENTRY.md) |
| Khởi tạo tồn lần đầu | [STOCK_INITIALIZATION.md](STOCK_INITIALIZATION.md) |
| Kiểm kê theo ô | [CYCLE_COUNT.md](CYCLE_COUNT.md) |
| Lấy hàng | [PICKING_ASSIST.md](PICKING_ASSIST.md) · [PICK_LIST.md](PICK_LIST.md) |
| Sơ đồ trực quan (chưa làm) | [LOCATION_MAP.md](LOCATION_MAP.md) |
| Nhập thông minh (chưa làm) | [SMART_PURCHASE.md](SMART_PURCHASE.md) |
