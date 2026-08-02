/**
 * VIDEO 03 — Danh mục thuốc · Hoạt chất · Giá niêm yết.
 *
 * Quy trình `10_QUY_TRINH_QUAY_LA_RA_SOAT.md`: bản quay **cũng là một lượt rà app**.
 *
 * 🔴 CÓ GHI — nhưng ghi thứ **tự trả về nguyên trạng**: nó đổi giá một thuốc rồi **đổi lại
 *    đúng giá cũ**, để cảnh "sửa giá + ghi lý do" quay được mà doanh thu không lệch. Cách này
 *    đã dùng ở `lib/dung-du-lieu-doi-gia.mjs`; ở đây làm qua **giao diện thật** vì chính thao
 *    tác ấy là thứ video cần cho thấy.
 */
import { mkdirSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { API, BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v03";
const DUR = { "00": 6, "01": 12, "02": 13, "03": 14, "04": 15, "05": 13, "06": 14, "07": 12, "08": 7 };
mkdirSync(OUT, { recursive: true });

/** Từ khoá tìm phải ra NHIỀU dòng — bài học dàn cảnh từ bản quay tổng quan (1 dòng ⇒ màn trống). */
const TU_KHOA = "clo"; // đo thật trên qt650: khớp 5 thuốc (para/amox/ibu chỉ khớp 1)

// ── Điều kiện: danh mục phải có đủ thuốc, và phải có thuốc khớp từ khoá ─────────
const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
if (!phien.access_token) {
  console.error("🔴 Đăng nhập API thất bại.");
  process.exit(2);
}
const ds = await (
  await fetch(`${API}/drugs?search=${encodeURIComponent(TU_KHOA)}&limit=20`, {
    headers: { Authorization: `Bearer ${phien.access_token}` },
  })
).json();
const khop = Array.isArray(ds) ? ds : (ds.items ?? []);
console.log(`điều kiện: "${TU_KHOA}" khớp ${khop.length} thuốc`);
if (khop.length < 2) {
  console.error(
    `⏭️  CHƯA ĐO ĐƯỢC — "${TU_KHOA}" chỉ khớp ${khop.length} thuốc. Cảnh tìm kiếm quay ra một\n` +
      "   màn gần như trống thì lên hình đọc như phần mềm đang tải dở. Đổi TU_KHOA.",
  );
  process.exit(2);
}

const browser = await webkit.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,
  locale: "vi-VN",
  recordVideo: { dir: OUT, size: { width: 1280, height: 800 } },
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
  await page.waitForTimeout(400);
  await loc.click();
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

  // ── 01 · vào Danh mục thuốc ───────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/danh-muc-thuoc`, { waitUntil: "load" });
  await page.locator("tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/01-danh-muc.png`, fullPage: true });
  await hold();

  // ── 02 · tìm theo tên ─────────────────────────────────────────────────────
  begin("02");
  const oTim = page.locator('input[placeholder*="Tìm"]').first();
  await type(oTim, TU_KHOA, 130);
  await page.waitForTimeout(2000);
  const soDong = await page.locator("tbody tr").count();
  console.log(`\n     (tìm "${TU_KHOA}" → ${soDong} dòng trên màn)`);
  await page.screenshot({ path: `${OUT}/02-tim.png`, fullPage: true });
  await hold();

  // ── 03 · mở chi tiết một thuốc ────────────────────────────────────────────
  begin("03");
  await tap(page.locator("tbody tr").first());
  await page.waitForTimeout(2200);
  await page.screenshot({ path: `${OUT}/03-chi-tiet.png`, fullPage: true });
  await hold();

  // ── 04 · khối HOẠT CHẤT — điểm nhấn của video này ─────────────────────────
  begin("04");
  const khoiHC = page.locator("text=/Hoạt chất/i").first();
  if (await khoiHC.count()) await khoiHC.scrollIntoViewIfNeeded();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${OUT}/04-hoat-chat.png`, fullPage: true });
  await hold();

  // ── 05 · mở ô sửa giá niêm yết ────────────────────────────────────────────
  begin("05");
  const nutGia = page.locator('button:has-text("Sửa giá"), button:has-text("Đổi giá")').first();
  const coSuaGia = (await nutGia.count()) > 0;
  if (coSuaGia) {
    await tap(nutGia);
    await page.waitForTimeout(2000);
  } else {
    console.log("\n     ⚠ không tìm thấy nút sửa giá — cảnh 4 của kịch bản CHƯA quay được");
  }
  await page.screenshot({ path: `${OUT}/05-sua-gia.png`, fullPage: true });
  await hold();

  // ── 06 · ô lý do đổi giá (bắt buộc) ───────────────────────────────────────
  begin("06");
  const oLyDo = page.locator('input[aria-label*="Lý do"], textarea[aria-label*="Lý do"]').first();
  if (await oLyDo.count()) {
    await type(oLyDo, "Cập nhật theo giá nhập mới", 45);
    await page.waitForTimeout(900);
  }
  await page.screenshot({ path: `${OUT}/06-ly-do.png`, fullPage: true });
  await hold();

  // ── 07 · đóng lại, KHÔNG lưu ──────────────────────────────────────────────
  // Cảnh quay cần cho thấy ô lý do là BẮT BUỘC; không cần đổi giá thật.
  begin("07");
  const dong = page.locator('button[aria-label*="Đóng"], button:has-text("Huỷ")').first();
  if (await dong.count()) await tap(dong);
  else await page.keyboard.press("Escape");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/07-dong.png`, fullPage: true });
  await hold();

  begin("08");
  await page.waitForTimeout(1200);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nlỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
console.log(`Ảnh + video: ${OUT}`);
if (loiJS.length) process.exit(1);
