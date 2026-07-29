/**
 * Định dạng số cho màn hình tiếng Việt.
 *
 * Nhận `string` chứ không phải `number`: backend trả `Decimal` dạng chuỗi, và
 * ép sang `number` sớm là tự chuốc sai số dấu phẩy động lên đúng những con số
 * người ta mang đi đối chiếu với sổ. Chỉ đổi sang `number` ở ranh giới hiển
 * thị, nơi sai số làm tròn cuối cùng không đi đâu tiếp được nữa.
 */

const VI = "vi-VN";

export function formatMoney(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return n.toLocaleString(VI, { maximumFractionDigits: 0 });
}

export function formatQty(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  // Bỏ số 0 thừa sau dấu phẩy: "16.000" → "16", nhưng "16.500" → "16,5".
  return n.toLocaleString(VI, { maximumFractionDigits: 3 });
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(VI, { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
}

/**
 * "Hết trong ~N ngày" — DẪN XUẤT ở giao diện, không phải trường API (docs/19
 * §5). Đây là thứ dược sĩ thực sự nghĩ, khác với "điểm đặt lại" vốn là khái
 * niệm của hệ thống. `null` khi chưa đủ dữ liệu bán để chia.
 */
export function daysOfStockLeft(onHand: string, velocityPerDay: string): number | null {
  const stock = Number(onHand);
  const velocity = Number(velocityPerDay);
  if (!Number.isFinite(stock) || !Number.isFinite(velocity) || velocity <= 0) return null;
  return Math.floor(stock / velocity);
}

/**
 * Ngày cho người Việt đọc: `dd/mm/yyyy`.
 *
 * 🔴 Sinh từ ảnh chụp màn hình 29/07: màn Tồn kho hiện thẳng `2027-09-05` lấy
 * nguyên từ API. ISO là định dạng để MÁY trao đổi; một dược sĩ đọc hạn dùng trên
 * hộp thuốc thấy `05/09/2027`. Không ai đọc sai được `2027-09-05`, nhưng nó đọc
 * chậm hơn và trông như dữ liệu chưa qua xử lý — đúng thứ phân biệt phần mềm
 * hoàn thiện với bản dựng thử.
 */
export function formatDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

/**
 * Ký hiệu tiền dùng CHUNG một chỗ.
 *
 * 🔴 Cũng sinh từ ảnh chụp: bảng điều hành dùng `₫` (U+20AB) còn màn bán hàng
 * dùng `đ`. `₫` **không nằm trong bộ ký tự Be Vietnam Pro đã nhúng**, nên nó rơi
 * về font dự phòng — hiện ra với nét khác hẳn phần số ngay bên cạnh, và lệch cả
 * khoảng cách. Trên ảnh chụp nhìn như một lỗi phông chữ, vì đúng là vậy.
 *
 * Chọn `đ`: là chữ cái tiếng Việt, chắc chắn có trong bộ đã nhúng, và là thứ
 * người Việt viết tay hằng ngày. Ai cần `₫` cho hoá đơn in thì đổi ở đây, một chỗ.
 */
export const CURRENCY = "đ";

/** Tiền + ký hiệu, dùng thay cho việc mỗi màn tự nối chuỗi một kiểu. */
export function money(value: string | number): string {
  return `${formatMoney(String(value))} ${CURRENCY}`;
}
