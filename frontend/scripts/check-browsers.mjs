/**
 * Kiểm BERAS trên hai engine trình duyệt, qua LAN IP — đúng đường điện thoại đi.
 *
 * 🔴 Sinh từ lỗi 29/07: Chain báo *"Safari iPhone mở lên khoảng trắng"*. Đo ra thì
 * **không phải lỗi Safari** — Firefox cũng trắng y hệt, và trắng ở MỌI màn trong
 * ứng dụng khi chưa đăng nhập. Nguyên nhân: Next chặn request chéo nguồn tới tài
 * nguyên dev ⇒ React không hydrate ⇒ màn server-render ra `null` rồi đứng im.
 *
 * Không cổng nào bắt được: `lint`/`tsc`/`test`/`build` đều xanh, và chính tôi chụp
 * được 22 ảnh đẹp — vì bộ chụp chạy qua `localhost`, còn điện thoại đi qua LAN IP.
 *
 * Chạy:  node scripts/check-browsers.mjs        (mặc định http://<LAN_IP>:3000)
 *        BASE_URL=http://localhost:3000 node scripts/check-browsers.mjs
 *
 * Cần một lần:
 *     npm i -D playwright-core && npx playwright install firefox webkit
 *     (WebKit trên Ubuntu/Mint còn cần: sudo apt-get install libavif16)
 *
 * Chạy:  cd frontend && npm run check:browsers
 */
import { webkit, firefox, devices } from "playwright-core";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
/** Màn trong ứng dụng: chưa đăng nhập thì PHẢI bị đẩy về /login, không được trắng. */
const GUARDED = ["/", "/ton-kho", "/bang-dieu-hanh"];

let failed = 0;
for (const [name, engine] of [["Firefox", firefox], ["WebKit (Safari)", webkit]]) {
  const b = await engine.launch();
  const ctx = await b.newContext({ ...devices["iPhone 13"] });
  const page = await ctx.newPage();
  for (const path of GUARDED) {
    await page.goto(`${BASE}${path}`, { waitUntil: "load" });
    await page.waitForTimeout(3500);
    // Bỏ thẻ <script> khi đếm: trang trắng vẫn có hàng chục KB payload của Next,
    // nên đếm cả script thì một trang hỏng trông y như một trang bình thường.
    const visible = await page.evaluate(() =>
      document.body.innerHTML.replace(/<script[\s\S]*?<\/script>/g, "").trim().length);
    const redirected = new URL(page.url()).pathname.startsWith("/login");
    const ok = redirected && visible > 200;
    if (!ok) failed++;
    console.log(
      `${name.padEnd(16)} ${path.padEnd(16)} → ${new URL(page.url()).pathname.padEnd(10)} ` +
      `${visible} ký tự ${ok ? "✓" : "🔴 TRẮNG / không chuyển hướng"}`,
    );
  }
  await b.close();
}
console.log(failed === 0 ? "\n✓ Hai engine đều chạy" : `\n🔴 ${failed} ca hỏng`);
process.exit(failed === 0 ? 0 : 1);
