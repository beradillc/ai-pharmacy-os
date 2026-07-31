# STORAGE_LOCATION — Sơ đồ kho (BERAS V2 Phase 1)

> Trạng thái: ✅ **ĐÃ LÀM**. Commit `47ac945` (miền) · `96a78b8` (bảng + endpoint + quyền)
> · bước 4 (tài liệu + màn hình) trong commit đi kèm tệp này.
>
> Tệp này thay cho `docs/features/<slug>/01_DECISIONS.md` của `docs/14` — kỷ luật #18 cấm
> dựng cấu trúc song song, và bản yêu cầu V2 đã chỉ định `docs/inventory/` là chỗ ở.
> Bước 0 (`INVENTORY_AUDIT.md`) đã làm phần rà soát; tệp này làm phần quyết định.

## Đích (DoD ngược)

| Vai | Khi xong làm được gì |
|---|---|
| Dược sĩ chi nhánh | Dựng sơ đồ kho của chi nhánh mình: Kho → Khu → Kệ → Ô, đặt thứ tự đi lấy hàng |
| Thu ngân · nhân viên kho | **Xem** được sơ đồ, **không** dựng lại được nó |
| Quản lý | Truy được ai tạo/đổi/ngừng một vị trí, lúc nào |

## Mô hình

```
Location (tự tham chiếu)
├── kind:  WAREHOUSE → ZONE → SHELF → BIN     (từ vựng ĐÓNG)
├── code:  do nhà thuốc đặt, tự viết HOA      (KHÔNG hard-code A/B/C)
├── path:  KHO1/A/A01/03                       (vật chất hoá)
└── pick_order: thứ tự đi lấy hàng trong cùng một cha
```

### Bốn quyết định, và vì sao

| # | Quyết định | Vì sao |
|---|---|---|
| 1 | **Module RIÊNG**, không nhét vào `inventory` | Sơ đồ kho là **dữ liệu cấu hình** (sửa vài lần/năm); chuyển động hàng là **dòng sự kiện** (hàng nghìn dòng/tháng). Nhét chung làm contract `import-linter` của `inventory` mất nghĩa |
| 2 | **Từ vựng tầng ĐÓNG, mã MỞ** | Yêu cầu *"không hard-code A/B/C"* nói về **mã** — mã do nhà thuốc đặt. Từ vựng tầng phải đóng: cho tự do đặt tên tầng thì không biết Kệ nằm trong Khu hay ngược lại, và mọi phép sắp đường đi mất căn cứ |
| 3 | **Thứ bậc = ràng buộc THỨ TỰ, không phải ĐỦ TẦNG** | Nhà thuốc nhỏ chỉ dùng Kho → Kệ. Bắt tạo Khu rỗng cho đủ tầng là bắt nhập dữ liệu giả. **Bỏ tầng thì được, đảo tầng thì không** |
| 4 | **Vị trí theo CHI NHÁNH** | Kệ A01 của cơ sở 1 và cơ sở 2 là hai chỗ khác nhau. Dùng chung buộc mọi truy vấn tồn phải nhớ lọc thêm chi nhánh ở tầng ứng dụng — chỗ dễ quên nhất |

### 🔴 `pick_order` có ngay từ Phase 1, không đợi Phase 4

Quãng đường trong kho **không suy ra được từ mã**. Kệ A01 và A02 có thể đối lưng nhau qua
một lối đi, và chỉ người xếp kho biết. Thiếu trường này thì Pick List (Phase 4) chỉ còn cách
sắp theo bảng chữ cái — **một phỏng đoán trông như tối ưu**, loại sai lầm không bao giờ làm
đỏ test mà chỉ làm người đi lấy hàng đi vòng mỗi ngày.

### 🔴 Mã bất biến, tên đổi được

`code` và `path` **không sửa được sau khi tạo**; `name` (tên hiển thị) thì thoải mái. Đổi mã
sẽ buộc viết lại đường dẫn của cả cây con — đúng loại thao tác hay hỏng nửa chừng. Cổng ghi
của repository (`save`) chỉ chạm ba trường `name`/`pick_order`/`is_active`, cùng khuôn hẹp
với `catalog.save_ingredients`.

### 🔴 Một cái bẫy SQL phải viết ra vì nó không nhìn thấy được

Khoá duy nhất `(branch_id, parent_id, code)` **không chặn được trùng mã giữa hai KHO GỐC** —
chuẩn SQL coi `NULL ≠ NULL`, mà kho gốc có `parent_id = NULL`. Chặn thật nằm ở tầng ứng dụng
(`by_code_under`). Có test riêng canh đúng ca đó để người sửa sau không bỏ phép kiểm ấy vì
tưởng CSDL đã lo hết.

Chiều ngược lại cũng có test: **trùng mã ở hai cha KHÁC nhau là hợp lệ** — ô "01" dưới kệ A
và dưới kệ B là hai chỗ khác nhau. Hai đột biến đi hai hướng ngược nhau đều bị bắt (#14).

## API

| Đường | Quyền | Ghi chú |
|---|---|---|
| `POST /locations` | `location.write` | `parent_id: null` ⇒ tạo KHO gốc. **409** trùng mã cùng cha · **422** sai tầng/mã · **404** cha không thuộc chi nhánh |
| `GET /locations` | `location.read` | Danh sách **phẳng** kèm `parent_id`+`path`, sắp theo **thứ tự đi lấy hàng**. `?include_inactive=true` để thấy cả chỗ đã ngừng |
| `PATCH /locations/{id}` | `location.write` | Đổi `name`/`pick_order`/`is_active`. **Không có `code`** |

Trả danh sách **phẳng** chứ không phải cây lồng: màn hình dựng cây từ `parent_id` mà không
cần endpoint đệ quy, và thứ tự trả về đã là thứ tự người ta đi trong kho.

## Phân quyền

| Vai | `location.read` | `location.write` |
|---|---|---|
| Quản trị hệ thống · Dược sĩ chuỗi · **Dược sĩ chi nhánh** | ✓ | ✓ |
| Thu ngân · Nhân viên kho | ✓ | ✗ |

Dược sĩ **chi nhánh** dựng được sơ đồ vì người xếp kho là người biết kệ nào đối lưng kệ nào.
Vị trí đã theo chi nhánh nên không có đường nào chạm sang cơ sở khác.

## Audit

`LOCATION_CREATED` · `LOCATION_CHANGED`. `context` mang **đường dẫn** — thứ người soát sổ đọc
được, khác một UUID. Thao tác đáng ngờ nhất là **ngừng hoạt động**: nó làm một chỗ biến mất
khỏi mọi màn hình mà hàng có thể vẫn đang nằm đó.

## Tương thích ngược

| Câu hỏi (kỷ luật #17) | Trả lời |
|---|---|
| Frontend cũ còn chạy? | **Có** — không màn nào bị sửa |
| API cũ còn chạy? | **Có** — không endpoint nào bị sửa |
| CSDL cũ còn chạy? | **Có** — một bảng MỚI, không cột nào của bảng cũ bị đụng |
| Migration lùi được? | **Có** — `0042` chỉ `create_table`, `downgrade` là `drop_table` |

## Còn nợ, KHÔNG làm tròn thành xong

1. **Chưa có tồn theo vị trí.** Sơ đồ dựng được nhưng chưa gắn hàng vào — đó là Phase 2+.
2. **Chưa nhập được sơ đồ hàng loạt.** Dựng kho 200 ô hiện là 200 lượt bấm.
3. `stock_movements` **chưa có** `from_location_id`/`to_location_id`. GĐ đã duyệt phương án
   thêm hai cột nullable (thay vì bảng phụ); sẽ làm khi tới Phase 5, vì đó là lần đầu **thật
   sự cần** — thêm sớm là thêm một cột không ai ghi vào.
