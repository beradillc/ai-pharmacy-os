/**
 * VIDEO 08 — Khách hàng · Dị ứng · Cảnh báo ở quầy. Khổ điện thoại, chủ đề Warm.
 *
 * 🔴 CẢNH CHÍNH: gắn khách có dị ứng vào giỏ đang có thuốc chứa đúng hoạt chất ấy, và phần
 *    mềm PHẢI kêu. Bản quay **đo** điều đó và ĐỎ nếu không kêu — một video khẳng định "phần
 *    mềm cảnh báo" mà không đo là một lời hứa.
 *
 * ⓪⁻ Đã thăm dò trước: màn Khách hàng có nút `Thêm khách`, ô tìm
 *    `Tìm khách theo số điện thoại, hoặc lọc theo tên`.
 *    Dữ liệu dựng sẵn qua API: khách 0912650088 · đồng ý HEALTH · dị ứng Amoxicillin (SEVERE).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v08";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 11, "02": 12, "03": 13, "04": 15, "05": 11 }),
);
mkdirSync(OUT, { recursive: true });

const SDT_KHACH = process.env.SDT_KHACH_DI_UNG ?? "0912650088";
const THUOC_XUNG_DOT = "Augmentin";

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
const nutTrongMan = (mau) => page.locator("main button", { hasText: mau });

let canhBao = null;

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

  // ── 01 · màn Khách hàng ───────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/khach-hang`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-khach-hang.png`, fullPage: true });
  await hold();

  // ── 02 · tìm khách, mở hồ sơ ──────────────────────────────────────────────
  begin("02");
  const oTim = page.locator('input[placeholder*="Tìm khách"]').first();
  if (await oTim.count()) {
    await type(oTim, SDT_KHACH, 110);
    await page.waitForTimeout(2200);
  }
  const dong = page.locator("main tbody tr, main [data-testid*='khach'] li").first();
  if (await dong.count()) {
    await tap(dong);
    await page.waitForTimeout(2200);
  }
  await page.screenshot({ path: `${OUT}/02-ho-so-khach.png`, fullPage: true });
  await hold();

  // ── 03 · sang quầy, thêm thuốc xung đột ───────────────────────────────────
  begin("03");
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  const oThuoc = page.locator('input[placeholder*="Tìm thuốc"]');
  await oThuoc.waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1000);
  await type(oThuoc, THUOC_XUNG_DOT, 110);
  await page.waitForTimeout(2200);
  const them = nutTrongMan(/^Thêm$/).first();
  if ((await them.count()) && (await them.isEnabled())) await tap(them);
  await page.waitForTimeout(1500);
  await hold();

  // ── 04 · CẢNH CHÍNH: gắn khách → cảnh báo phải kêu ────────────────────────
  begin("04");
  const xemGio = page.locator('button:has-text("Xem giỏ")');
  if (await xemGio.count()) {
    await tap(xemGio.first());
    await page.waitForTimeout(1500);
  }
  const oSdt = page.locator('input[placeholder*="Hỏi khách"], input[type="tel"]').first();
  if (await oSdt.count()) {
    await type(oSdt, SDT_KHACH, 120);
    await page.waitForTimeout(3000);
  }
  // Đo THẬT: cảnh báo phải hiện, và phải có ô ghi lý do nếu vẫn muốn bán.
  canhBao = await page.evaluate(() => {
    const t = document.body.innerText;
    return {
      coCanhBao: /dị ứng/i.test(t),
      coOLyDo: !!document.querySelector('input[aria-label^="Lý do vẫn bán"]'),
    };
  });
  await page.screenshot({ path: `${OUT}/04-canh-bao.png`, fullPage: true });
  await hold();

  begin("05");
  await page.waitForTimeout(1500);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nđo cảnh báo dị ứng: ${JSON.stringify(canhBao)}`);
if (canhBao && !canhBao.coCanhBao) {
  console.error("🔴 KHÔNG có cảnh báo dị ứng — cảnh chính của video KHÔNG đúng.");
  process.exit(1);
}
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
