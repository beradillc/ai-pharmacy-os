/**
 * 🔴 NHÓM GHI — chạy trọn luồng chụp đơn thật: chọn tệp ở quầy ⇒ tạo đơn thuốc ⇒ lưu ảnh.
 *
 * **Tạo dữ liệu thật.** Không nằm trong nhóm đọc-thuần của `ui-gates.sh`; chỉ chạy khi
 * người ta cố ý gọi `--all`.
 *
 * Vì sao vẫn cần: cổng `check-luu-tru` xanh với **0 dòng** thì khẳng định quan trọng nhất
 * của nó — *ảnh mở ra và trình duyệt giải mã được* — chưa hề chạy. Một cổng xanh vì không
 * có gì để đo là cổng xanh vì lý do sai (kỷ luật #14). Tệp này tạo đúng cái để đo.
 *
 * Nó cũng là phép kiểm end-to-end duy nhất đi qua `canvas` → nén → base64 → `POST
 * /prescriptions` → `PUT /image`. Bốn lớp đó không lớp nào chứng minh được ba lớp kia.
 */
import { firefox } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }

/** PNG 2×2 thật (chữ ký `\x89PNG`), không phải chuỗi rác — `createImageBitmap` sẽ từ chối rác. */
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGM4ISeHFTEMLQkAkL9BAbKfPiIAAAAASUVORK5CYII=",
  "base64",
);

const b = await firefox.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();
const loi = [];
p.on("pageerror", (e) => loi.push(String(e).slice(0, 160)));

await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
await p.fill('input[type="email"]', EMAIL);
await p.fill('input[type="password"]', PASSWORD);
await p.click('button[type="submit"]'); await p.waitForTimeout(4000);
await p.goto(`${BASE}/`, { waitUntil: "load" }); await p.waitForTimeout(3000);

// Thêm một thuốc KÊ ĐƠN vào giỏ. KHÔNG bọc `.catch()`: bấm trượt phải nổ ngay tại đây.
await p.locator("li").filter({ hasText: "Amoxicillin 500mg" }).first()
  .locator("button", { hasText: /^Thêm$/ }).click();
await p.waitForTimeout(1200);

// Cố ý KHÔNG gắn khách — đúng ca Chain chốt: "không cung cấp sdt, chỉ cần chụp đơn là xong".
await p.locator('input[aria-label="Tên bác sĩ kê đơn"]').fill("BS. Nguyễn Văn A");
await p.waitForTimeout(400);
await p.locator('input[aria-label="Chụp đơn thuốc"]')
  .setInputFiles({ name: "don-thuoc.png", mimeType: "image/png", buffer: PNG });
await p.waitForTimeout(4000);

const nhan = await p.locator("text=Đã lưu ảnh đơn").count();
console.log(`  nhãn "Đã lưu ảnh đơn": ${nhan > 0 ? "✓" : "🔴"} · lỗi JS: ${loi.length}`);
if (loi.length) console.log("   " + loi.join(" | "));

await b.close();
if (nhan === 0 || loi.length > 0) { console.log("\n🔴 Luồng chụp đơn KHÔNG chạy trọn."); process.exit(1); }
console.log("\n✅ Đã tạo một đơn thuốc từ ảnh (dữ liệu THẬT).");
