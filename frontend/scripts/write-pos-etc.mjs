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

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
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
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();
const loi = [];
p.on("pageerror", (e) => loi.push(String(e).slice(0, 160)));

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

const banXong = (await p.locator("text=Đã bán thành công").count()) > 0;
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

await b.close();
if (!menhDe1 || !menhDe2 || !menhDe3 || loi.length > 0) {
  console.log("\n🔴 Luồng bán thuốc kê đơn KHÔNG chạy trọn.");
  process.exit(1);
}
console.log("\n✅ Bán được trọn một đơn ETC: chụp ⇒ duyệt ⇒ thanh toán (dữ liệu THẬT).");
