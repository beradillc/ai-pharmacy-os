/**
 * **CHẠM TỚI ĐƯỢC** — bậc thứ ba, sau "có trên trang" và "nhìn thấy được". (02/08)
 *
 * Kỷ luật #21 dựng cổng cho bậc hai: `innerText` đọc được cả phần tràn ngoài khung nhìn, nên
 * phải đo `boundingBox()` nằm trong `viewport`. Tệp này dựng bậc **ba**, vì hôm nay có một ca
 * qua được cả hai bậc trước mà người dùng **vẫn không dùng được**:
 *
 *   `<dialog aria-label="Lộ trình lấy hàng">` **đã đóng** (không có thuộc tính `open`) nhưng
 *   CSS `.hop` đè `display: flex` lên mặc định `display: none` của trình duyệt ⇒ cửa sổ đóng
 *   vẫn được VẼ, và thanh đầu `sticky` của nó phủ dải y=72…141 trên khổ 402px — đúng chỗ ô
 *   **"Tìm thuốc"** của màn BÁN HÀNG (y=89).
 *
 *   Ô nhập vẫn **có trên trang** ✓, vẫn **nằm trong khung nhìn** ✓, và vẫn **không chạm được**.
 *   Dược sĩ bấm vào ô tìm thuốc thì không có gì xảy ra, trên đúng màn dùng nhiều nhất cả ngày.
 *
 * Phép đo đúng cho bậc ba là `document.elementFromPoint` tại **tâm** phần tử: nó trả về thứ
 * ngón tay thật sự chạm phải. Không phần tử nào khác được đứng chắn ở đó.
 *
 * 🔴 Không cổng nào trong 21 cổng trước bắt được — và nó lộ ra không phải nhờ một phép đo, mà
 *    vì **bản quay video chết** đúng chỗ đó với `subtree intercepts pointer events`. Cùng họ
 *    với các ca kỷ luật #20 đã ghi: thứ chạy thật biết những điều phép đo không được dặn tìm.
 */
import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();

/** Phần tử người dùng PHẢI chạm được để làm việc. Mỗi dòng là một ca đã hoặc suýt hỏng. */
const PHAI_CHAM_DUOC = [
  { duong: "/", ten: "ô Tìm thuốc (màn bán hàng)", chon: 'input[placeholder*="Tìm thuốc"]' },
  { duong: "/khach-hang", ten: "ô tìm khách hàng", chon: 'input[placeholder*="Tìm"]' },
  { duong: "/danh-muc-thuoc", ten: "ô lọc danh mục", chon: 'input[placeholder*="Tìm"]' },
  { duong: "/ton-kho", ten: "ô lọc tồn kho", chon: 'input[placeholder*="Lọc"]' },
];

const b = await webkit.launch();
let hong = 0;

for (const [ten, w, h, mob] of [
  ["mobile", 402, 874, true],
  ["desktop", 1440, 900, false],
]) {
  const ctx = await b.newContext({
    viewport: { width: w, height: h },
    isMobile: mob,
    hasTouch: mob,
    deviceScaleFactor: 2,
    locale: "vi-VN",
  });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4500);

  console.log(`\n──${ten}──`);
  for (const { duong, ten: tenO, chon } of PHAI_CHAM_DUOC) {
    await p.goto(`${BASE}${duong}`, { waitUntil: "load" });
    await p.waitForTimeout(3000);

    const kq = await p.evaluate(
      ({ chon }) => {
        const el = document.querySelector(chon);
        if (!el) return { co: false };
        const r = el.getBoundingClientRect();
        const x = r.x + r.width / 2;
        const y = r.y + r.height / 2;
        const tren = document.elementFromPoint(x, y);
        // "Chạm được" = thứ ở điểm chạm CHÍNH LÀ phần tử đó, hoặc nằm bên trong nó
        // (vd `<span>` con của một `<button>`). Không phải "có phần tử nào đó ở đấy".
        const dat = !!tren && (tren === el || el.contains(tren) || tren.contains(el));
        return {
          co: true,
          dat,
          trongKhung: r.x >= 0 && r.y >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
          che: dat ? null : `${tren?.tagName}.${tren?.className ?? ""}`.slice(0, 60),
        };
      },
      { chon },
    );

    if (!kq.co) {
      console.log(`  ${tenO.padEnd(30)} ⏭️  không có trên màn này — bỏ qua`);
      continue;
    }
    if (!kq.dat) hong++;
    console.log(
      `  ${tenO.padEnd(30)} ${kq.dat ? "✓ chạm được" : "🔴 BỊ CHE"}` +
        ` · trong khung nhìn: ${kq.trongKhung ? "✓" : "🔴"}` +
        (kq.che ? `\n${" ".repeat(34)}thứ nằm trên: ${kq.che}` : ""),
    );
  }
  await ctx.close();
}

await b.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} phần tử CÓ trên trang, NHÌN THẤY được, nhưng KHÔNG chạm được.`);
  process.exit(1);
}
console.log("\n✅ Mọi phần tử phải chạm được đều chạm được.");
