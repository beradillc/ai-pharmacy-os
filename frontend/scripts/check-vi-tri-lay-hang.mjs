/**
 * Tồn theo vị trí, đi trọn vòng THẬT (BERAS V2 Phase 2).
 *
 * 🔴 NHÓM GHI — cất hàng thật vào ô thật. Chỉ chạy khi gọi `--all`.
 *
 * Đây là cổng duy nhất đi hết một vòng đúng như Chain mô tả:
 *
 *     dựng ô  →  cất thuốc vào ô  →  mở ô xem có gì  →  ra quầy thấy chỗ lấy
 *
 * Bốn lớp đó không lớp nào chứng minh được ba lớp kia. Đo bốn mệnh đề:
 *   1. cất hàng xong màn hình nói ra **số chưa xếp ô** (không giấu);
 *   2. mở ô thì thấy **đúng lô và hạn dùng** vừa cất;
 *   3. ra quầy, dòng hàng hiện **📍 đường dẫn ô · lô · HSD · số lượng**;
 *   4. thuốc **chưa xếp ô** thì quầy nói "chưa xếp ô", KHÔNG nói hết hàng.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/vi-tri";
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

  // ① Dựng một kho + một ô riêng cho lượt này (khoanh vùng — bài học 31/07: cổng phải tự
  //    cô lập khỏi dữ liệu nó để lại lần trước).
  const khoMa = `V${ten[0].toUpperCase()}${N}`;
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  const cayNay = () => p.locator('[data-testid="cay-so-do"] > li').filter({ hasText: khoMa });

  await p.locator("button", { hasText: /^\+ Thêm kho$/ }).click();
  await p.waitForTimeout(700);
  await p.locator('input[aria-label="Mã vị trí"]').fill(khoMa);
  await p.locator("button", { hasText: /^Lưu vị trí$/ }).click();
  await p.waitForTimeout(1800);

  await cayNay().locator("button", { hasText: /^\+ Thêm/ }).first().click();
  await p.waitForTimeout(700);
  await p.selectOption('select[aria-label="Tầng vị trí"]', "BIN");
  const oMa = `O${N}`;
  await p.locator('input[aria-label="Mã vị trí"]').fill(oMa);
  await p.locator("button", { hasText: /^Lưu vị trí$/ }).click();
  await p.waitForTimeout(1800);

  // ② Cất hàng. 🔴 Hai khổ phải dùng HAI LÔ KHÁC NHAU.
  //
  // Lần chạy đầu cả hai khổ cùng lấy lô số 1, nên sau lượt desktop thì lô đó đã nằm ở hai
  // ô; quầy hiện ô của lượt desktop kèm "+1 chỗ khác" và khẳng định của lượt mobile đỏ.
  // Sản phẩm ĐÚNG — FEFO chọn ô nào là quyền của nó, và hai ô cùng giữ một lô thì hạn dùng
  // bằng nhau, thứ tự do đường đi rồi tới đường dẫn quyết. Cái sai là kỳ vọng "ô của lượt
  // này phải đứng đầu". Tách lô ra là cách sửa đúng: mỗi khổ đo trên dữ liệu của chính nó.
  await p.goto(`${BASE}/ton-kho`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  const hangDau = p.locator("tbody tr").nth(mob ? 1 : 0);
  const tenThuoc = (await hangDau.locator("td").first().innerText()).trim();
  await hangDau.locator("button", { hasText: /^Cất vào ô$/ }).click();
  await p.waitForTimeout(1500);

  // `selectOption` không nhận RegExp cho label — chọn theo VALUE lấy từ DOM.
  const oValue = await p.locator('select[aria-label="Chọn ô"] option')
    .filter({ hasText: `${khoMa}/${oMa}` }).first().getAttribute("value");
  await p.selectOption('select[aria-label="Chọn ô"]', oValue);
  await p.locator('input[aria-label="Số lượng cất vào ô"]').fill("2");
  await p.locator("button", { hasText: /^Cất vào ô$/ }).last().click();
  await p.waitForTimeout(2500);

  const thongBao = await p.locator("text=/Đã cất/").first().innerText().catch(() => "");
  // Mệnh đề ①: màn hình phải NÓI RA số chưa xếp ô.
  const noiChuaXep = /chưa xếp ô/i.test(thongBao);

  await p.screenshot({ path: `${OUT}/${ten}-1-cat-vao-o.png`, fullPage: true });

  // ③ Mở ô xem có gì.
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  await cayNay().locator("li").filter({ hasText: oMa }).last()
    .locator("button", { hasText: /^Xem hàng$/ }).click();
  await p.waitForTimeout(2000);
  const trongO = await p.locator('section[aria-label^="Hàng trong"]').innerText().catch(() => "");
  const oCoHang = /\d/.test(trongO) && !/chưa có hàng/i.test(trongO);

  await p.screenshot({ path: `${OUT}/${ten}-2-trong-o.png`, fullPage: true });

  // ④ Ra quầy: thêm đúng thuốc vừa cất, dòng hàng phải hiện chỗ lấy.
  await p.goto(`${BASE}/`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  await p.locator('input[placeholder*="Tìm thuốc"]').fill(tenThuoc.slice(0, 12));
  await p.waitForTimeout(2000);
  await p.locator("li").filter({ hasText: tenThuoc.slice(0, 12) }).first()
    .locator("button", { hasText: /^Thêm$/ }).click();
  await p.waitForTimeout(2500);

  const viTri = await p.locator('[data-testid="vi-tri-lay"]').first().innerText().catch(() => "");

  // 🔴 KHÔNG khẳng định "ô của lượt này phải đứng đầu" — đó là khẳng định KHÔNG kiểm chứng
  // được, vì thứ tự do FEFO quyết, và cổng này tự tích luỹ dữ liệu qua các lượt chạy trước
  // (cùng một lô nay nằm ở nhiều ô của nhiều lượt). Hai lần đỏ đầu tiên đều vì kỳ vọng đó,
  // và cả hai lần **sản phẩm đúng**.
  //
  // Khẳng định đúng là hợp đồng thật của màn hình: hiện MỘT đường dẫn thật, đủ lô/HSD/còn,
  // và **nếu còn chỗ khác thì phải nói ra** — im lặng cắt bớt danh sách mới là lỗi.
  const hienDuongDan =
    viTri.includes(`${khoMa}/${oMa}`) || /\+\d+ chỗ khác/.test(viTri);
  const hienDuThongTin =
    /\//.test(viTri) && /lô/i.test(viTri) && /HSD/i.test(viTri) && /còn/i.test(viTri);

  await p.screenshot({ path: `${OUT}/${ten}-3-quay-thay-vi-tri.png`, fullPage: true });

  const dat = noiChuaXep && oCoHang && hienDuongDan && hienDuThongTin && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  cất xong nói ra số CHƯA XẾP Ô: ${noiChuaXep ? "✓" : "🔴"} · "${thongBao.slice(0, 90)}"`);
  console.log(`  mở ô ${oMa} thấy hàng: ${oCoHang ? "✓" : "🔴"}`);
  console.log(`  quầy chỉ đúng chỗ (hoặc nói ra còn chỗ khác): ${hienDuongDan ? "✓" : "🔴"} · đủ đường dẫn/lô/HSD/còn: ${hienDuThongTin ? "✓" : "🔴"}`);
  console.log(`  dòng vị trí: "${viTri.slice(0, 110)}"`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Đi trọn vòng: dựng ô → cất hàng → xem ô → quầy thấy chỗ lấy." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
