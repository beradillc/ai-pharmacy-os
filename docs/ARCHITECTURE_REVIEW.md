# Rà soát kiến trúc sau BERAS V2 (2026-08-01)

> Viết cuối phiên P6 của kế hoạch §7cv. Không phải kiểm toán độc lập — đây là bản tự rà của
> Trợ lý Code, và mọi bản tự rà đều có điểm mù. Bản kiểm toán độc lập gần nhất là
> `docs/audit/2026-07-26_BAO_CAO_KIEM_TOAN.md`.

## Cái gì đã giữ được

| Ràng buộc | Bằng chứng |
|---|---|
| Module không import chéo nhau | `import-linter` **18 contract, 0 broken**, chạy trong mọi commit qua pre-commit hook |
| Cross-module chỉ nối ở composition root | 6 adapter trong `api/v1/cross_module.py`; module không biết nhau tồn tại |
| Domain không phụ thuộc framework | `inventory/domain`, `sales/domain` không import FastAPI/SQLAlchemy |
| Kiểu chặt | `mypy --strict` phủ `pharmacy_os` + `seeds`, **273 tệp, 0 lỗi** |

## Cái gì đang căng

**① `SalesService.__init__` đã tám tham số.** Ngày 01/08 suýt phá tương thích khi chèn tham
số thứ chín vào giữa — mọi bên gọi theo vị trí sẽ nhận sai chỗ, mà chữ ký vẫn "trông đúng".
Đã chuyển xuống cuối, nhưng **cách đó không mở rộng được thêm lần nữa**. Lần sau nên gom các
port thành một dataclass `SalesPorts`.

**② `PROJECT_STATE.md` đã hơn 7.400 dòng.** Kỷ luật #18 cấm dựng dòng thời gian thứ hai, và
điều đó vẫn đúng. Nhưng một tệp chỉ-ghi-thêm cỡ này thì phiên sau **không đọc lại** — đúng
nguyên nhân kiểm toán 26/07 chỉ ra. Mục lục ở đầu tệp có thể là bước rẻ nhất.

**③ Cổng trình duyệt đã 16 tệp, chạy ~10 phút.** Chúng đang bắt được thứ bốn cổng nhanh mù
hoàn toàn — không có gì để cắt. Nhưng chúng chạy **bằng tay**, và
`.github/workflows/ci.yml` **vẫn chưa chạy lần nào** (repo không remote, kiểm toán C-03).
Hạ tầng viết sẵn mà không nối dây thì bằng không.

**④ Test đa số chạy trên SQLite.** Món nợ **F-4**, đã đếm được **4 lần** chênh lệch dialect
cho lọt lỗi thật tới deployment. Lần gần nhất: migration 0045 thiếu `server_default=now()`,
**1439 test SQLite xanh hết**.

## Cái gì đã học được, đáng giữ

**Kỷ luật #16 (grep composition root) tiết kiệm ba mục trong sáu phiên**: khớp dị ứng
(30/07, xoá 262 dòng), mẫu in hoá đơn (P3), lộ trình lấy hàng (P6 — `where_is`,
`allocate_from_locations` đã có sẵn). Đây là kỷ luật có tỉ lệ hoàn vốn cao nhất từ trước tới
nay.

**Bài học ghi ở chỗ NGUYÊN NHÂN thì máy nhớ hộ; ghi ở chỗ HẬU QUẢ thì phải nhớ mãi.** Bẫy
`flex-basis` trong hộp dọc đã được ghi thành chú thích ở chỗ *dùng* từ 31/07 và **vẫn tái
phát lần thứ ba** ngày 01/08. Sửa ở chỗ *khai* thì hết.

**Trả lời "đỏ này có phải của tôi không" bằng `git stash` + một lượt chạy**, không bằng suy
luận. Dùng ba lần trong sáu phiên, ba lần đều kết luận chắc chắn — hai lần "không phải",
một lần "đúng là".

## Việc đề nghị, xếp theo tỉ lệ hoàn vốn

| # | Việc | Vì sao |
|---|---|---|
| 1 | Nối `git remote` để CI thật sự chạy | Rẻ nhất, và đóng được C-03 mở từ kiểm toán 26/07 |
| 2 | Bộ test chạy trên Postgres (nợ F-4) | 4 lỗi đã lọt vì thiếu nó |
| 3 | Mục lục cho `PROJECT_STATE.md` | Trí nhớ dự án không đọc được thì bằng không |
| 4 | Gom port của `SalesService` thành `SalesPorts` | Chữ ký tám tham số là bẫy đã suýt nổ một lần |
