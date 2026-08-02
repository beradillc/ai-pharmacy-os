/**
 * VIDEO 02 — Thông tin cơ sở · Tài khoản của tôi · Đổi mật khẩu.
 *
 * Quy trình `10_QUY_TRINH_QUAY_LA_RA_SOAT.md`: bản quay này **cũng là một lượt rà app**. Mỗi
 * lần nó chết là một phát hiện, không phải một phiền toái.
 *
 * 🔴 ĐỌC-THUẦN + GHI HẠN CHẾ. Nó **lưu thông tin cơ sở** (ghi thật, nhưng ghi đè đúng thứ đã
 *    có nên chạy lại không sinh rác) và **KHÔNG đổi mật khẩu** — chỉ mở màn đổi mật khẩu ra
 *    cho thấy, không bấm xác nhận. Đổi mật khẩu trong lúc quay là tự khoá mình ra khỏi CSDL,
 *    và lượt quay sau sẽ đỏ ở màn login với thông điệp đọc như lỗi sản phẩm.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v02";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? // eslint-disable-next-line no-undef
      (await import("node:fs")).readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : '{"00":6,"01":13,"02":12,"03":15,"04":14,"05":13,"06":12,"07":11,"08":7}',
);
mkdirSync(OUT, { recursive: true });

/** Khổ ĐIỆN THOẠI — Chain chốt 2026-08-02: cả bộ video quay khổ điện thoại, chủ đề Warm.
 *  Đúng thứ dược sĩ cầm trên tay ở quầy; khổ laptop là ngoại lệ chứ không phải mặc định. */
const VIEWPORT = { width: 402, height: 874 };
const GAP_MS = 700;

const browser = await webkit.launch();
const ctx = await browser.newContext({
  viewport: VIEWPORT,
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  locale: "vi-VN",
  timezoneId: "Asia/Ho_Chi_Minh",
  recordVideo: { dir: OUT, size: { width: 804, height: 1748 } },
});

/** Bật chủ đề **Warm** TRƯỚC khi trang kịp vẽ (Chain chốt 02/08).
 *  Ghi thẳng `localStorage` chứ không bấm qua Cài đặt → Giao diện: bấm qua màn thì khung
 *  hình đầu tiên vẫn là Classic rồi mới đổi, tức video mở màn bằng đúng cái theme KHÔNG
 *  định giới thiệu. `ThemeProvider` đọc khoá này trong script đặt ở `<head>`. */
await ctx.addInitScript(() => {
  try {
    localStorage.setItem("beras.theme", "warm");
  } catch {
    /* chế độ riêng tư — chỉ mất theme, không hỏng gì */
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
  const left = DUR[seg] * 1000 + GAP_MS - (Date.now() - segStart);
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
async function type(loc, text, delay = 60) {
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
  await type(page.locator('input[type="email"]'), EMAIL, 35);
  await type(page.locator('input[type="password"]'), PASSWORD, 35);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForTimeout(2500);
  await hold();

  // ── 01 · vào Cài đặt ──────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/cai-dat`, { waitUntil: "load" });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/01-cai-dat.png`, fullPage: true });
  await hold();

  // ── 02 · khối Thông tin cơ sở ─────────────────────────────────────────────
  begin("02");
  const oTen = page.locator('input[aria-label*="Tên cơ sở"], input[name*="ten"]').first();
  await oTen.waitFor({ timeout: 20_000 });
  await oTen.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/02-thong-tin-co-so.png`, fullPage: true });
  await hold();

  // ── 03 · điền từng ô, chậm ────────────────────────────────────────────────
  begin("03");
  await type(oTen, "Quầy thuốc 650");
  await page.waitForTimeout(700);
  await hold();

  begin("04");
  for (const [nhan, gt] of [
    ["Địa chỉ", "xã Thạnh Trị, Vĩnh Long"],
    ["Điện thoại", "0918280650"],
    ["Mã số thuế", "5800001234"],
  ]) {
    const o = page.locator(`input[aria-label*="${nhan}"]`).first();
    if (await o.count()) {
      await type(o, gt, 45);
      await page.waitForTimeout(500);
    }
  }
  await hold();

  // ── 05 · mã cơ sở bán lẻ — ô BẮT BUỘC ─────────────────────────────────────
  begin("05");
  const oMa = page.locator('input[aria-label*="bán lẻ"]').first();
  if (await oMa.count()) {
    await type(oMa, "68-01234");
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: `${OUT}/05-da-dien.png`, fullPage: true });
  await hold();

  // ── 06 · lưu ──────────────────────────────────────────────────────────────
  begin("06");
  const nutLuu = page.locator('button:has-text("Lưu thông tin cơ sở")').first();
  await nutLuu.waitFor({ timeout: 15_000 });
  await tap(nutLuu);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/06-da-luu.png`, fullPage: true });
  await hold();

  // ── 07 · Tài khoản của tôi + màn Đổi mật khẩu (KHÔNG bấm xác nhận) ────────
  begin("07");
  const nutDoiMK = page.locator('button:has-text("Đổi mật khẩu")').first();
  if (await nutDoiMK.count()) {
    await tap(nutDoiMK);
    await page.waitForTimeout(2000);
  }
  await page.screenshot({ path: `${OUT}/07-doi-mat-khau.png`, fullPage: true });
  await hold();

  // ── 08 · bìa kết ──────────────────────────────────────────────────────────
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
