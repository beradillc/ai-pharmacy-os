# BERAS — Frontend (S4.6 FE POS tối thiểu, 5/5 bước)

Next.js + TypeScript + TanStack Query, gọi thẳng backend `pharmacy_os` (xem `../README.md`
mục 7 để chạy backend trước). Cấu trúc thư mục theo `../docs/04_FOLDER_STRUCTURE.md` §3;
nhận diện thương hiệu theo `../docs/16_BRAND_UI_GUIDE.md`.

## Chạy dev

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL trỏ vào backend đang chạy
npm install
npm run dev
```

→ `http://localhost:3000/login`. Backend phải đã có ít nhất 1 tài khoản — dùng
`python -m seeds.bootstrap_tenant` (xem README gốc mục 7). Không dùng dev-header —
đăng nhập thật qua `POST /auth/login`.

## Phạm vi hiện tại (S4.6, 5/5 bước)

| Đã có | Chưa có |
|-------|---------|
| Đăng nhập JWT thật, chọn chi nhánh khi có nhiều | Giá bán tự động — `catalog`/`inventory` chưa có nguồn giá bán, thu ngân nhập tay (chốt sếp 2026-07-23: không xây module `pricing`) |
| Tra thuốc (lọc phía client — `GET /drugs` không có tham số tìm kiếm) | Luồng đơn thuốc (ETC) — thấy nhãn cảnh báo, chưa có màn nhập đơn |
| Giỏ hàng, thanh toán `POST /sales` | Bộ test tự động (vitest/playwright) |
| **Hàng đợi offline (Dexie)** — mất mạng lúc thanh toán thì lưu vào IndexedDB, tự đồng bộ qua `POST /sync/sales` khi có mạng lại hoặc khi mở lại app | |

### Hàng đợi offline — cách hoạt động

`src/shared/offline/`: `db.ts` (bảng Dexie `pendingSales`, khóa bằng chính `client_uuid`) +
`sync-queue.ts` (`enqueueSale`/`flushQueue`) + `use-offline-sync.ts` (hook tự flush khi mount và
khi có sự kiện `online`, gắn ở `(pos)/layout.tsx` nên chạy trên mọi màn POS).

`useCheckout` phân biệt 2 loại lỗi: **`ApiError`** (server đã trả lời — 4xx/5xx, một lời từ chối
thật, ví dụ thiếu tồn kho) thì ném lại nguyên trạng, hiện lỗi cho thu ngân; **lỗi khác** (bản thân
`fetch` không kết nối được — mất mạng) thì lưu đơn vào hàng đợi thay vì báo lỗi. `flushQueue` phát
lại theo đúng thứ tự đã lưu, dừng ở đơn đầu tiên vẫn không kết nối được (giữ nguyên hàng đợi cho
lần sau); một đơn bị server từ chối thật sự thì bị bỏ khỏi hàng đợi ngay (không giữ lại retry vô
hạn, vì sẽ chặn mọi đơn xếp sau nó).

**Giới hạn đã biết:** phân biệt "mất mạng" vs "lỗi JS khác" chỉ dựa vào việc lỗi có phải `ApiError`
hay không (tức server có trả lời hay không) — đơn giản, đúng cho MVP, nhưng không phân biệt được
"mất mạng thật" với các lỗi runtime hiếm khác không phải business rejection. Chưa diễn tập thật với
DevTools "Offline" hay tắt Wi-Fi thật (môi trường này không có trình duyệt — xem mục kiểm chứng
bên dưới).

Xem `src/shared/api/types.ts` để biết chỗ tài liệu `../docs/11_API_DESIGN.md` bị lệch so
với API thật (đặc biệt module `sales`) — types ở đây theo code, không theo doc cũ.

## Kiểm tra trước khi commit

```bash
npx tsc --noEmit
npm run lint
npm run build
```

Chưa có bộ test tự động (vitest/playwright) — ghi nợ.

**Kiểm chứng đã làm cho hàng đợi offline:** `tsc`/`eslint`/`next build` sạch; `next dev` thật chạy,
2 route trả 200, không lỗi runtime trong log server. **Chưa click-through UI thật** (môi trường
không có trình duyệt) — chưa tự tay ngắt mạng, gõ đơn, bật mạng lại xem đơn có tự đồng bộ không.
Sếp cần tự làm việc này trên `http://localhost:3000` trước khi coi Bước 5 là dùng được thật.
