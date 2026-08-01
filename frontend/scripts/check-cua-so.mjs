/**
 * Cổng **P4** — mọi phím xem/nhập/sửa chi tiết mở CỬA SỔ có dấu ✕ (Chain giao 2026-08-01).
 * Nhóm ĐỌC-THUẦN: chỉ bấm nút mở rồi bấm ✕ đóng lại, không lưu gì.
 *
 * Với mỗi lối vào đã khai dưới đây, đo **bốn** mệnh đề — tách rời, in riêng, vì gộp lại
 * thành một chữ ✓ thì lần sau hỏng một cái vẫn có thể xanh vì ba cái kia (kỷ luật #14):
 *
 *   ① bấm nút ⇒ có `<dialog open>` (không phải một khối nằm cuối trang như trước)
 *   ② cửa sổ có nút ✕
 *   ③ nút ✕ nằm TRONG khung nhìn — kỷ luật #21: nút thoát mà phải cuộn mới chạm tới thì
 *     bằng không có, và trên điện thoại đó là người dùng bị kẹt
 *   ④ bấm ✕ thì cửa sổ đóng thật
 *
 * 🔴 Mệnh đề ③ là lý do cổng này tồn tại chứ không phải ①. "Có cửa sổ" thì nhìn ảnh là
 * biết; "nút thoát có chạm tới được ở khổ 390px không" thì chỉ phép đo mới trả lời được,
 * và đó đúng là chỗ ba lần trước đã hỏng.
 */
import { firefox } from "playwright-core";

import { trongKhungNhin } from "./lib/nhin-thay.mjs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

/**
 * Lối vào cửa sổ, khai theo màn. `mo` là hàm bấm-cho-cửa-sổ-hiện-ra.
 *
 * Chỉ khai những lối **mở được mà không ghi gì**. Ba cửa sổ còn lại — "Thêm khách hàng",
 * "Thêm nhân viên", "Nhận hàng cho đơn" — mở được nhưng nằm sau một biểu mẫu tạo dữ liệu;
 * chúng thuộc nhóm GHI và đã có cổng riêng đi qua. Khai chúng ở đây để rồi không bấm sẽ
 * cho một cổng xanh vì không đo gì.
 */
const LOI_VAO = [
  {
    man: "/danh-muc-thuoc",
    ten: "Hoạt chất",
    mo: (p) => p.getByRole("button", { name: /^Hoạt chất$/ }).first().click(),
  },
  {
    man: "/danh-muc-thuoc",
    ten: "Giá niêm yết",
    mo: (p) => p.getByRole("button", { name: /^Sửa giá$/ }).first().click(),
  },
  {
    man: "/ton-kho",
    ten: "Sắp xếp lô vào ô",
    mo: (p) => p.locator("tbody tr").first().getByRole("button", { name: /^Sắp xếp$/ }).click(),
  },
  {
    man: "/so-do-kho",
    ten: "Thêm kho",
    mo: (p) => p.getByRole("button", { name: /^\+ Thêm kho$/ }).click(),
  },
  {
    man: "/hoa-don",
    ten: "Chi tiết hoá đơn",
    chuanBi: async (p) => {
      const truoc = new Date(Date.now() - 400 * 86400e3).toISOString().slice(0, 10);
      await p.locator('input[aria-label="Từ ngày"]').fill(truoc);
      await p.waitForTimeout(3000);
    },
    mo: (p) => p.getByRole("button", { name: /^Xem$/ }).first().click(),
  },
];

const b = await firefox.launch();
let hong = 0;

for (const [khoTen, w, h, mob] of [
  ["laptop-1440", 1440, 900, false],
  ["mobile-390", 390, 844, true],
]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 140)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4000);

  console.log(`\n──${khoTen}──`);
  for (const { man, ten, mo, chuanBi } of LOI_VAO) {
    await p.goto(`${BASE}${man}`, { waitUntil: "load" });
    await p.waitForTimeout(2800);
    if (chuanBi) await chuanBi(p);

    let moDuoc = true;
    await mo(p).catch(() => {
      moDuoc = false;
    });
    await p.waitForTimeout(1800);

    const cuaSo = p.locator("dialog[open]");
    const menhDe1 = moDuoc && (await cuaSo.count()) === 1;
    const nutX = cuaSo.getByRole("button", { name: "Đóng" });
    const menhDe2 = menhDe1 && (await nutX.count()) === 1;
    const viTri = menhDe2 ? await trongKhungNhin(p, nutX) : { dat: false, ly_do: "khong-mo-duoc" };

    let menhDe4 = false;
    if (menhDe2) {
      await nutX.click().catch(() => {});
      await p.waitForTimeout(800);
      menhDe4 = (await p.locator("dialog[open]").count()) === 0;
    }

    const dat = menhDe1 && menhDe2 && viTri.dat && menhDe4;
    if (!dat) hong += 1;
    console.log(
      `  ${dat ? "✓" : "🔴"} ${man} · ${ten} — ` +
        `mở:${menhDe1 ? "✓" : "🔴"} ✕có:${menhDe2 ? "✓" : "🔴"} ` +
        `✕trong-khung:${viTri.dat ? "✓" : `🔴 ${viTri.ly_do}`} đóng:${menhDe4 ? "✓" : "🔴"}`,
    );
  }
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  if (loi.length) hong += 1;
  await ctx.close();
}

await b.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} phép đo KHÔNG đạt.`);
  process.exit(1);
}
console.log("\n✅ Mọi lối vào chi tiết đều mở cửa sổ, có ✕ chạm tới được, đóng được.");
