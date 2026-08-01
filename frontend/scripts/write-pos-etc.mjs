/**
 * 🔴 NHÓM GHI — BÁN THẬT một đơn có thuốc kê đơn, đi trọn luồng Chain báo hỏng 01/08:
 * thêm thuốc ETC ⇒ chụp đơn ⇒ dược sĩ duyệt ⇒ thanh toán ⇒ đơn được ghi nhận.
 *
 * **Vì sao cổng này phải tồn tại riêng, không gộp vào `write-rx-photo.mjs`:** cổng kia
 * dừng đúng ở chỗ *"Đã lưu ảnh đơn"* — và đó chính xác là chỗ lỗi của Chain bắt đầu. Ảnh
 * lưu xong, nhãn hiện xanh, rồi bấm Thanh toán thì máy chủ vẫn từ chối. Một cổng dừng
 * trước chỗ hỏng không bao giờ thấy chỗ hỏng.
 *
 * Cổng đo BA mệnh đề tách rời, in riêng từng cái — gộp lại thành một chữ ✓ thì lần sau
 * hỏng một mệnh đề vẫn có thể xanh vì hai mệnh đề kia (kỷ luật #14):
 *   ① nút "Dược sĩ duyệt đơn" hiện ra SAU khi lưu ảnh (không phải trước)
 *   ② bấm duyệt xong nhãn đổi sang "Dược sĩ đã duyệt"
 *   ③ thanh toán ĐI QUA — và tuyệt đối KHÔNG có câu "cần đơn thuốc hợp lệ"
 *
 * Mệnh đề ③ là mệnh đề Chain quan tâm. Hai cái trên chỉ để khi ③ đỏ thì biết ngay nó gãy
 * ở đâu.
 */
import { firefox } from "playwright-core";

import { trongKhungNhin } from "./lib/nhin-thay.mjs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}

/** PNG 2×2 thật (chữ ký `\x89PNG`) — `createImageBitmap` từ chối chuỗi rác. */
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGM4ISeHFTEMLQkAkL9BAbKfPiIAAAAASUVORK5CYII=",
  "base64",
);

const b = await firefox.launch();
let hong = 0;

// 🔴 CẢ HAI KHỔ. Bản đầu chỉ chạy 1440×900 — và lỗi "bán xong không thấy xác nhận" là lỗi
// CHỈ CÓ ở khổ điện thoại (giỏ thu thành thanh đáy là bản vá riêng cho mobile). Một cổng
// chạy đúng một khổ không canh được thứ chỉ hỏng ở khổ kia.
for (const [khoTen, w, h, mob] of [
  ["laptop-1440", 1440, 900, false],
  ["mobile-390", 390, 844, true],
]) {
const ctx = await b.newContext({
  viewport: { width: w, height: h },
  isMobile: mob,
  hasTouch: mob,
});
const p = await ctx.newPage();
const loi = [];
p.on("pageerror", (e) => loi.push(String(e).slice(0, 160)));
console.log(`\n──${khoTen}──`);

await p.goto(`${BASE}/login`, { waitUntil: "load" });
await p.waitForTimeout(1500);
await p.fill('input[type="email"]', EMAIL);
await p.fill('input[type="password"]', PASSWORD);
await p.click('button[type="submit"]');
await p.waitForTimeout(4000);
await p.goto(`${BASE}/`, { waitUntil: "load" });
await p.waitForTimeout(3000);

// Thuốc KÊ ĐƠN. Không bọc `.catch()`: bấm trượt phải nổ ngay tại đây, không lặng lẽ đi tiếp.
await p
  .locator("li")
  .filter({ hasText: "Amoxicillin 500mg" })
  .first()
  .locator("button", { hasText: /^Thêm$/ })
  .click();
await p.waitForTimeout(1200);

// Trên điện thoại giỏ thu thành thanh đáy — phải mở ra mới thao tác được.
const moGio = p.getByRole("button", { name: /^Xem giỏ$/ });
if (await moGio.count()) {
  await moGio.click();
  await p.waitForTimeout(900);
}

// Nút duyệt PHẢI chưa có lúc này — chưa có tờ đơn nào để duyệt.
const duyetTruocKhiChup = await p.getByRole("button", { name: /Dược sĩ duyệt đơn/ }).count();

await p
  .locator('input[aria-label="Chụp đơn thuốc"]')
  .setInputFiles({ name: "don-thuoc.png", mimeType: "image/png", buffer: PNG });
await p.waitForTimeout(4000);

const nutDuyet = p.getByRole("button", { name: /Dược sĩ duyệt đơn/ });
const menhDe1 = duyetTruocKhiChup === 0 && (await nutDuyet.count()) === 1;
console.log(`  ① nút duyệt chỉ hiện SAU khi lưu ảnh: ${menhDe1 ? "✓" : "🔴"}`);

if (await nutDuyet.count()) {
  await nutDuyet.click();
  await p.waitForTimeout(2500);
}
const menhDe2 = (await p.locator("text=Dược sĩ đã duyệt").count()) > 0;
console.log(`  ② duyệt xong nhãn đổi: ${menhDe2 ? "✓" : "🔴"}`);

// Thanh toán: đủ tiền ⇒ bấm lần một (mở xác nhận) ⇒ bấm lần hai (gọi máy chủ).
await p.getByRole("button", { name: /^Đủ tiền$/ }).click();
await p.waitForTimeout(500);
const nutTra = p.getByRole("button", { name: /^Thanh toán$/ });
await nutTra.click();
await p.waitForTimeout(600);
await nutTra.click();
await p.waitForTimeout(5000);

// 🔴 `trongKhungNhin`, KHÔNG phải `count()` và cũng KHÔNG phải `isVisible()`. Hai lượt sai
// liên tiếp trong cùng một bước, cả hai đều do ẢNH CHỤP bắt được chứ không phép đo nào:
//   · `count()`     xanh khi dòng xác nhận đi theo giỏ vào `display: none`
//   · `isVisible()` xanh khi dòng xác nhận nằm DƯỚI danh mục thuốc, ngoài khung nhìn —
//     Playwright chỉ hỏi "có hộp và không display:none", không hỏi "có nhìn thấy được"
// Kỷ luật #21 lần thứ năm, và cả hai lần nạn nhân là chính cổng tôi vừa viết.
const xacNhan = await trongKhungNhin(p, p.locator("text=Đã bán thành công").first());
const banXong = xacNhan.dat;
// Đo ĐÍCH DANH câu Chain đọc được, không chỉ đo "có lỗi hay không": nếu mai này lỗi đổi
// sang nguyên nhân khác thì `banXong` vẫn bắt được, còn dòng này nói rõ CÁI GÌ đã hết.
const conDoiDon = (await p.locator("text=cần đơn thuốc hợp lệ").count()) > 0;
const conDoiDuyet = (await p.locator("text=chưa cho phép bán").count()) > 0;
const menhDe3 = banXong && !conDoiDon && !conDoiDuyet;
console.log(
  `  ③ bán xong: ${menhDe3 ? "✓" : "🔴"} · "cần đơn thuốc hợp lệ": ${
    conDoiDon ? "CÒN 🔴" : "hết"
  } · "chưa cho phép bán": ${conDoiDuyet ? "CÒN 🔴" : "hết"} · lỗi JS: ${loi.length}`,
);
if (loi.length) console.log("   " + loi.join(" | "));

if (!menhDe1 || !menhDe2 || !menhDe3 || loi.length > 0) hong += 1;
await ctx.close();
}

await b.close();
if (hong > 0) {
  console.log(`\n🔴 ${hong} khổ: luồng bán thuốc kê đơn KHÔNG chạy trọn.`);
  process.exit(1);
}
console.log("\n✅ Bán được trọn một đơn ETC ở CẢ HAI KHỔ: chụp ⇒ duyệt ⇒ thanh toán (THẬT).");
