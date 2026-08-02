# Uỷ quyền quản trị — QUYẾT ĐỊNH ĐÃ CHỐT

- **Ngày:** 2026-08-03
- **Người quyết:** Chain (CEO) — *"Uỷ quyền được, chủ chuỗi sẽ chịu trách nhiệm, thời hạn 24
  tiếng mỗi xác nhận."*
- **Đề xuất gốc:** `00_DESIGN_PROPOSAL.md`

## Chốt

| Điểm | Quyết định | Khác đề xuất gốc? |
|---|---|---|
| Cơ chế uỷ quyền T2 | **Duyệt** | — |
| Thời hạn | **24 giờ mỗi lần xác nhận**, cố định | Đề xuất là mặc định 4h / tối đa 24h ⇒ **Chain chọn 24h thẳng** |
| Người chịu trách nhiệm | **Chủ chuỗi** | — |
| Lý do bắt buộc khi cấp | Giữ | — |
| Tự hết hạn, không cần thu hồi tay | Giữ | — |
| Báo cáo lại khi hết hạn | Giữ | — |

## 🔴 T3 (`compliance.ledger.sign`) — ĐỂ NGOÀI phạm vi lần này

Câu trả lời của Chain nói về **cơ chế uỷ quyền**; nó **không nói rõ** có bao gồm quyền ký sổ
thuốc kiểm soát đặc biệt hay không. GĐ **không tự suy**, và chọn cách để nguyên trạng thay vì
đoán theo hướng rộng hơn.

Lý do kỹ thuật của việc chọn hướng hẹp: chữ ký sổ thuốc kiểm soát không phải một quyền phần
mềm mà là **lời khai của một dược sĩ có Chứng chỉ hành nghề** trước cơ quan quản lý. Chủ chuỗi
nhận được trách nhiệm **dân sự/quản trị**, nhưng **tư cách chuyên môn** không chuyển sang người
khác bằng một thao tác trong phần mềm. Nếu thanh tra hỏi *"ai ký sổ này"* thì câu trả lời phải
là một người có chứng chỉ — và một chữ ký sai người trong sổ pháp lý là thứ **không sửa lại
được** sau khi đã nộp.

**Hệ quả hôm nay:** `system_admin` **vẫn** giữ `compliance.ledger.sign` như trước bản này — tức
lỗi thiết kế ② của bản rà soát 03/08 **chưa được đóng**. Nó không xấu đi, nhưng cũng chưa tốt
lên. Cần Chain trả lời một câu để đóng: *quyền ký sổ có nằm trong phạm vi uỷ quyền không?*

## Ràng buộc cài đặt suy ra từ quyết định

1. **Cưỡng chế lúc REQUEST, không phải lúc cấp token.** Quyền hiện nằm trong JWT. Nếu nhét
   quyền uỷ quyền vào token thì một uỷ quyền 24 giờ **sống dai hơn cửa sổ của nó** mỗi khi
   token còn hạn — tức chính cơ chế kiểm soát hỏng. Đổi lại: thêm một lượt đọc CSDL có chỉ mục
   trên mỗi request đã xác thực (`TokenScopeGuard` đã có 2 lượt; đây là lượt thứ ba).
2. **Hết hạn là một phép so thời gian, không phải một tác vụ nền.** Không có job nào phải chạy
   đúng giờ để thu hồi — thứ phải nhớ là thứ sẽ quên. `expires_at <= now()` ⇒ không còn hiệu lực,
   kể cả khi máy vừa mất điện ba ngày.
3. **Uỷ quyền mở cửa, nó KHÔNG tắt camera.** Trong thời gian uỷ quyền, mọi lượt đọc dữ liệu
   nhạy cảm **vẫn ghi `CUSTOMER_SENSITIVE_READ`** như hiện nay.
4. **Không cấp được quyền mà chính người cấp không có.** Chặn đường leo thang: một uỷ quyền
   không bao giờ rộng hơn người ký uỷ quyền.

   🔴 **Nhưng nó KHÔNG tự chặn được T3 — giả định ban đầu của GĐ SAI, đã kiểm bằng lệnh.**
   Bản nháp mục này viết *"chủ chuỗi không có `compliance.ledger.sign` … kiểm lại khi code"*.
   Kiểm ra: vai `chain_pharmacist` **CÓ** `compliance.ledger.sign` (đúng như phải thế — chủ
   chuỗi là dược sĩ phụ trách chuyên môn cấp chuỗi, người ký sổ hợp pháp). Nên ràng buộc "không
   cấp thứ mình không có" **không** ngăn được việc chuyển quyền ký sang một tài khoản kỹ thuật.
   ⇒ Phải có một **danh sách loại trừ tường minh**, không dựa vào hệ quả gián tiếp.

   Bài học ghi lại vì nó lặp được: *"ràng buộc A tự nhiên kéo theo tính chất B"* là một **giả
   định**, không phải một suy luận — và nó phải được `grep` xác nhận trước khi ghi vào tài liệu
   thiết kế. Cùng họ kỷ luật #16.

5. **Danh sách KHÔNG-UỶ-QUYỀN-ĐƯỢC là hằng số trong domain**, không phải cấu hình. Một quyền
   chỉ ra khỏi danh sách đó bằng cách sửa mã và qua cổng — không bằng một dòng `.env` gõ vội
   lúc 2 giờ sáng đang xử lý sự cố.
