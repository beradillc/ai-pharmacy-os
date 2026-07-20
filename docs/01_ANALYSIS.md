# 01 — PHÂN TÍCH HỆ THỐNG (Analysis)

> Tài liệu phân tích nghiệp vụ & yêu cầu cho **AI Pharmacy OS**.
> Sprint 1 · Trạng thái: *Hoàn thành thiết kế, chưa hiện thực hóa*.

---

## 1. Tầm nhìn (Vision)

**AI Pharmacy OS** là một *hệ điều hành nghiệp vụ* (business operating system) cho nhà thuốc / chuỗi nhà thuốc tại Việt Nam, lấy AI làm lõi (AI-native). Mục tiêu không chỉ số hóa quầy thuốc mà biến mỗi nghiệp vụ (bán hàng, kê đơn, nhập kho, tư vấn) thành một luồng có AI hỗ trợ ra quyết định an toàn dược lý và tối ưu vận hành.

**Một câu:** *"POS + Kho + Đơn thuốc + Dược sĩ AI, chạy trên một nền tảng module hóa, tuân thủ quy định Bộ Y tế Việt Nam."*

---

## 2. Vấn đề cần giải quyết (Problem Statement)

| # | Vấn đề thực tế | Hệ quả | AI Pharmacy OS giải quyết |
|---|----------------|--------|---------------------------|
| P1 | Bán thuốc thiếu kiểm tra tương tác/chống chỉ định | Rủi ro an toàn bệnh nhân | Module **Clinical/AI** kiểm tra tương tác, dị ứng, liều |
| P2 | Quản lý lô/hạn dùng thủ công | Hàng hết hạn, thất thoát | Module **Inventory** với FEFO, cảnh báo cận date |
| P3 | Liên thông Dược Quốc gia làm tay | Sai sót, phạt hành chính | Module **Compliance** + Plugin liên thông DAV |
| P4 | Tư vấn phụ thuộc kinh nghiệm nhân viên | Chất lượng không đồng đều | **Dược sĩ AI** (RAG trên tri thức dược) |
| P5 | Dự báo nhập hàng theo cảm tính | Tồn kho lệch, đọng vốn | **Analytics** dự báo nhu cầu |
| P6 | Nhiều chi nhánh, dữ liệu rời rạc | Khó tổng hợp, kiểm soát | Kiến trúc **multi-branch / multi-tenant** |

---

## 3. Phạm vi (Scope)

### 3.1 Trong phạm vi (In-scope) — MVP → v1
- Quản lý danh mục thuốc (drug master, ATC, hoạt chất, dạng bào chế, đơn vị quy đổi).
- Quản lý kho: lô (batch/lot), hạn dùng, nhập/xuất/kiểm kê, FEFO.
- Bán hàng POS: đơn bán, thanh toán, in hóa đơn, trả hàng.
- Quản lý đơn thuốc (Rx): tiếp nhận, xác thực, cấp phát.
- Dược sĩ AI: kiểm tra tương tác thuốc, dị ứng, liều, gợi ý thay thế, tra cứu thông tin.
- CRM: khách hàng, bệnh nhân, lịch sử mua.
- Mua hàng: nhà cung cấp, đơn đặt hàng (PO), nhập kho (GRN).
- Báo cáo & Dashboard cơ bản.
- Phân quyền theo vai trò (RBAC), đa chi nhánh.
- Liên thông Dược Quốc gia (qua plugin).

### 3.2 Ngoài phạm vi (Out-of-scope) — cân nhắc sau v1
- Sàn thương mại điện tử B2C hoàn chỉnh.
- Ứng dụng di động cho bệnh nhân.
- Tích hợp bảo hiểm y tế (BHYT) claim tự động (giai đoạn 3).
- Sản xuất/pha chế thuốc (compounding) quy mô công nghiệp.
- Kế toán tài chính đầy đủ (chỉ cung cấp API export cho phần mềm kế toán).

---

## 4. Các bên liên quan (Stakeholders) & Actor

| Actor | Vai trò | Nhu cầu chính |
|-------|---------|---------------|
| **Dược sĩ phụ trách** | Chịu trách nhiệm chuyên môn | Duyệt đơn, kiểm soát thuốc kê đơn/kiểm soát đặc biệt |
| **Nhân viên bán hàng** | Thu ngân, tư vấn cơ bản | POS nhanh, gợi ý AI, tra cứu |
| **Thủ kho** | Nhập/xuất/kiểm kê | Quản lý lô, hạn dùng, cảnh báo |
| **Quản lý chi nhánh** | Vận hành 1 điểm bán | Báo cáo, tồn kho, doanh thu |
| **Chủ chuỗi / Admin** | Điều hành toàn hệ thống | Tổng hợp đa chi nhánh, phân quyền, cấu hình |
| **Bệnh nhân / Khách hàng** | Người mua/sử dụng | Đơn thuốc đúng, tư vấn an toàn |
| **Cơ quan quản lý (DAV)** | Giám sát tuân thủ | Liên thông dữ liệu, báo cáo |
| **Dược sĩ AI (Agent)** | Trợ lý phần mềm | Không phải người — là actor hệ thống hỗ trợ ra quyết định |

---

## 5. Yêu cầu chức năng (Functional Requirements)

Mã hóa theo module. `FR-<MODULE>-<n>`.

### Catalog (danh mục)
- FR-CAT-1: Quản lý CRUD thuốc với mã ATC, hoạt chất, hàm lượng, dạng bào chế.
- FR-CAT-2: Đơn vị quy đổi (hộp → vỉ → viên) với hệ số.
- FR-CAT-3: Barcode / QR, mã DAV, số đăng ký (SĐK).
- FR-CAT-4: Phân loại: OTC / kê đơn (ETC) / kiểm soát đặc biệt.

### Inventory (kho)
- FR-INV-1: Theo dõi tồn theo lô + hạn dùng.
- FR-INV-2: Xuất kho theo FEFO (First-Expired-First-Out).
- FR-INV-3: Cảnh báo cận date, dưới định mức (reorder point).
- FR-INV-4: Kiểm kê, điều chỉnh, chuyển kho giữa chi nhánh.

### Sales / POS
- FR-SAL-1: Tạo đơn bán, quét barcode, tính tiền, thuế VAT.
- FR-SAL-2: Nhiều hình thức thanh toán (tiền mặt, thẻ, ví, QR).
- FR-SAL-3: Trả hàng / hoàn tiền có kiểm soát.
- FR-SAL-4: Chặn bán thuốc ETC khi thiếu đơn hợp lệ.

### Prescription (Rx)
- FR-RX-1: Tiếp nhận đơn (nhập tay / ảnh / e-prescription).
- FR-RX-2: Trích xuất đơn từ ảnh bằng AI (OCR + LLM).
- FR-RX-3: Xác thực đơn: bác sĩ, chẩn đoán, liều.
- FR-RX-4: Cấp phát & ghi nhận vào lịch sử bệnh nhân.

### Clinical / AI
- FR-AI-1: Kiểm tra tương tác thuốc–thuốc, thuốc–bệnh, thuốc–dị ứng.
- FR-AI-2: Kiểm tra liều theo tuổi/cân nặng/chức năng thận.
- FR-AI-3: Gợi ý thuốc thay thế cùng hoạt chất/nhóm.
- FR-AI-4: Dược sĩ AI hội thoại (RAG) tra cứu thông tin thuốc.
- FR-AI-5: Mọi khuyến nghị AI đều ghi log, có mức độ tin cậy & nguồn.

### CRM
- FR-CRM-1: Hồ sơ khách hàng/bệnh nhân, dị ứng, bệnh nền.
- FR-CRM-2: Lịch sử mua & lịch sử dùng thuốc.
- FR-CRM-3: Điểm thưởng / loyalty (tùy chọn).

### Procurement
- FR-PRO-1: Quản lý nhà cung cấp.
- FR-PRO-2: Đơn đặt hàng (PO), đề xuất tự động từ Analytics.
- FR-PRO-3: Nhập kho từ PO (GRN), đối chiếu.

### Compliance
- FR-COM-1: Sổ theo dõi thuốc kiểm soát đặc biệt (TT 20/2017).
- FR-COM-2: Audit log bất biến mọi thao tác nhạy cảm.
- FR-COM-3: Xuất báo cáo & liên thông Dược Quốc gia (plugin).

### Analytics
- FR-ANA-1: Dashboard doanh thu, tồn kho, lợi nhuận gộp.
- FR-ANA-2: Dự báo nhu cầu theo mùa vụ/lịch sử.
- FR-ANA-3: Đề xuất nhập hàng.

### Identity / Access
- FR-IAM-1: Người dùng, vai trò, quyền (RBAC).
- FR-IAM-2: Đa chi nhánh, phân tách dữ liệu.
- FR-IAM-3: SSO/OAuth2 (tùy chọn), 2FA cho vai trò nhạy cảm.

---

## 6. Yêu cầu phi chức năng (Non-Functional Requirements)

| Nhóm | Yêu cầu | Chỉ tiêu |
|------|---------|----------|
| **Hiệu năng** | Thời gian phản hồi POS | < 300ms (p95), thao tác quét–thêm |
| | Kiểm tra tương tác AI | < 2s (p95) |
| **Sẵn sàng** | Uptime | 99.5% (chế độ offline-first cho POS) |
| **Bảo mật** | Mã hóa dữ liệu nhạy cảm | At-rest (AES-256) + in-transit (TLS 1.3) |
| | Kiểm soát truy cập | RBAC + audit log bất biến |
| **Tuân thủ** | Dữ liệu cá nhân/bệnh nhân | Nghị định 13/2023 (bảo vệ DLCN) |
| | Thuốc kiểm soát | TT 20/2017/TT-BYT |
| **Khả mở rộng** | Kiến trúc | Modular monolith → tách microservice khi cần |
| **Khả bảo trì** | Test coverage lõi | ≥ 80% domain layer |
| **Khả di động** | Triển khai | Docker, chạy on-premise hoặc cloud |
| **An toàn AI** | Human-in-the-loop | AI *khuyến nghị*, người *quyết định*; không tự động cấp phát |
| **I18n** | Ngôn ngữ | Tiếng Việt mặc định, kiến trúc sẵn sàng đa ngữ |

---

## 7. Ràng buộc & Giả định (Constraints & Assumptions)

**Ràng buộc:**
- Tuân thủ pháp lý Việt Nam (Bộ Y tế / DAV) là bắt buộc, không phải tùy chọn.
- POS phải hoạt động khi mất mạng (offline-first, đồng bộ sau).
- AI không được phép ra quyết định cuối cùng cho việc cấp phát thuốc (chỉ hỗ trợ).

**Giả định:**
- Mỗi nhà thuốc có kết nối Internet ổn định phần lớn thời gian.
- Dữ liệu tri thức dược (tương tác, liều) được cung cấp từ nguồn có bản quyền/được phép + tự xây dựng.
- Người dùng cuối có thiết bị đọc barcode.

---

## 8. Rủi ro chính (Risk Register — tóm tắt)

| ID | Rủi ro | Mức | Giảm thiểu |
|----|--------|-----|-----------|
| R1 | AI đưa khuyến nghị dược lý sai | Cao | RAG có nguồn, human-in-the-loop, ngưỡng tin cậy, guardrails |
| R2 | Rò rỉ dữ liệu bệnh nhân | Cao | Mã hóa, RBAC, audit, tối thiểu hóa dữ liệu |
| R3 | Sai lệch tồn kho khi offline sync | Trung | Event sourcing cho tồn kho, conflict resolution |
| R4 | Thay đổi quy định DAV | Trung | Compliance qua plugin, tách biệt khỏi lõi |
| R5 | Phụ thuộc nhà cung cấp AI | Trung | Abstraction layer `LLMProvider`, có thể thay thế model |

Chi tiết đánh giá & workflow xem [06_WORKFLOWS.md](06_WORKFLOWS.md) và [12_AI_INTEGRATION.md](12_AI_INTEGRATION.md).

---

## 9. Tiêu chí thành công Sprint 1 (Definition of Done)

- [x] Phân tích nghiệp vụ & actor hoàn chỉnh.
- [x] Yêu cầu FR/NFR mã hóa đầy đủ.
- [x] Kiến trúc, ERD, UML, workflow, module, plugin, config được thiết kế.
- [x] README / ROADMAP / PROJECT_STATE hoàn chỉnh.
- [ ] *(Sprint 2)* Bất kỳ code sản phẩm nào — **không thuộc Sprint 1**.
