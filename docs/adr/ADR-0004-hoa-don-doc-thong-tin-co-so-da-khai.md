# ADR-0004 · Hoá đơn đọc thông tin cơ sở ĐÃ KHAI, không đọc biến môi trường

- **Ngày:** 2026-08-02
- **Trạng thái:** Đã áp dụng
- **Người quyết:** GĐ dưới uỷ quyền Chain (*"uỷ quyền GĐ hoàn thiện tiếp phần mềm, phần làm
  được ngay"*) — đóng nợ **N-1**, bước **A2** của kế hoạch 9 bước (PROJECT_STATE §7dn)

## Vấn đề

Hai nguồn sự thật cho cùng một câu hỏi *"cơ sở này là ai"*, và chúng không nối nhau:

| | Nguồn | Ai ghi |
|---|---|---|
| Đầu trang hoá đơn in ra | biến môi trường `APP__ORG__*` | người cài đặt máy chủ, một lần |
| Màn **Cài đặt → Thông tin cơ sở** | bảng `tenant_compliance_configs` | dược sĩ, bất cứ lúc nào |

Người dùng đổi tên cơ sở trên màn, bấm Lưu, thấy `✓ Đã lưu` — rồi in ra tờ hoá đơn **vẫn
mang tên cũ**. Không mã lỗi nào. Màn đó đã phải tự dán một dòng cáo lỗi (*"Hoá đơn in ra
chưa dùng thông tin ở đây"*) để người dùng khỏi in nhầm 200 tờ; dòng chữ ấy là bằng chứng
rằng thiết kế đang sai, không phải là cách sửa nó.

Riêng với nhà thuốc bán nhiều cơ sở trên **một** deployment thì nặng hơn: `OrgSettings` là
**một giá trị toàn cục**, nên mọi tenant in ra cùng một đầu trang.

## Quyết định

`sales` khai một **cổng đọc** `OrgProfileProvider`; `compliance` cấp dữ liệu qua adapter
`ComplianceOrgProfileReader` ở composition root. Hai module vẫn không import nhau —
`import-linter` **19/19 kept**.

Ba điểm đáng ghi vì chúng đều là lựa chọn, không phải chuyện hiển nhiên:

**① Trộn theo TỪNG TRƯỜNG, không lấy trọn một bên.** Một cơ sở có thể đã khai tên và địa
chỉ mà chưa có mã số thuế. Lấy trọn bản khai thì tờ hoá đơn **mất dòng MST đang in đúng từ
trước** — một bước lùi im lặng. Lấy trọn cấu hình thì cả màn Cài đặt vô nghĩa. Nên: trường
nào đã khai thì thắng, trường nào rỗng thì lùi về `APP__ORG__*`.

**② Adapter chạy dưới DANH TÍNH HỆ THỐNG, với đúng một quyền.** In hoá đơn cần `sales.read`.
Nếu adapter dùng danh tính người đang đăng nhập thì **thu ngân phải được cấp thêm
`compliance.config.read`** chỉ để đầu trang hiện đúng tên nhà thuốc — tức nới quyền đọc hồ
sơ tuân thủ cho toàn bộ nhân viên quầy để đổi lấy một dòng chữ. Cái giá đó sai. Cùng khuôn
`SalesLoyaltyAccrualReader` (§7bt).

**③ Lỗi tra cứu KHÔNG được làm hỏng tờ hoá đơn.** CSDL chớp, tenant chưa có hàng cấu hình,
quyền lệch — hoá đơn vẫn phải in, nó là chứng từ khách đang đứng chờ ở quầy. Bắt lỗi, ghi
log, lùi về đúng hành vi cũ.

**Cổng đọc đi vào tầng interface, không vào `SalesService`.** Chữ ký `SalesService.__init__`
đã **tám tham số** và `docs/ARCHITECTURE_REVIEW.md` ① ghi rõ *"cách đó không mở rộng thêm
lần nữa được"* — 01/08 đã suýt phá tương thích khi chèn tham số thứ chín vào giữa. Đầu trang
hoá đơn chỉ đổi **cách vẽ tờ giấy**, nó không phải luật nghiệp vụ, nên nó thuộc tầng
interface. Việc gom `SalesPorts` vẫn còn nợ (bước C3).

## Đây là thay đổi NGỮ NGHĨA, khai báo theo kỷ luật #17

| | Trước | Sau |
|---|---|---|
| `GET /sales/{id}/receipt` — đường dẫn, mã trạng thái, hình dạng | không đổi | **không đổi** |
| **Giá trị** đầu trang | luôn từ `APP__ORG__*` | bản khai của tenant, lùi về `APP__ORG__*` khi trống |

Hình dạng giữ nguyên; **nguồn** của giá trị đổi. Kỷ luật #17 dặn thẳng: *"hình dạng không
đổi KHÔNG có nghĩa là không phá vỡ tương thích"* — nên nó được ghi ADR, y như ADR-0002.

**Ai có thể bị ảnh hưởng:** một deployment đang khai `APP__ORG__*` **và** đã có hàng trong
`tenant_compliance_configs` với nội dung khác sẽ thấy hoá đơn đổi đầu trang ngay lần in kế
tiếp. Đó **đúng là hành vi mong muốn** (bản khai của người dùng phải thắng tệp cấu hình của
người cài máy), nhưng nó là một thay đổi nhìn thấy được và không nên để ai bị bất ngờ.

**Bốn câu bắt buộc của kỷ luật #17:** frontend cũ còn chạy ✓ (không đổi API) · API cũ còn
chạy ✓ · CSDL cũ còn chạy ✓ (**không migration** — dùng bảng đã có) · lùi lại được ✓
(`git revert`, không có bước dữ liệu nào phải hoàn tác).

## Hệ quả kéo theo — một cổng đang canh câu đã thành SAI

Cổng `check-thong-tin-co-so` có mệnh đề ③ đòi màn **tự thú** *"hoá đơn chưa dùng thông tin
ở đây"*. Đó là sự thật cho tới hôm nay. Đóng N-1 làm câu đó **sai**, và một cổng canh một
câu đã sai thì nó **giữ nguyên chỗ hỏng thay vì canh nó** — nó sẽ đỏ đúng vào lúc sản phẩm
đúng. Đã **đổi vế** mệnh đề ③ (đòi màn nói *"hoá đơn CÓ dùng"*) thay vì xoá nó: người dùng
vẫn phải đọc được việc mình vừa làm có hiệu lực tới đâu.

*Ghi lại vì đây là một hình dạng lặp được:* **đóng một nợ có thể làm đỏ một cổng đang đúng.**
Khi bản vá gỡ bỏ một hạn chế mà một cổng đang canh, phải đi tìm cổng đó — nó không tự biết.
