# Rà soát lộ trình trước khi quay video — GĐ, 2026-08-02

> Chain yêu cầu: *"Trước khi quay, GĐ rà soát lộ trình đã làm được tới đâu."*
> **Mọi con số dưới đây đo bằng lệnh trong phiên này**, không chép từ `ROADMAP.md` —
> chính `ROADMAP.md` đã có ít nhất một dòng tự thú *"tài liệu lệch với thực tế"* (Sprint 7).

---

## 1. Đo được gì

| Hạng mục | Số đo | Cách đo |
|---|---|---|
| Module nghiệp vụ | **11** | `ls modules/` — analytics · catalog · clinical · compliance · crm · iam · inventory · location · prescription · procurement · sales |
| Màn giao diện | **18** | `ls app/(app)/` |
| Migration | **46** (`0046_tenant_co_so`) | `ls migrations/versions/` |
| Plugin thật | **1** (`payment_vnpay`) | `ls plugins/` |
| Test backend | **1480 xanh** | `pytest` — xem mục 5, hôm nay nó ĐỎ |
| Test frontend | **117 xanh** | `vitest` |
| Cổng trình duyệt | **21** | `ui-gates.sh` |

## 2. Lộ trình — trạng thái thật

| Sprint | Tuyên bố | Thực tế đo được | Đánh giá |
|---|---|---|---|
| 1 Kiến trúc | ✅ | 20 tài liệu `docs/` | ✅ khớp |
| 2 Kernel | ✅ | config · DI · event bus · UoW · security · audit · plugin loader | ✅ khớp |
| 3 Catalog & Inventory | ✅ | 2 module, FEFO, event-sourced movements | ✅ khớp |
| 4 Sales/POS offline | ✅ backend | POS chạy thật, hàng chờ offline có, đồng bộ có | ✅ khớp |
| 5 Prescription & Clinical | ⚠️ "DONE ở mức MOCK" | `# BLOCKER: AI__API_KEY thật` + `# BLOCKER: nguồn tri thức dược có bản quyền` | ⚠️ **đúng như khai** — khớp dị ứng chạy bằng luật tự viết, không phải AI |
| 6 Procurement & CRM | ✅ | 2 module + hồ sơ sức khoẻ có gác đồng ý | ✅ khớp |
| 7 Compliance & Analytics | ✅ DoD đạt | sổ kiểm soát · dashboard · đề xuất đặt hàng · 6 loại báo cáo CSV | ✅ khớp — **nhưng xem mục 3** |
| 8 Plugin & Hardening | 🟠 3/5 | plugin loader ✅ · 2FA ✅ · load test ✅ (p95 217ms @ 8 luồng) · **observability ❌** · **mã hoá at-rest ❌** · **rate limit ❌** | 🟠 **chưa xong** |
| 9 Beta & Pilot | 🟠 1/4 | FE analytics ✅ · **chưa pilot nhà thuốc thật nào** | 🟠 đang ở đây |
| 10 Demo khách hàng | ✅ 12/12 | 4 màn quản lý + `make demo` | ✅ khớp |

**Vị trí thật: cuối Sprint 8, đầu Sprint 9.** Phần mềm chạy được đầu-cuối; phần còn thiếu
là *chịu tải thật* và *chạy thật ở một quầy thật*, không phải thiếu tính năng.

## 3. Điều kiện pháp lý — cái nào phần mềm đã đáp ứng, cái nào chưa

| # | Nghĩa vụ | Phần mềm làm được gì | Còn thiếu |
|---|---|---|---|
| 1 | Sổ thuốc kiểm soát đặc biệt | Ghi sổ · kết xuất · ký xác nhận điện tử · hash toàn vẹn | 🔴 **chưa ai có chuyên môn pháp lý rà** (N-3) |
| 2 | Báo cáo định kỳ 6 tháng/năm gửi UBND tỉnh | Kết xuất Mẫu số 06 | 🟠 chưa in phần đầu sổ (N-2) |
| 3 | Biên bản nhận lại thuốc GN/HT/TC | Có | — |
| 4 | Lưu trữ hồ sơ điện tử | Có · sao lưu có runbook | 🟠 sao lưu **chưa chạy thật lần nào** ở quầy |
| 5 | Liên thông CSDL Dược Quốc gia | Hạ tầng gửi + hàng đợi gửi lại **xong** | 🔴 **CHẶN CỨNG** — chưa có đặc tả API thật (`# BLOCKER: DAV API spec`). Đang là adapter giả |
| 6 | Chuẩn dữ liệu 23 trường | Có converter | — |
| 7 | Niêm yết giá | Có, bắt ghi lý do khi sửa | — |
| 8 | Phân quyền dược sĩ ⇄ thu ngân | Có, cưỡng chế ở cả API lẫn giao diện | — |
| 9 | Dữ liệu cá nhân nhạy cảm | Gác đồng ý · che số điện thoại · nhật ký mỗi lượt xem | 🟠 **mã hoá at-rest chưa xong** |

🔴 **Hai điều Chain cần biết rõ trước khi bán phần mềm này cho ai:**

1. **Liên thông CSDL Dược Quốc gia chưa chạy thật** — không phải chưa code, mà **chưa có
   đặc tả API để nối**. Mọi thứ quanh nó xong; đúng cái đầu dây thì chặn. Bán mà hứa
   "đã liên thông" là hứa sai.
2. **Màn Sổ kiểm soát chưa ai có chuyên môn pháp lý rà** (N-3, mở từ 01/08). Nó tự dán nhãn
   đỏ *"Chưa được rà pháp lý"* ngay trên màn — cố ý, và **không được gỡ nhãn đó** cho tới khi
   có người rà thật.

## 4. Còn thiếu gì để bán được — xếp theo mức chặn

| Mức | Việc | Vì sao |
|---|---|---|
| 🔴 Chặn phát hành | Rà pháp lý màn Sổ kiểm soát | Bán một sổ pháp lý chưa ai rà là rủi ro của BeraLLC, không phải của khách |
| 🔴 Chặn phát hành | Mã hoá at-rest dữ liệu bệnh nhân | Dữ liệu sức khoẻ đang nằm dạng đọc được trong CSDL |
| 🔴 Chặn phát hành | Rate limit | Chưa có gì chặn dò mật khẩu |
| 🟠 Chặn pilot | Pilot 1 nhà thuốc thật 2 tuần | Chưa quầy nào chạy thật ngày nào |
| 🟠 Chặn pilot | Observability | Hỏng ở quầy khách thì hiện không ai biết trước |
| 🟡 Sau | Liên thông DAV thật | Chặn ngoài tầm — chờ cơ quan cấp đặc tả |
| 🟡 Sau | AI lâm sàng thật | Chờ nguồn tri thức dược có bản quyền |

## 5. 🔴 Phát hiện trong lúc rà: bộ test ĐANG ĐỎ, và nó đỏ từ hôm qua

`pytest` hôm nay: **2 đỏ / 1478 xanh**. Nguyên nhân **không phải mã sản phẩm**:

```
test_fefo_dispense_picks_nearest_expiry   lô "NEAR" ghi cứng hạn date(2026, 8, 1)
test_catalog_and_inventory_flow           lô "NEAR" ghi cứng hạn "2026-08-01"
```

Hôm nay là **02/08**. Hai lô ấy vừa hết hạn, `dispense` lọc lô hết hạn (đúng), còn 10 đơn vị,
test xuất 12 ⇒ 409. **Sản phẩm đúng, phép kiểm sai.**

Nghĩa là bộ test **tự đỏ lúc nửa đêm 01→02/08** và không ai biết — vì các phiên gần đây đóng
mục bằng 4 cổng nhanh của hook, và **hook cố ý không chạy pytest** (536 giây).

Đã vá: tính hạn **tương đối** (`date.today() + timedelta`), đúng mẫu mà **chính hai tệp đó**
đã dùng ở chỗ khác. Đây là chỗ quên dùng mẫu đã có, không phải chỗ thiếu mẫu.

> **Bài học cho lộ trình, không chỉ cho hai tệp:** một dự án có *cổng nhanh chạy mọi lúc* và
> *cổng chậm chạy khi nhớ* thì cổng chậm là cổng **không tồn tại**. Đề nghị: chạy `make check`
> đầy đủ **mở đầu mỗi phiên**, không chỉ trước khi đóng mục.

## 6. Đề nghị của GĐ

1. **Quay video được** — phần mềm đủ chín cho 14 video hướng dẫn thao tác.
2. **Video 14 (mới) nói thẳng phần còn thiếu**, thay vì để người xem tự phát hiện. Một bộ
   video chỉ khoe cái chạy được sẽ mất uy tín ngay lần đầu khách hỏi *"liên thông chưa?"*.
3. **Không phát hành thương mại** cho tới khi đóng 3 mục 🔴 ở mục 4.
4. **Giao Trợ lý Pháp Lý rà màn Sổ kiểm soát** — đã đứng yên 2 ngày, hạn nêu lại 04/08.
