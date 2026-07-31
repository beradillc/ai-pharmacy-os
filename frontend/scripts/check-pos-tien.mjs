/**
 * Bảng thu tiền ở quầy — thành tiền · khách đưa · thối lại · nút mệnh giá (Chain giao 31/07).
 *
 * 🔴 ĐỌC THUẦN: thêm hàng vào giỏ và bấm nút mệnh giá đều chỉ đổi trạng thái trong trình
 * duyệt. **Không bấm Thanh toán** — cổng này chạy được cả trên `nt650v2`, CSDL Chain đang
 * dùng, mà không thêm một hoá đơn rác nào.
 *
 * Đo cái gì: phép TÍNH tiền thối, không phải "ô có tồn tại". Một bảng hiện đủ nhãn mà tính
 * sai còn tệ hơn không có bảng — thu ngân tin nó và đếm tiền theo.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/pos-tien";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

const so = (t) => Number(String(t).replace(/[^\d-]/g, "")) * (String(t).includes("-") ? -1 : 1);

const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [["desktop",1440,900,false],["mobile",390,844,true]]) {
  const ctx = await b.newContext({ viewport:{width:w,height:h}, isMobile:mob, hasTouch:mob, deviceScaleFactor:2 });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 120)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]'); await p.waitForTimeout(4000);
  await p.goto(`${BASE}/`, { waitUntil: "load" }); await p.waitForTimeout(3000);

  // Giỏ RỖNG: bảng tiền không được hiện — một ô "thối lại" trên giỏ rỗng là nhiễu.
  const khiRong = await p.locator('[data-testid="thoi-lai"]').count();

  // Thêm một mặt hàng bất kỳ từ danh mục bên trái.
  await p.locator("button", { hasText: /Thêm|\+/ }).first().click().catch(() => {});

  // 🔴 Trên điện thoại giỏ thu thành thanh đáy (bản vá 31/07 — nút Thanh toán từng nằm cách
  // 3,9 màn). Giỏ đóng là `display: none`, nên MỌI phép đo bên trong giỏ đều hỏng ở khổ
  // mobile: `innerText` trả rỗng, `click()` báo "element is not visible". Cổng này chạy hai
  // khổ nhưng chưa bao giờ mở giỏ ⇒ đỏ ở khổ mobile từ 31/07, và cái đỏ là PHÉP ĐO chứ
  // không phải sản phẩm. Trên máy tính không có nút này, `count()` bằng 0 nên bỏ qua.
  const moGio__ = p.getByRole("button", { name: /^Xem giỏ$/ });
  if (await moGio__.count()) {
    await moGio__.click();
    await p.waitForTimeout(900);
  }
  await p.waitForTimeout(1200);
  let thanhTien = so(await p.locator("text=Thành tiền").locator("xpath=..").innerText().catch(() => "0"));

  // Bấm mệnh giá 100.000 hai lần ⇒ khách đưa 200.000.
  const nut100 = p.locator("button", { hasText: /^\+100\.000$/ });
  const coNutMenhGia = (await nut100.count()) > 0;
  if (coNutMenhGia) { await nut100.click(); await nut100.click(); await p.waitForTimeout(600); }

  const tienNhanEl = p.locator('input[aria-label="Tiền khách đưa"]');
  const daNhan = so(await tienNhanEl.inputValue().catch(() => "0"));
  const thoiLaiHien = so(await p.locator('[data-testid="thoi-lai"]').innerText().catch(() => "0"));

  // Nút "Đủ tiền" phải cho thối lại đúng 0.
  await p.locator("button", { hasText: /^Đủ tiền$/ }).click().catch(() => {});
  await p.waitForTimeout(500);
  const thoiLaiKhiDu = so(await p.locator('[data-testid="thoi-lai"]').innerText().catch(() => "-999"));

  await p.screenshot({ path: `${OUT}/${ten}-quay-thu-tien.png`, fullPage: true });

  const tinhDung = daNhan > 0 && thoiLaiHien === daNhan - thanhTien;
  const dat = khiRong === 0 && coNutMenhGia && tinhDung && thoiLaiKhiDu === 0 && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  giỏ rỗng KHÔNG hiện bảng tiền: ${khiRong === 0 ? "✓" : "🔴"}`);
  console.log(`  nút mệnh giá: ${coNutMenhGia ? "✓" : "🔴"} · thành tiền ${thanhTien} · khách đưa ${daNhan}`);
  console.log(`  thối lại hiện ${thoiLaiHien} · phải là ${daNhan - thanhTien} ${tinhDung ? "✓" : "🔴"}`);
  console.log(`  nút "Đủ tiền" ⇒ thối lại ${thoiLaiKhiDu} (phải 0) ${thoiLaiKhiDu === 0 ? "✓" : "🔴"}`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Bảng thu tiền ở quầy tính đúng." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
