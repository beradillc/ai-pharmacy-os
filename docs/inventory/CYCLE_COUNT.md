# Kiểm kê theo ô (BERAS V2 Phase 11)

> Ngày: 2026-08-01 · Màn `/kiem-ke` · 7 endpoint dưới `/api/v1/inventory/counts`

## Quy tắc trung tâm: chênh lệch CHỜ DUYỆT

```
ĐANG ĐẾM ──nộp──> CHỜ DUYỆT ──duyệt──> ĐÃ DUYỆT (sinh ADJUST)
                          └─từ chối──> TỪ CHỐI (không đụng tồn kho)
```

Con số đếm được là một **lời khai**, không phải một **sự thật**. Đếm sót một hộp nằm khuất
sau lô khác thì hệ thống sẽ ghi nhận mất hàng — và một khi đã thành chuyển động `ADJUST` thì
nó nằm trong sổ vĩnh viễn, kèm giá vốn. Chi phí của một bước duyệt là vài giây; chi phí của
một lần tự áp sai là một dòng mất mát giả trong báo cáo mà không ai truy được nữa.

Không có đường từ CHỜ DUYỆT về ĐANG ĐẾM: sửa một phiên đã nộp thì con số *"sổ ghi bao nhiêu
tại lúc nộp"* mất nghĩa. Đếm lại là **một phiên mới** — rẻ, và để lại vết cả hai lần.

## Ba quyết định nghiệp vụ

| Quyết định | Vì sao |
|---|---|
| Đếm lại cùng lô thì **đè**, không cộng dồn | Người đếm lại là người vừa phát hiện mình đếm sai, không phải người tìm thấy thêm hàng. 3 rồi 5 ra 8 trông y hệt một lô thật sự có 8 |
| Số sổ chốt lúc **nộp**, không lúc duyệt | Giữa hai mốc có thể có bán hàng. Chốt lúc duyệt thì chênh lệch nuốt luôn số đã bán, và người duyệt nhìn vào một con số không ứng với thời điểm nào có thật |
| Người đếm **được** tự duyệt phiếu mình | Nhà thuốc nhỏ chỉ có một người; chặn thì tính năng vô dụng với nhóm khách hàng đông nhất. Thay vào đó lưu **cả hai tên** và màn hình nói ra *"(cùng một người)"* — làm cho thấy được thay vì cấm |

## Vì sao KHÔNG dùng lại `stock_reconciliation_needed`

Bảng đó mang `grn_id` **NOT NULL** — nó là cờ cho *một phiếu nhập không trọn vẹn*, không
phải bản ghi sai lệch tổng quát. Nới thành nullable là sửa lược đồ của một thứ đang chạy và
đang có test ⇒ kỷ luật #17 bảo phải hỏi Chain. Hai bảng mới rẻ hơn và không đụng gì.

## `MovementType.ADJUST` — lần đầu được dùng

`ADJUST` có trong enum từ **commit đầu tiên** của dự án và **0 call site** cho tới đây (kỷ
luật #16 tìm ra bằng `grep`). Duyệt ghi `ADJUST` với `ref_type='COUNT'`.

Ba thứ đi **cùng một giao dịch**, thiếu một là hai sổ lệch nhau:
`stock_balances` · `stock_at_location` · một `StockMovement`.

Dòng **khớp** không sinh chuyển động nào — ghi một `ADJUST` bằng 0 vào sổ chỉ-ghi-thêm là
rác vĩnh viễn.

## Quyền

| Việc | Quyền |
|---|---|
| Xem phiên | `inventory.read` |
| Mở phiên · đếm · nộp | `inventory.receive` |
| Duyệt · từ chối | `inventory.reconcile` |

Cả ba đã có trong `INVENTORY_PERMISSIONS` và đã seed — **không đụng seeding**, tránh đúng lớp
lỗi §7l mà kỷ luật #7 canh.

## Tương thích ngược

| Câu hỏi | Trả lời |
|---|---|
| Frontend cũ còn chạy? | Có — thêm màn mới |
| API cũ còn chạy? | Có — không endpoint nào đổi hình dạng lẫn ngữ nghĩa |
| CSDL cũ còn chạy? | Có — hai bảng mới, không sửa cột nào của bảng cũ |
| Migration lùi được? | **Đã thử thật** trên `nt650v2`: upgrade → downgrade → upgrade lại. Dữ liệu nguyên vẹn |

## 🔴 Một lỗi mà 1439 test SQLite không thấy

Bản đầu của migration 0045 **quên `server_default=sa.text("now()")`** cho `created_at`/
`updated_at`. Postgres từ chối INSERT với `NotNullViolation`; SQLite không bao giờ thấy vì
`Base.metadata.create_all` dựng bảng thẳng từ ORM, nơi `TimestampMixin` luôn mang
`server_default`.

Cái bắt được nó là **cổng trình duyệt chạy trên Postgres thật** — và cụ thể hơn là **ảnh
chụp**, vì màn hình hiện đúng một dòng `TypeError: NetworkError`. Đây chính là lớp chênh
lệch dialect mà kỷ luật #7 (bổ sung) ghi, và là lý do món nợ F-4 *"bộ test phải chạy được
trên Postgres"* vẫn đáng làm.

## Cổng

`frontend/scripts/check-kiem-ke.mjs` (nhóm **ghi**, `--all`) đo bốn mệnh đề; ② là lý do cả
Phase 11 tồn tại:

1. đếm lệch thì màn hình **nói ra con số lệch**;
2. **nộp KHÔNG đụng tồn kho**;
3. duyệt xong tồn ở ô **bằng đúng số đã đếm**;
4. người đếm tự duyệt thì màn hình **nói ra là cùng một người**.

Một màn hình gọi `approve` ngay sau `submit` sẽ xanh cả ①, ③ và ④ — chỉ ② phân biệt được.
