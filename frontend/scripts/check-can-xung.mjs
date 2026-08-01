/**
 * Cổng **P5** — cân xứng ở CẢ HAI khổ (Chain giao 2026-08-01, lệnh #8 và #9). Nhóm ĐỌC-THUẦN.
 *
 * Ba phép đo, và cả ba sinh từ một lỗi thật đã xảy ra:
 *
 *   ① **Ô nhập không được cao quá `NGUONG_CAO`.** Ngày 01/08 ô nhập giá cao **260px** trên
 *      khổ laptop vì `flex: 0 1 260px` áp cho mọi `.input`, mà `flex-basis` đo theo **trục
 *      chính** — trong hộp dọc nó là CHIỀU CAO. Lần thứ BA cùng một bẫy trong dự án này
 *      (`ô nhập cao 260px` · `khối chữ cao 260px` · lần này lại 260px). Ba lần thì phải có
 *      cổng, không phải có thêm một chú thích.
 *
 *   ② **Chữ không được vỡ từng ký tự.** Bảng danh mục thuốc ở 390px hiện `Alaxa`/`n`/`Ibu`/
 *      `prof` vì hai media query đá nhau. Không cổng nào cũ bắt được: trang không cuộn
 *      ngang, không phần tử nào tràn khung nhìn, `innerText` đọc **đủ chữ**. Đo bằng tỉ lệ
 *      cao/rộng của ô — một ô chứa chữ mà cao gấp nhiều lần bề rộng thì chữ đang vỡ dọc.
 *
 *   ③ **Cỡ chữ thân bài phải đồng nhất.** Chain: *"kích thước chữ tương đồng nhau tại mọi
 *      cửa sổ"*. Đo số cỡ chữ KHÁC NHAU đang dùng cho chữ thường; quá nhiều nghĩa là mỗi
 *      màn một kiểu.
 */
import { firefox } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

/** Ô nhập một dòng cao hơn ngần này là hỏng. 44px là sàn chạm, 96px đã rất rộng tay. */
const NGUONG_CAO = 96;

const MAN = [
  "/",
  "/bang-dieu-hanh",
  "/hoa-don",
  "/khach-hang",
  "/ton-kho",
  "/danh-muc-thuoc",
  "/nhap-nhanh",
  "/khoi-tao-ton",
  "/kiem-ke",
  "/so-do-kho",
  "/don-mua-hang",
  "/de-xuat-dat-hang",
  "/bao-cao",
  "/nhan-vien",
  "/cai-dat",
];

/** Mở một cửa sổ trên màn có cửa sổ — lỗi 260px CHỈ hiện bên trong cửa sổ. */
const MO_CUA_SO = {
  "/danh-muc-thuoc": (p) => p.getByRole("button", { name: /^Sửa giá$/ }).first().click(),
  "/so-do-kho": (p) => p.getByRole("button", { name: /^\+ Thêm kho$/ }).click(),
};

const b = await firefox.launch();
let hong = 0;

for (const [khoTen, w, h, mob] of [
  ["laptop-1440", 1440, 900, false],
  ["mobile-390", 390, 844, true],
]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob });
  const p = await ctx.newPage();

  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4000);

  console.log(`\n──${khoTen}──`);
  const coChu = new Set();

  for (const man of MAN) {
    await p.goto(`${BASE}${man}`, { waitUntil: "load" });
    await p.waitForTimeout(2200);
    if (MO_CUA_SO[man]) {
      await MO_CUA_SO[man](p).catch(() => {});
      await p.waitForTimeout(1600);
    }

    const kq = await p.evaluate((nguong) => {
      const cao = [];
      for (const e of document.querySelectorAll("input:not([type=hidden]), select")) {
        const r = e.getBoundingClientRect();
        if (r.height > nguong) {
          cao.push(`${e.getAttribute("aria-label") ?? e.type}=${Math.round(r.height)}px`);
        }
      }

      // Ô chứa CHỮ mà cao gấp >3 lần bề rộng ⇒ chữ đang vỡ dọc từng ký tự.
      const vo = [];
      for (const e of document.querySelectorAll("td, th")) {
        const r = e.getBoundingClientRect();
        const chu = (e.textContent ?? "").trim();
        if (chu.length < 4 || r.width < 8 || r.height < 8) continue;
        if (r.height > r.width * 3) vo.push(`"${chu.slice(0, 14)}" ${Math.round(r.width)}×${Math.round(r.height)}`);
      }

      const co = new Set();
      for (const e of document.querySelectorAll("p, td, span, label, li")) {
        const r = e.getBoundingClientRect();
        if (r.height === 0 || (e.textContent ?? "").trim().length < 3) continue;
        co.add(getComputedStyle(e).fontSize);
      }
      return { cao: cao.slice(0, 3), vo: vo.slice(0, 3), co: [...co] };
    }, NGUONG_CAO);

    kq.co.forEach((c) => coChu.add(c));
    const dat = kq.cao.length === 0 && kq.vo.length === 0;
    if (!dat) hong += 1;
    if (!dat) {
      console.log(
        `  🔴 ${man}` +
          (kq.cao.length ? ` · ô nhập cao: ${kq.cao.join(", ")}` : "") +
          (kq.vo.length ? ` · chữ vỡ dọc: ${kq.vo.join(", ")}` : ""),
      );
    } else {
      console.log(`  ✓ ${man}`);
    }
  }

  // ③ Cỡ chữ thân bài: đếm số cỡ khác nhau. Ngưỡng 6 là rộng tay — thang chữ của dự án có
  // xs/sm/base/lg/xl, thêm một cỡ lạc là dấu hiệu ai đó đặt px cứng ở đâu đó.
  const nhieuCo = coChu.size > 6;
  if (nhieuCo) hong += 1;
  console.log(
    `  ${nhieuCo ? "🔴" : "✓"} cỡ chữ thân bài: ${coChu.size} cỡ — ${[...coChu].sort().join(" ")}`,
  );
  await ctx.close();
}

await b.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} phép đo KHÔNG đạt.`);
  process.exit(1);
}
console.log("\n✅ Không ô nhập nào cao bất thường, không chữ nào vỡ dọc, cỡ chữ đồng nhất.");
