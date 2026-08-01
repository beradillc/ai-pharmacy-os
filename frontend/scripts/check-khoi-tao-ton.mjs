/**
 * Khởi tạo tồn kho, nhập theo kệ (BERAS V2 Phase 9-10).
 *
 * 🔴 NHÓM GHI — ghi tồn kho thật vào ô thật. Chỉ chạy khi gọi `--all`.
 *
 * Đo đúng ba mệnh đề, và mệnh đề thứ ba mới là lý do màn này tồn tại:
 *
 *   1. chọn ô một lần rồi **ô ở lại** — sau khi ghi xong một mặt hàng, đường dẫn ô vẫn
 *      hiện nguyên trên đầu màn, không quay về ô select rỗng;
 *   2. ghi xong thì **phần mặt hàng trống trở lại** (thuốc/lô/HSD/số lượng) — mặt hàng kế
 *      tiếp trong cùng ô là mặt hàng KHÁC, giữ lại cái cũ là mời nhập trùng;
 *   3. hàng vừa đếm **thật sự vào đúng ô đó** — kiểm bằng cách sang Sơ đồ kho mở ô ra xem.
 *
 * Mệnh đề 3 là thứ không lớp nào khác chứng minh được: 1 và 2 chỉ nói về trạng thái trong
 * trình duyệt. Một màn giữ ô rất đẹp mà gửi `location_id` rỗng lên máy chủ vẫn xanh cả 1
 * lẫn 2.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/khoi-tao-ton";
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

  // ① Ô riêng cho lượt này — cổng phải tự cô lập khỏi dữ liệu nó để lại lần trước
  //    (bài học 31/07: cổng sơ đồ kho đỏ lần hai vì đúng lý do này).
  const khoMa = `K${ten[0].toUpperCase()}${N}`;
  const oMa = `I${N}`;
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

  // ② Vào màn khởi tạo, chọn ô một lần.
  await p.goto(`${BASE}/khoi-tao-ton`, { waitUntil: "load" }); await p.waitForTimeout(3000);
  // `selectOption` không nhận RegExp cho label — lấy VALUE từ DOM.
  const oValue = await p.locator('select[aria-label="Chọn ô đang đếm"] option')
    .filter({ hasText: `${khoMa}/${oMa}` }).first().getAttribute("value");
  await p.selectOption('select[aria-label="Chọn ô đang đếm"]', oValue);
  await p.locator("button", { hasText: /^Bắt đầu đếm ô này$/ }).click();
  await p.waitForTimeout(800);

  await p.screenshot({ path: `${OUT}/${ten}-1-chon-o.png`, fullPage: true });

  // ③ Đếm HAI mặt hàng liên tiếp. Một mặt hàng không chứng minh được gì về mệnh đề ①:
  //    ô chỉ có cơ hội tuột đi SAU lần ghi đầu tiên.
  const dsThuoc = await p.locator('select[aria-label="Chọn thuốc"] option').evaluateAll(
    (os) => os.filter((o) => o.value).slice(0, 2).map((o) => ({ v: o.value, t: o.textContent.trim() })),
  );
  const hsd = new Date(Date.now() + 400 * 86400e3).toISOString().slice(0, 10);
  for (const [i, t] of dsThuoc.entries()) {
    await p.selectOption('select[aria-label="Chọn thuốc"]', t.v);
    await p.locator('input[aria-label="Số lượng đếm được"]').fill(String(3 + i));
    await p.locator('input[aria-label="Số lô"]').fill(`KT${N}-${i}`);
    await p.locator('input[aria-label="Hạn dùng"]').fill(hsd);
    await p.locator("button", { hasText: /^Ghi vào ô này$/ }).click();
    await p.waitForTimeout(2500);
  }

  // Mệnh đề ①: ô còn nguyên trên đầu màn sau khi đã ghi.
  const bangO = await p.locator('[data-testid="o-dang-dem"]').innerText().catch(() => "");
  const oOLai = bangO.includes(`${khoMa}/${oMa}`);

  // Mệnh đề ②: phần mặt hàng đã trống trở lại.
  const conSot = await p.evaluate(() => {
    const g = (s) => document.querySelector(s)?.value ?? "";
    return {
      thuoc: g('select[aria-label="Chọn thuốc"]'),
      sl: g('input[aria-label="Số lượng đếm được"]'),
      lo: g('input[aria-label="Số lô"]'),
      hsd: g('input[aria-label="Hạn dùng"]'),
    };
  });
  const daDonSach = Object.values(conSot).every((v) => v === "");

  const daDem = await p.locator('[data-testid="da-dem"] li').count();

  await p.screenshot({ path: `${OUT}/${ten}-2-da-dem.png`, fullPage: true });

  // ④ Mệnh đề ③ — sang Sơ đồ kho, mở ô ra xem hàng có thật ở đó không.
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  await cayNay().locator("li").filter({ hasText: oMa }).last()
    .locator("button", { hasText: /^Xem hàng$/ }).click();
  await p.waitForTimeout(2000);
  const trongO = await p.locator('dialog[aria-label^="Hàng trong"]').innerText().catch(() => "");
  // Đúng hai lô của lượt này, đúng số lượng đã đếm.
  const vaoDungO =
    trongO.includes(`KT${N}-0`) && trongO.includes(`KT${N}-1`) &&
    /\b3\b/.test(trongO) && /\b4\b/.test(trongO);

  await p.screenshot({ path: `${OUT}/${ten}-3-trong-o.png`, fullPage: true });

  const dat = oOLai && daDonSach && daDem === dsThuoc.length && vaoDungO && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  ① ô ${khoMa}/${oMa} Ở LẠI sau khi ghi: ${oOLai ? "✓" : "🔴"} · "${bangO.replace(/\n/g, " ").slice(0, 70)}"`);
  console.log(`  ② phần mặt hàng trống trở lại: ${daDonSach ? "✓" : "🔴"} · ${JSON.stringify(conSot)}`);
  console.log(`  ③ hàng vào ĐÚNG ô đó: ${vaoDungO ? "✓" : "🔴"} · "${trongO.replace(/\n/g, " ").slice(0, 90)}"`);
  console.log(`  đã đếm ${daDem}/${dsThuoc.length} mặt hàng · lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Chọn ô một lần → đếm nhiều mặt hàng → hàng vào đúng ô." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
