# Thiết kế: ký sổ điện tử theo TT18 Điều 15.1.d — CHỜ CHAIN DUYỆT

> Soạn 2026-07-25 (bước 6, Chain chốt "thiết kế trước, chưa code"). **Chưa code dòng nào.**
> Nguồn: `docs/legal/Thông-tư-18-2026-TT-BYT.SUMMARY.md` mục 7; `docs/13` mục C.5.

## 1. Nghĩa vụ nguyên văn

TT18 **Điều 15.1** — được dùng sổ trên phần mềm khi đủ **cả 4** điều kiện; điểm (d):

> *"Người theo dõi hoặc người xác nhận các thông tin, dữ liệu trên các sổ sách phải sử dụng
> các kỹ thuật xác nhận điện tử hoặc chữ ký số để ký vào biểu mẫu có liên quan."*

Ghi chú **Phụ lục VIII** (bắt buộc kèm): dùng phần mềm ⇒ phải **trích xuất, in vào cuối MỖI NGÀY**,
lưu hồ sơ, **có chữ ký xác nhận trên TỪNG TRANG** của người quản lý thuốc và trưởng bộ phận.

⚠️ Văn bản cho **hai lựa chọn** — "kỹ thuật xác nhận điện tử" **hoặc** "chữ ký số". Đây là chỗ mở
để chọn phương án; không bắt buộc phải chữ ký số USB token.

## 2. Ba hướng

| | **A. Xác nhận điện tử bằng tài khoản IAM + chuỗi hash** | **B. Chữ ký số USB token (dược sĩ phụ trách)** | **C. Chữ ký số HSM/remote signing** |
|---|---|---|---|
| Cách làm | Người ký đăng nhập lại (re-auth), hệ thống ghi `signed_by`, `signed_at`, `hash` của nội dung sổ ngày đó, móc xích vào hash ngày trước | Tích hợp token USB (VNPT-CA/Viettel-CA/FPT-CA), ký PDF sổ theo chuẩn PAdES | Ký từ xa qua nhà cung cấp, không cần cắm token |
| Chi phí/năm | **0đ** (dùng lại IAM sẵn có) | ~1–2 triệu/token/năm × số người ký | ~1–3 triệu/năm/thuê bao |
| Công code | ~1 sprint nhỏ | Trung bình (SDK/driver, chỉ chạy Windows là chuyện thường gặp) | Trung bình (API, không cần driver) |
| Hợp lệ pháp lý | Khớp vế **"kỹ thuật xác nhận điện tử"** — nhưng chưa có tiền lệ thanh tra để chắc | Khớp vế **"chữ ký số"** — an toàn nhất, không tranh cãi | Khớp vế "chữ ký số" nếu nhà cung cấp được cấp phép |
| Vận hành hằng ngày | Dược sĩ nhập lại mật khẩu 1 lần/ngày | Phải cắm token, nhớ mã PIN; mất token là tắc | Ký trên điện thoại/web, không cần thiết bị |
| Rủi ro chính | Thanh tra không chấp nhận ⇒ phải làm lại theo B/C | Chi phí + phiền hà; máy Linux/Mac vướng driver | Phụ thuộc nhà cung cấp còn sống, còn hợp đồng |

## 3. GĐ khuyến nghị: **A trước, mở đường sang C**

Lý do:
1. **Văn bản cho phép A** — "hoặc" là hoặc thật, không phải câu đệm. Làm A là tuân thủ, không phải lách.
2. **A rẻ và không đổi thói quen** — nhà thuốc nhỏ, ép cắm token mỗi ngày là thứ sẽ bị bỏ sau 2 tuần,
   rồi quay lại ký giấy — tức là tiền mất mà nghĩa vụ vẫn hở.
3. **Chuỗi hash là phần đắt giá, dùng lại được cho cả B lẫn C.** Nếu sau này thanh tra đòi chữ ký số
   thật, phần đã làm không bỏ đi: chỉ thay bước "ký" ở cuối, hạ tầng toàn vẹn dữ liệu giữ nguyên.
4. Chọn C hơn B khi phải nâng cấp — cùng giá trị pháp lý, không dính driver/thiết bị.

**Điều kiện kèm theo (bắt buộc nếu chọn A):** vẫn **in và ký tay cuối mỗi ngày** theo ghi chú
Phụ lục VIII cho tới khi có hướng dẫn rõ hơn. A giải quyết điểm (d), **không** giải quyết ghi chú
"ký từng trang" — hai nghĩa vụ khác nhau, đừng gộp.

## 4. Nếu Chain chọn A — phạm vi kỹ thuật

| Việc | Ghi chú |
|---|---|
| Bảng `ledger_book_signatures` | `tenant_id`, `book_type`, `book_date`, `drug_id`, `content_hash`, `prev_hash`, `signed_by_user_id`, `signed_at` |
| Endpoint `POST .../books/{book_type}/sign` | Re-auth bắt buộc (nhập lại mật khẩu), không chấp nhận token đang mở sẵn |
| Chuỗi hash | `prev_hash` = chữ ký ngày liền trước cùng sổ ⇒ sửa lùi một ngày là gãy cả chuỗi, phát hiện được |
| Quyền mới | `compliance.ledger.sign` — tách khỏi `ledger.write`, chỉ người quản lý thuốc/trưởng bộ phận |
| Chặn | Không cho ký lại ngày đã ký; không cho ghi thêm dòng vào ngày đã ký |

Việc này **gộp chung với bước 5** (kết xuất cuối ngày) là hợp lý — cùng chạm một chỗ, cùng một khái
niệm "chốt sổ ngày".

## 5. Cần Chain trả lời trước khi code

| # | Câu hỏi |
|---|---|
| 1 | Chọn A, B hay C? (GĐ khuyến nghị **A**) |
| 2 | Ai là người ký trong nhà thuốc — chỉ dược sĩ phụ trách, hay có cả trưởng ca? (quyết định số vai trong RBAC) |
| 3 | Nhà thuốc hiện **đã ghi sổ tay** cho thuốc dạng phối hợp từ 16/7 chưa? (nếu chưa là thiếu sót hồ sơ ngoài đời, phần mềm không lấp ngược được) |
