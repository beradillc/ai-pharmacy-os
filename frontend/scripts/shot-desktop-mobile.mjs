/**
 * Chụp mọi màn ở HAI khổ — desktop và khung điện thoại — rồi **ĐO**, không chỉ nhìn.
 *
 * 🔴 Kỷ luật #15 nói rõ hai điều mà script này làm đúng theo:
 *  1. *"Ảnh chụp là cổng, không phải trang trí"* — 29/07 ảnh chụp bắt được lỗi cột định
 *     danh trượt khỏi màn hình ở **5/5 bảng**, không cổng tự động nào thấy.
 *  2. *"Sau khi nhìn ảnh, VẪN PHẢI ĐO"* — nên mỗi màn đều đo `scrollWidth` vs
 *     `clientWidth`, đếm ký tự thân trang (bỏ `<script>`), và tìm phần tử tràn ra ngoài.
 *
 * Và *"phải đo cả chính phép đo"*: một kết quả tự mâu thuẫn (0 ký tự mà vẫn có tiêu đề)
 * luôn là lỗi phép đo — script in đủ số liệu thô để nhận ra chuyện đó.
 *
 * Chạy:  BASE_URL=http://localhost:3000 EMAIL=... PASSWORD=... \
 *          node scripts/shot-desktop-mobile.mjs
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";
import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();

const OUT = process.env.OUT_DIR ?? "/tmp/shots";

/** Khổ desktop thật + khung iPhone 13. Không dùng `devices[]` để hai lượt chỉ khác đúng
 *  kích thước — nếu khác cả user-agent thì không quy được lỗi về khổ màn hình. */
const KHO = [
  { ten: "desktop", width: 1440, height: 900, mobile: false },
  { ten: "mobile", width: 390, height: 844, mobile: true },
];

const MAN = [
  ["/", "POS-ban-hang"],
  ["/hoa-don", "Hoa-don"],
  ["/khach-hang", "Khach-hang"],
  ["/ton-kho", "Ton-kho"],
  ["/bang-dieu-hanh", "Bang-dieu-hanh"],
  ["/de-xuat-dat-hang", "De-xuat-dat-hang"],
];

mkdirSync(OUT, { recursive: true });
let hong = 0;
const bang = [];

for (const kho of KHO) {
  const browser = await firefox.launch();
  const ctx = await browser.newContext({
    viewport: { width: kho.width, height: kho.height },
    isMobile: kho.mobile,
    hasTouch: kho.mobile,
    deviceScaleFactor: 2, // phóng 2× — kỷ luật #15: đừng kết luận từ ảnh thu nhỏ
  });
  const page = await ctx.newPage();

  // --- đăng nhập qua đúng màn người dùng gõ, không tiêm token ---
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  await page.fill('input[type="email"], input[name="email"]', EMAIL);
  await page.fill('input[type="password"], input[name="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(4000);
  const sauDangNhap = new URL(page.url()).pathname;
  if (sauDangNhap.startsWith("/login")) {
    console.log(`🔴 ${kho.ten}: ĐĂNG NHẬP HỎNG — vẫn ở ${sauDangNhap}`);
    await page.screenshot({ path: `${OUT}/${kho.ten}-00-login-HONG.png`, fullPage: true });
    hong++;
    await browser.close();
    continue;
  }

  for (const [duongDan, ten] of MAN) {
    await page.goto(`${BASE}${duongDan}`, { waitUntil: "load" });
    await page.waitForTimeout(3000);

    const do_ = await page.evaluate(() => {
      const b = document.body;
      const kyTu = b.innerHTML.replace(/<script[\s\S]*?<\/script>/g, "").trim().length;
      const chu = (b.innerText || "").trim().length;
      // Phần tử nào tràn khỏi khung nhìn theo chiều ngang — đây là lỗi 29/07 đã bắt
      const tran = [...document.querySelectorAll("*")]
        .map((e) => ({ e, r: e.getBoundingClientRect() }))
        .filter(({ r }) => r.width > 0 && r.right > window.innerWidth + 1)
        .map(({ e, r }) => `${e.tagName.toLowerCase()}${e.className ? "." + String(e.className).split(" ")[0] : ""} +${Math.round(r.right - window.innerWidth)}px`);
      return {
        kyTu,
        chu,
        cuonNgang: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        tran: [...new Set(tran)].slice(0, 4),
      };
    });

    const file = `${OUT}/${kho.ten}-${ten}.png`;
    await page.screenshot({ path: file, fullPage: true });

    // Trang trắng = có payload Next nhưng không có chữ nào cho người đọc.
    const trang = do_.chu < 40;
    const loi = trang || do_.cuonNgang;
    if (loi) hong++;
    bang.push({
      kho: kho.ten,
      man: ten,
      chu: do_.chu,
      cuon: do_.cuonNgang ? `${do_.scrollWidth}>${do_.clientWidth}` : "—",
      tran: do_.tran.join(" · ") || "—",
      ket: trang ? "🔴 TRẮNG" : do_.cuonNgang ? "🔴 CUỘN NGANG" : "✓",
    });
  }
  await browser.close();
}

console.log("\n| Khổ | Màn | Ký tự chữ | Cuộn ngang | Phần tử tràn | Kết |");
console.log("|---|---|---|---|---|---|");
for (const r of bang) {
  console.log(`| ${r.kho} | ${r.man} | ${r.chu} | ${r.cuon} | ${r.tran} | ${r.ket} |`);
}
console.log(`\nẢnh: ${OUT}`);
console.log(hong === 0 ? "✅ Không màn nào trắng, không màn nào cuộn ngang." : `🔴 ${hong} vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
