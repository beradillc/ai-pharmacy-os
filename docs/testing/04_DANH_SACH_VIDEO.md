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
| CSDL quay | ⚠️ **Không quay trên `qt650` thật.** Xem cảnh báo dưới |

## 🔴 Cảnh báo trước khi bấm máy

**Quay trên CSDL thật của quầy sẽ để lại dữ liệu rác trong sổ sách thật** — mỗi lần quay lại
cảnh bán hàng là thêm một hoá đơn không có khách. Sau một buổi quay, doanh thu tuần sẽ sai và
**không ai tách được đâu là đơn thật**.

**Phải dựng một CSDL riêng để quay** (ví dụ `qt650_video`, sao từ mốc sạch). Việc này cũng
giải quyết luôn vướng mắc UAT ở `01_BAO_CAO_UAT.md` §4.

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
| **14** | Sổ thuốc kiểm soát đặc biệt | 4' | ⚠️ **chờ màn** (lỗi C-03) | 🟠 Sau |

**Tổng: 14 video · ~55 phút.**

## Quay được ngay bao nhiêu

| Nhóm | Video | Ghi chú |
|---|---|---|
| ✅ **Quay được ngay** | 01 · 03 | Không cần thêm gì |
| 🟠 **Quay được sau khi dựng dữ liệu** | 04 · 05 · 06 · 07 · 08 · 09 · 10 | Dữ liệu dựng trong chính video 04–05 |
| 🔴 **Chờ sửa lỗi** | 02 (C-01) · 13 (M-04) · 14 (C-03) | Không quay được vì màn chưa có |
| 🟡 **Chờ dữ liệu tích luỹ** | 11 (30 ngày) · 12 (2 chi nhánh) | |

## Thứ tự quay đề nghị

**Quay theo đúng thứ tự dựng dữ liệu**, để mỗi video để lại dữ liệu cho video sau:

```
01 Đăng nhập  →  03 Danh mục  →  04 Sơ đồ kho + Khởi tạo tồn  →  05 Nhập hàng
   →  06 Bán hàng  →  07 Phân quyền  →  08 Khách hàng  →  09 Hoá đơn  →  10 Kiểm kê
```

Chín video trên quay **liên tục trong một buổi**, dữ liệu chảy tự nhiên từ video này sang
video kia — không phải dựng lại giữa chừng, và người xem thấy đúng thứ tự họ sẽ làm thật.

Năm video còn lại (02 · 11 · 12 · 13 · 14) quay đợt sau.
