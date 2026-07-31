/**
 * Nút "Chụp đơn thuốc" ở quầy (Chain giao 2026-07-31).
 *
 * 🔴 ĐỌC THUẦN: chỉ thêm thuốc vào giỏ và đọc trạng thái nút. **Không chọn tệp**, nên
 * không tạo đơn thuốc nào, không ghi ảnh nào. Chạy được cả trên `nt650v2`.
 *
 * Đo cái gì — ba mệnh đề, không phải "nút có tồn tại":
 *   1. giỏ toàn thuốc THƯỜNG  ⇒ khối chụp đơn **không hiện** (nút thừa là nhiễu);
 *   2. giỏ có thuốc KÊ ĐƠN nhưng chưa gắn khách ⇒ hiện lời nhắc, **chưa có nút**;
 *   3. có khách + tên bác sĩ ⇒ ô chọn tệp **bật**, và nó phải mang `capture` để mở
 *      thẳng camera sau trên điện thoại.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/pos-rx";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

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

  const khoiChup = () => p.locator('text=thuốc kê đơn trong giỏ');
  const oChon = () => p.locator('input[aria-label="Chụp đơn thuốc"]');

  // 🔴 KHÔNG bọc `.catch(() => {})` quanh các lượt bấm dựng bối cảnh. Lần chạy đầu tôi có
  // bọc, một locator sai làm cả hai lượt bấm trượt, giỏ rỗng — và cổng báo đỏ về **sản
  // phẩm** trong khi hỏng là **phép đo**. Ảnh chụp mới lộ ra ("Chưa có thuốc trong giỏ").
  // Bấm trượt phải làm cổng ném lỗi ngay tại dòng đó, đừng đi tiếp rồi đo một màn hình
  // không ở trạng thái mình tưởng.
  const themThuoc = async (ten) => {
    await p.locator("li").filter({ hasText: ten }).first()
      .locator("button", { hasText: /^Thêm$/ }).click();
    await p.waitForTimeout(1200);
  };

  // ① Thuốc THƯỜNG (không có nhãn ETC ở hàng) — khối chụp đơn không được hiện.
  await themThuoc("Paracetamol 500mg");
  const hienKhiThuong = await khoiChup().count();

  // ② Thêm một thuốc KÊ ĐƠN — khối hiện, nhưng chưa gắn khách nên chưa có ô chọn tệp.
  await themThuoc("Amoxicillin 500mg");
  const hienKhiEtc = await khoiChup().count();
  const oChonKhiChuaCoKhach = await oChon().count();

  await p.screenshot({ path: `${OUT}/${ten}-1-chua-co-khach.png`, fullPage: true });

  // ③ Gắn khách bằng số điện thoại có sẵn trong CSDL demo, rồi nhập tên bác sĩ.
  const oSdt = p.locator('input[placeholder*="gõ vào đây"]').first();
  await oSdt.fill("0977532099").catch(() => {});
  await p.waitForTimeout(2500);
  await p.locator('input[aria-label="Tên bác sĩ kê đơn"]').fill("BS. Nguyễn Văn A").catch(() => {});
  await p.waitForTimeout(600);

  const coOChon = await oChon().count();
  const batDuoc = coOChon > 0 ? await oChon().isEnabled() : false;
  const coCapture = coOChon > 0 ? await oChon().getAttribute("capture") : null;
  const nhanNut = await p.locator("text=Chụp đơn thuốc").first().innerText().catch(() => "");

  await p.screenshot({ path: `${OUT}/${ten}-2-san-sang-chup.png`, fullPage: true });

  const dat =
    hienKhiThuong === 0 && hienKhiEtc > 0 && oChonKhiChuaCoKhach === 0 &&
    coOChon > 0 && batDuoc && coCapture === "environment" && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  giỏ toàn thuốc thường ⇒ KHÔNG hiện khối chụp: ${hienKhiThuong === 0 ? "✓" : "🔴"}`);
  console.log(`  có thuốc kê đơn ⇒ hiện khối: ${hienKhiEtc > 0 ? "✓" : "🔴"} · chưa có khách ⇒ chưa có ô chọn: ${oChonKhiChuaCoKhach === 0 ? "✓" : "🔴"}`);
  console.log(`  có khách + tên bác sĩ ⇒ ô chọn bật: ${batDuoc ? "✓" : "🔴"} · capture="${coCapture}" ${coCapture === "environment" ? "✓" : "🔴"}`);
  console.log(`  nhãn nút: "${nhanNut}" · lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Nút chụp đơn hiện đúng lúc, mở đúng camera." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
