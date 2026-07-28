# Demo cho khách hàng — kịch bản 10 phút

> Ban hành 2026-07-28 (Sprint 10). Đọc cùng `scripts/demo.sh` và
> `backend/seeds/demo_pharmacy.py`.

## 0. Chuẩn bị (5 phút, làm TRƯỚC khi khách tới)

```bash
make demo                                   # dựng CSDL demo + dữ liệu nhà thuốc
DB__URL='postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os_demo' make serve
cd frontend && npm run dev                  # cửa sổ thứ hai
```

Mở `http://localhost:3000/login` · đăng nhập **demo@bera.vn** / **NhaThuocDemo2026**

**Kiểm 30 giây trước khi ngồi xuống với khách** — mở đúng 3 màn: Bảng điều hành
(có số, không phải 0), Tồn kho (có chip cam/đỏ), Hoá đơn (có đơn hôm nay). Một
buổi demo hỏng vì backend chưa chạy là buổi demo hỏng vô lý nhất.

## 1. Nhà thuốc trong bản demo

| Hạng mục | Con số |
|---|---|
| Thuốc trong danh mục | 36 (26 OTC · 10 kê đơn), có dạng bào chế, hàm lượng, giá bán |
| Lô hàng | 72, hạn dùng lệch nhau · **6 lô cận hạn ≤90 ngày** |
| Khách hàng | 10 người có tên, số điện thoại |
| Nhà cung cấp | 4 (DHG, Traphaco, Imexpharm, Zuellig) |
| Đơn mua | 3 — PO-0001 nháp, PO-0002/0003 đã gửi |
| Hoá đơn | ~279 đơn trải 28 ngày, cuối tuần đông hơn |
| Mặt hàng dưới điểm đặt lại | 5 — để màn Đề xuất đặt hàng có việc |

## 2. Kịch bản 10 phút

| Phút | Màn | Nói gì |
|---|---|---|
| 0–1 | Đăng nhập | "Mỗi nhân viên một tài khoản, thấy đúng phần việc của mình." Chỉ vào menu: vai khác thì menu khác. |
| 1–3 | **Bán hàng** | Gõ "para" → chọn Paracetamol → **giá tự điền** → thêm 2–3 món → Thanh toán. Nhấn mạnh: giá lấy từ danh mục, thu ngân không phải nhớ. |
| 3–4 | **Hoá đơn** | Đơn vừa bán nằm đầu danh sách. Mở chi tiết → in. "Ca này bán bao nhiêu" trả lời được ngay tại quầy. |
| 4–6 | **Tồn kho** | Bấm "Chỉ lô cận hạn" → các lô đỏ/cam nổi lên. **Đây thường là phút khách gật đầu**: tiền chôn ở lô sắp hết hạn là nỗi đau ai cũng có. |
| 6–8 | **Bảng điều hành** | Doanh thu 28 ngày, thuốc bán chạy, 4 ô cảnh báo. Xuất CSV cho kế toán. |
| 8–9 | **Đề xuất đặt hàng** | Bấm "Tính lại" → **5 đề xuất** (5 mặt hàng dưới điểm đặt lại, mỗi mặt hàng đã có NCC gần nhất) → bấm tạo đơn ở dòng đầu → **PO-0004**. Đã chạy thật 28/07: `RUN=200 · suggested=5 · tạo đơn được 5/5 · MATERIALIZE=200 → po_code "PO-0004"`. |
| 9–10 | **Đơn mua hàng** | Đơn vừa tạo nằm đầu. "Mã này đọc cho nhà cung cấp qua điện thoại." |

**Câu chốt:** một vòng khép kín — bán → trừ kho → cảnh báo → đề xuất đặt →
đơn mua — không phải năm phần mềm rời nhau.

## 3. 🔴 Bốn câu KHÔNG được nói trong buổi demo

Dữ liệu demo có bốn chỗ không phản ánh đúng đời thật (ghi đầy đủ ở docstring
`seeds/demo_pharmacy.py`). Nói sai một câu ở đây là hứa một thứ chưa có:

1. **Đừng nói "đây là dữ liệu thật của một nhà thuốc đang chạy."** Đơn bán được
   lùi ngày bằng lệnh; bút toán kho mang ngày hôm nay. Nói đúng: *"dữ liệu mẫu,
   dựng theo hình dạng một nhà thuốc thật."*
2. **Đừng bán tính năng bán thuốc kê đơn qua màn này.** Dữ liệu demo chỉ bán
   OTC vì không tạo đơn thuốc nào. Luồng kê đơn có thật trong hệ thống (Sprint
   5) nhưng **không nằm trong kịch bản 10 phút**.
3. **Đừng nói "kho tự động trừ theo từng đơn trong quá khứ".** Năm mặt hàng bán
   chạy được hạ tồn bằng một lệnh xuất kho đánh dấu `demo_setup` để màn Đề xuất
   có việc — không có bước đó thì phút thứ 8 là một danh sách rỗng.
4. **Đừng hứa tìm kiếm khách hàng theo tên trên toàn bộ dữ liệu.** Ô lọc ở màn
   Khách hàng lọc **trong trang đang xem** — họ tên và số điện thoại là cột mã
   hoá at-rest nên `LIKE` không chạy; tìm thật cần blind index, chưa làm.

## 4. Câu hỏi khách hay hỏi

| Khách hỏi | Trả lời đúng |
|---|---|
| "Mất mạng có bán được không?" | Được. Màn bán hàng lưu đơn tại máy và tự đồng bộ khi có mạng lại; thanh trên cùng đếm số đơn đang chờ. |
| "Dữ liệu khách hàng có an toàn không?" | Họ tên, điện thoại, giới tính, CCCD **mã hoá trong CSDL**. Có nhật ký ai đọc dữ liệu nhạy cảm, có xuất/ẩn danh theo Luật 91/2025. |
| "Nhiều chi nhánh được không?" | Được — mỗi phiên gắn một chi nhánh, đổi chi nhánh không cần đăng xuất; báo cáo xem được cả chuỗi. |
| "Báo cáo cho Sở Y tế?" | Có module tuân thủ riêng: sổ thuốc kiểm soát đặc biệt, biên bản nhận lại thuốc, báo cáo định kỳ Mẫu số 06 (NĐ 163/2025). Không nằm trong 10 phút này. |
| "Bao giờ dùng được thật?" | **Chưa chốt.** Câu này thuộc về Chain, không thuộc về người demo. |

## 5. Sau buổi demo

- Dựng lại bản sạch cho lần sau: xoá CSDL demo rồi `make demo`
  (lệnh DROP in ra ở cuối `scripts/demo.sh` — **người** chạy, không tự động).
- Ghi lại vào `PROJECT_STATE.md`: khách hỏi gì mà hệ thống chưa trả lời được.
  Đó là danh sách tính năng có giá trị nhất, và nó chỉ tồn tại nếu được ghi ngay.
