/**
 * VIDEO 10 — Kiểm kê · Chênh lệch chờ duyệt. Khổ điện thoại, chủ đề Warm.
 *
 * ⓪⁻ Đã thăm dò: màn có ô `Chọn ô để kiểm kê`, nút `Bắt đầu kiểm ô này` và
 *    `Điều chỉnh nhanh một lô…`. Màn tự nói mệnh đề cốt lõi:
 *    *"Chênh lệch chờ duyệt — tồn kho chỉ đổi sau khi có người ký, không đổi lúc nộp."*
 *
 * ⑥⁺ **Mỗi khẳng định trong lời thoại phải có phép đo** (quy tắc Chain duyệt 02/08).
 *    Lời thoại nói ba điều; bản quay đo cả ba:
 *      ① màn nói ra nguyên tắc "chỉ đổi sau khi ký"  → `noiNguyenTac`
 *      ② có lối vào đếm theo Ô                        → `coChonO`
 *      ③ có lối đi tắt cho một lô                     → `coDieuChinhNhanh`
 *
 * 🔴 KHÔNG nộp phiếu kiểm kê thật — chỉ mở luồng ra cho thấy. Nộp là để lại phiếu chờ duyệt
 *    trong sổ, và video 10 không có nhiệm vụ dựng dữ liệu cho ai.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v10";
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

  // ── 01 · màn Kiểm kê ──────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/kiem-ke`, { waitUntil: "load" });
  await page.waitForTimeout(3200);
  do3 = await page.evaluate(() => {
    const t = (document.querySelector("main") ?? document.body).innerText;
    const nut = [...document.querySelectorAll("main button")].map((b) => b.innerText.trim());
    return {
      noiNguyenTac: /chỉ đổi sau khi có người ký|chờ duyệt/i.test(t),
      coChonO: !!document.querySelector('select[aria-label*="Chọn ô"], [aria-label*="Chọn ô"]'),
      coDieuChinhNhanh: nut.some((x) => /điều chỉnh nhanh/i.test(x)),
    };
  });
  await page.screenshot({ path: `${OUT}/01-kiem-ke.png`, fullPage: true });
  await hold();

  // ── 02 · chọn ô để đếm ────────────────────────────────────────────────────
  begin("02");
  const chonO = page.locator("main select").first();
  if (await chonO.count()) {
    const nhan = await chonO.locator("option").allTextContents();
    const muon = nhan.find((t) => !/chọn ô|—/i.test(t));
    if (muon) {
      await chonO.selectOption({ label: muon });
      console.log(`\n     (chọn ô: ${muon})`);
      await page.waitForTimeout(2000);
    }
  }
  await page.screenshot({ path: `${OUT}/02-chon-o.png`, fullPage: true });
  await hold();

  // ── 03 · bắt đầu kiểm — KHÔNG nộp ─────────────────────────────────────────
  begin("03");
  const batDau = page.locator("main button", { hasText: /^Bắt đầu kiểm ô này$/ }).first();
  if ((await batDau.count()) && (await batDau.isEnabled())) {
    await tap(batDau);
    await page.waitForTimeout(2800);
  }
  await page.screenshot({ path: `${OUT}/03-dang-kiem.png`, fullPage: true });
  await hold();

  // ── 04 · cuộn xem nguyên tắc chờ duyệt, bìa kết ───────────────────────────
  begin("04");
  await cuon(380);
  await page.waitForTimeout(1800);
  await page.screenshot({ path: `${OUT}/04-cho-duyet.png`, fullPage: true });
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nđo 3 mệnh đề lời thoại: ${JSON.stringify(do3)}`);
if (do3 && !do3.noiNguyenTac) {
  console.error("🔴 Màn KHÔNG nói ra nguyên tắc 'chỉ đổi sau khi ký' — lời thoại đang khẳng định sai.");
  process.exit(1);
}
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
