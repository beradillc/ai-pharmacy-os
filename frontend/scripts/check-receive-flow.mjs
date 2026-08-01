/**
 * Kiểm luồng NHẬN HÀNG trên trình duyệt THẬT, qua LAN IP, ở khổ điện thoại.
 *
 * Vì sao cần thứ này bên cạnh lint/tsc/test/build: ngày 29/07 cả bốn cổng đó
 * xanh, 22 ảnh chụp màn hình đẹp, 7 phép kiểm của `lan-dev.sh` xanh — mà app
 * vẫn TRẮNG TINH trên iPhone. Không lớp nào chạy JavaScript trong một trình
 * duyệt thật qua đúng địa chỉ người dùng gõ. `check-browsers.mjs` đóng phần
 * "trang có hiện không"; file này đóng phần "bấm vào có chạy không".
 *
 * KHÔNG nhúng mật khẩu vào đây (yêu cầu số 7 của Chain: không commit secrets).
 * Chạy:
 *     cd frontend
 *     BERAS_EMAIL=demo@bera.vn BERAS_PASSWORD='…' npm run check:receive
 *
 * Cần: máy chủ LAN đang chạy (`make lan`) trên CSDL đã seed có ít nhất một đơn
 * mua ở trạng thái ORDERED hoặc PARTIALLY_RECEIVED. Không có đơn nào như vậy
 * thì script báo BỎ QUA chứ không báo xanh — một phép kiểm không chạy được
 * không phải là một phép kiểm đã qua.
 */
import { firefox, webkit } from "playwright-core";

const BASE = process.env.BERAS_BASE ?? "http://192.168.1.10:3000";
const EMAIL = process.env.BERAS_EMAIL;
const PASSWORD = process.env.BERAS_PASSWORD;

if (!EMAIL || !PASSWORD) {
  console.error("Thiếu BERAS_EMAIL / BERAS_PASSWORD trong biến môi trường.");
  process.exit(2);
}

let failures = 0;
let skipped = 0;

for (const [name, engine] of [
  ["Firefox", firefox],
  ["WebKit (Safari)", webkit],
]) {
  const browser = await engine.launch();
  // Khổ iPhone 13/14 — khổ Chain thật sự cầm, không phải khổ máy tính thu nhỏ.
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));

  try {
    await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20_000 });

    // 🔴 ĐỢI YÊN trước khi chuyển trang. Chuyển khi request còn đang bay thì
    // WebKit huỷ nó và báo lỗi *"…due to access control checks"* — đọc y hệt
    // một lỗi CORS. Tôi đã suýt đuổi theo nó HAI LẦN trong cùng một ngày.
    // Đo dứt điểm bằng cách đóng dấu thời gian: đợi yên 6 giây thì lỗi biến
    // mất hoàn toàn, và `/drugs?limit=200` chạy xong bình thường. Lỗi ở phép
    // đo, không ở sản phẩm — cùng họ với `$UID` chỉ-đọc và mypy chạy sai thư mục.
    // `networkidle` KHÔNG đủ: React Query bắn `/drugs` sau khi hydrate xong, tức
    // là có thể sau lúc mạng đã "idle" một nhịp. Chờ đích danh phản hồi đó rồi
    // mới rời trang — chặn tại GỐC thay vì lọc thông điệp lỗi, vì lọc thông điệp
    // là cách làm cổng mất răng với một lỗi CORS thật sau này.
    await page
      .waitForResponse((r) => r.url().includes("/drugs"), { timeout: 15_000 })
      .catch(() => {});
    await page.waitForLoadState("networkidle");

    await page.goto(`${BASE}/don-mua-hang`, { waitUntil: "networkidle" });

    const button = page.locator('button:has-text("Nhận hàng")').first();
    // waitFor, KHÔNG phải waitForTimeout: bản đầu của script này chờ cứng 2,5s
    // rồi báo đỏ vì bảng chưa tải xong — một phép đo hỏng, không phải lỗi sản phẩm.
    await button.waitFor({ timeout: 20_000 }).catch(() => {});
    if ((await page.locator('button:has-text("Nhận hàng")').count()) === 0) {
      console.log(`${name.padEnd(16)} ⚠ BỎ QUA — không có đơn nào đang chờ nhận hàng`);
      skipped++;
      continue;
    }

    await button.click();
    const drawer = page.locator('dialog[aria-label*="Nhận hàng"]');
    await drawer.waitFor({ timeout: 20_000 });
    // 🔴 Chờ DÒNG ĐẦU TIÊN, không chỉ chờ cái ngăn kéo. Ngăn kéo hiện ngay kèm
    // khung xương; các dòng chỉ tới sau khi `GET /purchase-orders/{id}` về. Bản
    // trước đếm ngay sau khi ngăn kéo hiện và ra kết quả TỰ MÂU THUẪN trên
    // WebKit — `dòng=0` mà `có-tên=4/0`. Một cổng đo hụt còn tệ hơn không có
    // cổng: nó dạy người đọc bỏ qua màu đỏ.
    await drawer.locator("tbody tr").first().waitFor({ timeout: 20_000 });
    const rows = await drawer.locator("tbody tr").count();

    // 🔴 CHỜ tên thuốc hiện ra, đừng chụp một lần rồi kết luận. Tên do `GET /drugs?ids=…`
    // gắn vào SAU khi bảng đã vẽ; đọc ngay thì có lúc kịp có lúc không. Đo thật 01/08: ba
    // lượt chạy liên tiếp cho Firefox 0/3 · cả hai 3/3 · WebKit 0/3 — **ngẫu nhiên theo
    // engine**, tức đua thời gian chứ không phải hồi quy.
    //
    // Một cổng lúc xanh lúc đỏ vì lý do thời gian là cổng người ta học cách bỏ qua — và
    // khi nó đỏ vì lý do THẬT thì không ai còn tin nữa. Kỷ luật #14 nói mã thoát phải biết
    // đổi màu; nó cũng phải đổi màu vì **đúng một** lý do.
    await drawer
      .locator("tbody tr td:first-child")
      .first()
      .filter({ hasNotText: /^Mã / })
      .waitFor({ timeout: 20_000 })
      .catch(() => {});
    const names = await drawer.locator("tbody tr td:first-child").allInnerTexts();
    // Tên thuốc do `GET /drugs?ids=…` gắn vào. Hỏng cái đó thì cột đầu ra
    // "Mã 3f2b1c9d" — chạy được nhưng vô dụng với người đứng dỡ hàng.
    const named = names.filter((t) => t.trim() && !t.startsWith("Mã ")).length;
    const lotInput = await drawer.locator('input[aria-label^="Số lô"]').first().isVisible();
    const expiryInput = await drawer.locator('input[aria-label^="Hạn dùng"]').first().isVisible();

    const ok = rows > 0 && named === rows && lotInput && expiryInput && errors.length === 0;
    if (!ok) failures++;
    console.log(
      `${name.padEnd(16)} dòng=${rows} có-tên=${named}/${rows} ô-số-lô=${lotInput ? "✓" : "✗"} ` +
        `ô-hạn-dùng=${expiryInput ? "✓" : "✗"} lỗiJS=${errors.length} ${ok ? "✓" : "🔴"}`,
    );
    if (errors.length) console.log("   ", errors.slice(0, 2).join(" | "));
  } catch (err) {
    failures++;
    console.log(`${name.padEnd(16)} 🔴 ${String(err).split("\n")[0]}`);
  } finally {
    await browser.close();
  }
}

if (skipped > 0 && failures === 0) {
  console.log("\n⚠ Bỏ qua — CSDL không có đơn nào chờ nhận. KHÔNG tính là đã kiểm.");
  process.exit(3);
}
console.log(failures === 0 ? "\n✓ Luồng Nhận hàng chạy trên cả hai engine" : `\n🔴 ${failures} engine hỏng`);
process.exit(failures === 0 ? 0 : 1);
