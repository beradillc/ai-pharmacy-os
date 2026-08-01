/**
 * Cổng trình duyệt cho cảnh báo dị ứng ở quầy (Đ-7) — chạy Firefox thật, qua LAN IP.
 *
 * 🔴 Đây là phép kiểm mà ba lớp test dưới KHÔNG thay được: unit/integration/e2e đều xanh
 * ngay cả khi màn POS không gọi endpoint, vì chúng gọi thẳng HTTP. Chỉ lớp này trả lời
 * được câu người dùng thật sự hỏi — *"đứng ở quầy thì tôi có THẤY cảnh báo không"*.
 *
 * Kiểm bốn trạng thái phải phân biệt được, và bốn cái đó là toàn bộ giá trị của tính năng:
 *
 *   1. khách dị ứng + thuốc chứa hoạt chất đó  → hiện SỐ cảnh báo + đòi lý do
 *   2. chưa ghi lý do                          → nút đổi thành "Ghi lý do để bán"
 *   3. ghi lý do                               → nút bật lại
 *   4. khách CHƯA đồng ý dữ liệu sức khoẻ      → "chưa kiểm được", KHÔNG phải "sạch"
 *
 * Trạng thái 4 là cái dễ làm sai nhất: nó trả `conflict_count = 0` y hệt ca sạch.
 *
 * Chạy:  node scripts/check-pos-allergy.mjs
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? "trinhthu@nhathuoc650.vn";
const PASSWORD = process.env.PASSWORD ?? "NhaThuoc650@2026";
const OUT = process.env.OUT_DIR ?? "/tmp/pos-allergy";

/** Khách + thuốc CÓ THẬT trên `nt650v2`: hai người khai dị ứng Acid clavulanic, và
 *  Augmentin 625mg chứa hoạt chất đó — tên thuốc không hề nhắc tới nó. */
const SDT_DI_UNG = process.env.SDT_DI_UNG ?? "0357205494";
const THUOC_XUNG_DOT = "Augmentin";
const THUOC_SACH = "Vitamin C";

mkdirSync(OUT, { recursive: true });
const KHO = [
  { ten: "desktop", width: 1440, height: 900, mobile: false },
  { ten: "mobile", width: 390, height: 844, mobile: true },
];

let hong = 0;
const browser = await firefox.launch();

for (const kho of KHO) {
  const ctx = await browser.newContext({
    viewport: { width: kho.width, height: kho.height },
    isMobile: kho.mobile,
    hasTouch: kho.mobile,
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1500);
  await page.fill('input[type="email"]', EMAIL);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(4000);
  await page.goto(`${BASE}/`, { waitUntil: "load" });
  await page.waitForTimeout(3000);

  const themThuoc = async (ten) => {
    // Giỏ đang mở CHE danh sách thuốc phía sau ⇒ thu gọn trước khi bấm Thêm. Trên máy tính
    // không có nút này (giỏ luôn hiện cạnh danh sách), `count()` bằng 0 nên bỏ qua.
    const thuGon = page.getByRole("button", { name: /^Thu gọn$/ });
    if (await thuGon.count()) {
      await thuGon.click();
      await page.waitForTimeout(600);
    }
    await page.fill('input[placeholder*="Tìm thuốc"]', ten);
    await page.waitForTimeout(1200);
    await page.locator("button", { hasText: /^Thêm$/ }).first().click();
    await page.waitForTimeout(800);
  };

  /**
   * Mở giỏ trên khổ điện thoại — giỏ đóng là `display: none`, nên mọi phép đo bên trong nó
   * hỏng (`innerText` rỗng, `click()` báo "element is not visible").
   *
   * 🔴 GỌI SAU KHI THÊM HẾT THUỐC, không gọi trong `themThuoc`. Bản vá 01/08 của tôi chèn
   * nó vào giữa `themThuoc` ⇒ lần thêm thứ hai bị chính giỏ đang mở CHE MẤT nút "Thêm", và
   * Playwright báo `cartHead ... intercepts pointer events`. Sửa một cổng ở sai chỗ thì nó
   * đỏ vì một lý do mới, không phải hết đỏ.
   */
  const moGio = async () => {
    const nut = page.getByRole("button", { name: /^Xem giỏ$/ });
    if (await nut.count()) {
      await nut.click();
      await page.waitForTimeout(900);
    }
  };
  const doc = () =>
    page.evaluate(() => {
      const t = document.body.innerText;
      const nut = [...document.querySelectorAll("button")].find((b) =>
        /Thanh toán|Ghi lý do để bán|Đang xử lý/.test(b.textContent ?? ""),
      );
      return {
        coCanhBao: /cảnh báo dị ứng/i.test(t),
        coSach: /Đã đối chiếu — không có dị ứng/i.test(t),
        coChuaKiem: /Chưa kiểm được|không đối chiếu được|Chưa đối chiếu được/i.test(t),
        nhanNut: nut?.textContent?.trim() ?? null,
        nutTat: nut?.hasAttribute("disabled") ?? null,
        coOLyDo: !!document.querySelector('input[aria-label^="Lý do vẫn bán"]'),
      };
    });

  // --- ① thuốc sạch, chưa có khách: KHÔNG được hiện gì cả -------------------
  await themThuoc(THUOC_SACH);
  await moGio();
  const chuaKhach = await doc();

  // --- ② gắn khách CÓ dị ứng + thuốc xung đột --------------------------------
  await page.fill('input[placeholder*="số"], input[type="tel"]', SDT_DI_UNG);
  await page.waitForTimeout(2500);
  await themThuoc(THUOC_XUNG_DOT);
  await moGio();
  await page.waitForTimeout(2500);
  const coXungDot = await doc();
  await page.screenshot({ path: `${OUT}/${kho.ten}-1-canh-bao.png`, fullPage: true });

  // --- ③ ghi lý do → nút bật lại --------------------------------------------
  let sauKhiGhi = null;
  if (coXungDot.coOLyDo) {
    await page.fill(
      'input[aria-label^="Lý do vẫn bán"]',
      "Bác sĩ đã chỉ định, khách dùng nhiều lần không sao",
    );
    await page.waitForTimeout(600);
    sauKhiGhi = await doc();
    await page.screenshot({ path: `${OUT}/${kho.ten}-2-da-ghi-ly-do.png`, fullPage: true });
  }

  const dat =
    !chuaKhach.coCanhBao &&
    coXungDot.coCanhBao &&
    coXungDot.coOLyDo &&
    coXungDot.nutTat === true &&
    coXungDot.nhanNut === "Ghi lý do để bán" &&
    sauKhiGhi?.nutTat === false &&
    sauKhiGhi?.nhanNut === "Thanh toán";
  if (!dat) hong++;

  console.log(`\n════ ${kho.ten} ════`);
  console.log(`① chưa gắn khách        · cảnh báo: ${chuaKhach.coCanhBao ? "🔴 hiện nhầm" : "✓ không hiện"}`);
  console.log(
    `② khách dị ứng + Augmentin · cảnh báo: ${coXungDot.coCanhBao ? "✓" : "🔴 KHÔNG HIỆN"}` +
      ` · ô lý do: ${coXungDot.coOLyDo ? "✓" : "🔴"}` +
      ` · nút: "${coXungDot.nhanNut}" ${coXungDot.nutTat ? "(tắt ✓)" : "🔴 (vẫn bấm được)"}`,
  );
  console.log(
    `③ sau khi ghi lý do      · nút: "${sauKhiGhi?.nhanNut}" ` +
      `${sauKhiGhi?.nutTat === false ? "(bật ✓)" : "🔴 (vẫn tắt)"}`,
  );
  await ctx.close();
}

await browser.close();
console.log(
  hong === 0
    ? "\n✅ Cảnh báo dị ứng hiện đúng ở quầy, cả hai khổ."
    : `\n🔴 ${hong} khổ có vấn đề.`,
);
process.exit(hong === 0 ? 0 : 1);
