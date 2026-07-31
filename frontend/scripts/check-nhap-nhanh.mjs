/**
 * Nhập hàng nhanh — không cần đơn mua hàng (BERAS V2 Phase 6), gắn ô ngay (Phase 5).
 *
 * 🔴 NHÓM GHI — nhận hàng THẬT vào kho. Chỉ chạy khi gọi `--all`.
 *
 * Đo bốn mệnh đề, và mệnh đề thứ tư là điểm của cả hai phase:
 *   1. màn có đủ ô nhập, KHÔNG đòi đơn mua hàng nào;
 *   2. nhận xong hiện lại dòng vừa nhận (người đứng nhập cần thấy mình vừa làm gì,
 *      nếu không họ nhập một lô hai lần mà không biết);
 *   3. ô "Thuốc" và "Cất vào ô" GIỮ NGUYÊN sau khi lưu — nhận nhiều lô cùng mặt hàng vào
 *      cùng một ô là ca thường gặp nhất;
 *   4. ra quầy thấy chỗ lấy NGAY, không phải qua bước cất hàng riêng.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/nhap-nhanh";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

const N = Date.now().toString().slice(-5);
const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [["desktop",1440,900,false],["mobile",390,844,true]]) {
  const ctx = await b.newContext({ viewport:{width:w,height:h}, isMobile:mob, hasTouch:mob, deviceScaleFactor:2 });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 140)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]'); await p.waitForTimeout(4000);

  // Dựng một ô riêng cho lượt này — cổng phải tự cô lập khỏi dữ liệu nó để lại lần trước.
  const khoMa = `N${ten[0].toUpperCase()}${N}`;
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  const cayNay = () => p.locator('[data-testid="cay-so-do"] > li').filter({ hasText: khoMa });
  await p.locator("button", { hasText: /^\+ Thêm kho$/ }).click(); await p.waitForTimeout(700);
  await p.locator('input[aria-label="Mã vị trí"]').fill(khoMa);
  await p.locator("button", { hasText: /^Lưu vị trí$/ }).click(); await p.waitForTimeout(1800);
  await cayNay().locator("button", { hasText: /^\+ Thêm/ }).first().click(); await p.waitForTimeout(700);
  await p.selectOption('select[aria-label="Tầng vị trí"]', "BIN");
  const oMa = `B${N}`;
  await p.locator('input[aria-label="Mã vị trí"]').fill(oMa);
  await p.locator("button", { hasText: /^Lưu vị trí$/ }).click(); await p.waitForTimeout(1800);

  // ① Màn nhập nhanh — không đòi đơn mua hàng nào.
  await p.goto(`${BASE}/nhap-nhanh`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  const khongDoiPO = !/đơn mua hàng nào|chọn đơn mua/i.test(await p.locator("body").innerText());

  const tenThuoc = await p.locator('select[aria-label="Chọn thuốc"] option').nth(1).innerText();
  const vThuoc = await p.locator('select[aria-label="Chọn thuốc"] option').nth(1).getAttribute("value");
  await p.selectOption('select[aria-label="Chọn thuốc"]', vThuoc);
  await p.locator('input[aria-label="Số lượng nhập"]').fill("7");
  await p.locator('input[aria-label="Số lô"]').fill(`NN${N}`);
  await p.locator('input[aria-label="Hạn dùng"]').fill("2027-06-30");
  const vO = await p.locator('select[aria-label="Cất vào ô"] option')
    .filter({ hasText: `${khoMa}/${oMa}` }).first().getAttribute("value");
  await p.selectOption('select[aria-label="Cất vào ô"]', vO);
  await p.locator("button", { hasText: /^Nhận vào kho$/ }).click();
  await p.waitForTimeout(3000);

  // ② + ③
  const daNhan = await p.locator('[data-testid="da-nhan"]').innerText().catch(() => "");
  const hienDaNhan = daNhan.includes(`${khoMa}/${oMa}`);
  const giuThuoc = (await p.locator('select[aria-label="Chọn thuốc"]').inputValue()) === vThuoc;
  const giuO = (await p.locator('select[aria-label="Cất vào ô"]').inputValue()) === vO;

  await p.screenshot({ path: `${OUT}/${ten}-1-nhap-nhanh.png`, fullPage: true });

  // ④ Ra quầy — chỗ lấy phải có NGAY, không qua bước cất hàng riêng.
  await p.goto(`${BASE}/`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  await p.locator('input[placeholder*="Tìm thuốc"]').fill(tenThuoc.slice(0, 12));
  await p.waitForTimeout(2000);
  await p.locator("li").filter({ hasText: tenThuoc.slice(0, 12) }).first()
    .locator("button", { hasText: /^Thêm$/ }).click();
  await p.waitForTimeout(2500);
  const viTri = await p.locator('[data-testid="vi-tri-lay"]').first().innerText().catch(() => "");
  const quayThayNgay = /\//.test(viTri) && /lô/i.test(viTri);

  await p.screenshot({ path: `${OUT}/${ten}-2-quay.png`, fullPage: true });

  const dat = khongDoiPO && hienDaNhan && giuThuoc && giuO && quayThayNgay && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  không đòi đơn mua hàng: ${khongDoiPO ? "✓" : "🔴"} · hiện dòng vừa nhận: ${hienDaNhan ? "✓" : "🔴"}`);
  console.log(`  giữ lại Thuốc: ${giuThuoc ? "✓" : "🔴"} · giữ lại Ô: ${giuO ? "✓" : "🔴"}`);
  console.log(`  quầy thấy chỗ lấy NGAY: ${quayThayNgay ? "✓" : "🔴"} · "${viTri.slice(0, 80)}"`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Nhập nhanh: không cần PO, gắn ô ngay, quầy thấy liền." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
