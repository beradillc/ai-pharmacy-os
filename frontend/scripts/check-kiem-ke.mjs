/**
 * Kiểm kê theo ô, đi trọn vòng THẬT (BERAS V2 Phase 11).
 *
 * 🔴 NHÓM GHI — mở phiên thật, duyệt thật, **đổi tồn kho thật**. Chỉ chạy khi gọi `--all`.
 *
 * Bốn mệnh đề. Mệnh đề ② là lý do cả Phase 11 tồn tại:
 *
 *   1. đếm lệch thì màn hình **nói ra con số lệch**, không im lặng;
 *   2. **nộp KHÔNG đụng tồn kho** — chỉ duyệt mới đụng;
 *   3. duyệt xong tồn kho ở ô **bằng đúng số đã đếm**;
 *   4. người đếm tự duyệt phiếu mình thì màn hình **nói ra là cùng một người**.
 *
 * ② là chỗ dễ code sai nhất và cũng là chỗ không lớp nào khác canh: một màn hình gọi
 * `approve` ngay sau `submit` sẽ xanh cả ①, ③ và ④.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/kiem-ke";
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

  // ① Ô riêng cho lượt này + một lô đã cất vào, qua màn Khởi tạo tồn (dùng lại đường thật).
  const khoMa = `C${ten[0].toUpperCase()}${N}`;
  const oMa = `B${N}`;
  const loMa = `KK${N}`;
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
  await p.locator('input[aria-label="Mã vị trí"]').fill(oMa);
  await p.locator("button", { hasText: /^Lưu vị trí$/ }).click();
  await p.waitForTimeout(1800);

  await p.goto(`${BASE}/khoi-tao-ton`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  const oValue = await p.locator('select[aria-label="Chọn ô đang đếm"] option')
    .filter({ hasText: `${khoMa}/${oMa}` }).first().getAttribute("value");
  await p.selectOption('select[aria-label="Chọn ô đang đếm"]', oValue);
  await p.locator("button", { hasText: /^Bắt đầu đếm ô này$/ }).click();
  await p.waitForTimeout(800);
  const thuoc = await p.locator('select[aria-label="Chọn thuốc"] option').evaluateAll(
    (os) => os.filter((o) => o.value)[0]?.value,
  );
  await p.selectOption('select[aria-label="Chọn thuốc"]', thuoc);
  await p.locator('input[aria-label="Số lượng đếm được"]').fill("10");
  await p.locator('input[aria-label="Số lô"]').fill(loMa);
  await p.locator('input[aria-label="Hạn dùng"]')
    .fill(new Date(Date.now() + 400 * 86400e3).toISOString().slice(0, 10));
  await p.locator("button", { hasText: /^Ghi vào ô này$/ }).click();
  await p.waitForTimeout(2500);

  // ② Kiểm kê: đếm 7 trong khi sổ ghi 10.
  await p.goto(`${BASE}/kiem-ke`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  const oKiemKe = await p.locator('select[aria-label="Chọn ô để kiểm kê"] option')
    .filter({ hasText: `${khoMa}/${oMa}` }).first().getAttribute("value");
  await p.selectOption('select[aria-label="Chọn ô để kiểm kê"]', oKiemKe);
  await p.locator("button", { hasText: /^Bắt đầu kiểm ô này$/ }).click();
  await p.waitForTimeout(2500);

  const oNhap = p.locator(`input[aria-label="Đếm được lô ${loMa}"]`);
  await oNhap.fill("7");
  await oNhap.blur();
  await p.waitForTimeout(2000);

  await p.locator("button", { hasText: /^Nộp phiên$/ }).click();
  await p.waitForTimeout(2500);

  const bangSauNop = await p.locator('[data-testid="bang-dem"]').innerText();
  // Mệnh đề ①: màn hình nói ra con số lệch (−3), không im lặng.
  const noiRaLech = /-3/.test(bangSauNop);

  await p.screenshot({ path: `${OUT}/${ten}-1-da-nop.png`, fullPage: true });

  // Mệnh đề ②: NỘP RỒI mà tồn ở ô VẪN là 10 — kiểm qua Sơ đồ kho, một đường khác hẳn.
  const tonSauNop = await donSoTrongO(p, BASE, khoMa, oMa, loMa);
  const nopChuaDungTon = tonSauNop === 10;

  // ③ Duyệt.
  await p.goto(`${BASE}/kiem-ke`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  await p.locator('[data-testid="ds-phien"] tr').filter({ hasText: `${khoMa}/${oMa}` }).first()
    .locator("button", { hasText: /^Mở$/ }).click();
  await p.waitForTimeout(2500);

  // Mệnh đề ④: người đếm tự duyệt ⇒ phải nói ra "cùng một người".
  await p.locator("button", { hasText: /^Duyệt/ }).click();
  await p.waitForTimeout(3000);
  const chuThich = await p.locator('section[aria-label="Phiên kiểm kê"]').innerText();
  const noiCungMotNguoi = /cùng một người/i.test(chuThich);

  await p.screenshot({ path: `${OUT}/${ten}-2-da-duyet.png`, fullPage: true });

  const tonSauDuyet = await donSoTrongO(p, BASE, khoMa, oMa, loMa);
  const duyetMoiDoiTon = tonSauDuyet === 7;

  const dat = noiRaLech && nopChuaDungTon && duyetMoiDoiTon && noiCungMotNguoi && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  ① nói ra con số lệch (−3): ${noiRaLech ? "✓" : "🔴"}`);
  console.log(`  ② NỘP chưa đụng tồn kho: ${nopChuaDungTon ? "✓" : "🔴"} · ô đang giữ ${tonSauNop} (phải là 10)`);
  console.log(`  ③ DUYỆT mới đổi tồn kho: ${duyetMoiDoiTon ? "✓" : "🔴"} · ô đang giữ ${tonSauDuyet} (phải là 7)`);
  console.log(`  ④ nói ra "cùng một người": ${noiCungMotNguoi ? "✓" : "🔴"}`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Đếm lệch → nộp (tồn giữ nguyên) → duyệt (tồn đổi)." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);

/** Số lượng của MỘT LÔ đang nằm trong ô, đọc từ Sơ đồ kho — đường KHÁC hẳn màn kiểm kê.
 *
 * 🔴 Đọc thẳng ô bảng, KHÔNG cào số bằng regex trên `innerText`. Bản đầu dùng
 * `/(\d+)\s*$/m` và trả về **34946** — đúng hậu tố trong mã lô `KK34946`. Một con số vô
 * lý như vậy luôn là lỗi PHÉP ĐO, không phải lỗi sản phẩm (kỷ luật #15: "phải đo cả chính
 * phép đo"); may là nó vô lý đủ để nhìn ra ngay, chứ nếu nó trả `10` vì lý do sai thì cổng
 * đã xanh mà chẳng chứng minh gì.
 */
async function donSoTrongO(p, BASE, khoMa, oMa, loMa) {
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" });
  await p.waitForTimeout(2500);
  await p.locator('[data-testid="cay-so-do"] > li').filter({ hasText: khoMa })
    .locator("li").filter({ hasText: oMa }).last()
    .locator("button", { hasText: /^Xem hàng$/ }).click();
  await p.waitForTimeout(2000);
  const hang = p.locator('section[aria-label^="Hàng trong"] tbody tr').filter({ hasText: loMa });
  if ((await hang.count()) === 0) return NaN;
  const o = (await hang.first().locator("td").last().innerText()).trim();
  return Number(o.replace(/\./g, "").replace(",", "."));
}
