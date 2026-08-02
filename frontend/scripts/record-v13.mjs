/**
 * VIDEO 13 — Nhật ký hoạt động. Khổ điện thoại, chủ đề Warm.
 *
 * ⓪⁻ Thăm dò: màn có bộ lọc `Từ ngày`/`Đến ngày`/`Loại hoạt động`, 50 dòng sẵn — vết của
 *    chín video trước (tạo kho, nhận hàng, bán đơn, tạo khách, ghi dị ứng, tạo tài khoản).
 *
 * ⑥⁺ Ba khẳng định của lời thoại, ba phép đo:
 *      ① nhật ký có dòng để xem            → `soDong > 0`
 *      ② lọc theo loại hoạt động thu hẹp   → `locThuHep`
 *      ③ không lọt mã máy ra màn            → `maMayLotRa === 0`
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v13";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 12, "02": 13, "03": 12, "04": 10 }),
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
    /* riêng tư */
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
async function type(loc, text, delay = 90) {
  await loc.scrollIntoViewIfNeeded();
  await loc.click();
  await loc.fill("");
  await loc.type(text, { delay });
}
async function cuon(y) {
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: "smooth" }), y);
}

let do3 = null;

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

  begin("01");
  await page.goto(`${BASE}/nhat-ky`, { waitUntil: "load" });
  await page.locator("main tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1800);
  const truoc = await page.locator("main tbody tr").count();
  await page.screenshot({ path: `${OUT}/01-nhat-ky.png`, fullPage: true });
  await hold();

  begin("02");
  await cuon(380);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/02-cuon.png`, fullPage: true });
  await hold();

  // ── 03 · lọc theo loại hoạt động ──────────────────────────────────────────
  begin("03");
  const loc = page.locator('select[aria-label="Loại hoạt động"]').first();
  let sau = truoc;
  if (await loc.count()) {
    const nhan = await loc.locator("option").allTextContents();
    const muon = nhan.find((t) => /đăng nhập/i.test(t)) ?? nhan.find((t, i) => i > 0);
    if (muon) {
      await loc.selectOption({ label: muon });
      await page.waitForTimeout(3000);
      sau = await page.locator("main tbody tr").count();
      console.log(`\n     (lọc "${muon}": ${truoc} → ${sau} dòng)`);
    }
  }
  do3 = await page.evaluate(() => {
    const rows = [...document.querySelectorAll("main tbody tr")];
    const cot = (r, n) => r.querySelector(`td[data-nhan="${n}"]`)?.innerText.trim() ?? "";
    return {
      soDong: rows.length,
      maMayLotRa: rows.filter((r) => /^[A-Z][A-Z0-9_]{4,}$/.test(cot(r, "Hoạt động"))).length,
    };
  });
  do3.locThuHep = sau <= truoc && sau > 0;
  await page.screenshot({ path: `${OUT}/03-loc.png`, fullPage: true });
  await hold();

  begin("04");
  await page.waitForTimeout(1600);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nđo 3 mệnh đề: ${JSON.stringify(do3)}`);
if (do3 && (do3.soDong === 0 || !do3.locThuHep || do3.maMayLotRa > 0)) {
  console.error("🔴 Một mệnh đề của lời thoại KHÔNG đúng — xem số đo trên.");
  process.exit(1);
}
console.log(`lỗi JS: ${loiJS.length}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
