# Chính sách lưu trữ dữ liệu khách hàng — Hồ sơ sức khỏe KH

> Bước 4 mục 4 của `01_DECISIONS.md`. Nguồn sự thật kỹ thuật là
> `core/privacy.py::processing_record()` (trường `retention` của từng `DataCategory`) — tài liệu
> này diễn giải bằng ngôn ngữ chính sách, không lặp lại logic code. Nếu 2 nơi lệch nhau, code đúng.

## 1. Hai loại dữ liệu, hai căn cứ thời hạn khác nhau

| Loại dữ liệu | Căn cứ pháp lý cho thời hạn | Thời hạn lưu tối thiểu | Xóa/khử nhận dạng khi nào |
|---|---|---|---|
| Cơ bản (tên, SĐT, ngày sinh, giới tính) | Nghĩa vụ lưu hồ sơ bán hàng (kế toán/hóa đơn) | Không có nghĩa vụ luật định riêng cho dữ liệu này | Ngay khi chủ thể yêu cầu (Luật 91/2025 Điều 13-14), qua `POST /customers/{id}/anonymise` |
| Sức khỏe (dị ứng, bệnh nền, lịch sử dùng thuốc) | GPP TT02/2018 I-1a.II.4.d — hồ sơ/sổ sách lưu **tối thiểu 1 năm kể từ khi hết hạn dùng của thuốc** | Dòng cấp phát/lịch sử dùng thuốc: ≥ 1 năm sau hạn dùng thuốc liên quan | Dị ứng/bệnh nền hiện tại: xóa ngay khi khử nhận dạng (không có nghĩa vụ giữ riêng chúng, chỉ dòng lịch sử cấp phát mới có nghĩa vụ) |

**Vì sao hai loại tách thời hạn khác nhau:** cơ sở pháp lý để *lưu* dị ứng/bệnh nền là đồng ý
(Luật 91 Điều 26.1) — không văn bản nào bắt nhà thuốc phải giữ chúng. Nhưng *dòng cấp phát thuốc
đã bán* thì GPP bắt giữ ≥ 1 năm, bất kể khách có rút đồng ý hay không. Khử nhận dạng (Q2,
`01_DECISIONS.md`) giải quyết đúng chỗ mâu thuẫn này: gỡ định danh, giữ dòng số liệu.

## 2. Cơ chế trong hệ thống

| Nhu cầu | Đã có | Chưa có (ghi nợ) |
|---|---|---|
| Chủ thể yêu cầu xóa → khử nhận dạng ngay | ✅ `POST /customers/{id}/anonymise` | — |
| Xóa/khử nhận dạng **tự động** khi hết hạn lưu trữ (không cần khách yêu cầu) | — | ❌ Chưa xây — hiện là quy trình thủ công. Ghi trong `known_gaps` của `processing_record()` |
| Diễn tập phục hồi dữ liệu đã sao lưu | Bảng nằm trong `pg_dump` toàn CSDL, tự động phủ (§1.6 `01_DECISIONS.md`) | ❌ Chưa từng diễn tập restore thật — rủi ro vận hành, không phải blocker tính năng này |

## 3. Vận hành — việc tenant (nhà thuốc) phải tự làm, BeraLLC không làm thay

1. Không có job tự động xóa dữ liệu hết hạn — nhà thuốc/chuỗi tự rà định kỳ nếu muốn dọn dữ liệu
   quá hạn lưu trữ tối thiểu (không bắt buộc xóa, chỉ bắt buộc *không xóa sớm hơn* mốc tối thiểu).
2. Diễn tập phục hồi từ backup là trách nhiệm vận hành hạ tầng (BeraLLC vận hành hosting), không
   phải nghiệp vụ nhà thuốc — ghi nợ vận hành riêng, không thuộc phạm vi tài liệu này.

## 4. Xem lại

Khi có luật sư xác nhận lại Q2 (khử nhận dạng vs xóa cứng, xem `01_DECISIONS.md` mục "Rủi ro còn
lại"), rà lại tài liệu này cùng lúc — thời hạn/lằn ranh có thể đổi theo kết luận của luật sư.
