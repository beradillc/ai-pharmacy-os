# 17 — QUY TRÌNH XỬ LÝ SỰ CỐ (Incident Response) — F-19

> **Trạng thái:** thiết kế **theo VAI**, chưa gắn người thật.
> **Điều kiện đóng F-19:** bảng §3 điền đủ người + số điện thoại + khung giờ trực.
> Chừng nào còn `TBD`, quy trình này **chạy được trên giấy nhưng chưa chạy được ngoài đời**.

Sinh từ kiểm toán độc lập 2026-07-26 (F-19, mục chặn Sprint 9). Áp dụng cho **pilot** —
deployment có **dữ liệu bệnh nhân thật** và **doanh thu thật** của một nhà thuốc đang bán hàng.

---

## 0. Quyết định chi phối (đã KHOÁ)

```
DECISION: Pilot không có thanh toán online
STATUS:   LOCKED (Chain, 2026-07-28)
IMPACT:   S9-C OPEN
IMPACT:   F-6 (giấy phép trung gian thanh toán) KHÔNG phải critical path của Pilot
PILOT_PHARMACY: TBD
F-19:     thiết kế role-based, bind người thật sau
```

**Hệ quả trực tiếp lên tài liệu này:** không có kịch bản sự cố nào liên quan tới cổng
thanh toán, hoàn tiền, hay đối soát tiền trực tuyến. Nhà thuốc thu tiền như trước khi có
phần mềm; phần mềm **ghi sổ**, không **giữ tiền**. Điều đó thu hẹp đáng kể bề mặt sự cố:
mất hệ thống = mất khả năng **ghi**, không phải mất **tiền đang trên đường đi**.

⚠️ Nếu có yêu cầu mới mở lại phạm vi thanh toán online, **DỪNG** và hỏi Chain — tài liệu
này phải viết lại phần đối soát (§6) trước khi pilot chạy tiếp.

---

## 1. Vai — định nghĩa trước, gắn người sau

Vai là **chức năng**, không phải chức danh. Một người có thể giữ nhiều vai; một vai phải
luôn có **đúng một người đang chịu trách nhiệm** tại mỗi thời điểm.

| Mã vai | Tên vai | Chịu trách nhiệm gì | Ai KHÔNG phải vai này |
|---|---|---|---|
| **R1** | **Người trực quầy** (Counter Operator) | Người đang đứng bán khi sự cố xảy ra. **Phát hiện** và **báo**. Quyết định dừng bán hay chuyển giấy ở **quầy của mình** | Không phải người sửa. Không được tự khởi động lại máy chủ |
| **R2** | **Quản lý nhà thuốc** (Pharmacy Manager) | Chủ sự cố về **nghiệp vụ**. Quyết định **chuyển sang quy trình giấy** cho cả nhà thuốc. Chịu trách nhiệm trước khách hàng | Không phải người sửa kỹ thuật |
| **R3** | **Trực kỹ thuật** (On-call Engineer) | Chủ sự cố về **kỹ thuật**. Chẩn đoán, khắc phục, quyết định rollback/restore | Không quyết định thay R2 chuyện dừng bán |
| **R4** | **Chỉ huy sự cố** (Incident Commander) | Chỉ kích hoạt ở **P1**. Điều phối, giữ mốc thời gian, quyết định leo thang và tuyên bố đóng | Không tự tay sửa — sửa là việc R3 |
| **R5** | **Đầu mối dữ liệu/pháp lý** | Vào cuộc khi sự cố **chạm dữ liệu bệnh nhân** hoặc **sổ thuốc kiểm soát đặc biệt**. Đánh giá nghĩa vụ thông báo | Không phải R3 kiêm nhiệm — xung đột lợi ích |

**Quy tắc bất biến:** R3 **không** được đồng thời là R4 trong cùng một sự cố P1. Người
đang cắm đầu vào log không phải người nhìn được toàn cảnh. Vi phạm quy tắc này là cách
một sự cố 20 phút trở thành 3 tiếng.

---

## 2. Phân mức sự cố

| Mức | Định nghĩa **quan sát được** | Ví dụ | SLA phản hồi | SLA khắc phục/giảm nhẹ |
|---|---|---|:---:|:---:|
| **P1** | Không bán được hàng, hoặc nghi mất/lộ dữ liệu bệnh nhân | POS chết cả nhà thuốc · CSDL không kết nối · nghi rò rỉ | **15 phút** | **60 phút** (khắc phục hoặc chuyển quy trình giấy ổn định) |
| **P2** | Bán được nhưng một chức năng quan trọng hỏng | Không in được hoá đơn · không ký được sổ kiểm soát đặc biệt · liên thông DAV đỏ | **60 phút** (trong giờ làm) | **1 ngày làm việc** |
| **P3** | Sai sót không chặn bán hàng | Báo cáo lệch số · cảnh báo cận date không hiện | **1 ngày làm việc** | **1 tuần** |

**Đo SLA từ lúc nào:** từ **thời điểm R1 báo**, không phải từ lúc R3 đọc được tin nhắn.
Đây là chủ đích — nếu đo từ lúc người trực đọc tin thì kênh liên lạc hỏng sẽ không bao
giờ hiện ra trong số liệu.

---

## 3. 🔴 BẢNG GẮN NGƯỜI — phải điền trước khi pilot chạy

> **Đây là phần duy nhất còn thiếu để đóng F-19.** Mọi thứ khác trong tài liệu này đã
> dùng được. Không được điền bằng tên phỏng đoán.

| Vai | Người | Điện thoại | Kênh chính | Kênh dự phòng | Khung trực | Người thay khi vắng |
|---|---|---|---|---|---|---|
| **R1** Người trực quầy | `TBD` | `TBD` | `TBD` | `TBD` | Theo ca bán | Ca kế tiếp |
| **R2** Quản lý nhà thuốc | `PILOT_OWNER = TBD` | `TBD` | `TBD` | `TBD` | Giờ mở cửa | `TBD` |
| **R3** Trực kỹ thuật | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| **R4** Chỉ huy sự cố | `TBD` | `TBD` | `TBD` | `TBD` | Chỉ khi P1 | `TBD` |
| **R5** Dữ liệu/pháp lý | `TBD` | `TBD` | `TBD` | `TBD` | Giờ hành chính | `TBD` |

| Biến | Giá trị |
|---|---|
| `PILOT_PHARMACY` | `TBD` |
| `PILOT_OWNER` | `TBD` |
| `PILOT_OPERATOR` | `TBD` |
| `PILOT_START_DATE` | `TBD` |
| `PILOT_SUPPORT_OWNER` | `TBD` |

**Quy tắc kênh liên lạc:** kênh chính **phải là thứ đổ chuông** (gọi điện), không phải
thứ chờ người mở ra xem (chat/email). Sự cố 21:00 mà báo bằng tin nhắn nhóm là báo vào
chỗ không ai đang nhìn.

**Kênh dự phòng phải khác hạ tầng với kênh chính.** Nếu cả hai đều cần internet của nhà
thuốc thì mất mạng là mất luôn cả hai đường báo.

---

## 4. Kịch bản chuẩn — «21:00, POS chết giữa ca bán hàng»

Đây là kịch bản **P1** và là bài kiểm tra của cả tài liệu này. Mỗi bước ghi rõ **ai**,
**làm gì**, **trong bao lâu**.

| # | Mốc | Ai | Hành động | Hạn |
|---|---|---|---|---|
| 1 | T+0 | **R1** | **Phát hiện**: bấm thanh toán không phản hồi / màn hình lỗi. **Không** thử sửa, **không** khởi động lại máy chủ | — |
| 2 | T+2′ | **R1** | **Gọi R3** (kênh chính, đổ chuông). Gọi **không được** ⇒ gọi R2. Đồng thời báo R2 dù đã gọi được R3 | 2 phút |
| 3 | T+3′ | **R1** | **Chuyển quầy sang giấy ngay, không chờ ai cho phép** — ghi tay: ngày giờ · tên thuốc · số lượng · lô/HSD nếu đọc được · tên khách nếu là thuốc kê đơn. Khách **không phải** đứng chờ hệ thống | 3 phút |
| 4 | T+5′ | **R3** | **Xác nhận đã nhận** với R1 và R2. Kể từ đây R3 là chủ sự cố kỹ thuật | **SLA 15′** |
| 5 | T+5′ | **R3** | **Tạo Incident** (§5) với mức P1 tạm thời. Tạo trước, chẩn đoán sau — sự cố không có hồ sơ là sự cố không đối soát lại được | — |
| 6 | T+10′ | **R2** | Quyết định **phạm vi chuyển giấy**: một quầy hay cả nhà thuốc. **Đây là quyết định của R2, không phải R3** | 10 phút |
| 7 | T+15′ | **R3** | Chẩn đoán sơ bộ, phân loại: app · CSDL · mạng · máy trạm. Báo R2 **ước tính thời gian**, kể cả khi ước tính là *"chưa biết"* | — |
| 8 | T+30′ | **R3** | Chưa khắc phục được ⇒ **leo thang**: gọi R4. R4 vào cuộc là chuyển từ *sửa* sang *chỉ huy* | **30 phút** |
| 9 | T+30′ | **R3/R4** | Nghi **mất hoặc lộ dữ liệu bệnh nhân** ⇒ gọi **R5 ngay**, không chờ khắc phục xong | Ngay |
| 10 | T+60′ | **R4** | Chưa khắc phục ⇒ **quyết định chạy quy trình giấy tới hết ca**, thông báo R2, dừng mọi thao tác sửa mạo hiểm trên dữ liệu thật | **SLA 60′** |
| 11 | Khi hệ thống sống lại | **R3** | Xác nhận bằng **lệnh thật**: đăng nhập được · bán thử 1 giao dịch nháp · số tồn kho khớp. **Không** tuyên bố "đã ổn" từ việc dịch vụ khởi động lại được | — |
| 12 | Sau khi sống lại | **R1 + R2** | **Nhập bù** phiếu giấy vào hệ thống. R1 nhập, **R2 đối chiếu từng phiếu** với sổ tay | Trước khi đóng ca |
| 13 | Cuối ca | **R2** | **Đối soát**: số phiếu giấy = số giao dịch đã nhập bù · tồn kho hệ thống = kiểm đếm thực tế các thuốc đã bán trong lúc mất hệ thống | Trước khi đóng ca |
| 14 | Sau đối soát | **R4** (P1) hoặc **R3** (P2/P3) | **Đóng Incident** — chỉ đóng khi §7 đủ 4 điều kiện | — |
| 15 | ≤ 3 ngày làm việc | **R4** chủ trì | **Post-Incident Review** (§8) | 3 ngày |

**Điều quan trọng nhất của kịch bản này nằm ở bước 3.** Người bán chuyển sang giấy
**ngay**, không xin phép. Mọi quy trình bắt người bán chờ quyết định trong khi khách
đứng trước quầy đều bị bỏ qua ngoài đời — và một quy trình bị bỏ qua thì tệ hơn là không
có, vì nó tạo ra ảo giác đã có quy trình.

---

## 5. Hồ sơ Incident — trường tối thiểu

Ghi ở đâu cũng được (kênh chat có ghim, file, hoặc issue tracker) miễn **một chỗ duy
nhất** và **không sửa được lịch sử**.

| Trường | Bắt buộc | Ghi chú |
|---|:---:|---|
| Mã sự cố | ✅ | `INC-YYYYMMDD-NN` |
| Thời điểm **phát hiện** | ✅ | Mốc tính SLA, không phải lúc tạo hồ sơ |
| Người phát hiện (vai + tên) | ✅ | |
| Mức (P1/P2/P3) | ✅ | Ghi cả **mức ban đầu** và mức sau khi đánh giá lại |
| Triệu chứng quan sát được | ✅ | *"Bấm thanh toán quay vòng 30 giây rồi báo lỗi"* — không phải *"hệ thống lỗi"* |
| Ảnh hưởng nghiệp vụ | ✅ | Bao nhiêu quầy · có bán được không · có chạm dữ liệu bệnh nhân không |
| Mốc thời gian từng bước | ✅ | Tối thiểu: phát hiện · báo · nhận · chuyển giấy · khắc phục · đối soát xong |
| Nguyên nhân gốc | ✅ khi đóng | Chưa tìm ra thì ghi **"chưa xác định"** — **cấm** đoán |
| Đã làm gì để khắc phục | ✅ | Kể cả những thứ đã thử mà không ăn thua |
| Có restore từ backup không | ✅ | Nếu có: backup ngày nào, mất bao nhiêu dữ liệu |
| Đối soát: lệch bao nhiêu | ✅ | Số phiếu giấy vs số đã nhập bù; lệch = 0 cũng phải ghi là 0 |
| Người đóng | ✅ | |

---

## 6. Đối soát sau sự cố — phần dễ bị bỏ nhất

Hệ thống chạy lại **không phải** là sự cố đã xong. Sự cố xong khi **sổ sách khớp**.

| Đối tượng | Ai kiểm | Cách kiểm |
|---|---|---|
| Giao dịch bán | **R2** | Đếm phiếu giấy, đối chiếu từng phiếu với giao dịch đã nhập bù. Lệch ⇒ **không đóng sự cố** |
| Tồn kho | **R2** | Kiểm đếm thực tế các mặt hàng đã bán trong lúc mất hệ thống, so với tồn hệ thống |
| Thuốc kiểm soát đặc biệt | **R2 + R5** | Bán trong lúc mất hệ thống ⇒ **bắt buộc** vào sổ theo TT18/2026, kể cả khi phải ghi bù. Đây là nghĩa vụ pháp lý, không phải việc dọn dẹp |
| Dữ liệu bệnh nhân | **R5** | Có mất/lộ không; nếu có, đánh giá nghĩa vụ thông báo theo Luật BVDLCN 91/2025 |

**Không có mục đối soát tiền trực tuyến** — pilot không có thanh toán online (§0). Tiền
mặt do nhà thuốc quản lý theo quy trình sẵn có của họ, phần mềm không tham gia.

---

## 7. Điều kiện đóng Incident — đủ **cả 4**

1. Chức năng đã hoạt động lại, **xác nhận bằng thao tác thật**, không bằng việc dịch vụ khởi động được.
2. **Đối soát §6 xong**, lệch bằng 0 — hoặc lệch được ghi rõ kèm người chịu trách nhiệm xử lý tiếp.
3. Hồ sơ §5 điền đủ trường bắt buộc. Nguyên nhân chưa rõ thì ghi **"chưa xác định"**, không đoán.
4. Đã hẹn lịch **Post-Incident Review** (với P1) hoặc ghi rõ lý do bỏ qua (với P2/P3).

**Ai đóng:** R4 với P1, R3 với P2/P3. **Người trực tiếp sửa không tự đóng sự cố P1** —
cùng lý do R3 không kiêm R4.

---

## 8. Post-Incident Review — bắt buộc với mọi P1

Trong **3 ngày làm việc**, R4 chủ trì, có mặt R1 · R2 · R3 (và R5 nếu chạm dữ liệu).

Bốn câu, không hơn:

1. Điều gì đã xảy ra? (mốc thời gian thật, không phải mốc lý tưởng)
2. Vì sao **phát hiện muộn** hoặc **báo muộn**, nếu có?
3. Điều gì làm khắc phục **chậm hơn cần thiết**?
4. Thay đổi **cụ thể** nào ngăn được lần sau — kèm người làm và hạn?

**Không truy trách nhiệm cá nhân.** Người báo sự cố muộn vì sợ bị mắng là cách một sự cố
20 phút trở thành một sự cố cả đêm. Điều duy nhất bị truy là **quy trình không hoạt động**.

Kết luận của mỗi PIR có thay đổi kèm hạn ⇒ **vào sổ điều phối** `GD-DieuPhoi-GiaoViec.md`
với cột *"Đứng yên từ"* (quy tắc R-9), nếu không nó sẽ là một bài học bị quên.

---

## 9. Việc còn lại để đóng F-19

| # | Việc | Ai | Chặn cái gì |
|---|---|---|---|
| 1 | Điền bảng §3 (người + số gọi được + khung trực) | Chain cung cấp | 🔴 **Chặn pilot chạy thật**, không chặn development |
| 2 | Chốt nơi lưu hồ sơ Incident (§5) | GĐ | Chặn bước 5 của kịch bản |
| 3 | **Diễn tập một lần** kịch bản §4 trước ngày pilot đầu tiên | R2 + R3 | 🔴 Quy trình chưa diễn tập là quy trình chưa biết có chạy không — cùng lý do F-16 đòi restore thật thay vì tài liệu mô tả restore |
| 4 | Mẫu phiếu giấy cho bước 3 | R2 | Chặn bước 3 |

**Việc 3 là việc dễ bỏ nhất và đắt nhất khi bỏ.** Cả đợt kiểm toán 2026-07-26 nói về đúng
một dạng lỗi: thứ được viết ra và được tin là đang hoạt động, mà chưa ai chạy thử lần nào.
