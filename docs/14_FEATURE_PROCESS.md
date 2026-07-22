# 14 — QUY TRÌNH THÊM TÍNH NĂNG MỚI (Compliance by Design + Privacy by Design)

> Tài liệu quản trị. Áp dụng **bắt buộc** cho mọi tính năng **không nằm trong
> ROADMAP gốc**. Đồng cấp với [docs/13_COMPLIANCE_SPEC.md](13_COMPLIANCE_SPEC.md)
> về hiệu lực. Chốt & áp dụng từ: **2026-07-23**.
>
> Mục tiêu tối thượng của AI Pharmacy OS: một **Sổ điện tử quản lý nhà thuốc**
> chứng minh được việc tuân thủ pháp luật khi thanh tra, mở rộng thành SaaS
> mà KHÔNG PHẢI thiết kế lại kiến trúc tuân thủ. Mọi tính năng mới phục vụ
> mục tiêu này trước, tính năng thương mại đến sau.

Mọi tính năng mới (không nằm trong ROADMAP gốc) đi qua đúng các bước sau,
**đảo ngược từ đích đến gốc** — nghĩ từ "muốn đạt DoD gì, chứng minh tuân thủ
ra sao" trước, rồi mới code.

## Bước 0 — Đích (DoD ngược)
Viết trước: "Khi xong, người dùng làm được gì, và bằng chứng gì cho thấy hệ
thống tuân thủ pháp luật khi bị hỏi." Không code cho tới khi câu này rõ.

## Bước 1 — Checklist Compliance by Design / Privacy by Design (BẮT BUỘC, theo đúng thứ tự, không bỏ qua bước nào dù có vẻ không liên quan)

1. **Căn cứ pháp lý** — Có luật/nghị định/thông tư nào cho phép xử lý loại
   dữ liệu này không? Ghi rõ trích dẫn văn bản (như docs/13 đã làm). Nếu
   không tìm được căn cứ rõ ràng → DỪNG, báo cáo, không tự suy diễn.
2. **Đồng ý — nếu cần** — Có cần sự đồng ý của chủ thể dữ liệu không? Nếu có:
   lưu bằng chứng **kiểm chứng được**: thời điểm, tài khoản/thiết bị thực hiện,
   IP, phiên bản điều khoản đã đồng ý, và có cơ chế **rút lại đồng ý** +
   **xóa dữ liệu theo yêu cầu** (Luật BVDLCN 91/2025/QH15).
3. **Phân loại dữ liệu** — Dữ liệu thường hay dữ liệu cá nhân **nhạy cảm**
   (sức khỏe, tài chính, sinh trắc học...)? Nhạy cảm → áp dụng toàn bộ các
   bước còn lại nghiêm ngặt hơn, không có ngoại lệ "làm tạm".
4. **Audit log bất biến** — Mọi thao tác ghi/sửa/xóa dữ liệu loại này phải có
   audit log KHÔNG THỂ chỉnh sửa (theo đúng khuôn `ControlledLedgerEntry`,
   `NationalSyncLog` đã có — append-only, không update/delete bản ghi cũ).
5. **Phân quyền theo vai trò (RBAC)** — Ai được xem/sửa dữ liệu này? Kiểm tra
   RBAC hiện tại có phải JWT thật hay vẫn dev-header tạm (xem TODO.md nợ cũ)
   — nếu vẫn tạm, đây là điều kiện tiên quyết phải xử lý trước, không xây
   tính năng nhạy cảm trên nền RBAC chưa hoàn chỉnh.
6. **Truy xuất, sao lưu, phục hồi** — Dữ liệu này có nằm trong quy trình
   backup/restore đã có không? Nếu là bảng mới, xác nhận nó được bao phủ.
7. **AI chỉ qua lớp phân quyền + RAG, không đụng DB trực tiếp** — Nếu tính
   năng dùng LLMProvider: AI chỉ được truy xuất qua port đã kiểm soát quyền
   (như `ClinicalService` hiện tại), KHÔNG BAO GIỜ cho AI query thẳng
   database. RAG (khi làm thật) chỉ đọc corpus đã duyệt, không đọc trực tiếp
   bảng nghiệp vụ chứa PII.
8. **Rà theo Luật Dược + Luật BVDLCN + NĐ 356/2025 + GPP hiện hành** — Với
   mỗi văn bản, tạo/mở rộng file trong `docs/legal/` giống cách đã làm với
   QĐ540/TT20/QĐ1867. Nếu thiếu văn bản → ghi rõ blocker, không tự suy diễn
   (đúng nguyên tắc đã giữ từ Compliance Sprint).

## Bước 2 — Rà chồng lấn với module đã có
Trước khi tạo entity mới, tìm trong 12 module hiện có xem đã có khái niệm
tương tự chưa (như CustomerDetail vs Customer đã hỏi trước khi code). Ghi
quyết định vào `docs/features/<slug>/01_DECISIONS.md`.

## Bước 3 — Bản đồ phụ thuộc & rủi ro cross-module
Liệt kê module nào bị đụng, đánh dấu rõ bước nào cross-module (→ Opus +
phiên riêng + dừng chờ duyệt, đúng tiền lệ S4.4/S5.4/C.5/S6-Bước2).

## Bước 4 — Cập nhật ROADMAP + PROJECT_STATE TRƯỚC khi mở sprint
Không code một dòng nào khi Bước 0-3 chưa xong và chưa được duyệt.

Chỉ sau 4 bước này mới bắt đầu domain thuần → app/infra/migration → interface.

---

## Trạng thái nền khi chốt quy trình (2026-07-23) — để không phải kiểm lại

Ghi nhận sự thật đã kiểm chứng tại thời điểm áp dụng, phục vụ Bước 1 của các
tính năng sắp tới (hồ sơ KH, tích điểm, in bill):

- **Bước 1.5 (RBAC) — CHƯA THỎA.** `api/deps.py` vẫn tổng hợp context từ
  header `X-Tenant-Id/X-Branch-Id/X-User-Id` cho non-prod; chỉ decode JWT thật
  khi có `Authorization: Bearer`; prod từ chối unauth. Module IAM (users/roles/
  cấp JWT) **chưa dựng**. → Là **điều kiện tiên quyết** phải xử lý trước khi
  xây bất kỳ tính năng chạm dữ liệu cá nhân nhạy cảm.
- **Bước 1.8 / 1.1 — văn bản pháp lý còn THIẾU.** `docs/legal/` hiện chỉ có
  QĐ540, QĐ1867, TT20/2017. **Chưa có**: Luật BVDLCN 91/2025/QH15, Luật Dược
  (bản hợp nhất hiện hành), NĐ 356/2025, GPP hiện hành. → **Blocker**, không
  tự suy diễn nội dung các văn bản này.
- **Audit log bất biến (Bước 1.4) — khuôn có sẵn:** `ControlledLedgerEntry`,
  `NationalSyncLog` (append-only) làm mẫu tham chiếu.
- **AI qua port (Bước 1.7) — khuôn có sẵn:** `ClinicalService` + `LLMProvider`
  (hiện `MockLLMProvider`); chưa có RAG thật.
