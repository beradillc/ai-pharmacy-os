/**
 * VIDEO 05 — Nhập hàng · Xếp vào ô. Khổ điện thoại, chủ đề Warm.
 *
 * 🔴 GHI DỮ LIỆU THẬT: nhận hàng vào kho, tạo lô, gắn ô. Lô này là thứ video 06 (bán hàng)
 *    sẽ bán. Chạy `lib/don-truoc-khi-quay.mjs` TRƯỚC mỗi lượt.
 *
 * Bộ chọn lấy từ cổng `check-nhap-nhanh.mjs` đang xanh (kỷ luật #16).
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v05";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 11, "02": 13, "03": 15, "04": 13, "05": 12, "06": 9 }),
);
mkdirSync(OUT, { recursive: true });

/** Hạn dùng tính TƯƠNG ĐỐI — ghi cứng một ngày là để bom hẹn giờ, đúng ca hai test tự đỏ
 *  lúc nửa đêm 01→02/08 (xem PROJECT_STATE). */
const han = new Date(Date.now() + 400 * 86400_000).toISOString().slice(0, 10);
const SO_LO = `L${new Date().toISOString().slice(2, 10).replace(/-/g, "")}`;

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
async function cuon(y) {
  await page.evaluate((d) => window.scrollBy({ top: d, behavior: "smooth" }), y);
}
/** Tìm nút TRONG VÙNG NỘI DUNG, không tính thanh điều hướng.
 *
 * 🔴 Ở khổ điện thoại, thanh điều hướng dưới có nút **"Thêm"** (mở menu phụ). `page.locator`
 *    toàn trang bắt trúng nó thay vì nút "Thêm" của màn — lượt quay đầu mở ra menu điều
 *    hướng rồi đứng chờ ô "Số lô" mãi không thấy. ĐÚNG lỗi đã gặp ở `check-man-rong` ngày
 *    02/08, khác màn, cùng nguyên nhân: quét toàn trang thì thanh điều hướng luôn nằm trong
 *    tầm quét. */
function nutTrongMan(mau) {
  return page.locator("main button", { hasText: mau });
}

async function type(loc, text, delay = 70) {
  await loc.scrollIntoViewIfNeeded();
  await loc.click();
  await loc.fill("");
  await loc.type(text, { delay });
}

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

  // ── 01 · màn Nhập hàng ────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/nhap-nhanh`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-nhap-hang.png`, fullPage: true });
  await hold();

  // ── 02 · chọn thuốc ───────────────────────────────────────────────────────
  begin("02");
  // 🔴 Màn này chọn thuốc bằng DANH SÁCH THẢ XUỐNG, không phải ô tìm + nút Thêm. Lượt viết
  //    đầu tôi đoán theo màn bán hàng và gõ vào ô tìm không tồn tại — ô "— chọn thuốc —" ở
  //    nguyên, nên nút "Nhận vào kho" bị KHOÁ và bản quay đứng chờ một nút không bao giờ bấm
  //    được. Ảnh khung hình chỉ ra ngay; log chỉ nói "waiting for element".
  const chonThuoc = page.locator("select").first();
  await chonThuoc.waitFor({ timeout: 20_000 });
  const nhan = await chonThuoc.locator("option").allTextContents();
  const muon = nhan.find((t) => /clorpheniramin/i.test(t)) ?? nhan.find((t) => !/chọn thuốc/i.test(t));
  if (!muon) {
    console.error("🔴 Danh sách thuốc rỗng — không quay được.");
    process.exit(2);
  }
  await chonThuoc.selectOption({ label: muon });
  await page.waitForTimeout(1500);
  console.log(`\n     (chọn thuốc: ${muon})`);
  await page.screenshot({ path: `${OUT}/02-chon-thuoc.png`, fullPage: true });
  await hold();

  // ── 03 · số lô + hạn dùng — hai ô quan trọng nhất ─────────────────────────
  begin("03");
  const oLo = page.locator('input[aria-label="Số lô"]').first();
  if (await oLo.count()) {
    await type(oLo, SO_LO, 90);
    await page.waitForTimeout(700);
  }
  const oHan = page.locator('input[aria-label="Hạn dùng"]').first();
  if (await oHan.count()) {
    await oHan.fill(han);
    await page.waitForTimeout(900);
  }
  await page.screenshot({ path: `${OUT}/03-lo-han.png`, fullPage: true });
  await hold();

  // ── 04 · số lượng + giá vốn ───────────────────────────────────────────────
  begin("04");
  for (const [nhan, gt] of [
    ["Số lượng", "50"],
    ["Giá vốn", "220"],
  ]) {
    const o = page.locator(`input[aria-label*="${nhan}"]`).first();
    if (await o.count()) {
      await type(o, gt, 110);
      await page.waitForTimeout(600);
    }
  }
  await page.screenshot({ path: `${OUT}/04-so-luong-gia.png`, fullPage: true });
  await hold();

  // ── 05 · nhận vào kho ─────────────────────────────────────────────────────
  begin("05");
  const nutNhan = nutTrongMan(/^Nhận vào kho$/).first();
  // Nút này BỊ KHOÁ cho tới khi đủ thông tin. Kiểm `isEnabled` chứ không chỉ `count` — một
  // nút có mặt nhưng bị khoá thì `count()` vẫn đếm được, và cú bấm sẽ chờ tới hết giờ.
  if ((await nutNhan.count()) && (await nutNhan.isEnabled())) {
    await tap(nutNhan);
    await page.waitForTimeout(3000);
  } else {
    console.log("\n     ⚠ nút 'Nhận vào kho' đang KHOÁ — thiếu thông tin, chưa nhận được hàng");
  }
  await page.screenshot({ path: `${OUT}/05-da-nhan.png`, fullPage: true });
  await hold();

  // ── 06 · khối "Đã nhận trong lượt này" + bìa kết ──────────────────────────
  begin("06");
  await cuon(400);
  await page.waitForTimeout(1800);
  await page.screenshot({ path: `${OUT}/06-da-nhan-luot-nay.png`, fullPage: true });
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nsố lô lượt này: ${SO_LO} · hạn dùng ${han}`);
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
