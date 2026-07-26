# AUDIT ĐỘC LẬP 2026-07 — CHỈ MỤC TỔNG HỢP

> **Đọc file này TRƯỚC.** Đây là bản tra cứu cho toàn bộ đợt kiểm toán độc lập; hai file phiên
> (2.053 dòng) chỉ mở khi cần bằng chứng chi tiết của một phát hiện cụ thể.
>
> **Vai thực hiện:** Kiểm toán viên độc lập — cởi bỏ hoàn toàn vai GĐ và Trợ lý Code. Nguyên tắc:
> mọi tuyên bố trong PROJECT_STATE/TODO/ROADMAP coi là **chưa được chứng minh** cho tới khi tự chạy
> lệnh xác minh.
>
> **Commit được audit:** `7bbc8d5` · branch `main` · working tree sạch.

| Phiên | File | Phạm vi | Trạng thái |
|---|---|---|---|
| **A** | `2026-07-26_AUDIT_PHIEN_A.md` (1.095 dòng) | Giai đoạn 0 (bằng chứng nền) + Giai đoạn 1 (kiến trúc, ISO 25010) | ✅ **XONG** |
| **B** | `2026-07-26_AUDIT_PHIEN_B.md` (958 dòng) | Giai đoạn 2 (bảo mật, OWASP ASVS L2) + Giai đoạn 3 (toàn vẹn dữ liệu) + Giai đoạn 4 (chất lượng test) | ✅ **XONG** |
| **C** | *(chưa tạo)* | Giai đoạn 5 (audit quy trình) + Giai đoạn 6 (báo cáo cuối) | ⏳ **CHỜ PHIÊN HẠN MỨC ĐẦY** |

---

## 1. SỐ LƯỢNG PHÁT HIỆN THEO MỨC

| Mức | Phiên A | Phiên B | **Tổng** |
|---|---:|---:|---:|
| **Critical** | 0 | 0 | **0** |
| **High** | 3 | 3 | **6** |
| **Medium** | 7 | 7 | **14** |
| **Low** | 6 | 3 | **9** |
| **Tổng** | **16** | **13** | **29** |

**Nhãn đặc biệt do Chain ban hành (2026-07-26):**

| Nhãn | Áp cho | Ý nghĩa |
|---|---|---|
| 🚫 **RELEASE BLOCKER Sprint 9** | **A-02**, **A-03** | Sprint 9 **không được đóng** khi còn mở, bất kể mục khác xanh hết |
| ⏸️ **QUYẾT ĐỊNH KINH DOANH CHỜ CHAIN** | **A-05** | Không phải chỉ lỗi kỹ thuật; 2 phương án + hệ quả pháp lý ghi trong Phiên A mục A-05 |

**Vì sao 0 Critical:** chưa có deployment production nào. A-02/A-03 có hậu quả cỡ Critical nhưng cần
một điều kiện chưa xảy ra — là *mìn cài chờ ngày deploy*, không phải lỗ hổng đang chảy máu.
"Critical" đo mức đang bị khai thác; "release blocker" đo điều kiện được phép phát hành. Hai trục
tách nhau có chủ đích.

---

## 2. DANH SÁCH PHÁT HIỆN — PHIÊN A (16)

### High (3)

| ID | Tiêu đề | Nhãn |
|---|---|---|
| **A-01** | Toàn bộ 1001 test chạy SQLite; `FOR UPDATE SKIP LOCKED` bị dialect nuốt im lặng ở đúng 2 chỗ cần khoá hàng | |
| **A-02** | Prod khởi động được với khoá ký JWT dài **3 byte** — `_fail_fast_in_prod` chỉ chặn chuỗi placeholder | 🚫 |
| **A-03** | Prod khởi động được với `ENCRYPTION__ENABLED=false` — PII bệnh nhân bản rõ, không tín hiệu nào | 🚫 |

### Medium (7)

| ID | Tiêu đề | Nhãn |
|---|---|---|
| **P0-03** | "pytest toàn repo 1001" không phải toàn repo — sót 16 test package `payment_vnpay` (gồm test thuật toán ký tiền) | |
| **P0-04** | Cổng `mypy` chỉ phủ `pharmacy_os`; `seeds/` (có `encrypt_backfill.py`) và `tests/` nằm ngoài; `tests/` có 109 lỗi strict | |
| **A-04** | Repository `iam` là bộ **duy nhất** không tenant-scope theo cấu trúc — an toàn phụ thuộc hoàn toàn vào guard tầng service | |
| **A-05** | Một cặp credential VNPAY dùng chung cho mọi tenant + `get_across_tenants` | ⏸️ |
| **A-06** | Docstring hứa timeout cho plugin — không có `asyncio.wait_for` nào trong repo | |
| **A-07** | Mock gateway CSDL Dược + Mock LLM nạp cả khi `APP__ENV=prod`, không một dòng cảnh báo | |
| **A-08** | `demo_preview.py` crash từ 2026-07-23, vẫn ở gốc repo, không cổng nào phủ | |

### Low (6)

| ID | Tiêu đề |
|---|---|
| **P0-01** | `pytest -q` — đúng lệnh §7az quy định — **không in ra dòng "N passed"** (`addopts` đã có `-q` ⇒ thành `-qq`) |
| **P0-05** | `make lint` chạy ruff từ `backend/`, sót 7 file (gồm `demo_preview.py` + package plugin) |
| **A-09** | `payment_vnpay._canonical_query`: docstring nói "mọi tham số `vnp_*`", code ký **mọi** khoá |
| **A-10** | `vnp_IpAddr` cứng `127.0.0.1`; thiếu `vnp_ExpireDate` |
| **A-11** | Kiểm tra port plugin bằng `isinstance` chỉ xét cấu trúc, không xét chữ ký hàm |
| **A-12** | `main.py`/`models_registry.py`/`logging.py`/`workers/` nằm ngoài 4 tầng contract `layers` |

---

## 3. DANH SÁCH PHÁT HIỆN — PHIÊN B (13)

### High (3)

| ID | Tiêu đề |
|---|---|
| **B-01** | `StockBalanceRepository.adjust` **mất cập nhật** khi ghi đồng thời — sổ kho tự mâu thuẫn (IN=10, OUT=16, số dư 0) |
| **B-02** | Khoá chống lặp `exists_for_ref` thua race — một sự kiện giao 2 lần tạo **2 dòng xuất kho cùng `ref_id`**, không unique index đỡ |
| **B-03** | `.env.example` bật `APP__DEBUG=true` ⇒ SQL echo đổ **PII bệnh nhân ra log** (tên, SĐT, ngày sinh, CCCD) |

### Medium (7)

| ID | Tiêu đề |
|---|---|
| **B-04** | Bán vượt tồn khi đồng thời: **không** phát `StockShortfallDetected`, **không** dòng đối soát nào |
| **B-05** | Endpoint HTTP gỡ 2FA của người khác **không đòi step-up** — yếu hơn chính thứ nó bảo vệ |
| **B-06** | `national_id_hash` (CCCD): tên cột nói "hash" nhưng lưu **nguyên văn**, không mã hoá, không hash, không docstring lý do |
| **B-07** | Không tầng nào ràng buộc `branch_id ∈ tenant` — DB không FK, request không kiểm lại |
| **B-08** | Kiểm quyền nằm ở tầng service, không ở route ⇒ 422 chạy trước 403, lộ schema cho người không quyền |
| **B-09** | **0 test đồng thời** trong toàn bộ 1001 test — nguyên nhân gốc chung của B-01/B-02/B-04 |
| **B-10** | Không có rate limit ở bất kỳ đâu; khoá tài khoản không kèm giới hạn IP tự nó thành vector DoS |

### Low (3)

| ID | Tiêu đề |
|---|---|
| **B-11** | Cơ chế cứu sự kiện của outbox **mặc định tắt**; validator prod cho phép đúng cấu hình vô hiệu hoá nó |
| **B-12** | Không thể chạy test suite trên CSDL có sẵn dữ liệu — conftest ghim cứng SQLite |
| **B-13** | Token không ràng buộc `sub` ↔ `tenant` ↔ `branch`; không `jti`/`iss`, không thu hồi access token trước hạn |

---

## 4. NHỮNG GÌ ĐÃ KIỂM VÀ KHÔNG RA LỖI

Ghi lại để Phiên C **không làm lại**, và để bức tranh cân bằng — 29 phát hiện ở trên không phải toàn
bộ những gì đã soát.

| Hạng mục | Kết quả |
|---|---|
| 5 cổng chất lượng (ruff/format/mypy/import-linter/pytest) | 5/5 EXIT=0, **con số khớp tài liệu 100%** |
| Chuỗi 32 migration từ DB rỗng (upgrade→check→downgrade base→upgrade→check) | 5/5 bước EXIT=0, không drift |
| 112 hash commit tài liệu trích dẫn | **112/112 tồn tại** (3 cái nhãn `(root)` nằm ở repo vault gốc, đã tra đúng) |
| Secret trong lịch sử git | **0** — `.env` chưa bao giờ commit, chỉ có placeholder `__set_me__` |
| Domain purity (10/10 module, kiểm tay) | 0 vi phạm |
| Module independence (tĩnh + `importlib` + `TYPE_CHECKING` + chuỗi config) | **0 import chéo module** |
| FK xuyên module | Đúng 1 (`customer_allergies.ingredient_id`), có lớp dịch lỗi đúng chỗ |
| Vòng phụ thuộc ẩn | 0 |
| Giả mạo JWT (alg=none, sai secret, hết hạn, config alg=none) | **4/4 bị chặn** |
| Refresh rotation + phát hiện tái sử dụng | Xoay vòng đúng, tái sử dụng ⇒ **thu hồi cả chuỗi phiên** (chuẩn ASVS 3.3) |
| 40 endpoint gọi bằng token **rỗng quyền** | **0 endpoint thiếu kiểm quyền** |
| Lỗ hổng `X-Branch-Id` (§7l tuyên bố đã vá) | **Đã vá thật** — kiểm bằng HTTP thật, không đọc code |
| Tấn công chéo tenant (5 đường, quyền admin đầy đủ) | **5/5 trả 404** (404 chứ không 403 — không rò sự tồn tại) |
| Idempotency đơn hàng (`/sales`, `/sync/sales`) | Đúng, **có unique index CSDL đỡ** (`uq_sale_client_uuid`) |
| Outbox: sự kiện có mất khi relay chết không? | **KHÔNG mất** — bật relay lại, 2 dòng PENDING được giao đủ |
| Ranh giới giao dịch (3.3) | **Không có dual-write** — outbox ghi trong chính transaction nghiệp vụ |
| Quản lý khoá mã hoá | Không vào git; xoay khoá nhiều phiên bản; cấu hình sai ⇒ từ chối khởi động mọi môi trường |
| Kỷ luật #7 (§7l role-seeding) | **Đã vá thật** — `seeds.run` chạy lần 2 trên CSDL có dữ liệu: created=0, updated=0, không nhân bản |
| Độ phủ dòng | **96%** (10.313 câu lệnh, 306 miss), EXIT=0 |
| `BlockchainProvider` | **Không tồn tại và không được tuyên bố ở đâu** — không có gì để audit |

---

## 5. ĐIỂM BẮT ĐẦU PHIÊN C

**Phiên C là phiên tổng hợp + phán xét toàn dự án. Cắt ngang giữa chừng thì báo cáo không dùng
được ⇒ chỉ mở khi hạn mức đầy.** (Chain chốt 2026-07-26.)

### 5.1 Chưa làm — phạm vi Phiên C

| Giai đoạn | Nội dung | Ghi chú |
|---|---|---|
| **Giai đoạn 5** | **Audit quy trình GĐ + Trợ lý Code** — quy trình làm việc có được tuân thủ thật không, hay chỉ được ghi là đã tuân thủ | Chưa bắt đầu |
| **Giai đoạn 6** | **Báo cáo cuối** — tổng hợp 29 phát hiện (+ phát hiện Giai đoạn 5), xếp ưu tiên, phán xét tổng thể dự án | Chưa bắt đầu |

### 5.2 Đọc theo đúng thứ tự này trước khi bắt đầu

| # | File | Vì sao |
|---|---|---|
| 1 | **`docs/audit/00_AUDIT_INDEX.md`** (file này) | Toàn cảnh 29 phát hiện, không phải đọc lại 2.053 dòng |
| 2 | `CLAUDE.md` (gốc vault) + `AI_Pharmacy_OS/CLAUDE.md` | **Văn bản ủy quyền** — chuẩn quy trình để đối chiếu ở Giai đoạn 5: kỷ luật bắt buộc 1-7, CHẾ ĐỘ FULL-AUTO (6 điều kiện giữ nguyên), quy tắc gắn nhãn vai, quy tắc bảng |
| 3 | `PROJECT_STATE.md` §7az → §7be | Quy trình nghiêm ngặt hơn full-auto cho 4 mục đụng tiền/khoá thật, và ghi chép 4 mục đó |
| 4 | `docs/14_FEATURE_PROCESS.md` + `docs/features/` (6 thư mục) | Cổng Bước 0-4 bắt buộc cho tính năng mới |
| 5 | `git log` + `GD-DieuPhoi-GiaoViec.md` (gốc vault) | Đối chiếu ghi chép ↔ commit thật |
| 6 | Hai file phiên A/B | **Chỉ mở khi cần bằng chứng chi tiết của một ID cụ thể** |

### 5.3 Câu hỏi Giai đoạn 5 nên trả lời (gợi ý, chưa kiểm)

Ba câu hỏi dưới đây xuất phát từ những gì Phiên A+B **quan sát được nhưng không thuộc phạm vi** —
Phiên C tự quyết có theo hay không, không bắt buộc.

1. **Stepped-commit có thật không?** Kỷ luật #1 đòi domain → app+infra+migration → interface, mỗi
   bước 1 commit, 4 cổng xanh trước mỗi commit. Đối chiếu `git log` 208 commit với thứ tự thật.
2. **Hồ sơ docs/14 có đủ cho mọi tính năng không?** `docs/features/` có **6** thư mục; **không có**
   thư mục cho `payment_vnpay` và cho "mã hoá at-rest". Cần xác minh hai mục đó có nằm trong ROADMAP
   gốc (được miễn cổng) hay không — **Phiên A+B chưa xác minh, không kết luận**.
3. **Nợ đã ghi có được đóng khung đúng phạm vi không?** Phiên B tìm thấy **2 chỗ nợ ghi hẹp hơn thực
   tế**: TODO:77 mô tả vấn đề tồn kho là "eventual-consistency ở prod" trong khi B-01 tái hiện được
   ở chế độ **đồng bộ, một tiến trình**; §7bb mô tả bề mặt break-glass là CLI trong khi B-05 tìm thấy
   endpoint HTTP tương đương yếu hơn. Đây là dạng sai lệch khó tự phát hiện nhất — đáng rà rộng.

### 5.4 Trạng thái hạ tầng khi đóng phiên B

| Mục | Trạng thái |
|---|---|
| `docker compose` | **Đã dừng** (`docker compose stop`) |
| Database thử `audit_empty_a` | **Còn tồn tại** trên Postgres dev — lệnh `DROP` bị chặn ở tầng quyền hạn nên kiểm toán viên không xoá được. Chain xoá tay khi tiện: `DROP DATABASE audit_empty_a;` |
| Database dev `pharmacy_os` | **Không bị chạm** ở bất kỳ bước nào của cả 2 phiên |
| Tiến trình `uvicorn` cổng 8098 | Đã tắt |
| Working tree | Sạch — 2 file audit + file này đã commit |

---

*Chỉ mục lập 2026-07-26, sau khi đóng Phiên B.*
