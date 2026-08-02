/**
 * VIDEO 07 — Phân quyền: vì sao thu ngân không bán được thuốc kê đơn.
 *
 * Đây là **cảnh đáng quay nhất cả bộ**: nó cho thấy phần mềm CHẶN THẬT, không phải chặn
 * bằng lời hứa trong tài liệu. Quầy cần đúng cảnh này khi phải chứng minh cách mình vận hành.
 *
 * ⓪⁻ **Đã thăm dò trước** (quy tắc 02/08):
 *      màn Nhân viên: nút `Thêm nhân viên` · `Vai trò` · `Tắt`
 *      hộp thêm nhân viên: 3 ô (họ tên · email · mật khẩu), vai trò gán RIÊNG sau
 *      thuốc kê đơn có sẵn: Diclofenac 50mg · Meloxicam 7,5mg · Amoxicillin 500mg · Augmentin
 *
 * 🔴 Tài khoản thu ngân dựng sẵn bằng API (`thungan@quaythuoc650.vn`) thay vì tạo trên máy
 *    quay. Lý do: điền một biểu mẫu ba ô mất gần một phần ba video, mà cái người xem cần
 *    thấy là **lúc bị chặn**, không phải lúc gõ email. Video vẫn mở hộp "Thêm nhân viên" ra
 *    cho thấy nó nằm đâu, rồi đóng lại.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v07";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 11, "02": 12, "03": 11, "04": 15, "05": 13, "06": 10 }),
);
mkdirSync(OUT, { recursive: true });

// 🔴 KHÔNG ghi cứng tài khoản ở đây — cổng `cong-moi-truong.test.ts` (dựng sáng nay cho
//    N-4) BẮT ĐƯỢC CHÍNH TÔI ở lượt viết đầu: tôi đặt email và mật khẩu thu ngân làm giá
//    trị mặc định, đúng thứ cổng ấy sinh ra để chặn. Mật khẩu trong mã là mật khẩu TRONG
//    GIT — đổi ở CSDL không xoá được nó khỏi lịch sử.
const THU_NGAN = process.env.EMAIL_THU_NGAN;
const MK_THU_NGAN = process.env.MK_THU_NGAN;
if (!THU_NGAN || !MK_THU_NGAN) {
  console.error(
    "🔴 Thiếu EMAIL_THU_NGAN / MK_THU_NGAN.\n" +
      "   Khai trong scripts/ui-gates.env (tệp này .gitignore bỏ qua).",
  );
  process.exit(2);
}
const THUOC_KE_DON = "Augmentin";

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

/** Đăng xuất bằng đúng nút người dùng bấm.
 *
 * 🔴 Vào thẳng `/login` khi ĐANG đăng nhập thì app đẩy ngay về màn trong — ô email không bao
 *    giờ hiện, và bản quay chờ nó tới hết giờ. Log chỉ nói "waiting for input[type=email]",
 *    câu đó đọc như màn login hỏng. Phải đăng XUẤT trước. Và đây cũng là thao tác người xem
 *    cần thấy: đổi ca thì đổi tài khoản. */
async function dangXuat() {
  const nut = page.locator('button:has-text("Đăng xuất")').first();
  if (await nut.count()) {
    await tap(nut);
    await page.waitForTimeout(2200);
  }
}

async function dangNhap(email, mk) {
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  await type(page.locator('input[type="email"]'), email, 30);
  await type(page.locator('input[type="password"]'), mk, 30);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForTimeout(2500);
}

let chan = null;

try {
  // ── 00 · đăng nhập bằng tài khoản dược sĩ ─────────────────────────────────
  begin("00");
  await dangNhap(EMAIL, PASSWORD);
  await hold();

  // ── 01 · màn Nhân viên ────────────────────────────────────────────────────
  begin("01");
  await page.goto(`${BASE}/nhan-vien`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/01-nhan-vien.png`, fullPage: true });
  await hold();

  // ── 02 · mở hộp Thêm nhân viên rồi đóng ───────────────────────────────────
  begin("02");
  const nutThem = nutTrongMan(/^Thêm nhân viên$/).first();
  if (await nutThem.count()) {
    await tap(nutThem);
    await page.waitForTimeout(2200);
    await page.screenshot({ path: `${OUT}/02-them-nhan-vien.png`, fullPage: true });
    const huy = page.locator('dialog[open] button:has-text("Huỷ")').first();
    if (await huy.count()) await tap(huy);
    else await page.keyboard.press("Escape");
    await page.waitForTimeout(1200);
  }
  await hold();

  // ── 03 · đăng xuất rồi đăng nhập bằng tài khoản thu ngân ──────────────────
  begin("03");
  await dangXuat();
  await dangNhap(THU_NGAN, MK_THU_NGAN);
  await page.screenshot({ path: `${OUT}/03-la-thu-ngan.png`, fullPage: true });
  await hold();

  // ── 04 · thu ngân thêm thuốc KÊ ĐƠN vào giỏ ───────────────────────────────
  begin("04");
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  const oTim = page.locator('input[placeholder*="Tìm thuốc"]');
  await oTim.waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1200);
  await type(oTim, THUOC_KE_DON, 110);
  await page.waitForTimeout(2200);
  const them = nutTrongMan(/^Thêm$/).first();
  if ((await them.count()) && (await them.isEnabled())) await tap(them);
  await page.waitForTimeout(1600);
  await page.screenshot({ path: `${OUT}/04-them-etc.png`, fullPage: true });
  await hold();

  // ── 05 · CẢNH CHÍNH: mở giỏ, thấy bị chặn ─────────────────────────────────
  begin("05");
  const xemGio = page.locator('button:has-text("Xem giỏ")');
  if (await xemGio.count()) {
    await tap(xemGio.first());
    await page.waitForTimeout(1800);
  }
  // Đo THẬT xem có bị chặn không, thay vì tin con mắt người dựng: nút duyệt PHẢI vắng mặt,
  // và màn PHẢI nói ra lý do. Một video khẳng định "phần mềm chặn" mà không đo là một lời hứa.
  chan = await page.evaluate(() => {
    const t = document.body.innerText;
    return {
      coNutDuyet: [...document.querySelectorAll("button")].some((b) =>
        /dược sĩ duyệt/i.test(b.textContent ?? ""),
      ),
      noiLyDo: /cần dược sĩ|không có quyền|dược sĩ duyệt/i.test(t),
      nutThanhToanTat: [...document.querySelectorAll("button")]
        .filter((b) => /thanh toán/i.test(b.textContent ?? ""))
        .some((b) => b.hasAttribute("disabled")),
    };
  });
  await page.screenshot({ path: `${OUT}/05-bi-chan.png`, fullPage: true });
  await hold();

  // ── 06 · bìa kết ──────────────────────────────────────────────────────────
  begin("06");
  await page.waitForTimeout(1500);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log(`\nđo cảnh chặn: ${JSON.stringify(chan)}`);
if (chan && chan.coNutDuyet) {
  console.error("🔴 Thu ngân VẪN thấy nút 'Dược sĩ duyệt' — cảnh chính của video KHÔNG đúng.");
  process.exit(1);
}
if (chan && !chan.noiLyDo) {
  console.error("⚠ Màn không nói ra lý do bị chặn — người xem chỉ thấy nút biến mất.");
}
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " · " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
if (loiJS.length) process.exit(1);
