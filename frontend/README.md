# BERAS — Frontend (S4.6 FE POS tối thiểu)

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

## Phạm vi hiện tại (S4.6, Bước 1-4/5)

| Đã có | Chưa có |
|-------|---------|
| Đăng nhập JWT thật, chọn chi nhánh khi có nhiều | Hàng đợi Dexie khi mất mạng (Bước 5, đợt sau) |
| Tra thuốc (lọc phía client — `GET /drugs` không có tham số tìm kiếm) | Giá bán tự động — `catalog`/`inventory` chưa có nguồn giá bán, thu ngân nhập tay |
| Giỏ hàng, thanh toán `POST /sales` | Luồng đơn thuốc (ETC) — thấy nhãn cảnh báo, chưa có màn nhập đơn |

Xem `src/shared/api/types.ts` để biết chỗ tài liệu `../docs/11_API_DESIGN.md` bị lệch so
với API thật (đặc biệt module `sales`) — types ở đây theo code, không theo doc cũ.

## Kiểm tra trước khi commit

```bash
npx tsc --noEmit
npm run lint
npm run build
```

Chưa có bộ test tự động (vitest/playwright) — ghi nợ, chưa nằm trong phạm vi S4.6.
