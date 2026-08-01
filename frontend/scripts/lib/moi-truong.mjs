/**
 * 🔴 **CHỖ DUY NHẤT biết địa chỉ và thông tin đăng nhập của cổng trình duyệt.** (N-4, 02/08)
 *
 * Trước tệp này, 33 script cổng mỗi cái tự khai lấy — và chúng khai KHÁC NHAU:
 *
 *   · **ba** địa chỉ mặc định cùng tồn tại: `192.168.1.10` (đa số), `192.168.1.8` (hai cổng
 *     viết sau), `localhost` (ba cổng chụp ảnh). LAN IP đổi theo ngày, nên mọi con số ghi
 *     cứng đều là ảnh chụp một ngày đã qua;
 *   · **bốn** quy ước tên biến: `BASE_URL` · `BERAS_BASE` · `EMAIL`/`PASSWORD` ·
 *     `BERAS_EMAIL`/`BERAS_PASSWORD`;
 *   · và **bốn script ghi cứng mật khẩu thật vào mã nguồn** — đã vào git.
 *
 * Vì sao đây là lỗi cổng chứ không phải lỗi tiện nghi: một cổng trỏ nhầm IP **đỏ vì hạ
 * tầng**, không phải vì sản phẩm — mà đọc log thì hai thứ đó trông y hệt nhau (§7dg đã mất
 * một lượt vì đúng chuyện này). Còn một cổng trỏ đúng IP nhưng đăng nhập bằng tài khoản
 * không tồn tại thì **đỏ ở màn login**, không bao giờ chạm tới thứ nó sinh ra để đo.
 *
 * Nguyên tắc: **không con số nào ghi cứng ở đây.** Địa chỉ suy ra từ card mạng lúc chạy;
 * thông tin đăng nhập chỉ đến từ môi trường (`scripts/ui-gates.env`, không vào git).
 */
import { networkInterfaces } from "node:os";

/**
 * LAN IP hôm nay, suy từ card mạng — thay cho con số ghi cứng của hôm qua.
 *
 * Bỏ qua cầu docker (`172.16.0.0/12`): máy này có tới ba cái (`172.17/18/19.0.1`) và chúng
 * đứng trước card thật trong danh sách của Node ở một số lần chạy. Trỏ cổng vào cầu docker
 * thì `curl` vẫn nối được — nên nó hỏng **im lặng**, đúng loại lỗi tệ nhất.
 */
function lanIpHomNay() {
  const ung = [];
  for (const dsach of Object.values(networkInterfaces())) {
    for (const n of dsach ?? []) {
      if (n.family !== "IPv4" || n.internal) continue;
      if (/^172\.(1[6-9]|2\d|3[01])\./.test(n.address)) continue;
      ung.push(n.address);
    }
  }
  // Ưu tiên dải LAN gia đình — điện thoại của Chain nằm ở đó.
  ung.sort((a, b) => Number(b.startsWith("192.168.")) - Number(a.startsWith("192.168.")));
  return ung[0];
}

function suyRaBase() {
  const ip = lanIpHomNay();
  if (!ip) {
    console.error(
      "🔴 Không tìm được LAN IP nào (chỉ thấy loopback và cầu docker).\n" +
        "   Đặt tay:  BASE_URL=http://<ip>:3000 node scripts/<cổng>.mjs",
    );
    process.exit(2);
  }
  return `http://${ip}:3000`;
}

/** Địa chỉ frontend — đúng thứ người dùng gõ (kỷ luật #15), không phải `localhost`. */
export const BASE = (process.env.BASE_URL ?? process.env.BERAS_BASE ?? suyRaBase()).replace(
  /\/+$/,
  "",
);

/** Địa chỉ API. Suy từ `BASE` bằng cách đổi cổng — cùng máy, cùng ngày, không lệch được. */
export const API = process.env.API_URL ?? `${BASE.replace(/:\d+$/, ":8000")}/api/v1`;

export const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
export const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;

/**
 * Gọi ở đầu mọi cổng có đăng nhập. Thiếu thì **dừng ngay với lời chỉ dẫn**, thay vì rơi về
 * một tài khoản mặc định không khớp CSDL nào — cái sau đỏ ở màn login và đọc như lỗi sản phẩm.
 */
export function doiDangNhap() {
  if (!EMAIL || !PASSWORD) {
    console.error(
      "🔴 Thiếu EMAIL / PASSWORD.\n" +
        "   Chạy cả bộ:  make ui-gates      (đọc scripts/ui-gates.env)\n" +
        "   Chạy một cổng:  EMAIL=… PASSWORD=… node scripts/<cổng>.mjs\n" +
        "   Chưa có tệp cấu hình:  cp scripts/ui-gates.env.example scripts/ui-gates.env",
    );
    process.exit(2);
  }
  return { EMAIL, PASSWORD };
}
