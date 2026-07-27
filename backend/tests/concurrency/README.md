# `tests/concurrency` — test đồng thời trên Postgres thật

> ## ✅ TRẠNG THÁI: B-01 / B-02 / B-04 ĐÃ VÁ (F-5, 2026-07-27)
>
> `pytest tests/concurrency` nay ra **`10 passed`**, mã thoát **0**, **0 dấu `xfail`**.
> Bảy dấu do F-4 đặt đã được gỡ **vì test xanh thật**, không phải vì ai nới khẳng
> định — bằng chứng nằm ở `strict=True`: bản vá làm chúng XPASS ⇒ bộ test **đỏ** ⇒
> người vá buộc phải quay lại gỡ dấu. Cơ chế đó đã chạy đúng như thiết kế.
>
> **Quy tắc cho test đua thêm sau này không đổi:** `xfail` ở thư mục này = **BUG ĐÃ
> BIẾT, CHƯA VÁ**, không phải "test đã xanh"; luôn kèm `strict=True` **và**
> `raises=AssertionError`, và luôn có hạn đóng (xem mục ⏳ bên dưới).

---

## Vì sao thư mục này tồn tại

Kiểm toán độc lập 2026-07-26 xếp **B-09** (*0 test đồng thời trong 1001 test*) là
**nguyên nhân gốc chung** của B-01/B-02/B-04. Khảo sát F-4 (2026-07-27) cho thấy đó
không phải sơ suất của người viết test:

| Nền test cũ (`tests/integration`) | Hệ quả |
|---|---|
| SQLite in-memory + **`StaticPool`** ⇒ đúng **1 kết nối** dùng chung | Hai giao dịch đồng thời **bất khả thi về vật lý** — "0 test đồng thời" là thứ **không biểu đạt được**, không phải thứ bị quên |
| SQLAlchemy **bỏ lặng** `FOR UPDATE [SKIP LOCKED]` trên SQLite | Đúng 2 chỗ khoá hàng của cả hệ thống chưa từng được kiểm chứng (kiểm toán **A-01**) |

Nền này sửa đúng hai điều đó, **không đụng một dòng nào** trong 1001 test hiện có
(thư mục mới, engine mới — Chain chốt 2026-07-27, `PROJECT_STATE.md` §7bh).

## Chạy

```bash
make up               # BẮT BUỘC — Postgres phải chạy, xem "Fail chứ không skip" bên dưới
make test-concurrency # hoặc: cd backend && pytest tests/concurrency
```

Lược đồ CSDL test do **`alembic upgrade head` thật** dựng, không phải `create_all`
(sửa 2026-07-27 — xem "Lược đồ" bên dưới). Không phải làm gì bằng tay: CSDL chưa có
thì tự tạo, tụt lại revision thì tự nâng, dựng bằng `create_all` đời cũ thì tự làm lại
từ số không.

CSDL `pharmacy_os_test` được **tự tạo** ở lần chạy đầu, cạnh CSDL dev `pharmacy_os`,
trên chính Postgres của `docker compose`. Không thêm phụ thuộc `testcontainers`
(quyết định của Chain: lợi ích hermetic của nó còn là lý thuyết khi CI chưa từng chạy
— kiểm toán C-03). Đường nâng cấp khi repo có remote: đổi đúng một fixture URL.

Đổi đích bằng `PHARMACY_CONCURRENCY_DB_URL`. Tên CSDL **vẫn phải** kết thúc `_test`.

## Bốn ràng buộc thiết kế — đừng nới ra

### 1. `NullPool`, không `StaticPool`
Mỗi phiên một kết nối riêng. Đây là toàn bộ lý do thư mục này tồn tại.
`test_harness.py::test_two_sessions_are_two_real_connections` so `pg_backend_pid()`
của hai phiên — nếu ai đó lỡ đổi về pool dùng chung, test đó đỏ ngay.

### 2. Guard tên CSDL — rủi ro duy nhất không hoàn tác được
Harness `TRUNCATE` 9 bảng trước **mỗi** test. Trỏ nhầm vào `pharmacy_os` dev là mất
dữ liệu thật, `git revert` không cứu được. Guard **từ chối chạy** nếu tên CSDL không
kết thúc `_test` — nổ ngay, không cảnh báo rồi chạy tiếp.

Tự kiểm chứng (đừng tin đoạn văn này, chạy đi):
```bash
cd backend
PHARMACY_CONCURRENCY_DB_URL="postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os" \
  pytest tests/concurrency -q; echo "EXIT=$?"
# Mong đợi: EXIT=1, RuntimeError "Từ chối chạy test đồng thời trên CSDL 'pharmacy_os'"
# và KHÔNG có câu lệnh nào chạm vào pharmacy_os.
```

### 3. Fail chứ không skip
Postgres không chạy ⇒ **lỗi**, kèm hướng dẫn `make up`. Không `pytest.skip`. Skip
lặng rồi báo xanh chính là bệnh "niềm tin giả" mà cả đợt kiểm toán chỉ ra.

Tự kiểm chứng:
```bash
docker compose stop postgres
cd backend && pytest tests/concurrency -q; echo "EXIT=$?"   # mong đợi: EXIT=1, 10 errors, 0 skipped
docker compose start postgres
```

Hệ quả có thật, không giấu: **`make check` nay đỏ nếu quên `make up`.** Đây là cái
giá đã biết của việc chọn "fail chứ không skip", không phải lỗi.

### 4. Interleaving tất định — CẤM `sleep`
`StatementGate` (trong `conftest.py`) móc vào `before_cursor_execute` và chặn phiên
ngay **trước** câu lệnh ghi đầu tiên, mở ra bằng `asyncio.Event`. Nhờ vậy dựng được
đúng thứ tự **A đọc → B đọc → A ghi+commit → B ghi+commit** mà không chờ đồng hồ:
"cả hai đã đọc xong" là một **sự kiện quan sát được**.

Đo thật 2026-07-27: **8/8 lượt chạy liên tiếp cho kết quả y hệt**. §7ay đã học một
lần rồi — một test đỏ ngẫu nhiên 8% làm mất giá trị của chính cái cổng nó bảo vệ.

`HANG_GUARD_SECONDS = 30` là **chặn treo**, không phải cơ chế đồng bộ: nó chỉ để một
bên chết giữa chừng không làm treo cả bộ test.

## Hợp đồng của dấu `xfail` ở đây

Luôn là `xfail(strict=True, raises=AssertionError)`. **Cả hai tham số đều bắt buộc.**

| Tham số | Nếu thiếu |
|---|---|
| `strict=True` | Bản vá F-5 làm test xanh mà **không ai được báo** ⇒ dấu xfail nằm lại vĩnh viễn. Có nó thì test chuyển XPASS ⇒ **bộ test ĐỎ** ⇒ người vá buộc phải quay lại gỡ dấu |
| `raises=AssertionError` | Chỉ khẳng định **nghiệp vụ** mới được tính là "đỏ đúng dự đoán". Thiếu nó, tắt Postgres đi là 7 test báo `xfailed` y hệt lúc chạy thật — hạ tầng hỏng đội lốt bug-đã-biết. Đo thật 2026-07-27: trước khi thêm → `7 xfailed, 3 errors`; sau khi thêm → `10 errors` |

Đây cũng là lý do `test_database_rejects_two_movements_for_same_ref_and_batch` **cố ý
không dùng `pytest.raises`**: nó ném `Failed`, không phải `AssertionError`, nên sẽ lọt
qua đúng cái lưới vừa dựng.

### ⏳ Hạn dùng — điều kiện CỨNG của Chain (2026-07-27) — **ĐÃ ĐÓNG ĐÚNG HẠN**

Điều kiện đặt ra: **7 dấu `xfail` phải đóng TRƯỚC KHI Sprint 9 mở**, quá hạn thì *tự
động là release blocker, không cần bàn lại*. Đóng đủ 7/7 trong ngày **2026-07-27**,
cùng ngày đặt hạn — dòng "Đứng yên từ = 27/07" trong `GD-DieuPhoi-GiaoViec.md` khép
lại, không đứng yên ngày nào.

Lý do có hạn dùng vẫn giữ nguyên cho mọi dấu `xfail` đặt sau này: *xfail không hạn
dùng là cách một bug đã biết trở thành một bug bị quên.*

## Bản đồ 10 test

| Test | Vai trò |
|---|---|
| `test_harness.py` (3 test) | **PHẢI XANH.** Nền tự chứng minh nó có thật: hai kết nối khác nhau · hai phiên thấy commit của nhau · `FOR UPDATE SKIP LOCKED` **có răng** (đóng A-01). Không có 3 test này thì 7 test dưới vô nghĩa — một harness không thực sự mở 2 kết nối vẫn "đỏ đúng dự đoán" vì lý do hoàn toàn khác |
| `test_two_concurrent_adjusts_must_both_land` | **B-01** dạng thuần nhất, tầng repository: 100 − 10 − 10 phải ra 80 (trước vá: **90**) |
| `test_ledger_and_balance_must_agree_after_concurrent_dispense` | **B-01** — "sổ kho tự mâu thuẫn": sổ chi tiết nói 80, số dư nói **90** |
| `test_same_sale_dispatched_twice_writes_one_set_of_movements` | **B-02** — một đơn giao 2 lần ghi **2** bộ dòng xuất thay vì 1 |
| `test_database_rejects_two_movements_for_same_ref_and_batch` | **B-02** — chống trùng phải có ràng buộc CSDL đỡ, không chỉ một `SELECT` trong code. Nay canh giữ **phạm vi** của index, không chỉ sự tồn tại của nó |
| `test_concurrent_dispense_never_exceeds_stock_on_hand` | **B-04** — tồn 10, trước vá xuất được **12** |
| `test_concurrent_dispense_never_drives_balance_negative` | **B-04** — trước vá tồn về **−2** |
| `test_concurrent_sale_shortfall_leaves_a_trail` | **B-04** phần nặng nhất: hụt 2 viên mà **không sự kiện `StockShortfallDetected` nào** được phát ⇒ *không dòng đối soát*, không ai lần ra được |

## Bản vá F-5 (2026-07-27) — ba chỗ hỏng, ba chỗ sửa

| Vị trí | Vấn đề (F-4 định vị) | Sửa thế nào |
|---|---|---|
| `SqlAlchemyBalanceRepository.adjust` | read-modify-write **trần**, không khoá gì | Số học vào trong `UPDATE ... SET quantity = quantity + :delta RETURNING quantity` — khoá hàng do chính câu lệnh giữ |
| cùng chỗ, chặn bán vượt tồn | không có | Vị ngữ `quantity + delta >= 0` **cùng câu lệnh đó**; 0 hàng cập nhật ⇒ `InsufficientStockError` kèm số thật sự còn |
| `exists_for_ref` | check-then-act **trần** | Vẫn là đường nhanh, nhưng bảo đảm chuyển xuống `uq_movement_ref_batch`; `add()` dịch `IntegrityError` thành `DuplicateMovementError` |
| `dispense_for_sale` thua cuộc đua | hỏng lặng, không dòng đối soát | Phát lại giao dịch tối đa **3 lần**; lần phát lại đọc tồn hiện tại và phát `StockShortfallDetected` cho phần hụt |
| `stock_movements` | thiếu ràng buộc duy nhất đỡ `ref_id` | Migration **0033**, unique **một phần** trên `(tenant_id, ref_type, ref_id, batch_id) WHERE ref_id IS NOT NULL` |

⚠️ **Phạm vi unique index — đặt sai là chặn nhầm nghiệp vụ đúng.** Khoá phải có
`batch_id`: một lần xuất FEFO trải trên nhiều lô ghi nhiều dòng cùng `ref_id` một cách
**hoàn toàn hợp lệ**. Đã kiểm bằng lệnh thật trên Postgres có dữ liệu (2026-07-27):
giao trùng cùng lô **bị chặn**; cùng `ref_id` khác lô **cho qua**; `ref_id IS NULL`
**cho qua**; khác `ref_type` **cho qua**.

Hệ quả kéo theo, ghi để khỏi bất ngờ: `receive_from_goods_receipt` nay cộng dồn theo
**lô** rồi mới ghi một dòng IN cho mỗi lô. Trước đó nó ghi một dòng mỗi *dòng hàng*, mà
hai dòng hàng cùng thuốc + cùng lô + cùng HSD của **một** phiếu nhập sẽ gộp về một lô ⇒
hai dòng IN cùng `(grn, batch)` ⇒ đụng chính index này. Cộng dồn không mất truy vết:
dòng IN của GRN vốn không mang `po_item_id`, và sự kiện `StockMovedIn` vẫn phát theo
từng dòng hàng như cũ.

## Lược đồ: `alembic upgrade head`, không phải `create_all` (sửa 2026-07-27)

`create_all` đọc model Python và **chỉ tạo bảng còn thiếu** — không thêm ràng buộc vào
bảng đã tồn tại, không biết migration là gì. Nó đã cắn thật ngay trong phiên F-5: máy có
sẵn `pharmacy_os_test` từ trước **không nhận** `uq_movement_ref_batch`, 2 test B-02 đỏ vì
**hạ tầng** chứ không vì mã sản phẩm — đúng bệnh *"hạ tầng hỏng đội lốt bug thật"* mà
thư mục này được dựng lên để chống.

Lý do sâu hơn chuyện tiện lợi: bộ test này tồn tại để nói *"cái chạy trên production hành
xử thế này"*. Lược đồ suy ra từ model Python **không phải** cái chạy trên production —
cái đó là chuỗi migration. Suy từ model là kiểm chứng hệ thống bằng một bản sao của chính
niềm tin đang cần kiểm chứng.

Ba đường vào, đã kiểm bằng lệnh thật (2026-07-27):

| Trạng thái CSDL test | Harness làm gì | Đo được |
|---|---|---|
| Chưa tồn tại | `CREATE DATABASE` → `upgrade head` | CSDL mới `f5_fresh_test`: **10 passed**, `alembic_version` = `0033…` |
| Dựng bằng `create_all` đời cũ (48 bảng, **không** `alembic_version`) | `DROP SCHEMA public CASCADE` → dựng lại từ số không | **10 passed**, về đúng `0033…`, index có mặt |
| Tụt lại revision (giả lập: hạ về `0032…` + xoá index) | `upgrade head` nâng tiếp | Trước: `0032…`, 0 index → sau: **`0033…`, 1 index**, 10 passed |

Đây chính là kịch bản đã cắn ở F-5, nay chạy thẳng không cần ai can thiệp.

**Alembic chạy trong tiến trình con**, không gọi `alembic.command` tại chỗ: `migrations/env.py`
lấy URL từ `get_settings()`, mà hàm đó có `@lru_cache`. Sửa biến môi trường rồi xoá cache
ngay trong tiến trình test là để lại quả mìn cho mọi test chạy sau.

⚠️ **Giới hạn còn lại, đừng hiểu nhầm:** alembic đối chiếu theo `alembic_version`, không
so lược đồ thật. Ai đó xoá tay một index **mà không** hạ revision thì harness không biết —
`upgrade head` sẽ là no-op. Nó chống **trôi theo migration** (kịch bản có thật), không
chống **sửa tay lén lút** (chưa từng xảy ra).

## Nợ

| Nợ | Vì sao chưa làm |
|---|---|
| `f4_probe` · `audit_empty_a` · `f5_fresh_test` còn nằm lại trên Postgres | `DROP DATABASE` nằm trong `deny` của allowlist công cụ. Xoá tay khi tiện, không ảnh hưởng gì |

## Chi phí

| Hạng mục | Đo thật 2026-07-27 |
|---|---|
| Cả thư mục này (10 test) | **≈ 6,2 s** (lượt đầu ≈ 14,7 s do phải `create_all`) |
| `TRUNCATE` 9 bảng, mỗi test | 362 ms |
| `TRUNCATE` cả 48 bảng (không dùng) | 946 ms |
| Mẹo transaction + `ROLLBACK` (**không dùng được**) | 0,5 ms |

Mẹo `ROLLBACK` rẻ hơn 700 lần nhưng **không dùng được ở đây**: hai phiên phải nhìn
thấy commit của nhau, nên phải commit thật rồi dọn thật. Chi phí này không tránh được.

Vòng lặp nhanh hằng ngày **không bị ảnh hưởng**: `pytest tests/unit` = 3,31 s.
