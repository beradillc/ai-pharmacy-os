/**
 * Chụp màn hình từng tính năng của BERAS bằng một phiên đăng nhập THẬT.
 *
 * Không giả lập, không chèn token bằng tay: script gõ email/mật khẩu vào chính
 * ô đăng nhập rồi để ứng dụng tự lưu phiên — nên ảnh chụp ra đúng thứ người dùng
 * thấy, kể cả các màn phụ thuộc quyền.
 *
 * Chụp ở HAI khổ: điện thoại 390px và máy tính 1440px. Khổ điện thoại là khổ
 * chưa ai từng nhìn (mục nợ 🔴 số 1 của REMAINING_UI_ISSUES).
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const EMAIL = process.env.DEMO_EMAIL ?? "demo@bera.vn";
const PASSWORD = process.env.DEMO_PASSWORD ?? "NhaThuocDemo2026";
const OUT = process.env.OUT_DIR ?? "./democapture";

const SCREENS = [
  { slug: "01-dang-nhap", path: "/login", label: "Đăng nhập", anonymous: true },
  { slug: "02-tong-quan", path: "/bang-dieu-hanh", label: "Tổng quan" },
  { slug: "03-ban-hang", path: "/", label: "Bán hàng (POS)" },
  { slug: "04-ton-kho", path: "/ton-kho", label: "Tồn kho" },
  { slug: "05-hoa-don", path: "/hoa-don", label: "Hoá đơn" },
  { slug: "06-khach-hang", path: "/khach-hang", label: "Khách hàng" },
  { slug: "07-don-mua-hang", path: "/don-mua-hang", label: "Đơn mua hàng" },
  { slug: "08-de-xuat-dat-hang", path: "/de-xuat-dat-hang", label: "Đề xuất đặt hàng" },
  { slug: "09-bao-cao", path: "/bao-cao", label: "Báo cáo" },
];

/**
 * `fullPage` = false ở khổ điện thoại, và đây là quyết định có lý do: thanh điều
 * hướng dưới là `position: fixed`, nên trong ảnh `fullPage` nó bị chụp ở đúng vị
 * trí đáy KHUNG NHÌN — tức lơ lửng giữa trang, trông y như một lỗi bố cục. Ảnh
 * khổ điện thoại vì vậy chụp đúng thứ người dùng thấy trên tay.
 * Khổ máy tính giữ `fullPage` để xem trọn nội dung một màn.
 */
const VIEWPORTS = [
  { name: "mobile", width: 390, height: 844, fullPage: false },
  { name: "desktop", width: 1440, height: 900, fullPage: true },
];

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  // Đăng nhập xong ứng dụng tự chuyển màn — chờ rời khỏi /login thay vì chờ một
  // khoảng thời gian cố định (chờ theo giây là cách chắc chắn nhất để có ảnh
  // chụp một màn đang tải dở).
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 15000 });
}

const results = [];

for (const vp of VIEWPORTS) {
  const browser = await firefox.launch();
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 2,
    locale: "vi-VN",
    timezoneId: "Asia/Ho_Chi_Minh",
  });
  const page = await context.newPage();

  const dir = `${OUT}/${vp.name}`;
  mkdirSync(dir, { recursive: true });

  // Ảnh màn đăng nhập phải chụp TRƯỚC khi có phiên.
  const anon = SCREENS.filter((s) => s.anonymous);
  for (const s of anon) {
    await page.goto(`${BASE}${s.path}`, { waitUntil: "networkidle" });
    await page.screenshot({ path: `${dir}/${s.slug}.png`, fullPage: vp.fullPage });
    results.push({ vp: vp.name, slug: s.slug, ok: true });
  }

  await login(page);

  for (const s of SCREENS.filter((x) => !x.anonymous)) {
    try {
      await page.goto(`${BASE}${s.path}`, { waitUntil: "networkidle" });
      // Chờ dữ liệu thật thay vì chờ khung xương: khối skeleton biến mất là dấu
      // hiệu react-query đã trả dữ liệu.
      await page.waitForTimeout(1200);
      await page.screenshot({ path: `${dir}/${s.slug}.png`, fullPage: vp.fullPage });
      results.push({ vp: vp.name, slug: s.slug, ok: true });
    } catch (err) {
      results.push({ vp: vp.name, slug: s.slug, ok: false, err: String(err).slice(0, 120) });
    }
  }

  await browser.close();
}

for (const r of results) {
  console.log(`${r.ok ? "✓" : "✗"} ${r.vp.padEnd(8)} ${r.slug}${r.ok ? "" : "  " + r.err}`);
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} ảnh chụp được`);
process.exit(failed > 0 ? 1 : 0);
