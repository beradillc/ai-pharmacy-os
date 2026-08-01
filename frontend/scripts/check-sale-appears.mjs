/**
 * Bán một đơn rồi mở màn Hoá đơn — đơn vừa bán phải nằm TRÊN CÙNG.
 *
 * 🔴 Sinh từ báo cáo thật 29/07: Gấu Bông bấm Thanh toán, **doanh thu tăng
 * đúng**, nhưng màn Hoá đơn nhìn y nguyên ⇒ tưởng phần mềm không cập nhật. Hai
 * nguyên nhân độc lập cùng lúc, và cổng này canh cả hai:
 *
 * ① `useCheckout` **không làm mới cache nào cả**. Bán xong mở màn Hoá đơn trong
 *    vòng 15 giây (`staleTime` của `useSalesList`) thì React Query trả danh sách
 *    cũ — **không gọi mạng**, nên cũng không có gì để nghi. Đúng khoảng thời
 *    gian người bán thật sự mở màn đó ra.
 * ② Dữ liệu demo sinh hoá đơn của **hôm nay** với giờ ngẫu nhiên 7h–20h, kể cả
 *    giờ **chưa tới**. Lúc 15h vẫn có hoá đơn ghi 23h30 nằm trên đầu.
 *
 * 🔴 HAI LẦN PHÉP ĐO NÀY TỰ SAI TRƯỚC KHI ĐO ĐÚNG — ghi lại để đừng lặp:
 *
 *  - Bản đầu dùng `page.goto()` để sang màn Hoá đơn. `goto` là **tải lại cả
 *    trang**, xoá sạch cache React Query ⇒ bản ĐỘT BIẾN (đã gỡ invalidate) vẫn
 *    **XANH**. Một tín hiệu xanh chứng minh mệnh đề *khác* với mệnh đề người đọc
 *    tưởng. Người dùng thật bấm menu, cache còn nguyên — nên cổng phải bấm menu.
 *  - Bản thứ hai đếm tải-lại bằng sự kiện `framenavigated`. Next App Router
 *    điều hướng phía client bằng `history.pushState`, mà `pushState` **cũng**
 *    bắn `framenavigated` ⇒ đếm kiểu đó không phân biệt được đúng thứ cần phân
 *    biệt. Nay cắm một dấu trên `window`: nó chỉ mất khi trang thật sự tải lại.
 *
 * Chạy:  cd frontend && BERAS_EMAIL=… BERAS_PASSWORD=… npm run check:sale
 * Cần:   máy chủ LAN đang chạy, CSDL đã seed, có ít nhất một thuốc OTC.
 */
import { webkit } from "playwright-core";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const DRUG = process.env.BERAS_DRUG ?? "Berberin";

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu BERAS_EMAIL / BERAS_PASSWORD.");
  process.exit(2);
}

const browser = await webkit.launch();
const ctx = await browser.newContext({ viewport: { width: 402, height: 874 }, locale: "vi-VN" });
const page = await ctx.newPage();

/** Cache còn sống? Dấu cắm mất đi nghĩa là trang đã tải lại, và phép đo vô nghĩa. */
const cacheStillAlive = () => page.evaluate(() => window.__BERAS_MARK === 1);

/** Sang màn Hoá đơn bằng cách **bấm**, không phải `goto` — xem docstring. */
async function toInvoices() {
  await page
    .locator('nav button:visible:has-text("Thêm"), nav a:visible:has-text("Thêm")')
    .first()
    .click();
  await page.locator('a:visible:has-text("Hoá đơn")').first().click();
  await page.locator("tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1800);
}

async function toPos() {
  await page.locator('nav a:visible:has-text("Bán hàng")').first().click();
  await page.locator('input[placeholder*="Tìm thuốc"]').waitFor({ timeout: 25_000 });
}

let ok = false;
try {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForResponse((r) => r.url().includes("/drugs"), { timeout: 15_000 }).catch(() => {});

  await toInvoices();
  const before = (await page.locator("tbody tr").first().innerText()).replace(/\n+/g, " · ");
  console.log(`hàng đầu TRƯỚC khi bán : ${before.slice(0, 62)}`);
  await page.evaluate(() => {
    window.__BERAS_MARK = 1;
  });

  await toPos();
  await page.locator('input[placeholder*="Tìm thuốc"]').fill(DRUG);
  await page.waitForTimeout(1500);
  await page.locator('button:has-text("Thêm")').first().click();
  await page.waitForTimeout(700);
  await page.locator('button:has-text("Thanh toán")').click();
  await page.locator("text=Đã bán thành công").waitFor({ timeout: 25_000 });
  const code = (await page.locator("text=Đã bán thành công").innerText()).match(/mã đơn (\w+)/)?.[1];
  console.log(`vừa bán, mã đơn        : ${code}`);

  await toInvoices();
  const after = (await page.locator("tbody tr").first().innerText()).replace(/\n+/g, " · ");
  console.log(`hàng đầu SAU khi bán   : ${after.slice(0, 62)}`);

  const alive = await cacheStillAlive();
  console.log(`cache còn nguyên       : ${alive ? "CÓ ✓" : "KHÔNG 🔴 — phép đo vô nghĩa"}`);
  ok = Boolean(code && after.includes(code) && alive);
  console.log(
    ok
      ? "\n✓ Đơn vừa bán lên đầu danh sách, không cần tải lại trang"
      : "\n🔴 Màn Hoá đơn KHÔNG cập nhật sau khi bán",
  );
} finally {
  await browser.close();
}
process.exit(ok ? 0 : 1);
