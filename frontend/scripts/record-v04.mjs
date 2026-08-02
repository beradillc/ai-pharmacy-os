/**
 * VIDEO 04 — Sơ đồ kho · Khởi tạo tồn. Khổ điện thoại, chủ đề Warm.
 *
 * 🔴 **VIDEO ĐẦU TIÊN CỦA BỘ CÓ GHI DỮ LIỆU THẬT.** Nó tạo kho/kệ/ô thật trong CSDL, và
 *    dữ liệu ấy là thứ video 05 (nhập hàng, xếp ô) và 06 (bán hàng) cần. Nên nó vừa là
 *    video vừa là bước dựng dữ liệu — quay hỏng giữa chừng thì phải dọn trước khi quay lại,
 *    không phải chạy lại là xong.
 *
 * **Idempotent bằng cách đặt mã theo mốc giờ**: mỗi lượt quay tạo một kho mang mã riêng nên
 * chạy lại không đụng kho lượt trước. Đổi lại: quay nhiều lượt thì sơ đồ có nhiều kho —
 * dọn bằng cách xoá các kho có tiền tố `QUAY-` khi xong.
 *
 * Bộ chọn lấy nguyên từ cổng `check-so-do-kho.mjs` đang xanh, không tự đoán lại (kỷ luật #16:
 * kiểm chỗ đã có trước khi tự viết).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v04";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 9, "01": 11, "02": 12, "03": 14, "04": 13, "05": 12, "06": 11, "07": 8 }),
);
mkdirSync(OUT, { recursive: true });

/** Mã kho riêng cho mỗi lượt quay — chạy lại không đụng kho lượt trước. */
const MA_KHO = `QUAY-${new Date().toISOString().slice(11, 16).replace(":", "")}`;

const browser = await webkit.launch();
const ctx = await browser.newContext({
  viewport: { width: 402, height: 874 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  locale: "vi-VN",
  timezoneId: "Asia/Ho_Chi_Minh",
  recordVideo: { dir: OUT, size: { width: 804, height: 1748 } },
});
await ctx.addInitScript(() => {
  try {
    localStorage.setItem("beras.theme", "warm");
  } catch {
    /* chế độ riêng tư — chỉ mất theme */
  }
});

const page = await ctx.newPage();
const loiJS = [];
page.on("pageerror", (e) => loiJS.push(String(e).slice(0, 140)));

const T0 = Date.now();
const timeline = {};
let seg = null;
let segStart = Date.now();
let tran = 0;
function begin(id) {
  seg = id;
  segStart = Date.now();
  timeline[id] = segStart - T0;
  process.stdout.write(`  đoạn ${id} (${DUR[id]}s) … `);
}
async function hold() {
  const left = DUR[seg] * 1000 + 700 - (Date.now() - segStart);
  if (left > 0) await page.waitForTimeout(left);
  else {
    tran++;
    process.stdout.write(`⚠ tràn ${Math.round(-left / 1000)}s `);
  }
  process.stdout.write("✓\n");
}
async function tap(loc) {
  await loc.scrollIntoViewIfNeeded();
  await page.waitForTimeout(350);
  await loc.click();
}
/** Cuộn trang.
 *
 * 🔴 KHÔNG dùng `page.mouse.wheel`: đặt `isMobile: true` là WebKit chặn hẳn nó
 *    ("Mouse wheel is not supported in mobile WebKit"). Video 01 dùng được vì nó KHÔNG đặt
 *    cờ đó — hai video cùng khổ màn nhưng khác chế độ, và khác biệt ấy chỉ lộ ra khi gọi
 *    đúng hàm bị chặn. `window.scrollBy` chạy ở cả hai chế độ, và `smooth` cho cú cuộn
 *    mượt hơn trên hình. */
async function cuon(y) {
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: "smooth" }), y);
}

async function type(loc, text, delay = 70) {
  await loc.scrollIntoViewIfNeeded();
  await loc.click();
  await loc.fill("");
  await loc.type(text, { delay });
}

try {
  // ── 00 · đăng nhập ────────────────────────────────────────────────────────
  begin("00");
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  await type(page.locator('input[type="email"]'), EMAIL, 30);
  await type(page.locator('input[type="password"]'), PASSWORD, 30);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForTimeout(2500);
  await hold();

  // ── 01 · vào Sơ đồ kho ────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/so-do-kho`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-so-do.png`, fullPage: true });
  await hold();

  // ── 02 · thêm KHO ─────────────────────────────────────────────────────────
  begin("02");
  const nutThemKho = page.locator("button", { hasText: /^\+ Thêm kho$/ }).first();
  await nutThemKho.waitFor({ timeout: 20_000 });
  await tap(nutThemKho);
  await page.waitForTimeout(1200);
  await type(page.locator('input[aria-label="Mã vị trí"]'), MA_KHO);
  await page.waitForTimeout(500);
  const oTen = page.locator('input[aria-label="Tên vị trí"]');
  if (await oTen.count()) await type(oTen, "Kho quầy trước", 55);
  await page.screenshot({ path: `${OUT}/02-them-kho.png`, fullPage: true });
  await hold();

  // ── 03 · thứ tự lấy hàng ──────────────────────────────────────────────────
  begin("03");
  const oThuTu = page.locator('input[aria-label="Thứ tự đi lấy hàng"]');
  if (await oThuTu.count()) {
    await type(oThuTu, "10", 160);
    await page.waitForTimeout(900);
  }
  await page.screenshot({ path: `${OUT}/03-thu-tu.png`, fullPage: true });
  await hold();

  // ── 04 · lưu ──────────────────────────────────────────────────────────────
  begin("04");
  await tap(page.locator("button", { hasText: /^Lưu vị trí$/ }).first());
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/04-da-luu.png`, fullPage: true });
  await hold();

  // ── 05 · sang màn Khởi tạo tồn ────────────────────────────────────────────
  begin("05");
  await page.goto(`${BASE}/khoi-tao-ton`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/05-khoi-tao-ton.png`, fullPage: true });
  await hold();

  // ── 06 · khác gì nhập hàng ────────────────────────────────────────────────
  begin("06");
  await cuon(420);
  await page.waitForTimeout(1600);
  await cuon(420);
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `${OUT}/06-giai-thich.png`, fullPage: true });
  await hold();

  // ── 07 · bìa kết ──────────────────────────────────────────────────────────
  begin("07");
  await page.goto(`${BASE}/so-do-kho`, { waitUntil: "load" });
  await page.waitForTimeout(2500);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nmã kho lượt này: ${MA_KHO}`);
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
