# Trợ giúp lấy hàng — bức tranh chung

> Gom ba mảnh đã có thành một câu chuyện. Không mảnh nào ở đây là mới.

## Ba mảnh, ba câu hỏi

| Mảnh | Trả lời | Ở đâu |
|---|---|---|
| `ViTriLay` trên dòng giỏ hàng | *"Mã này lấy ở đâu?"* | quầy, tự hiện, không phải bấm |
| `GET /inventory/where` | *"Mã này còn ở những ô nào?"* | Phase 2 |
| `POST /inventory/pick-route` | *"Cả giỏ thì đi một vòng thế nào?"* | Phase 4 — [PICK_LIST.md](PICK_LIST.md) |

Thứ tự trên cũng là thứ tự **mức độ can thiệp**: cái đầu không đòi thao tác nào, cái cuối
đòi một cú bấm. Nút lộ trình vì thế chỉ hiện khi giỏ **từ hai mã** — dưới ngưỡng đó dòng
`📍` đã đủ, và một nút thừa là một nút người ta học cách bỏ qua.

## Quy tắc chung cho cả ba

**FEFO thắng, đường đi chỉ quyết khi hạn dùng bằng nhau** (GĐ chốt 2026-07-31, Chain uỷ
quyền). An toàn thuốc không đánh đổi lấy vài bước chân — Điều 6.5 Luật Dược cấm bán thuốc
quá hạn.

Sắp thứ tự nằm ở **máy chủ**, không ở màn hình. Mỗi màn tự sắp là mỗi màn có cơ hội sắp sai
một kiểu khác nhau.

## Còn nợ

- Tách `thieu` thành *chưa xếp ô* và *không đủ trong ô* — hiện gộp một.
- In tờ lộ trình ra giấy (hiện chỉ xem trên màn).
