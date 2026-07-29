/**
 * Sinh UUID v4 chạy được **ngoài ngữ cảnh bảo mật**.
 *
 * 🔴 Vì sao không dùng thẳng `crypto.randomUUID()` — đo thật 2026-07-29:
 *
 * | Địa chỉ | `isSecureContext` | `crypto.randomUUID` | `crypto.getRandomValues` |
 * |---|---|---|---|
 * | `http://localhost:3000` | `true` | `function` | `function` |
 * | `http://192.168.1.10:3000` | **`false`** | **`undefined`** | `function` |
 *
 * Giống nhau ở cả Firefox lẫn WebKit. `randomUUID` là API **chỉ có ở ngữ cảnh
 * bảo mật** (HTTPS hoặc `localhost`); máy dev gõ `localhost` nên luôn có, còn
 * điện thoại gõ địa chỉ LAN thì **không bao giờ có**.
 *
 * Hậu quả trước bản vá: bấm **Thanh toán** trên điện thoại ném `TypeError`
 * **trước khi** gửi request — không một lời gọi `POST /sales` nào rời máy — và
 * màn hình chỉ hiện *"Thanh toán thất bại"*. Tức là **POS không bán được gì
 * trên bất kỳ điện thoại nào**, còn thu ngân thì không có manh mối nào để báo.
 * Không cổng nào thấy: `vitest` chạy trong Node (có `randomUUID`), 4 cổng khác
 * không mở trình duyệt, và mọi ảnh chụp trước nay đều đi qua `localhost`.
 *
 * `getRandomValues` **có** ở ngữ cảnh không bảo mật (khác `subtle`/`randomUUID`),
 * nên vẫn là số ngẫu nhiên chất lượng mật mã — không hạ tiêu chuẩn để đổi lấy
 * tương thích. Chỗ này quan trọng vì `client_uuid` là **khoá chống trùng đơn**:
 * hai đơn trùng khoá là một lần bán bị nuốt mất.
 */
export function randomUuid(): string {
  const c = globalThis.crypto;
  if (typeof c?.randomUUID === "function") return c.randomUUID();

  const b = new Uint8Array(16);
  c.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40; // phiên bản 4
  b[8] = (b[8] & 0x3f) | 0x80; // biến thể RFC 4122
  const hex = Array.from(b, (n) => n.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
