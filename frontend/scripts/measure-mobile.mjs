/**
 * Đo hai thứ mà **ảnh chụp không trả lời được**, ở khung điện thoại.
 *
 * 🔴 Vì sao phải có script này thay vì nhìn ảnh: ảnh `fullPage` vẽ phần tử
 * `position: fixed` đúng **một lần** ở vị trí cố định của nó trong tấm ảnh dài, nên
 * thanh điều hướng dưới đáy **trông như đang đè lên giữa bảng**. Đó là hiện vật của
 * cách chụp, không phải lỗi giao diện. Kỷ luật #15 đã ghi hai lần suýt sửa thứ không
 * hỏng vì tin mắt nhìn ảnh — script này tránh lần thứ ba.
 *
 * Hai phép đo:
 *  1. **Thanh điều hướng có che mất gì không** — cuộn xuống đáy thật, so hình chữ nhật
 *     của thanh với hình chữ nhật của phần tử cuối cùng có ý nghĩa (phân trang).
 *  2. **Cột định danh có đọc được ở trạng thái nghỉ không** — `scrollLeft = 0`, cột đầu
 *     của bảng phải nằm trọn trong khung nhìn. Đây đúng là lỗi ảnh chụp bắt được 29/07
 *     ở 5/5 bảng; bảng cuộn ngang được là chấp nhận được, cột TÊN bị đẩy khuất thì không.
 */
import { firefox } from "playwright-core";
import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();


const MAN = [
  ["/khach-hang", "Khach-hang"],
  ["/ton-kho", "Ton-kho"],
  ["/hoa-don", "Hoa-don"],
];

const browser = await firefox.launch();
const ctx = await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});
const page = await ctx.newPage();

await page.goto(`${BASE}/login`, { waitUntil: "load" });
await page.waitForTimeout(1500);
await page.fill('input[type="email"], input[name="email"]', EMAIL);
await page.fill('input[type="password"], input[name="password"]', PASSWORD);
await page.click('button[type="submit"]');
await page.waitForTimeout(4000);

let hong = 0;
const bang = [];

for (const [duongDan, ten] of MAN) {
  await page.goto(`${BASE}${duongDan}`, { waitUntil: "load" });
  await page.waitForTimeout(2500);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(800);

  const r = await page.evaluate(() => {
    const vh = window.innerHeight;
    const vw = window.innerWidth;

    // Thanh điều hướng: phần tử `fixed` bám đáy khung nhìn.
    const nav = [...document.querySelectorAll("nav, [class*='bottomNav'], [class*='tabBar']")]
      .map((e) => ({ e, r: e.getBoundingClientRect(), pos: getComputedStyle(e).position }))
      .filter(({ r, pos }) => pos === "fixed" && r.height > 0 && r.bottom > vh - 5)
      .sort((a, b) => b.r.height - a.r.height)[0];
    const navTop = nav ? nav.r.top : null;

    // Phần tử cuối có ý nghĩa: khối phân trang, hoặc dòng cuối của bảng.
    const cuoi =
      [...document.querySelectorAll("*")]
        .filter((e) => /Trang\s*\d/.test(e.textContent ?? "") && e.children.length < 6)
        .pop() ?? document.querySelector("tbody tr:last-child");
    const cuoiRect = cuoi ? cuoi.getBoundingClientRect() : null;
    const biChe =
      navTop !== null && cuoiRect !== null && cuoiRect.bottom > navTop && cuoiRect.top < vh;

    // Cột định danh ở trạng thái nghỉ.
    const table = document.querySelector("table");
    const boc = table?.closest("[style*='overflow'], [class*='scroll'], [class*='wrap']");
    if (boc) boc.scrollLeft = 0;
    const o1 = table?.querySelector("thead th");
    const oRect = o1 ? o1.getBoundingClientRect() : null;
    const cotDauDocDuoc = oRect ? oRect.left >= -1 && oRect.right <= vw + 1 : null;

    return {
      coNav: !!nav,
      navTop: navTop === null ? null : Math.round(navTop),
      vh,
      cuoiText: (cuoi?.textContent ?? "").trim().slice(0, 30),
      cuoiBottom: cuoiRect ? Math.round(cuoiRect.bottom) : null,
      biChe,
      cotDau: o1?.textContent?.trim() ?? null,
      cotDauRight: oRect ? Math.round(oRect.right) : null,
      cotDauDocDuoc,
      vw,
    };
  });

  const ketNav = r.biChe ? "🔴 BỊ CHE" : r.coNav ? "✓" : "(không có thanh)";
  const ketCot = r.cotDau === null ? "(không có bảng)" : r.cotDauDocDuoc ? "✓" : "🔴 KHUẤT";
  if (r.biChe || r.cotDauDocDuoc === false) hong++;
  bang.push({ ten, r, ketNav, ketCot });
}

console.log("\n### 1. Thanh điều hướng có che mất phần tử cuối không (đã cuộn xuống đáy)\n");
console.log("| Màn | Thanh ở y | Đáy phần tử cuối | Phần tử cuối | Kết |");
console.log("|---|---|---|---|---|");
for (const b of bang) {
  console.log(
    `| ${b.ten} | ${b.r.navTop ?? "—"} | ${b.r.cuoiBottom ?? "—"} | ${b.r.cuoiText || "—"} | ${b.ketNav} |`,
  );
}
console.log("\n### 2. Cột định danh ở trạng thái nghỉ (scrollLeft = 0, khung rộng 390)\n");
console.log("| Màn | Cột đầu | Mép phải | Kết |");
console.log("|---|---|---|---|");
for (const b of bang) {
  console.log(`| ${b.ten} | ${b.r.cotDau ?? "—"} | ${b.r.cotDauRight ?? "—"} | ${b.ketCot} |`);
}

await browser.close();
console.log(hong === 0 ? "\n✅ Không có gì bị che, cột định danh đọc được ở cả 3 màn." : `\n🔴 ${hong} vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
