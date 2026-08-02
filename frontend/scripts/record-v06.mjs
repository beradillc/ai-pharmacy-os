/**
 * VIDEO 06 — Bán thuốc ở quầy. Khổ điện thoại, chủ đề Warm.
 *
 * 🔴 GHI DỮ LIỆU THẬT: bán một đơn thật, trừ tồn thật, ghi doanh thu thật. Chạy
 *    `lib/don-truoc-khi-quay.mjs` trước mỗi lượt.
 *
 * ⓪⁻ **Đã chụp màn trước khi viết** (quy tắc Chain duyệt 02/08). Thăm dò cho biết:
 *      ô tìm  = `placeholder*="Tìm thuốc"`
 *      nút    = nhiều nút `Thêm`, mỗi thuốc một nút, đều nằm trong `main`
 *      ô khách = `Số điện thoại khách hàng`
 *    Nhờ vậy không phải đoán như video 04 và 05 — hai lần đó mỗi lần mất một lượt quay.
 *
 * Luồng thanh toán lấy nguyên từ `record-tutorial.mjs` đang chạy được: mở giỏ bằng "Xem giỏ",
 * rồi bấm "Thanh toán" HAI LẦN (xác nhận hai bước, Chain yêu cầu 31/07).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v06";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 11, "02": 12, "03": 11, "04": 14, "05": 13, "06": 10 }),
);
mkdirSync(OUT, { recursive: true });

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
    /* chế độ riêng tư */
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
async function type(loc, text, delay = 90) {
  await loc.scrollIntoViewIfNeeded();
  await loc.click();
  await loc.fill("");
  await loc.type(text, { delay });
}
/** Nút TRONG vùng nội dung — thanh điều hướng cũng có nút tên "Thêm". */
const nutTrongMan = (mau) => page.locator("main button", { hasText: mau });

try {
  begin("00");
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  await type(page.locator('input[type="email"]'), EMAIL, 30);
  await type(page.locator('input[type="password"]'), PASSWORD, 30);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForTimeout(2500);
  await hold();

  // ── 01 · màn bán hàng ─────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  const oTim = page.locator('input[placeholder*="Tìm thuốc"]');
  await oTim.waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/01-ban-hang.png`, fullPage: true });
  await hold();

  // ── 02 · tìm thuốc ────────────────────────────────────────────────────────
  begin("02");
  await type(oTim, "Clorpheniramin", 110);
  await page.waitForTimeout(2200);
  await page.screenshot({ path: `${OUT}/02-tim-thuoc.png`, fullPage: true });
  await hold();

  // ── 03 · thêm vào giỏ, rồi thêm món nữa ───────────────────────────────────
  begin("03");
  await tap(nutTrongMan(/^Thêm$/).first());
  await page.waitForTimeout(1400);
  await type(oTim, "Natri clorid", 100);
  await page.waitForTimeout(1800);
  const them2 = nutTrongMan(/^Thêm$/).first();
  if ((await them2.count()) && (await them2.isEnabled())) await tap(them2);
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `${OUT}/03-gio.png`, fullPage: true });
  await hold();

  // ── 04 · mở giỏ ───────────────────────────────────────────────────────────
  begin("04");
  const xemGio = page.locator('button:has-text("Xem giỏ")');
  if (await xemGio.count()) {
    await tap(xemGio.first());
    await page.waitForTimeout(1600);
  }
  await page.screenshot({ path: `${OUT}/04-xem-gio.png`, fullPage: true });
  await hold();

  // ── 05 · thanh toán hai bước ──────────────────────────────────────────────
  begin("05");
  const pay = page.locator('button:has-text("Thanh toán")').first();
  await pay.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1200);
  await tap(pay);
  // Bấm lần đầu chỉ MỞ khối xác nhận, không gọi máy chủ; lần hai mới chốt đơn.
  if (await page.locator("text=Sửa lại đơn").count()) {
    await page.waitForTimeout(2200);
    await page.screenshot({ path: `${OUT}/05-xac-nhan.png`, fullPage: true });
    await tap(pay);
  }
  await page.locator("text=Đã bán thành công").waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/05-da-ban.png`, fullPage: true });
  await hold();

  // ── 06 · hoá đơn vừa bán ──────────────────────────────────────────────────
  begin("06");
  await page.goto(`${BASE}/hoa-don`, { waitUntil: "load" });
  await page.waitForTimeout(2800);
  await page.screenshot({ path: `${OUT}/06-hoa-don.png`, fullPage: true });
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nlỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
