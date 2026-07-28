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
