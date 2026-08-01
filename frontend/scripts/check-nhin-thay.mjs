/**
 * Cổng **kỷ luật #21** — nhìn thấy được, không chỉ có trên trang. Nhóm ĐỌC-THUẦN.
 *
 * Chạy MỌI màn ở khổ điện thoại 390×844 và hỏi hai câu:
 *   ① trang có phải cuộn ngang không (áp cho mọi màn, không cần khai báo)
 *   ② những thứ đã khai là *phải nhìn thấy mới làm việc được* có nằm trong khung nhìn không
 *
 * Câu ② cần một **danh sách khai báo** chứ không tự đoán được: máy không biết cột nào là lý
 * do một màn tồn tại. `PHAI_THAY` dưới đây là danh sách đó — thêm màn mới thì thêm một dòng,
 * đừng viết cổng thứ hai.
 *
 * 🔴 Cổng này ĐỌC THUẦN: chỉ mở màn và đo. Không tạo, không sửa, không bán. Vì vậy nó chạy
 * được lên cả CSDL demo của Chain.
 */
import { firefox } from "playwright-core";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

/** Mọi màn của khu quản lý + màn quầy. Câu ① áp cho tất cả. */
const MAN = [
  "/",
  "/bang-dieu-hanh",
  "/hoa-don",
  "/khach-hang",
  "/ton-kho",
  "/danh-muc-thuoc",
  "/nhap-nhanh",
  "/khoi-tao-ton",
  "/kiem-ke",
  "/so-do-kho",
  "/don-mua-hang",
  "/de-xuat-dat-hang",
  "/bao-cao",
  "/nhan-vien",
  "/cai-dat",
];

/**
 * Thứ người dùng **phải nhìn thấy mới làm việc được**, khai theo màn.
 *
 * Mỗi dòng: `{ man, ten, loc, chuanBi? }`. `ten` phải nói rõ *vì sao* nó bắt buộc — người
 * đọc log sáu tháng sau không nhớ màn kiểm kê để làm gì. `chuanBi` là các thao tác đưa màn
 * về đúng trạng thái cần đo, và **chỉ được phép là thao tác không ghi gì lên máy chủ**.
 *
 * 🔴 Lần chạy đầu (01/08) cổng báo *"KHÔNG TÌM THẤY"* cho hai dòng, và cả hai đều là **lỗi
 * phép đo, không phải lỗi bố cục** — kỷ luật #15 nói dừng lại đọc kỹ chứ đừng vá sản phẩm:
 *   · nút Thanh toán: trên mobile `.cart { display: none }` cho tới khi bấm mở giỏ (bản vá
 *     31/07 — giỏ thu thành thanh đáy). `getByRole` bỏ qua phần tử `display:none`, nên
 *     `count()` bằng 0 chứ không phải "bị ẩn". Phải thêm hàng vào giỏ và mở giỏ rồi mới đo.
 *   · cột "Chênh": bảng đếm chỉ tồn tại khi CÓ một phiên kiểm kê đang mở. Đo nó ở cổng
 *     đọc-thuần là đo một cái không có ⇒ **đã chuyển sang `check-kiem-ke.mjs`** (nhóm ghi,
 *     nơi phiên được tạo thật). Để lại đây thì cổng sẽ đỏ mãi vì lý do sai — hoặc tệ hơn,
 *     ai đó "sửa" bằng cách nới điều kiện và mất luôn phép đo.
 */
const PHAI_THAY = [
  {
    man: "/",
    ten: "ô tìm thuốc",
    loc: (p) => p.locator('input[placeholder*="Tìm thuốc"]'),
  },
  {
    man: "/",
    ten: "nút Thanh toán (sau khi mở giỏ)",
    chuanBi: async (p) => {
      // Thêm hàng + mở giỏ: cả hai đều là trạng thái phía máy khách, KHÔNG gọi ghi.
      await p.locator("li button", { hasText: /^Thêm$/ }).first().click();
      await p.waitForTimeout(800);
      const moGio = p.getByRole("button", { name: /^Xem giỏ$/ });
      if (await moGio.count()) await moGio.click();
      await p.waitForTimeout(800);
    },
    loc: (p) => p.getByRole("button", { name: /^(Thanh toán|Ghi lý do để bán)$/ }),
  },
];

const browser = await firefox.launch();
const ctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});
const page = await ctx.newPage();

await page.goto(`${BASE}/login`, { waitUntil: "load" });
await page.waitForTimeout(1500);
await page.fill('input[type="email"]', EMAIL);
await page.fill('input[type="password"]', PASSWORD);
await page.click('button[type="submit"]');
await page.waitForTimeout(4000);

let hong = 0;

console.log("① Trang KHÔNG được cuộn ngang ở khổ 390px");
for (const duongDan of MAN) {
  await page.goto(`${BASE}${duongDan}`, { waitUntil: "load" });
  await page.waitForTimeout(2000);
  const kq = await cuonNgangTrang(page);
  inDong(duongDan, kq);
  if (!kq.dat) hong += 1;
}

console.log("\n② Thứ PHẢI nhìn thấy mới làm việc được");
for (const { man, ten, loc, chuanBi } of PHAI_THAY) {
  await page.goto(`${BASE}${man}`, { waitUntil: "load" });
  await page.waitForTimeout(2500);
  if (chuanBi) await chuanBi(page);
  const kq = await trongKhungNhin(page, loc(page));
  inDong(`${man} — ${ten}`, kq);
  if (!kq.dat) hong += 1;
}

await browser.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} phép đo KHÔNG đạt — có thứ trên trang mà không nhìn thấy được.`);
  process.exit(1);
}
console.log("\n✅ Mọi màn vừa bề ngang 390px, mọi thứ bắt buộc đều trong khung nhìn.");
