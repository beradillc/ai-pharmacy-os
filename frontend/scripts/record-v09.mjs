/**
 * VIDEO 09 — Hoá đơn · In · Ghi nhận trả hàng. Khổ điện thoại, chủ đề Warm.
 *
 * ⓪⁻ Đã thăm dò trước: màn có bộ lọc `Từ ngày`/`Đến ngày`, nút `Hôm nay`, mỗi dòng một nút
 *    `Xem`; trong cửa sổ chi tiết có `🖨 In` và `Ghi nhận trả hàng`. Bấm vào DÒNG không mở
 *    cửa sổ — phải bấm đúng nút `Xem`.
 *
 * 🔴 KHÔNG bấm "Ghi nhận trả hàng" — chỉ mở ra cho thấy nó nằm đâu. Trả hàng là nghiệp vụ
 *    đụng tiền và tồn kho; quay một cú trả hàng thật là để lại phiếu trả rác trong sổ.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v09";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 11, "02": 12, "03": 13, "04": 12, "05": 10 }),
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

let doCuaSo = null;

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

  // ── 01 · màn Hoá đơn ──────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/hoa-don`, { waitUntil: "load" });
  await page.locator("main tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/01-hoa-don.png`, fullPage: true });
  await hold();

  // ── 02 · lọc theo ngày ────────────────────────────────────────────────────
  begin("02");
  const homNay = page.locator("main button", { hasText: /^Hôm nay$/ }).first();
  if (await homNay.count()) {
    await tap(homNay);
    await page.waitForTimeout(2200);
  }
  await page.screenshot({ path: `${OUT}/02-loc-ngay.png`, fullPage: true });
  await hold();

  // ── 03 · mở chi tiết một hoá đơn ──────────────────────────────────────────
  begin("03");
  const xem = page.locator("main button", { hasText: /^Xem$/ }).first();
  await xem.waitFor({ timeout: 20_000 });
  await tap(xem);
  await page.waitForTimeout(2500);
  doCuaSo = await page.evaluate(() => {
    const d = document.querySelector("dialog[open]");
    if (!d) return { moDuoc: false };
    const nut = [...d.querySelectorAll("button")].map((b) => b.innerText.trim());
    return {
      moDuoc: true,
      coNutIn: nut.some((t) => /in/i.test(t)),
      coTraLai: nut.some((t) => /trả lại/i.test(t)),
      coNutDong: nut.some((t) => /^✕$/.test(t)),
    };
  });
  await page.screenshot({ path: `${OUT}/03-chi-tiet.png`, fullPage: true });
  await hold();

  // ── 04 · chỉ CHỈ RA nút trả hàng, KHÔNG bấm ───────────────────────────────
  begin("04");
  const tra = page.locator(String.raw`dialog[open] button:has-text("Trả lại")`).first();
  if (await tra.count()) await tra.scrollIntoViewIfNeeded();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/04-tra-hang.png`, fullPage: true });
  await hold();

  // ── 05 · đóng lại, bìa kết ────────────────────────────────────────────────
  begin("05");
  const dong = page.locator('dialog[open] button:has-text("✕")').first();
  if (await dong.count()) await tap(dong);
  else await page.keyboard.press("Escape");
  await page.waitForTimeout(1500);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nđo cửa sổ hoá đơn: ${JSON.stringify(doCuaSo)}`);
if (doCuaSo && !doCuaSo.moDuoc) {
  console.error("🔴 Không mở được cửa sổ chi tiết hoá đơn.");
  process.exit(1);
}
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
