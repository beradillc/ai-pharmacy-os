# Architecture Decision Records

Một ADR = **một quyết định kiến trúc**, ghi lúc quyết, **không sửa lại**. Quyết định sau
thay quyết định trước thì viết ADR mới và trỏ ngược, không viết đè.

## 🔴 Đọc trước khi tạo ADR mới: dự án ĐÃ CÓ chỗ cho hầu hết loại quyết định

Chính sách 31/07 yêu cầu một số thư mục ghi nhớ. Phần lớn **đã tồn tại dưới tên khác** —
và quy tắc "không ghi trùng" của chính chính sách đó đòi dùng lại thay vì dựng song song.
Bảng ánh xạ:

| Chính sách yêu cầu | Dự án đã có | Ghi ở đâu |
|---|---|---|
| Quyết định kiến trúc (ADR) | thư mục này | `docs/adr/ADR-xxxx.md` |
| Quyết định **nghiệp vụ/pháp lý** của một tính năng | ✅ đã có | `docs/features/<tính-năng>/01_DECISIONS.md` |
| Kinh nghiệm triển khai theo ngày | ✅ đã có | `PROJECT_STATE.md` (chỉ-ghi-thêm, §7xx) |
| Quy tắc mới cho Claude | ✅ đã có | `CLAUDE.md` — kỷ luật #1…#16 |
| Lỗi đã sửa | mới | `CHANGELOG.md` |
| Cải tiến giao diện + ảnh trước/sau | mới | `docs/ui-history/` |
| Vấn đề UI còn treo | ✅ đã có | `docs/ui/REMAINING_UI_ISSUES.md` |
| Cổng bắt buộc cho tính năng mới | ✅ đã có | `docs/14_FEATURE_PROCESS.md` |

**Đừng tạo `optimization-cycle/`.** `PROJECT_STATE.md` đã là đúng thứ đó và đã dài 3.600+
dòng lịch sử; dựng thêm một dòng thời gian thứ hai là chia đôi trí nhớ dự án — đúng thứ
kiểm toán 26/07 đã chỉ ra là nguyên nhân bài học không được kế thừa (kỷ luật #13).

## Khi nào viết ADR, khi nào không

Viết ADR khi quyết định **đổi hình dạng của hệ thống** và đắt để đảo ngược: một điểm nối
giữa hai module, một hợp đồng API đổi ngữ nghĩa, một chỗ dữ liệu đổi nguồn sự thật.

Không viết ADR cho: sửa lỗi, đổi giao diện, thêm một endpoint theo khuôn đã có. Những thứ
đó vào `CHANGELOG.md`.
