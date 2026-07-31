/**
 * Màn Sơ đồ kho (BERAS V2 Phase 1).
 *
 * 🔴 NHÓM GHI — tạo vị trí thật. Không nằm trong nhóm đọc-thuần; chỉ chạy khi gọi `--all`.
 *
 * Vì sao phải ghi mới đo được: màn này **chỉ có ý nghĩa khi có cây**. Chạy đọc-thuần trên
 * một kho rỗng sẽ xanh mà không chứng minh được gì — đúng cái bẫy "cổng xanh với 0 dòng"
 * đã gặp ở màn Lưu trữ hôm nay.
 *
 * Đo bốn mệnh đề, không phải "màn có hiện":
 *   1. tạo được **Kho → Kệ** (BỎ TẦNG Khu) — nhà thuốc nhỏ phải làm được;
 *   2. trùng mã ở **hai cha khác nhau** đi qua được (ô 01 dưới kệ A và dưới kệ B);
 *   3. cây hiện **đúng thứ tự đi lấy hàng**, không phải bảng chữ cái;
 *   4. bấm Ngừng thì chỗ đó biến khỏi danh sách mặc định.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/so-do-kho";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

/** Hậu tố duy nhất để chạy lại nhiều lần không đụng mã cũ. */
const N = Date.now().toString().slice(-5);

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
  await p.goto(`${BASE}/so-do-kho`, { waitUntil: "load" }); await p.waitForTimeout(3000);

  // KHÔNG bọc `.catch()` quanh các lượt bấm dựng bối cảnh: bấm trượt phải nổ ngay tại dòng
  // đó, đừng đi tiếp rồi đo một màn hình không ở trạng thái mình tưởng (bài học 31/07).
  const luu = async ({ ma, ten: nhan, thuTu }) => {
    await p.locator('input[aria-label="Mã vị trí"]').fill(ma);
    if (nhan) await p.locator('input[aria-label="Tên vị trí"]').fill(nhan);
    if (thuTu !== undefined) {
      await p.locator('input[aria-label="Thứ tự đi lấy hàng"]').fill(String(thuTu));
    }
    await p.locator("button", { hasText: /^Lưu vị trí$/ }).click();
    await p.waitForTimeout(1800);
  };

  // ① Kho gốc, rồi Kệ THẲNG trong Kho — bỏ tầng Khu.
  const kho = `K${ten[0].toUpperCase()}${N}`;
  await p.locator("button", { hasText: /^\+ Thêm kho$/ }).click();
  await p.waitForTimeout(800);
  await luu({ ma: kho, ten: "Kho thử" });

  // 🔴 MỌI locator sau đây phải khoanh trong ĐÚNG cây của lượt chạy này. Lượt trước để lại
  // kho cũ cũng có kệ "AA1"/"ZZ9", nên tìm toàn trang là tìm nhầm sang cây khác — đó là lý
  // do lần chạy thứ hai đỏ với 0/2 trong khi sản phẩm không hỏng gì. Cổng phải tự cô lập
  // khỏi dữ liệu nó để lại lần trước, đừng giả định CSDL sạch.
  const cayNay = () => p.locator('[data-testid="cay-so-do"] > li').filter({ hasText: kho });
  const nut = (ma) => cayNay().locator("li").filter({ hasText: ma }).last();

  await cayNay().locator("button", { hasText: /^\+ Thêm/ }).first().click();
  await p.waitForTimeout(800);
  // Danh sách tầng con dưới Kho phải có Kệ — bằng chứng "bỏ tầng thì được".
  const coTangKe = await p.locator('select[aria-label="Tầng vị trí"] option').allInnerTexts();
  await p.selectOption('select[aria-label="Tầng vị trí"]', "SHELF");
  await luu({ ma: "ZZ9", ten: "Kệ đi sau", thuTu: 9 });

  await cayNay().locator("button", { hasText: /^\+ Thêm/ }).first().click();
  await p.waitForTimeout(800);
  await p.selectOption('select[aria-label="Tầng vị trí"]', "SHELF");
  await luu({ ma: "AA1", ten: "Kệ đi trước", thuTu: 1 });

  // ② Ô "01" dưới CẢ HAI kệ — trùng mã ở hai cha khác nhau phải hợp lệ.
  // 🔴 `.last()` chứ KHÔNG `.first()`: cây lồng nhau nên `li` chứa chữ "ZZ9" gồm cả `li`
  // của Kho ở ngoài cùng. Lấy `.first()` là lấy nhánh gốc, và nút "+ Thêm Ô" tìm thấy bên
  // trong nó là nút của kệ ĐẦU TIÊN — nên hai lượt bấm rơi vào cùng một kệ và lượt hai bị
  // 409. Lần chạy đầu cổng đỏ đúng vì lý do này: hỏng là PHÉP ĐO, không phải sản phẩm
  // (backend đã có test riêng chứng minh trùng mã ở hai cha khác nhau là hợp lệ).
  // Thứ tự locator là thứ tự tài liệu, nên nút sâu nhất là nút cuối cùng.
  for (const ke of ["AA1", "ZZ9"]) {
    await nut(ke).locator("button", { hasText: /^\+ Thêm Ô$/ }).first().click();
    await p.waitForTimeout(800);
    await luu({ ma: "01" });
  }

  await p.screenshot({ path: `${OUT}/${ten}-1-cay.png`, fullPage: true });

  const doc = await p.evaluate((khoMa) => {
    const goc = [...document.querySelectorAll('[data-testid="cay-so-do"] > li')]
      .find((li) => li.innerText.includes(khoMa));
    if (!goc) return null;
    const ma = [...goc.querySelectorAll("strong")].map((x) => x.textContent?.trim());
    return { ma, soO01: ma.filter((m) => m === "01").length };
  }, kho);

  // ③ Thứ tự: Kệ AA1 (đi thứ 1) phải đứng TRƯỚC ZZ9 (đi thứ 9) — ngược bảng chữ cái.
  const iAA1 = doc?.ma.indexOf("AA1") ?? -1;
  const iZZ9 = doc?.ma.indexOf("ZZ9") ?? -1;
  const dungThuTu = iAA1 > -1 && iZZ9 > -1 && iAA1 < iZZ9;

  // ④ Ngừng kệ ZZ9 (ô con của nó vẫn còn ⇒ phải bị TỪ CHỐI, rồi ngừng ô trước).
  await nut("ZZ9").locator("button", { hasText: /^Ngừng$/ }).first().click();
  await p.waitForTimeout(2000);
  const vanConZZ9 = (await cayNay().innerText()).includes("ZZ9");

  await p.screenshot({ path: `${OUT}/${ten}-2-sau-khi-ngung.png`, fullPage: true });

  const dat = coTangKe.some((t) => /Kệ/.test(t)) && doc !== null && doc.soO01 === 2 &&
              dungThuTu && vanConZZ9 && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  bỏ tầng Khu — dưới Kho chọn được Kệ: ${coTangKe.some((t) => /Kệ/.test(t)) ? "✓" : "🔴"} (${coTangKe.join(", ")})`);
  console.log(`  ô "01" dưới HAI kệ khác nhau: ${doc?.soO01 ?? 0}/2 ${doc?.soO01 === 2 ? "✓" : "🔴"}`);
  console.log(`  thứ tự đi lấy hàng (AA1 đi thứ 1 trước ZZ9 đi thứ 9): ${dungThuTu ? "✓" : "🔴"} · thứ tự thấy: ${doc?.ma.join(" → ")}`);
  console.log(`  ngừng kệ còn ô con ⇒ BỊ TỪ CHỐI, kệ vẫn hiện: ${vanConZZ9 ? "✓" : "🔴"}`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Sơ đồ kho dựng đúng thiết kế." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
