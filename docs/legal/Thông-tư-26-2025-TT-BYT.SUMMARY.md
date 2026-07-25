# Tóm tắt — TT 26/2025/TT-BYT (Đơn thuốc & kê đơn ngoại trú)

> Văn bản gốc: `Thông-tư-26-2025-TT-BYT.docx`. Ban hành + hiệu lực **01/7/2025**. 14 Điều + 7 Phụ
> lục (mẫu đơn thuốc thường, đơn "N" gây nghiện, đơn "H" hướng thần/tiền chất, cam kết dùng thuốc
> gây nghiện, xác nhận trạm y tế, biên bản nhận lại thuốc của KCB, danh mục bệnh kê đơn >30 ngày).

## Đối tượng điều chỉnh chính: người **kê đơn** (bác sĩ/y sĩ tại cơ sở KCB), không phải nhà thuốc

Thông tư này quy định việc **kê đơn**, không phải việc **bán/cấp phát** — nhà thuốc bán lẻ chỉ
xuất hiện ở 2 chỗ: (1) nghĩa vụ lưu đơn (Điều 11), (2) là nơi nhận đơn "N"/"H" có đóng dấu treo.

## Điều 11 — Lưu đơn, tài liệu về thuốc (liên quan trực tiếp `docs/13` mục C.4)

> Khoản 1: "Các cơ sở: khám bệnh chữa bệnh, pha chế, cấp thuốc, **bán lẻ thuốc** lưu toàn bộ đơn
> thuốc và tài liệu quy định tại khoản 3 Điều 7, khoản 2 Điều 8, điểm b khoản 6 và điểm b khoản 7
> Điều 12 Thông tư này theo quy định về lưu Hồ sơ... tại **Thông tư số 53/2017/TT-BYT**."

⚠️ TT53/2017 **đã hết hiệu lực** — bị TT33/2025 bãi bỏ cùng ngày (01/7/2025). Đọc tham chiếu này
là **TT33/2025** (xem `Thông-tư-33-2025-TT-BYT.SUMMARY.md`).

> Khoản 2: hết hạn lưu → cơ sở lập Hội đồng hủy tài liệu theo **TT 20/2017/TT-BYT**.

⚠️ TT20/2017 **cũng đã hết hiệu lực** — bị TT18/2026 bãi bỏ (16/7/2026). Đọc tham chiếu này là
**TT18/2026 Điều 15.4** (lập hội đồng hủy, lập biên bản hủy, lưu hồ sơ việc hủy).

## Tài liệu nhà thuốc bán lẻ phải lưu theo Điều 11 (trỏ đến các khoản khác của TT26)

| Khoản dẫn chiếu | Nội dung | Áp dụng nhà thuốc bán lẻ? |
|---|---|---|
| Điều 7.3 (cam kết dùng thuốc gây nghiện, Phụ lục IV) | Người kê đơn hướng dẫn bệnh nhân viết cam kết | Do **cơ sở KCB** lập, không phải nhà thuốc — nhà thuốc chỉ lưu đơn "N" có dấu treo |
| Điều 8.2 (cam kết thuốc gây nghiện giảm đau ung thư) | Như trên | Như trên |
| Điều 12.6.b (biên bản nhận lại thuốc, Phụ lục VI) | Cơ sở KCB nhận lại thuốc không dùng hết | Áp cho **cơ sở KCB** — nhà thuốc bán lẻ dùng **Phụ lục XVIII của TT18**, không phải Phụ lục VI của TT26 (2 mẫu song song cho 2 loại hình cơ sở khác nhau, không mâu thuẫn) |
| Điều 12.7.b | (không trích được do giới hạn phạm vi đọc) | Cần đọc thêm nếu áp dụng |

⇒ **Với nhà thuốc bán lẻ, tài liệu chính phải lưu theo Điều 11 chỉ là: đơn thuốc "N"/"H" gốc có
dấu treo của cơ sở KCB, lưu tại nơi bán thuốc.** Không phát sinh thêm nghĩa vụ hồ sơ mới ngoài
những gì `docs/13` mục C.2 (Điều 12.1.c TT18 — lưu đơn GN/HT sau khi bán) đã có.

## Không phải nguồn cho rule "mọi thuốc ETC cần đơn thuốc"

TT26 chỉ điều chỉnh **việc kê đơn tại cơ sở KCB** (Điều 1), không điều chỉnh nghĩa vụ của nhà
thuốc bán lẻ phải đòi đơn khi bán ETC nói chung. Rule C.3.1 trong `docs/13` (hiện feature-flag
TẮT, chờ nguồn) **vẫn chưa có nguồn trực tiếp** — giữ nguyên trạng thái, không đổi.

## Không cần thay đổi code

TT26 không phát sinh nghĩa vụ mới nào cho module `compliance` ngoài việc **xác nhận lại đúng**
2 tham chiếu đã lỗi thời trong chính TT26 (TT53→TT33, TT20→TT18 Điều 15.4) — đã ghi vào
`docs/13_COMPLIANCE_SPEC.md` mục C.4/C.5.
