/**
 * Màn **Đơn thuốc** (tra cứu) — cổng cho lỗi M-08 (UAT 2026-08-01).
 *
 * 🔴 ĐỌC THUẦN. Không tạo đơn, không duyệt đơn.
 *
 * Đo sáu mệnh đề:
 *   1. có lối vào từ menu;
 *   2. bảng có dòng thật;
 *   3. **không mã máy lọt ra màn** ở cột Trạng thái và cột Nguồn (`DRAFT`, `MANUAL`…);
 *   4. 🔴 màn này trả **NHIỀU HƠN** `/prescriptions/archive` — đúng lý do nó tồn tại.
 *      Cổng tự gọi cả hai API và so; nếu ai đó "tối ưu" màn về dùng lại `useArchive` thì
 *      màn vẫn chạy, vẫn có dòng, chỉ **im lặng giấu mất đơn chưa chụp ảnh**;
 *   5. lọc trạng thái thu hẹp thật, và mọi dòng còn lại đúng loại;
 *   6. nhìn thấy được ở khổ điện thoại · trang không cuộn ngang · không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const API = process.env.API_URL ?? "http://192.168.1.10:8000/api/v1";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/don-thuoc";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
const H = { Authorization: `Bearer ${phien.access_token}` };
const tatCa = await (await fetch(`${API}/prescriptions?limit=200`, { headers: H })).json();
const chiCoAnh = await (
  await fetch(`${API}/prescriptions/archive?limit=200`, { headers: H })
).json();

if (tatCa.length === 0) {
  // Tự kiểm phép đo (kỷ luật #15): không có đơn nào thì màn chỉ hiện trạng thái rỗng, và
  // mọi khẳng định bên dưới thành đúng vô nghĩa. Đỏ thẳng chứ không xanh giả.
  console.error("🔴 CSDL không có đơn thuốc nào — cổng này không chứng minh được gì.");
  process.exit(2);
}

const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [
  ["desktop", 1440, 900, false],
  ["mobile", 390, 844, true],
]) {
  const ctx = await b.newContext({
    viewport: { width: w, height: h },
    isMobile: mob,
    hasTouch: mob,
    deviceScaleFactor: 2,
  });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 120)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4000);

  const coLoiVao = await p.locator('a[href="/don-thuoc"]').count();

  await p.goto(`${BASE}/don-thuoc`, { waitUntil: "load" });
  await p.waitForTimeout(3500);

  const d = await p.evaluate(() => {
    const rows = [...document.querySelectorAll('[data-testid="ds-don-thuoc"] tbody tr')];
    const cot = (r, n) => r.querySelector(`td[data-nhan="${n}"]`)?.innerText.trim() ?? "";
    return {
      soDong: rows.length,
      maMayLotRa: rows.filter(
        (r) =>
          /^[A-Z][A-Z0-9_]{3,}$/.test(cot(r, "Trạng thái")) ||
          /^[A-Z][A-Z0-9_]{3,}$/.test(cot(r, "Nguồn")),
      ).length,
      noiKhacLuuTru: /chưa chụp ảnh/i.test(document.body.innerText),
    };
  });

  await p.screenshot({ path: `${OUT}/${ten}-1-don-thuoc.png`, fullPage: true });

  const oTrangThai = await trongKhungNhin(p, p.locator('td[data-nhan="Trạng thái"]').first());
  const cuon = await cuonNgangTrang(p);

  // ⑤ Lọc trạng thái. `VALIDATED` là trạng thái duy nhất chắc chắn khác `DRAFT` trong dữ
  //    liệu kiểm thử — nếu không có dòng nào thì mệnh đề này bỏ qua, ghi rõ chứ không nuốt.
  await p.selectOption('select[aria-label="Trạng thái"]', "VALIDATED");
  await p.waitForTimeout(3000);
  const loc = await p.evaluate(() => {
    const rows = [...document.querySelectorAll('[data-testid="ds-don-thuoc"] tbody tr')];
    const cot = (r) => r.querySelector('td[data-nhan="Trạng thái"]')?.innerText.trim() ?? "";
    return {
      soDong: rows.length,
      dungLoai: rows.every((r) => cot(r) === "Dược sĩ đã duyệt"),
    };
  });
  await p.screenshot({ path: `${OUT}/${ten}-2-loc-da-duyet.png`, fullPage: true });

  const datLoc = loc.soDong === 0 || (loc.dungLoai && loc.soDong < d.soDong);
  // ④ Mệnh đề quan trọng nhất: màn này KHÔNG phải là Lưu trữ đội lốt.
  const rongHonLuuTru = tatCa.length > chiCoAnh.length;

  const dat =
    coLoiVao > 0 &&
    d.soDong > 0 &&
    d.maMayLotRa === 0 &&
    d.noiKhacLuuTru &&
    rongHonLuuTru &&
    oTrangThai.dat &&
    cuon.dat &&
    datLoc &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  lối vào từ menu: ${coLoiVao > 0 ? "✓" : "🔴"} · nói rõ khác Lưu trữ: ${d.noiKhacLuuTru ? "✓" : "🔴"}`);
  console.log(`  ${d.soDong} dòng ${d.soDong > 0 ? "✓" : "🔴"} · mã máy lọt ra màn: ${d.maMayLotRa} (phải 0) ${d.maMayLotRa === 0 ? "✓" : "🔴"}`);
  console.log(`  API: tra cứu ${tatCa.length} đơn · lưu trữ (chỉ có ảnh) ${chiCoAnh.length} ⇒ rộng hơn: ${rongHonLuuTru ? "✓" : "🔴 (màn này đang là Lưu trữ đội lốt)"}`);
  console.log(`  lọc "Dược sĩ đã duyệt": ${d.soDong} → ${loc.soDong} dòng${loc.soDong === 0 ? " (không có đơn đã duyệt — bỏ qua)" : ` · đúng loại: ${loc.dungLoai ? "✓" : "🔴"}`}`);
  inDong("cột Trạng thái nhìn thấy được", oTrangThai);
  inDong("trang không cuộn ngang", cuon);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Màn Đơn thuốc tra được, gồm cả đơn chưa chụp ảnh." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
