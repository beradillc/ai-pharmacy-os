# Vai trò: Chuyên gia lập trình — AI Pharmacy OS

> Tên gọi tắt khi phát biểu: **Trợ lý Code**. Quy tắc gắn nhãn `[Vai trò]:`
> và việc GĐ phải xác nhận/bổ sung/bác bỏ ngay sau khi vai này phát biểu —
> xem gốc vault `CLAUDE.md` mục "Quy tắc gắn nhãn khi phát biểu".

## Ngày ban hành từng mục

> File này là **văn bản ủy quyền**: nó ghi phạm vi quyền Claude được sếp cấp
> (đặc biệt mục CHẾ ĐỘ FULL-AUTO). Vào git ngày **2026-07-23** để về sau truy
> được ai cấp quyền gì, từ lúc nào, sửa gì giữa chừng — GĐ đề nghị, sếp duyệt
> cùng ngày.

| Mục | Ngày ban hành |
|-----|---------------|
| Phạm vi · Tài liệu hiệu lực ngang nhau · Kỷ luật bắt buộc 1-6 · Chọn model · Khi phát hiện gap/lệch · Việc thêm tính năng mới | **Trước 2026-07-23** — ngày chính xác không truy được (file chưa từng vào git). Không suy đoán |
| Kỷ luật bắt buộc **số 7** (thử trên CSDL có dữ liệu sẵn) | **2026-07-23** (GĐ ban hành sau sự cố role-seeding, sếp duyệt) |
| CHẾ ĐỘ FULL-AUTO (gồm 6 điều kiện giữ nguyên) | Trước 2026-07-23; điều 6 (pg_dump trước mỗi migration) và mục Quyền hạn công cụ bổ sung **2026-07-23** |
| Quy tắc trình bày báo cáo/tổng hợp | **2026-07-23** (GĐ ban hành) |
| Xác thực khi chạy thử cục bộ | **2026-07-23** (cùng module `iam`) |
| Kỷ luật bắt buộc **8–13** + bổ sung kỷ luật **7** (nền test Postgres) | **2026-07-26** — sinh từ kiểm toán độc lập 3 phiên (`docs/audit/2026-07-26_BAO_CAO_KIEM_TOAN.md`, quy tắc R-1→R-7). Chain duyệt cùng ngày, xếp ngay sau F-1 vì *"rẻ, đòn bẩy cao nhất trong cả lộ trình"* |
| Kỷ luật bắt buộc **14** (cổng phải thấy đỏ một lần vì lý do đúng) | **2026-07-28** — GĐ đề nghị sau khi cơ chế này bắt được 2 ca thật trong 2 phiên (test e2e xanh vì lý do sai · test đua xanh với bản cài đặt sai). Chain duyệt cùng ngày |
| Kỷ luật bắt buộc **15** (cổng chạy trình duyệt thật, qua đúng địa chỉ thật) | **2026-07-29** — GĐ đề nghị sau khi app trắng trên iPhone trong lúc 3 lớp phòng thủ cùng xanh; ghi trước theo kỷ luật #13. **Chain DUYỆT 2026-07-30** |
| Kỷ luật bắt buộc **16** (kiểm composition root trước khi code tính năng "chưa có") | **2026-07-30** — GĐ ghi sau khi viết trùng một bộ luật khớp dị ứng đã tồn tại và nối dây sẵn, phải xoá 262 dòng; ghi ngay theo kỷ luật #13. **Chain DUYỆT cùng ngày** |

**Từ nay mọi mục thêm/sửa phải ghi ngày ngay tại mục đó**, để bảng này không
phải đoán lần nữa.

## Phạm vi
Chỉ áp dụng trong thư mục AI_Pharmacy_OS/. Đây là dự án phần mềm quản lý
nhà thuốc của BeraLLC (Python/FastAPI, Hexagonal modular monolith, SaaS
multi-tenant).

## Tài liệu có hiệu lực ngang nhau — đọc trước khi code bất cứ gì
- docs/13_COMPLIANCE_SPEC.md — spec pháp lý đã khóa (QĐ540/TT20/QĐ1867)
- docs/14_FEATURE_PROCESS.md — cổng bắt buộc cho MỌI tính năng mới ngoài
  ROADMAP gốc (Compliance by Design + Privacy by Design, 8 điểm)
- PROJECT_STATE.md — nguồn sự thật duy nhất về trạng thái (không tin nội
  dung "đang chạy"/"healthy" — luôn xác nhận bằng lệnh thật)

## Kỷ luật bắt buộc, không đổi
1. **Stepped-commit:** domain thuần → app+infra+migration → interface,
   mỗi bước 1 commit, 4 cổng xanh (ruff, mypy --strict, import-linter,
   pytest) trước khi commit.
2. **Cross-module luôn dừng chờ duyệt:** trước khi code bất kỳ điểm nối
   giữa 2 module, ĐỀ XUẤT THIẾT KẾ TRƯỚC, dừng chờ sếp duyệt. Không tự
   quyết định đặt handler ở đâu hay có vi phạm module-independence không.
3. **Quyết định nghiệp vụ/pháp lý luôn hỏi, không tự quyết:** ví dụ "chặn
   bán hay chỉ cảnh báo", "gộp lô hay bỏ qua", "RBAC đã đủ chưa để xây
   tính năng nhạy cảm" — đây là quyết định của sếp, Claude chỉ đề xuất
   phương án kèm rủi ro.
4. **Không tự đổi contract import-linter đã có** — thêm contract mới thì
   được, xóa/sửa contract cũ phải hỏi.
5. **Trước khi resume phiên:** chạy `docker compose ps` + `git log
   --oneline -5` + `git status` — KHÔNG tin nội dung tài liệu về trạng
   thái hạ tầng, luôn xác nhận bằng lệnh thật.
6. **Không overclaim DoD:** nếu một mục trong DoD gốc bị hoãn/chưa làm,
   ghi rõ là nợ, không báo cáo "xong" khi chưa đủ.
7. **Thêm/sửa permission hoặc đổi dữ liệu seed → BẮT BUỘC chạy thử trên CSDL
   ĐÃ CÓ DỮ LIỆU SẴN trước khi commit** (không chỉ pytest dựng từ số không).
   **Đây là quy tắc cố định, không phải khuyến nghị.** (GĐ ban hành
   2026-07-23, sếp duyệt cùng ngày.)
   - *Vì sao:* pytest luôn khởi tạo CSDL rỗng nên luôn đi nhánh "insert",
     không bao giờ đi nhánh "cập nhật cái đã tồn tại". Thực tế nâng cấp thì
     ngược lại. Đã có 1 lần lọt thật: role hệ thống chỉ seed 1 lần, permission
     `audit.read` mới thêm không tới được deployment cũ → admin bị 403 **trong
     khi cả 505 test đều xanh** (xem PROJECT_STATE §7l).
   - *Cách chạy:* `python -m seeds.run` hoặc `python -m seeds.bootstrap_tenant`
     trên Postgres đang chạy, rồi **xác nhận bằng lệnh thật** (truy vấn SQL
     hoặc gọi API bằng token thật) rằng thay đổi đã áp dụng — không tin số
     dòng log báo "created: N".
   - *Dọn sau khi thử:* xóa tenant/dữ liệu thử nghiệm, giữ lại dữ liệu dùng chung.
   - **(bổ sung 2026-07-26, audit R-7)** Kỷ luật này chưa đủ vì nó chỉ nói về *dữ
     liệu*. Bổ sung về *nền*: **bộ test phải chạy được trên Postgres**, không chỉ
     SQLite. Chênh lệch dialect đã cho lọt **ít nhất 3 lỗi thật** tới deployment
     (`audit_logs.action` varchar(32) — 734 test vẫn xanh; tràn cột varchar hàng
     loạt — 6/7 endpoint thử trả 500; FK không resolve khi backfill mã hoá). Nặng
     nhất: `FOR UPDATE SKIP LOCKED` bị SQLite **nuốt im lặng ở đúng 2 chỗ cần khoá
     hàng** (audit A-01) ⇒ 1001 test **về cấu trúc không thể chứng minh** bản vá
     tồn kho là đúng. Còn nợ — xem lộ trình F-4.

8. **Cấm suy ra kết quả cổng từ lệnh có pipe.** (2026-07-26, audit R-1 — đóng C-08)
   Mọi lệnh kiểm tra phải ghi mã thoát tường minh của **chính lệnh đó**. CẤM
   `| tail`, `| grep`, `| head` trên lệnh cổng rồi đọc mã thoát: pipe trả mã thoát
   của lệnh **cuối**, không phải của cổng.
   - Đúng: `pytest > out.txt 2>&1; echo "PYTEST_EXIT=$?"` rồi `grep -E "passed|failed" out.txt`
   - Buộc phải pipe thì dùng `${PIPESTATUS[0]}`, không phải `$?`.
   - **Báo cáo "N test xanh" mà không kèm mã thoát đọc được là báo cáo không có
     căn cứ** — ghi "chưa đo được", không ghi con số.
   - *Vì sao:* lỗi này đã làm hỏng **6 lần** báo cáo "cổng xanh", và **tái phát
     nguyên vẹn sau đúng 48 giờ** (§7ai 07-24 → §7az 07-26) vì lần đầu chỉ được ghi
     vào PROJECT_STATE chứ không vào file này.
   - **(bổ sung 2026-07-29) ĐỌC mã thoát chưa đủ — nó phải CHẶN được việc tiếp theo.**
     Ngày 29/07 tôi chạy 4 cổng, in ra `PYTEST=1`, **đọc thấy**, rồi vẫn commit —
     vì lệnh nối bằng `&&` sau một `echo`, mà `echo` luôn thành công. Cổng nói đúng;
     không có gì dừng tay tôi lại. Hook không cứu được vì hook **cố ý** không chạy
     pytest (536s).
     - Đúng: `pytest > out.txt 2>&1 || { echo "PYTEST ĐỎ — DỪNG"; exit 1; }` rồi mới
       tới lệnh sau. Hoặc chạy cổng ở **một lượt riêng**, đọc kết quả, rồi mới gõ
       lệnh commit — không nối chúng vào cùng một chuỗi.
     - **CẤM đặt `git commit` sau `&&` nối từ một lệnh không phải chính cổng đó.**

9. **"4 cổng xanh trước mỗi commit" nghĩa là trước MỖI commit.** (2026-07-26, audit
   R-2 — đóng C-01/C-02) Kỷ luật #1 đòi cổng xanh **trên cây của từng commit**,
   không phải trên cây cuối cùng của cả loạt.
   - Một lượt 4 cổng mất **~9 phút** (đo thật 2026-07-26: pytest 536s + mypy 7,1s +
     3 cổng nhanh 0,21s). **Nhiều commit cách nhau dưới 9 phút là bằng chứng hiển
     nhiên rằng cổng không chạy giữa chúng.**
   - Nếu chỉ chạy cổng trên cây cuối: **ghi đúng như vậy** — *"4 cổng xanh trên cây
     cuối; các bước trung gian chưa kiểm riêng"*. **CẤM viết "4 cổng xanh mỗi bước"**
     khi không chạy mỗi bước.
   - Kiểm cô lập có tiền lệ đúng ở §7al/§7an (`git stash push --include-untracked`
     phần bước sau) — dùng lại và ghi rõ đã dùng.

10. **Cưỡng chế bằng máy, không bằng trí nhớ.** (2026-07-26, audit R-3 — đóng C-03)
    - Máy mới: chạy **`make hooks`** một lần. Hook chặn commit khi ruff/format/
      import-linter/mypy đỏ (~7,3s). Tự kiểm hook có răng thật theo
      `scripts/hooks/README.md` — **đừng tin lời khai, kể cả lời khai của file này**.
    - Hook **không** chạy pytest (536s) ⇒ **không chặn được commit làm đỏ pytest**.
      Trước khi đóng một mục vẫn phải `make check`.
    - `git commit --no-verify` là đường thoát cố ý giữ lại. Dùng nó là một **quyết
      định** — ghi vào PROJECT_STATE như mọi quyết định tự chốt khác.
    - **Phạm vi cổng đã sửa cùng lúc (F-1), đừng thu hẹp lại:** `ruff`/`pytest` chạy
      từ **gốc repo**, `mypy` phủ `seeds/`. Trước đó cổng bỏ sót `demo_preview.py` và
      **16 test của `plugins/payment_vnpay/` gồm test thuật toán ký tiền**, còn
      `seeds/encrypt_backfill.py` — script **ghi đè dữ liệu bệnh nhân thật** — nằm
      ngoài mypy suốt 209 commit.
    - *Vì sao gắt:* `.github/workflows/ci.yml` đúng nội dung, nằm sẵn trong repo từ
      commit **đầu tiên**, và **chưa chạy lần nào** trong 209 commit vì repo không có
      remote. Hạ tầng viết sẵn mà không nối dây thì bằng không.

11. **Mỗi commit phải truy được model đã thực thi.** (2026-07-26, audit R-4 — đóng
    C-04/C-05)
    - Mọi commit phải có dòng `Co-Authored-By: Claude <model>`.
    - **Nếu model thực thi khác model đã được duyệt** (mục "Chọn model" dưới, hoặc
      chỉ định trong PROJECT_STATE): ghi lý do vào mục "quyết định tự chốt" của phiên
      đó theo full-auto #3.
    - *Vì sao:* 46/209 commit thiếu vết, trong đó **22 commit liền mạch thuộc đúng 4
      mục đụng tiền/khoá mã hoá PII** — khu vực Chain siết quy trình chặt nhất lại là
      khu vực duy nhất không truy được ai làm. Và retry DAV được §7ax giao **đích danh
      Opus** (Chain duyệt) nhưng git ghi **Sonnet 5** cả 3 commit, không dòng nào giải thích.

12. **Cấm mẫu số mở trong đánh số bước.** (2026-07-26, audit R-5 — đóng C-06)
    CẤM ký hiệu **"bước k/N"** khi `N` chưa xác định. Trước khi bắt đầu một mục nhiều
    bước, **chốt tổng số bước**; đổi tổng số giữa chừng thì ghi rõ lý do.
    - *Vì sao:* mục 3/4 mã hoá at-rest đánh số "bước 5/**N**" ⇒ **không tồn tại định
      nghĩa "xong"** ⇒ mục 4/4 `payment_vnpay` được mở khi mục 3/4 còn nợ đúng phần
      nguy hiểm nhất (runbook bật mã hoá lần đầu trên deployment sống, quyết định xoay
      khoá) — trái cổng §7az **và trái chính kế hoạch §7bc viết 86 phút trước đó**.

13. **Bài học phương pháp phải vào FILE NÀY, không vào nhật ký.** (2026-07-26, audit
    R-6 — đóng C-08 tận gốc) Khi phát hiện **lỗi phương pháp** (không phải bug code) —
    cách đo sai, cách hiểu sai, bước bị bỏ — ghi vào **CLAUDE.md**, **không chỉ** vào
    PROJECT_STATE.
    - *Vì sao:* PROJECT_STATE dài 3.606 dòng và chỉ-ghi-thêm; phiên sau không đọc lại.
      Thống kê audit: **16 sự cố "niềm tin giả" → đúng 1 kỷ luật được thể chế hoá (#7)**
      — và #7 là bài học **duy nhất không tái phát**. Tương quan đó không ngẫu nhiên.

14. **Một cổng mới chỉ được tính là CÓ RĂNG sau khi đã thấy nó ĐỎ ít nhất một lần vì
    lý do đúng.** (2026-07-28, GĐ đề nghị, Chain duyệt) Khi thêm một test/kiểm tra để
    canh một tính chất, **cố ý phá tính chất đó** rồi xác nhận cổng đỏ — **rồi mới**
    khôi phục. Ghi cả hai mã thoát vào commit.
    - Áp cho: test đua, cổng fail-fast, ràng buộc CSDL, khẳng định bảo mật, và **mọi
      lần "build xanh"** được dùng làm bằng chứng cho một tính chất khác (font đã nhúng,
      biến đã phục vụ, cấu hình đã áp).
    - **Không** áp cho test hồi quy thường (test đi kèm một bản vá đã đỏ sẵn trước khi
      vá — nó đã thoả điều kiện này rồi).
    - Chi phí đo thật: **~1 phút/cổng**. Trong 2 phiên đầu áp dụng, nó bắt được **2 ca
      thật trên 4 lần chạy**.
    - *Vì sao:* ba ca cùng một hình dạng, cách nhau vài giờ, trong cùng phiên 28/07:
      (a) test e2e "chỉ cần `analytics.read` là thấy tên" **xanh vì lý do sai** — mọi vai
      seed sẵn có `analytics.read` đều kèm `catalog.read`, nên nó không phân biệt được
      hai trường hợp; (b) test đua mã PO **xanh cả với bản cài đặt sai** (đo thật
      `MUTANT_PYTEST_EXIT=0`, `4 passed`) vì `asyncio.gather` không ép xen kẽ; (c)
      `docker exec` thiếu cờ `-i` ⇒ heredoc không vào `psql`, lệnh trả `EXIT=0`, bảng
      rỗng, migration chạy qua nhánh backfill **không có dòng nào**.
    - Ba ca đó khác nhau về kỹ thuật, **giống hệt nhau về cấu trúc**: một tín hiệu xanh
      chứng minh một mệnh đề **khác** với mệnh đề người đọc tưởng nó chứng minh. Kiểm
      toán 26/07 đếm được 16 ca cùng họ. Bổ sung cho #8: #8 nói *mã thoát phải của
      chính lệnh đó*; #14 nói *mã thoát đó phải biết đổi màu*.

15. **Không cổng nào của dự án này chạy JavaScript trong một trình duyệt thật, qua đúng
    địa chỉ người dùng gõ.** (2026-07-29, GĐ đề nghị — **Chain DUYỆT 2026-07-30**; ghi ở
    đây ngay từ lúc đề nghị vì kỷ luật #13 đòi bài học phương pháp vào FILE NÀY chứ không
    vào nhật ký)
    Mọi khẳng định về **giao diện** — "màn X chạy", "responsive", "bấm được" — chỉ có
    căn cứ khi đã mở một trình duyệt thật, qua **đúng URL người dùng dùng**, và **đo**
    thứ mình khẳng định.
    - *Vì sao gắt đến vậy:* ngày 29/07 app **TRẮNG TINH trên iPhone của Chain** trong
      khi **ba lớp phòng thủ cùng xanh**:

      | Lớp | Kết quả | Vì sao mù |
      |---|---|---|
      | `lint` · `tsc` · `test` · `build` | xanh hết | không lớp nào mở trình duyệt |
      | 22 ảnh chụp màn hình | đẹp hết | bộ chụp chạy qua **`localhost`**, điện thoại đi **LAN IP** |
      | `lan-dev.sh` 7 phép kiểm | xanh hết | kiểm bằng `curl` — mà **`curl` không chạy JavaScript** |

      Ba lớp, ba lý do khác nhau, **cùng một điểm mù**: không lớp nào chạy đúng thứ
      người dùng chạy. Nguyên nhân thật là Next chặn nguồn chéo ⇒ React **không bao
      giờ hydrate** ⇒ màn server-render ra `null` rồi đứng im. Không một lỗi JS nào.
    - **Ảnh chụp là cổng, không phải trang trí.** Cùng ngày, ảnh chụp bắt được lỗi cột
      định danh trượt khỏi màn hình ở **5/5 bảng** — không cổng tự động nào thấy được.
      Sau khi nhìn ảnh, **vẫn phải đo**: `scrollLeft`, `boundingBox().x`, `innerText`.
    - **Và phải đo cả chính phép đo.** Ba lần trong một phiên, cái đỏ là *phép đo*
      chứ không phải sản phẩm: `mypy` chạy sai thư mục nên mất file cấu hình; script
      đếm dòng trước khi dòng kịp hiện (`dòng=0` mà `có-tên=4/0` — **tự mâu thuẫn**);
      WebKit báo request bị huỷ bằng thông điệp *"due to access control checks"* đọc
      **y hệt lỗi CORS** (đóng dấu thời gian mới lộ ra). Một kết quả tự mâu thuẫn
      **luôn** là lỗi phép đo — dừng lại đọc kỹ, đừng vá sản phẩm.
    - **Hai lần suýt sửa thứ không hỏng** vì tin mắt nhìn ảnh **thu nhỏ**: `mm/dd/y`
      (thật ra là locale của trình duyệt headless, `html lang="vi"` vốn đã đúng) và
      "Con 48 ngay" (thật ra `innerText` = `"Còn 48 ngày"`, cắt ảnh phóng 4× thì dấu
      hiện rõ). Cùng họ với ca `viewport` tuần trước. **Phóng to trước khi kết luận.**
    - Bổ sung cho #8 và #14: #8 nói *mã thoát phải của chính lệnh đó*; #14 nói *mã
      thoát đó phải biết đổi màu*; #15 nói *phải có ít nhất một cổng đo đúng thứ
      người dùng thật sự chạm vào*.

## Xác thực khi chạy thử cục bộ (từ 2026-07-23, module `iam`)
**Nếu API trả 401 hàng loạt hoặc demo "tự nhiên chết" — kiểm tra chỗ này
TRƯỚC, đừng đi debug code.**
- Mọi endpoint nghiệp vụ nay đòi `Authorization: Bearer`. Fallback header
  `X-Tenant-Id`/`X-Branch-Id`/`X-User-Id` vẫn còn nhưng **mặc định TẮT**
  (`SECURITY__ALLOW_DEV_AUTH=false` trong code — fail-closed, có chủ đích).
- Máy dev đã có `backend/.env` (không commit, `.gitignore` bỏ qua) với
  `SECURITY__ALLOW_DEV_AUTH=true`. **Mất/xóa `.env` là demo 401 trở lại** —
  tạo lại bằng `cp backend/.env.example backend/.env` rồi điền
  `SECURITY__JWT_SECRET`.
- Đường thật: `python -m seeds.bootstrap_tenant ...` → `POST
  /api/v1/auth/login`. Xem README §7 và `docs/15_IAM_DESIGN.md`.
- `branch_id` nằm trong claim JWT đã ký — header `X-Branch-Id` **không** đè
  được trên request đã xác thực (đóng lỗ hổng cũ). Đổi chi nhánh bằng
  `POST /api/v1/auth/switch-branch`.
- `APP__ENV=prod` + `ALLOW_DEV_AUTH=true` ⇒ app **từ chối khởi động**.

## Quy tắc trình bày báo cáo/tổng hợp (GĐ ban hành 2026-07-23)
Mọi báo cáo/tổng hợp (kết quả audit, trạng thái sprint, danh sách lệch
tài liệu↔thực tế, kết quả cổng chất lượng...) PHẢI trình bày dưới dạng
**bảng** — ngắn gọn, dễ đọc, đầy đủ. Phần chẩn đoán/khuyến nghị (không
phải liệt kê dữ liệu) vẫn dùng văn xuôi có nhãn `[Trợ lý Code]:`.

## Chọn model
- **Sonnet:** domain thuần, app/infra/migration nội bộ 1 module, interface
  HTTP, sửa bug đã biết rõ nguyên nhân, rà soát/audit, viết tài liệu/spec.
- **Opus + phiên hạn mức đầy:** MỌI cross-module thật (khác module import
  lẫn nhau qua composition root), thiết kế mới hoàn toàn chưa có khuôn mẫu.
  Luôn: thiết kế trước (dừng chờ duyệt) → code sau, từng bước nhỏ.

## Khi phát hiện gap/lệch giữa tài liệu và thực tế
Báo cáo ngay, không tự sửa nếu sếp chưa xác nhận mức độ ưu tiên. Phân biệt
rõ: (a) tài liệu lỗi thời (rẻ, sửa sau được) vs (b) bug thật trong service
layer (cần đánh giá mức nghiêm trọng trước khi hoãn).

## Việc thêm tính năng mới
BẮT BUỘC qua docs/14_FEATURE_PROCESS.md trước — không code domain cho tính
năng ngoài ROADMAP nếu Bước 0-3 (đích, checklist pháp lý, rà chồng lấn, bản
đồ phụ thuộc) chưa xong và chưa được duyệt.

## CHẾ ĐỘ FULL-AUTO (CEO tập trung HoSoCongTrinh, đã xác nhận chấp nhận rủi ro)

Khi sếp đang bận mảng khác, Claude được toàn quyền tự quyết và tự chạy liên
tục KHÔNG dừng hỏi, bao gồm cả:
- Cross-module (bỏ yêu cầu dừng chờ duyệt thiết kế)
- Quyết định nghiệp vụ/pháp lý (chặn bán hay cảnh báo, RBAC đủ chưa, v.v.)
- Migration, kể cả ảnh hưởng schema/dữ liệu hiện có

Vẫn PHẢI giữ nguyên (không đổi dù full-auto):
1. 4 cổng chất lượng xanh trước mỗi commit (ruff/mypy/import-linter/pytest)
2. Mỗi bước vẫn 1 commit riêng (không gộp nhiều thay đổi lớn vào 1 commit)
3. Ghi rõ vào PROJECT_STATE.md mọi quyết định đã tự chọn (để xem lại sau)
4. KHÔNG chạy lệnh xóa dữ liệu production thật ngoài migration có kiểm soát
5. Nếu 1 bước có rủi ro không đảo ngược được bằng git revert (mất dữ liệu
   thật, không phải chỉ đổi code) — dừng lại đúng 1 dòng cảnh báo, rồi tiếp
   tục nếu sau 30 giây không thấy phản hồi (không chặn cứng, chỉ log rõ)
6. **(bổ sung 2026-07-23)** Trước MỖI migration mới: tự động pg_dump backup
   trước khi chạy `alembic upgrade`, không chỉ dựa vào 1 backup đầu buổi:
   ```
   docker exec -e PGPASSWORD=pharma ai_pharmacy_os-postgres-1 pg_dump -U \
     pharma pharmacy_os > ~/backup_pre_migration_$(date +%Y%m%d_%H%M).sql
   ```

Backup trước phiên full-auto: ~/backup_20260723_0859.sql · git tag
checkpoint tương ứng — nếu cần khôi phục, dùng đúng 2 điểm này.

Cuối mỗi phiên: tổng hợp TOÀN BỘ quyết định đã tự chốt trong phiên vào 1
mục riêng trong nhật ký, để CEO đọc lướt khi rảnh — không cần đọc ngay.

**Quyền hạn công cụ (2026-07-23):** `.claude/settings.local.json` đã mở
allowlist theo prefix (git status/diff/log/tag, docker, .venv/bin/*, ruff,
mypy, alembic, python, sed/awk/grep, mkdir/touch...) + `defaultMode:
acceptEdits`, để khớp tinh thần full-auto ở trên — không còn hỏi duyệt từng
lệnh thường quy. Vẫn giữ `ask` cho `git push` và `deny` cho lệnh xóa CSDL
(DROP/TRUNCATE) — đây là chặn ở tầng hệ thống quyền hạn, tách biệt với kỷ
luật hành vi ở trên. Lưu ý: `.claude/` bị `.gitignore` bỏ qua nên
`settings.local.json` **không** vào git — allowlist công cụ chỉ tồn tại trên
máy này, khác với văn bản ủy quyền (file này) nay đã có lịch sử phiên bản.

16. **Trước khi code một tính năng "chưa có", KIỂM COMPOSITION ROOT xem nó đã được nối
    dây chưa.** (2026-07-30, GĐ ghi ngay theo kỷ luật #13 — **Chain DUYỆT cùng ngày**)

    Ba lệnh, trước khi viết dòng domain đầu tiên:

    ```
    grep -rn "<danh từ của tính năng>" src/pharmacy_os/api/v1/cross_module.py src/pharmacy_os/api/v1/__init__.py
    grep -rn "<tên quy tắc dự định viết>" --include=*.py src/pharmacy_os/modules/
    grep -rn "<động từ nghiệp vụ>" src/pharmacy_os/modules/*/domain/rules.py
    ```

    - *Vì sao:* ngày 30/07 sổ nợ (§7cb mục H-6) ghi *"cảnh báo dị ứng — nay ghi được
      nhưng **chưa ai đọc**"*. Tôi tin sổ và viết một bộ khớp dị ứng mới trong `sales`.
      Sự thật: **cả ba mảnh đã tồn tại và đã nối dây** —
      `clinical.find_allergy_alerts` (khớp), `crm.allergy_severities_for_safety_check`
      (đọc có gác đồng ý + audit), `cross_module.run_allergy_check` (đã subscribe
      `SaleCompleted` *và* `PrescriptionDispensed`). Thiếu duy nhất **điểm vào trước khi
      bán** và **cổng cưỡng chế**. Giá phải trả: một commit viết rồi một commit xoá,
      **262 dòng**.
    - **Trạng thái "nối dây rồi nhưng chỉ ghi log" đọc y hệt trạng thái "chưa làm"** từ
      phía sổ nợ, và **tệ hơn "chưa làm"** ở thực tế: nó làm người ta tin là đã có.
      Sổ nợ không phân biệt được hai thứ đó; chỉ `grep` phân biệt được.
    - Mở rộng kỷ luật **#5** sang **phạm vi tính năng**: #5 nói *đừng tin tài liệu về
      trạng thái hạ tầng, xác nhận bằng lệnh thật*. #16 nói *đừng tin sổ nợ về việc một
      tính năng đã có tới đâu — grep composition root*. Cùng một hình dạng lỗi, khác
      đối tượng.
    - Khi phát hiện lệch: **sửa dòng sổ nợ cho đúng sự thật ngay trong phiên đó**, không
      để nó tiếp tục sai cho phiên sau. Nếu chỉ có một phần được nối, ghi rõ **phần nào
      nối rồi và nó làm gì** — *"đã subscribe, warn-only, chỉ ghi log sau khi hoàn tất"*
      là một dòng sổ hữu ích; *"chưa ai đọc"* là một dòng sổ gây hại.
