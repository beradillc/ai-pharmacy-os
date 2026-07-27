# `tests/concurrency` — test đồng thời trên Postgres thật

> ## ⚠️ ĐỌC TRƯỚC KHI DIỄN GIẢI KẾT QUẢ
>
> **`xfail` trong thư mục này = BUG ĐÃ BIẾT, CHƯA VÁ. KHÔNG phải "test đã xanh".**
>
> Chạy `pytest tests/concurrency` hiện ra **`3 passed, 7 xfailed`** và mã thoát **0**.
> Mã thoát 0 đó **không** có nghĩa là tồn kho đã đúng. Nó có nghĩa là *"7 lỗi đã biết
> vẫn đang hỏng đúng như dự đoán"*. Bảy dòng `x` đó là **B-01, B-02, B-04** của kiểm
> toán 2026-07-26 — **tồn kho vẫn sai khi hai quầy bán cùng lúc.**
>
> Muốn thấy chúng hỏng ra sao: `pytest tests/concurrency --runxfail`.

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

### ⏳ Hạn dùng — điều kiện CỨNG của Chain (2026-07-27)

**7 dấu `xfail` này PHẢI được đóng TRƯỚC KHI Sprint 9 mở.** Không phải "theo dõi vô
thời hạn". Nếu tới lúc chuẩn bị Sprint 9 mà còn dấu nào mở, **đó tự động là release
blocker, không cần bàn lại**.

Đã ghi vào `GD-DieuPhoi-GiaoViec.md` với cột **"Đứng yên từ" = 2026-07-27** (quy tắc
R-9). Lý do có hạn dùng: *xfail không hạn dùng là cách một bug đã biết trở thành một
bug bị quên.*

## Bản đồ 10 test

| Test | Vai trò |
|---|---|
| `test_harness.py` (3 test) | **PHẢI XANH.** Nền tự chứng minh nó có thật: hai kết nối khác nhau · hai phiên thấy commit của nhau · `FOR UPDATE SKIP LOCKED` **có răng** (đóng A-01). Không có 3 test này thì 7 test dưới vô nghĩa — một harness không thực sự mở 2 kết nối vẫn "đỏ đúng dự đoán" vì lý do hoàn toàn khác |
| `test_two_concurrent_adjusts_must_both_land` | **B-01** dạng thuần nhất, tầng repository: 100 − 10 − 10 phải ra 80, hiện ra **90** |
| `test_ledger_and_balance_must_agree_after_concurrent_dispense` | **B-01** — "sổ kho tự mâu thuẫn": sổ chi tiết nói 80, số dư nói **90** |
| `test_same_sale_dispatched_twice_writes_one_set_of_movements` | **B-02** — một đơn giao 2 lần ghi **2** bộ dòng xuất thay vì 1 |
| `test_database_rejects_two_movements_for_same_ref_and_batch` | **B-02** — chống trùng phải có ràng buộc CSDL đỡ, không chỉ một `SELECT` trong code |
| `test_concurrent_dispense_never_exceeds_stock_on_hand` | **B-04** — tồn 10, xuất được **12** |
| `test_concurrent_dispense_never_drives_balance_negative` | **B-04** — tồn về **−2** |
| `test_concurrent_sale_shortfall_leaves_a_trail` | **B-04** phần nặng nhất: hụt 2 viên mà **không sự kiện `StockShortfallDetected` nào** được phát ⇒ *không dòng đối soát*, không ai lần ra được |

## Ghi chú cho F-5 (bước vá tiếp theo)

Thứ tự **F-4 trước F-5 là bắt buộc**, không phải sở thích: vá trước rồi mới viết test
thì bản vá được nghiệm thu bằng chính bộ test không thể nhìn thấy lỗi.

Ba chỗ hỏng đã định vị chính xác trong khảo sát:

| Vị trí | Vấn đề |
|---|---|
| `inventory/infrastructure/repository.py:197-219` (`adjust`) | read-modify-write **trần**, không khoá gì cả |
| `inventory/infrastructure/repository.py:182-189` (`exists_for_ref`) | check-then-act **trần** |
| `stock_movements` | thiếu ràng buộc duy nhất đỡ `ref_id` |

⚠️ **Phạm vi unique index — đọc kỹ, đặt sai là chặn nhầm nghiệp vụ đúng.** Ràng buộc
đúng là trên `(tenant_id, ref_type, ref_id, batch_id)`, **không phải**
`(tenant_id, ref_type, ref_id)`: một lần xuất FEFO trải trên nhiều lô ghi nhiều dòng
cùng `ref_id` một cách **hoàn toàn hợp lệ**.

Vá xong, 7 test chuyển XPASS ⇒ bộ test đỏ ⇒ gỡ dấu `xfail`. Chỉ khi đó B-01/B-02/B-04
mới được coi là đóng.

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
