# Danh sách video cần sản xuất

> Output **04**. **KHÔNG tạo video** trong đợt này — chỉ liệt kê và chuẩn bị.
> Kịch bản đầy đủ: `05_KICH_BAN_VIDEO.md`. Storyboard + cảnh quay: `05` §Storyboard.

## Quy ước chung

| | |
|---|---|
| Độ dài | **3–5 phút** mỗi video |
| Người dẫn | **Hai người** — nữ nói chính, nam hỏi lại và tóm tắt |
| Nhịp | **Chậm**, như một buổi hướng dẫn trực tiếp tại quầy |
| Khổ quay | **Điện thoại dọc 390×844** là chính (đúng thứ dược sĩ cầm), chèn khổ laptop khi cần thấy toàn cảnh |
| Cách dạy | ① giới thiệu → ② làm nhanh một lần → ③ **làm lại thật chậm** → ④ giải thích từng nút → ⑤ lỗi thường gặp → ⑥ tóm tắt |
| CSDL quay | ✅ **`qt650`** — Chain chốt 2026-08-02. Xem mục dưới |

## Quay trên `qt650` — Chain chốt 2026-08-02

**Chain: *"Không cần đổi, cứ lấy dữ liệu qt650 làm kịch bản."*** Bản trước của mục này cấm
điều đó. Cấm sai — và sai vì **suy đoán chứ không đếm**.

Đếm thật ngày 02/08 (bằng `count(*)`, xem cảnh báo dưới):

| CSDL | Thuốc | Đơn bán | Khách | Lô | Nhà cung cấp |
|---|---|---|---|---|---|
| **`qt650`** | **70** (danh mục thật) | **1** — rác của cổng, xem dưới | **0** | **0** | **0** |
| `uat650` | 36 | 250 | 12 | 75 | có |

🔴 **`qt650` chưa có một đơn bán THẬT nào.** Đơn duy nhất là
`client_uuid = "gate-rejected-0001"` · COMPLETED · 12.000đ · 01/08 — do cổng
`check-rejected-sales` ghi vào, không phải do ai bán. Cảnh báo cũ — *"doanh thu tuần sẽ sai,
không ai tách được đâu là đơn thật"* — nói về một khoản doanh thu **không tồn tại**.

✅ **Đã dọn 2026-08-02** (Chain duyệt): đơn rác + dòng bán + thanh toán của nó đã xoá khỏi
`qt650`; xác nhận bằng ảnh màn Báo cáo — `0 đ`, đường phẳng. Cổng cũng đã vá để không ghi nữa.
Xem `PROJECT_STATE` §7dj. **`qt650` nay: 0 đơn / 0 dòng bán / 0 thanh toán.**

🔴 **Lần đếm đầu tôi báo "0 đơn" — SAI.** Tôi đọc `pg_stat_user_tables.n_live_tup`, một con số
**ước lượng** do autovacuum cập nhật, chứ không phải `count(*)`. Bảng một dòng mới chèn có thể
hiện `0`. Thứ vạch ra sai số này không phải một phép đo nào — mà là **ảnh chụp** màn Báo cáo hiện
`12.000 đ` trong lúc tôi vừa khẳng định CSDL rỗng (kỷ luật #20). **Đếm sổ sách thì dùng
`count(*)`, không dùng số liệu thống kê.**

Và `qt650` không chỉ *chấp nhận được*, nó là **sân khấu đúng**: một nhà thuốc sạch đã nạp sẵn
70 mã thuốc thật cùng 122 hoạt chất kiểm soát. Thứ tự quay đề nghị (`02→03→04→05→…`) vốn được
thiết kế để **mỗi video dựng dữ liệu cho video sau** — nó cần đúng một CSDL sạch-có-danh-mục để
bắt đầu. Dựng thêm `qt650_video` chỉ là chép lại `qt650` rồi đặt tên khác.

⚠️ **Điều còn đúng từ cảnh báo cũ:** sau buổi quay, `qt650` sẽ có hoá đơn của các cảnh quay.
Kể từ ngày quầy bắt đầu bán thật trên CSDL này, **những đơn đó thành dữ liệu lẫn**. Nên: quay
xong thì **hoặc** dọn các đơn đã quay, **hoặc** chốt ngày bắt đầu bán thật và coi mọi thứ trước
ngày đó là dữ liệu dựng. Đây là việc của Chain, không phải của phần mềm — ghi ở đây để phiên
sau không đọc *"Chain đã duyệt quay trên qt650"* thành *"không còn gì phải nghĩ"*.

---

## Danh sách

| # | Video | Thời lượng | Điều kiện dữ liệu | Ưu tiên |
|---|---|---|---|---|
| **01** | Đăng nhập · Tổng quan giao diện | 4' | CSDL sạch | 🔴 Cao |
| **02** | Thông tin cơ sở · Tài khoản · **Đổi mật khẩu** | 3' | ⚠️ **chờ màn Đổi mật khẩu** (lỗi C-01) | 🔴 Cao |
| **03** | Danh mục thuốc · Hoạt chất · Giá niêm yết | 5' | 70 mã có sẵn ✅ | 🔴 Cao |
| **04** | Sơ đồ kho · Khởi tạo tồn kho | 5' | Cần dựng kho khi quay | 🔴 Cao |
| **05** | Nhập hàng · Sắp xếp vào ô | 4' | Cần có nhà cung cấp ⚠️ (lỗi M-01) | 🟠 |
| **06** | **Bán thuốc — thường và kê đơn** | 5' | Cần tồn kho | 🔴 **Cao nhất** |
| **07** | Phân quyền — thu ngân **bị chặn** khi bán thuốc kê đơn | 3' | Cần tài khoản thứ hai | 🔴 **Cao nhất** |
| **08** | Khách hàng · Dị ứng · Cảnh báo ở quầy | 4' | Cần khách + đơn bán | 🔴 Cao |
| **09** | Hoá đơn · In khổ K80 | 3' | Cần đơn đã bán | 🟠 |
| **10** | Kiểm kê · Chênh lệch chờ duyệt | 5' | Cần tồn kho | 🟠 |
| **11** | Báo cáo · Đề xuất đặt hàng | 4' | ⚠️ cần ~30 ngày dữ liệu | 🟡 Sau |
| **12** | Dashboard chủ chuỗi | 3' | ⚠️ cần **2 chi nhánh** | 🟡 Sau |
| **13** | Nhật ký hoạt động | 3' | ⚠️ **chờ màn** (lỗi M-04) | 🟡 Sau |
| ~~**14**~~ | ~~Sổ thuốc kiểm soát đặc biệt~~ **RÚT** → `07_CHO_PHAP_LY_…` | — | Chain chốt 01/08 | — |
| **14** ⭐ | **Định hướng phát triển** — phần mềm sẽ làm thêm gì (MỚI 02/08, Chain yêu cầu) | 4' | Không cần dữ liệu; slide + cảnh đã quay | 🔴 Cao |

**Tổng: 14 video · ~57 phút** (13 hướng dẫn thao tác + 1 định hướng).

## Quay được ngay bao nhiêu

| Nhóm | Video | Ghi chú |
|---|---|---|
| ✅ **Quay được ngay** | 01 · 03 | Không cần thêm gì |
| 🟠 **Quay được sau khi dựng dữ liệu** | 04 · 05 · 06 · 07 · 08 · 09 · 10 | Dữ liệu dựng trong chính video 04–05 |
| ✅ ~~Chờ sửa lỗi~~ | ~~02 (C-01) · 13 (M-04)~~ | **5 lỗi UAT đóng hết 2026-08-01** — cả hai màn nay đã có, quay được |
| 🟡 **Chờ dữ liệu tích luỹ** | 11 (30 ngày) · 12 (2 chi nhánh) | |

## Thứ tự quay đề nghị

**Quay theo đúng thứ tự dựng dữ liệu**, để mỗi video để lại dữ liệu cho video sau:

```
01 Đăng nhập  →  03 Danh mục  →  04 Sơ đồ kho + Khởi tạo tồn  →  05 Nhập hàng
   →  06 Bán hàng  →  07 Phân quyền  →  08 Khách hàng  →  09 Hoá đơn  →  10 Kiểm kê
```

Chín video trên quay **liên tục trong một buổi**, dữ liệu chảy tự nhiên từ video này sang
video kia — không phải dựng lại giữa chừng, và người xem thấy đúng thứ tự họ sẽ làm thật.

Năm video còn lại (**02 · 11 · 12 · 13 · 14**) quay đợt sau — 02 và 13 nay đã hết chặn (màn có
rồi); 11 chờ dữ liệu tích luỹ từ chính buổi quay; 12 cần tenant hai chi nhánh; 14 là video định
hướng, quay bằng slide, **nhưng phải qua Trợ lý Pháp Lý trước khi phát hành**.
