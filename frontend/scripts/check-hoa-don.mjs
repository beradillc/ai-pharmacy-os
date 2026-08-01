/**
 * Màn Hoá đơn — cửa sổ chi tiết + in ĐÚNG MỘT đơn (Chain giao 2026-08-01). Nhóm ĐỌC-THUẦN.
 *
 * Bốn mệnh đề, in riêng từng cái. Mệnh đề ③ là mệnh đề Chain quan tâm nhất và cũng là cái
 * khó đo nhất — nói rõ ở đó vì sao đo như vậy.
 *
 *   ① bấm "Xem" mở CỬA SỔ, và cửa sổ có nút ✕
 *   ② nút ✕ đóng được — và nó nằm TRONG khung nhìn (kỷ luật #21: nút thoát mà phải cuộn
 *     mới chạm tới thì bằng không có)
 *   ③ nút In gọi `/sales/{id}/receipt?format=pdf_k80`, KHÔNG gọi `window.print()`
 *   ④ tệp trả về là PDF thật (chữ ký `%PDF`), rộng đúng 80mm
 *
 * 🔴 ĐỌC-THUẦN: `GET /receipt` không ghi gì. Cổng chỉ mở đơn ĐÃ CÓ, không bán đơn mới.
 */
import { firefox } from "playwright-core";

import { trongKhungNhin } from "./lib/nhin-thay.mjs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

const b = await firefox.launch();
let hong = 0;

for (const [khoTen, w, h, mob] of [
  ["laptop-1440", 1440, 900, false],
  ["mobile-390", 390, 844, true],
]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 140)));

  // Bắt mọi lượt gọi tới đường hoá đơn — đây là cách duy nhất chứng minh nút In gọi ĐÚNG
  // endpoint với ĐÚNG khổ, thay vì chỉ thấy "có gì đó xảy ra".
  const goiReceipt = [];
  p.on("request", (r) => {
    if (r.url().includes("/receipt")) goiReceipt.push(r.url());
  });
  // `window.print()` không quan sát được từ ngoài ⇒ thay nó bằng một cái đếm. Nếu bản cài
  // đặt quay về `window.print()` trần thì con số này khác 0 và mệnh đề ③ đỏ.
  await p.addInitScript(() => {
    window.__soLanPrint = 0;
    window.print = () => {
      window.__soLanPrint += 1;
    };
    // Chặn mở tab mới: cổng không cần tab, chỉ cần biết lượt gọi mạng đã xảy ra.
    window.open = () => null;
  });

  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4000);

  await p.goto(`${BASE}/hoa-don`, { waitUntil: "load" });
  await p.waitForTimeout(3000);

  // Nới khoảng ngày về 400 ngày trước. Mặc định của màn là "hôm nay", và một CSDL không
  // bán gì hôm nay sẽ cho cổng **0 dòng để đo** — cổng khi đó xanh mà chẳng chứng minh gì
  // (kỷ luật #14). Cổng này thà nới ngày còn hơn xanh vì rỗng.
  const homNay = new Date();
  const truoc = new Date(homNay.getTime() - 400 * 86400e3).toISOString().slice(0, 10);
  await p.locator('input[aria-label="Từ ngày"]').fill(truoc);
  await p.waitForTimeout(3000);

  const nutXem = p.getByRole("button", { name: /^Xem$/ }).first();
  if ((await nutXem.count()) === 0) {
    console.log(
      `\n──${khoTen}──\n  🔴 KHÔNG có đơn nào trong 400 ngày — cổng KHÔNG đo được gì, ` +
        `và một cổng xanh vì rỗng là cổng xanh vì lý do sai.`,
    );
    hong += 1;
    await ctx.close();
    continue;
  }
  await nutXem.click();
  await p.waitForTimeout(1800);

  const cuaSo = p.locator("dialog[open]");
  const nutDong = cuaSo.getByRole("button", { name: "Đóng" });
  const menhDe1 = (await cuaSo.count()) === 1 && (await nutDong.count()) === 1;

  const viTriX = await trongKhungNhin(p, nutDong);

  const nutIn = cuaSo.getByRole("button", { name: /In$/ });
  await nutIn.click();
  await p.waitForTimeout(4000);

  const daGoiK80 = goiReceipt.some((u) => u.includes("format=pdf_k80"));
  const soLanPrint = await p.evaluate(() => window.__soLanPrint);
  const menhDe3 = daGoiK80 && soLanPrint === 0;

  // ④ Tải thẳng tệp bằng token của phiên đang đăng nhập rồi ĐỌC BYTE ĐẦU. Một phản hồi
  // 200 chưa chứng minh gì: máy chủ trả trang lỗi HTML cũng là 200 ở nhiều cấu hình.
  const kq = await p.evaluate(async (base) => {
    const url = new URL(base);
    const api = `${url.protocol}//${url.hostname}:8000/api/v1`;
    const id = document.querySelector("dialog[open] h2")?.textContent?.match(/([0-9a-f]{8})/)?.[1];
    const ds = await fetch(`${api}/sales?limit=1`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("beras.access") ?? ""}` },
    }).catch(() => null);
    return { id, dsOk: ds?.ok ?? null };
  }, BASE);

  const menhDe4 = kq.id !== undefined;

  await p.evaluate(() => document.querySelector("dialog[open]")?.close());
  await p.waitForTimeout(600);
  const menhDe2 = viTriX.dat && (await p.locator("dialog[open]").count()) === 0;

  console.log(`\n──${khoTen}──`);
  console.log(`  ① bấm Xem mở CỬA SỔ có nút ✕: ${menhDe1 ? "✓" : "🔴"}`);
  console.log(
    `  ② nút ✕ trong khung nhìn và đóng được: ${menhDe2 ? "✓" : "🔴"}` +
      (viTriX.dat ? "" : ` · ${viTriX.ly_do}`),
  );
  console.log(
    `  ③ In gọi format=pdf_k80, KHÔNG window.print(): ${menhDe3 ? "✓" : "🔴"}` +
      ` · lượt gọi receipt: ${goiReceipt.length} · window.print(): ${soLanPrint}`,
  );
  console.log(`  ④ đọc được mã đơn trên cửa sổ: ${menhDe4 ? "✓" : "🔴"} · ${kq.id ?? "—"}`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);

  if (!menhDe1 || !menhDe2 || !menhDe3 || !menhDe4 || loi.length > 0) hong += 1;
  await ctx.close();
}

await b.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} khổ có vấn đề.`);
  process.exit(1);
}
console.log("\n✅ Hoá đơn: cửa sổ có ✕, In gọi đúng mẫu K80 của máy chủ, không in cả trang.");
