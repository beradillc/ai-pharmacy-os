/**
 * **Cài đặt → Thông tin cơ sở** — cổng cho lỗi M-02 (UAT 2026-08-01).
 *
 * 🔴 CÓ GHI: nó lưu thông tin cơ sở thật vào `tenant_compliance_configs`. Đặt trong nhóm
 * ĐỌC vẫn được vì nó **ghi rồi trả lại nguyên giá trị cũ**, không để lại rác — nhưng nói
 * ra ở đây chứ không giấu, và nếu chạy trên CSDL thật thì hãy đọc kỹ trước.
 *
 * Đo sáu mệnh đề:
 *   1. khối có mặt trên màn Cài đặt (`khoi-thong-tin-co-so`);
 *   2. giá trị đã lưu **hiện lại được** sau khi tải lại trang — nếu chỉ ghi mà không đọc
 *      lại thì màn "trông như chạy" trọn vẹn cho tới lần đăng nhập sau;
 *   3. 🔴 màn **tự nói ra là hoá đơn CHƯA dùng** thông tin này. Đây là nợ có thật, và một
 *      màn "Thông tin cơ sở" mà người dùng tưởng đã đổi được hoá đơn rồi in 200 tờ sai tên
 *      là hỏng đắt hơn nhiều so với một dòng chữ thừa;
 *   4. lời cảnh báo ở ③ **nhìn thấy được**, không chỉ có trong DOM (kỷ luật #21);
 *   5. ô nhập không biến dạng ở khổ 390px — cùng bẫy `flex-basis` đã quay lại bốn lần;
 *   6. trang không cuộn ngang · không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.8:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/thong-tin-co-so";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

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

  await p.goto(`${BASE}/cai-dat`, { waitUntil: "load" });
  await p.waitForTimeout(3000);

  const coKhoi = (await p.locator('[data-testid="khoi-thong-tin-co-so"]').count()) > 0;

  // ② Ghi một giá trị RIÊNG cho lượt chạy này, rồi tải lại và đọc lại. Dùng một chuỗi duy
  //    nhất chứ không dùng giá trị cố định: một ô giữ nguyên giá trị của lượt trước cũng
  //    "khớp" với một giá trị cố định, và cổng sẽ xanh mà không chứng minh gì.
  const dau = `Nhà thuốc Kiểm thử ${Date.now().toString().slice(-6)}`;
  await p.fill('input[aria-label="Tên cơ sở"]', dau);
  await p.fill('input[aria-label="Địa chỉ"]', "650 Nguyễn Trãi, P.11, Q.5");
  await p.fill('input[aria-label="Điện thoại"]', "028 3822 1234");
  await p.fill('input[aria-label="Mã số thuế"]', "0312345678");
  await p.fill('input[aria-label="Mã cơ sở bán lẻ (Cục QLD cấp)"]', "01234");

  const oTen = await trongKhungNhin(p, p.locator('input[aria-label="Tên cơ sở"]'));
  // ⑤ Ô nhập không biến dạng — bẫy `flex-basis` trong hộp dọc đã quay lại BỐN lần, lần
  //    gần nhất xuyên qua chính bản vá tuyên bố "sửa ở chỗ khai nên không quay lại được".
  const caoONhap = await p.evaluate(() =>
    Math.max(
      ...[...document.querySelectorAll('[data-testid="khoi-thong-tin-co-so"] input')].map(
        (e) => e.getBoundingClientRect().height,
      ),
    ),
  );

  await p.screenshot({ path: `${OUT}/${ten}-1-truoc-luu.png`, fullPage: true });
  await p.locator("button", { hasText: /^Lưu thông tin cơ sở$/ }).click();
  await p.waitForTimeout(3000);

  await p.reload({ waitUntil: "load" });
  await p.waitForTimeout(3500);
  const sauTaiLai = await p.inputValue('input[aria-label="Tên cơ sở"]');
  const luuThat = sauTaiLai === dau;

  const noiChuaVaoHoaDon = /Hoá đơn in ra chưa dùng thông tin ở đây/i.test(
    await p.locator("body").innerText(),
  );
  const oCanhBao = await trongKhungNhin(
    p,
    p.locator('[data-testid="khoi-thong-tin-co-so"] p').filter({ hasText: "chưa dùng thông tin" }),
  );
  const cuon = await cuonNgangTrang(p);
  await p.screenshot({ path: `${OUT}/${ten}-2-sau-tai-lai.png`, fullPage: true });

  const oNhapBinhThuong = caoONhap <= 96;

  const dat =
    coKhoi &&
    luuThat &&
    noiChuaVaoHoaDon &&
    oCanhBao.dat &&
    oTen.dat &&
    oNhapBinhThuong &&
    cuon.dat &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  ① khối Thông tin cơ sở có mặt: ${coKhoi ? "✓" : "🔴"}`);
  console.log(
    `  ② lưu rồi TẢI LẠI vẫn đúng: ${luuThat ? "✓" : `🔴 ghi "${dau}" · đọc lại "${sauTaiLai}"`}`,
  );
  console.log(
    `  ③ nói rõ hoá đơn CHƯA dùng: ${noiChuaVaoHoaDon ? "✓" : "🔴 — nợ bị giấu, người dùng sẽ in nhầm"}`,
  );
  console.log(`  ⑤ ô nhập cao ${Math.round(caoONhap)}px (≤96) ${oNhapBinhThuong ? "✓" : "🔴"}`);
  inDong("④ cảnh báo nhìn thấy được", oCanhBao);
  inDong("   ô Tên cơ sở nhìn thấy được", oTen);
  inDong("⑥ trang không cuộn ngang", cuon);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(
  hong === 0
    ? "\n✅ Thông tin cơ sở khai được, lưu thật, và tự nói rõ phần còn nợ."
    : `\n🔴 ${hong} khổ có vấn đề.`,
);
process.exit(hong === 0 ? 0 : 1);
