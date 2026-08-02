# Quay video = một lượt RÀ SOÁT app — quy trình (Chain chốt 2026-08-02)

> Chain: *"Các video cũng là review app, làm từng video để phát hiện lỗi và sửa cho dứt điểm
> các tính năng, giao diện, âm thanh khớp video, trong video đó. Các tính năng liên thông giữa
> các video thì ghi nhận lại, sửa cùng lúc."*

## Vì sao chỉ đạo này đúng — bằng chứng có sẵn

Lượt quay đầu (video tổng quan, 02/08) phải chạy **5 lần** mới trọn 16/16 đoạn. Bốn lần chết
đầu **không lần nào là lỗi ngẫu nhiên**, và trên đường đi nó tìm ra **hai lỗi sản phẩm thật**:

| Lỗi | Ai bắt được | 21 cổng trình duyệt |
|---|---|---|
| Cửa sổ đã đóng vẫn được vẽ, **chặn ô "Tìm thuốc"** màn bán hàng, cả 2 khổ | bản quay chết | **mù hết** |
| Thông báo nhận hàng nói ngược: *"chốt phiếu"* ngay trên *"Nhận một phần"* | ảnh khung hình | **mù hết** |

Lý do bộ cổng mù: nó giỏi kiểm **cấu trúc** (phần tử có không · nằm đâu · chạm được không) và
**mù về ý nghĩa** — nó không đọc được rằng hai câu tiếng Việt cạnh nhau đang nói ngược nhau,
cũng không biết một thao tác đòi hai bước mà kịch bản chỉ làm một.

**Quay video là phép kiểm duy nhất đi trọn một luồng nghiệp vụ bằng đúng thao tác người dùng,
theo đúng thứ tự, và có người nhìn từng khung hình.** Không cổng nào thay được.

## Vòng lặp cho MỖI video

```
⓪⁻ CHỤP MÀN TRƯỚC → mở đúng màn sắp quay, chụp một ảnh, NHÌN. Rồi mới viết script.
⓪ DỌN TRƯỚC      → node scripts/lib/don-truoc-khi-quay.mjs   (video có GHI dữ liệu)
① dựng dữ liệu    → node scripts/lib/dung-du-lieu-quay.mjs (hoặc bước riêng của video)
② quay            → node scripts/record-vNN.mjs
③ đọc log         → mọi lần chết là MỘT phát hiện, không phải một phiền toái
④ xem ẢNH khung   → trích 4–6 khung, phóng to, đọc từng chữ trên màn
⑤ phân loại       → (a) lỗi TRONG video này  (b) lỗi LIÊN THÔNG  (c) không phải lỗi
⑥ sửa (a) dứt điểm→ kèm cổng nếu là lớp lỗi lặp lại (kỷ luật #24)
⑦ ghi (b) vào sổ  → `11_SO_LOI_LIEN_THONG.md`, KHÔNG sửa lẻ
⑧ ghi (c) lại     → "không phải lỗi" cũng phải ghi, để phiên sau khỏi báo lại
⑨ quay lại        → cho tới khi trọn, log sạch, ảnh sạch
⑩ đóng video      → ghi vào bảng dưới
```

### ⓪⁻ Chụp màn TRƯỚC khi viết script — Chain duyệt 2026-08-02

**Mở màn sắp quay, chụp một ảnh, nhìn nó. Rồi mới viết `record-vNN.mjs`.** Mất 30 giây.

🔴 *Vì sao thành quy tắc:* **ba video liên tiếp** vấp cùng một chuyện — tôi **đoán bố cục màn
thay vì mở ra xem**:

| Video | Đoán gì | Sự thật | Giá phải trả |
|---|---|---|---|
| 04 | `mouse.wheel` cuộn được | `isMobile: true` ⇒ WebKit chặn hẳn | một lượt quay |
| 05 | màn nhập hàng có ô tìm như màn bán hàng | nó dùng **danh sách thả xuống** | một lượt quay |
| 05 | nút `Thêm` là nút của màn | trùng tên nút **thanh điều hướng** dưới | một lượt quay |

Cả ba lần thứ chỉ ra sự thật đều là **ảnh**, không phải log — log chỉ nói *"waiting for
element"*, câu đó đúng với mọi nguyên nhân. Kỷ luật #18: một vấn đề lặp từ ba lần thì nâng
thành quy tắc.

Hệ quả kèm theo, rút từ chính ba ca trên:
- **Tìm nút trong `main`**, đừng quét toàn trang — thanh điều hướng luôn nằm trong tầm quét
  và nó có những nút trùng tên với nút của màn (`Thêm`).
- **`count()` đếm cả nút đang KHOÁ.** Muốn bấm thì kiểm `isEnabled()`, không thì cú bấm chờ
  tới hết giờ và log đọc y như nút không tồn tại.

### ⑤ Phân loại — ranh giới

| Loại | Định nghĩa | Xử |
|---|---|---|
| **(a) trong video** | Chỉ chạm màn/luồng mà video này quay | **Sửa ngay, dứt điểm** |
| **(b) liên thông** | Chạm ≥2 màn, hoặc sửa nó làm đổi video khác | **Ghi sổ, sửa gộp một đợt** |
| **(c) không phải lỗi** | Đã đo và đúng; hoặc là quyết định có chủ đích | **Ghi lại kèm lý do** |

🔴 **Ranh giới (a)/(b) là ranh giới quan trọng nhất của quy trình này.** Sửa một lỗi liên
thông ngay giữa lúc quay video 04 sẽ làm hỏng bản quay video 02 đã đóng — và không ai biết
cho tới lúc phát hành. Nghi ngờ ⇒ xếp vào (b).

🔴 **(c) phải ghi, không được bỏ qua.** Ngày 02/08 tôi suýt vá `Thối lại: −6.000 đ` — hoá ra
là quyết định có chủ đích, có chú thích ngay trong mã. Không ghi lại thì phiên sau lại suýt vá.

## "Âm thanh khớp video" nghĩa là gì ở đây

Máy **không** đọc được tiếng Việt ở mức giao khách — phần giọng do người thu. Nhưng phần
*khớp* thì kiểm được, và phải kiểm trong chính video đó:

- `hold()` in `⚠ tràn Xs` khi **thao tác dài hơn lời thoại** ⇒ **viết lại lời cho dài ra**,
  KHÔNG cắt thao tác. Thao tác là thứ người xem cần nhìn.
- Đoạn nào lời hết mà màn còn đứng im ⇒ lời quá ngắn, thêm câu.
- Mỗi video có một tệp lời thoại riêng `09_LOI_THOAI_vNN.md`, khớp sẵn mốc từ `timeline.json`.

## Thứ tự làm — theo dòng chảy dữ liệu, không theo số

```
02 → 03 → 04 → 05 → 01 → 08 → 06 → 07 → 09 → 10 → 13 → 11 → 12 → 14
```

Mỗi video dùng dữ liệu video trước vừa tạo ⇒ không phải dựng dữ liệu giả lần nào, và **thứ tự
này cũng là thứ tự một quầy thật đi khi mới nhận phần mềm**.

## Giọng chuẩn

Khai ở **`scripts/giong-he-thong.json`** — một chỗ duy nhất, đúng bài học N-4. Chain chốt
2026-08-02: **VieNeu-TTS v3 Turbo · giọng "Thùy Dung"** (`Nữ · miền Nam · phong cách tin tức`,
48 kHz). Piper `vivos` spk62 giữ làm dự phòng.

Dựng tiếng cho một video:

```
~/.local/share/beras-tts/venv-vieneu/bin/python scripts/doc_vieneu.py \
    docs/testing/09_LOI_THOAI_vNN.md /tmp/tieng-vNN
```

## Bảng theo dõi

| # | Video | Quay trọn | Lỗi (a) đã sửa | Lỗi (b) ghi sổ | Lời thoại | Đóng |
|---|---|---|---|---|---|---|
| 01 | Một vòng làm việc trong ngày | ✅ 16/16 | 2 | 1 | ✅ Thùy Dung | ✅ **XONG** |
| 02 | Thông tin cơ sở · Tài khoản · Đổi mật khẩu | ✅ 9/9 | **1** (lỗi 422 tiếng Anh) | **1** (L-2) | 🟠 giọng CŨ, cần dựng lại | 🟠 chờ Chain cấp số thật |
| 03 | Danh mục thuốc · Hoạt chất · Giá | ✅ 9/9 | 0 | 0 | ✅ Thùy Dung | ✅ **XONG** |
| 04 | Sơ đồ kho · Khởi tạo tồn | ✅ 8/8 | **2** (mouse.wheel · kho rác) | 0 | ✅ BERAS | ✅ **XONG** |
| 05 | Nhập hàng · Xếp ô | ✅ 7/7 | **3** (nút thanh điều hướng · chọn thuốc bằng dropdown · nút khoá) | 0 | ✅ BERAS | ✅ **XONG** |
| ~~01~~ | ~~Đăng nhập · Tổng quan~~ — gộp vào video 01 ở trên | — | — | — | — | — |
| 08 | Khách hàng · Dị ứng | | | | | |
| 06 | Bán thuốc | ✅ 7/7 **lượt đầu** | 0 | 0 | ✅ BERAS | ✅ **XONG** |
| 07 | Phân quyền thu ngân | ✅ 7/7 | **2** (thiếu bước đăng xuất · **màn không báo trước**) | 0 | ✅ BERAS | ✅ **XONG** |
| 09 | Hoá đơn · Trả hàng | | | | | |
| 10 | Kiểm kê | | | | | |
| 13 | Nhật ký hoạt động | | | | | |
| 11 | Báo cáo | | | | | |
| 12 | Dashboard chuỗi | | | | | |
| 14 | Định hướng phát triển | | | | | 🔴 chờ Pháp Lý |
