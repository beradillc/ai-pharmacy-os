/**
 * Đo mức "phải kéo bao xa" trên điện thoại — chẩn đoán, KHÔNG phải cổng.
 *
 * Chain báo: *"ô nhập đơn, hàng, khách hàng… đều nằm cuối trang kéo xuống rất lâu"*.
 * Tệp này biến câu đó thành con số, vì "rất lâu" không sửa được còn "phải kéo 3,4 màn"
 * thì sửa được và kiểm lại được.
 *
 * 🔴 ĐỌC THUẦN: chỉ mở màn, thêm hàng vào giỏ (trạng thái trong trình duyệt), rồi đo.
 * Không bán đơn nào, không ghi gì.
 *
 * Đo cái gì, và vì sao đo đúng thứ đó:
 *   · `soManPhaiKeo` = chiều cao trang ÷ chiều cao màn hình — bao nhiêu màn hình mới hết trang;
 *   · `yCuaViec` = vị trí dọc của **thứ người ta tới đây để làm** (ô nhập, giỏ hàng, nút chốt).
 *     Đây mới là con số quyết định: một trang dài 5 màn mà việc chính nằm ở màn 1 thì không
 *     ai phải kéo. Đo chiều dài trang mà không đo chỗ của việc là đo sai thứ.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/mobile-ux";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

const MAN = [
  { ten: "quay", url: "/", viec: "nút chốt đơn", chu: ["Xem giỏ", "Thanh toán"] },
  { ten: "danh-muc", url: "/danh-muc-thuoc", viec: "ô tìm thuốc", sel: 'input[aria-label="Tìm thuốc"]' },
  { ten: "khach-hang", url: "/khach-hang", viec: "ô tìm khách", sel: "input" },
  { ten: "ton-kho", url: "/ton-kho", viec: "ô lọc", sel: "input" },
  { ten: "so-do-kho", url: "/so-do-kho", viec: "nút Thêm kho", chu: "Thêm kho" },
];

const b = await firefox.launch();
const ctx = await b.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  deviceScaleFactor: 2,
});
const p = await ctx.newPage();

await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
await p.fill('input[type="email"]', EMAIL);
await p.fill('input[type="password"]', PASSWORD);
await p.click('button[type="submit"]'); await p.waitForTimeout(4000);

console.log("\nMàn hình 390×844 · số càng lớn càng phải kéo lâu\n");
console.log("màn".padEnd(12), "cao trang".padStart(10), "số màn".padStart(8), "việc chính ở y".padStart(16), "  phải kéo");
console.log("─".repeat(72));

for (const m of MAN) {
  await p.goto(`${BASE}${m.url}`, { waitUntil: "load" });
  await p.waitForTimeout(3000);

  // Ở quầy: thêm một mặt hàng để giỏ có thật — giỏ rỗng thì nút Thanh toán nằm cao giả tạo.
  if (m.ten === "quay") {
    await p.locator("li").filter({ hasText: "Paracetamol 500mg" }).first()
      .locator("button", { hasText: /^Thêm$/ }).click().catch(() => {});
    await p.waitForTimeout(1500);
  }

  // 🔴 `:has-text()` là cú pháp của Playwright, KHÔNG phải CSS — `document.querySelector`
  // từ chối nó. Trong `evaluate` chỉ có CSS thật, nên tìm nút theo CHỮ bằng tay.
  const d = await p.evaluate(({ sel, chu }) => {
    const nut = [...document.querySelectorAll("button")];
    // `chu` có thể là chuỗi hoặc mảng — chuẩn hoá, nếu không `.map` ném trên chuỗi và
    // cả lượt đo chết giữa chừng (lỗi thật ở lần chạy trước).
    const ds = chu === null ? null : Array.isArray(chu) ? chu : [chu];
    const el = ds
      ? ds.map((t) => nut.find((b) => b.textContent?.includes(t))).find(Boolean)
      : document.querySelector(sel);
    if (!el) {
      return { caoTrang: document.documentElement.scrollHeight, caoMan: window.innerHeight, yViec: -1 };
    }
    const r = el.getBoundingClientRect();
    // 🔴 Với phần tử `position: fixed`, `top + scrollY` VÔ NGHĨA — nó không cuộn theo
    // trang, nên "vị trí trong tài liệu" không phải thứ người dùng phải kéo tới. Phép đo
    // đầu tiên của tôi báo 2,0 màn trong khi ảnh chụp cho thấy nút nằm ngay trong tầm mắt.
    // Thứ cần đo là: phải cuộn bao nhiêu thì nó hiện ra — và với `fixed` thì luôn là 0.
    // 🔴 Phải đi NGƯỢC LÊN cây cha. Bản đầu kiểm `position` của chính cái nút và báo
    // "2,9 màn" trong khi ảnh chụp cho thấy nút nằm ngay trong tầm ngón cái — vì nút thì
    // `static`, chỉ có THANH CHỨA nó mới `fixed`. Đo sai phần tử là đo sai mệnh đề.
    let coDinh = false;
    for (let n = el; n; n = n.parentElement) {
      if (getComputedStyle(n).position === "fixed") { coDinh = true; break; }
    }
    return {
      caoTrang: document.documentElement.scrollHeight,
      caoMan: window.innerHeight,
      yViec: coDinh ? 0 : Math.round(r.top + window.scrollY),
      coDinh,
    };
  }, { sel: m.sel ?? null, chu: m.chu ?? null });

  const soMan = (d.caoTrang / d.caoMan).toFixed(1);
  const phaiKeo =
    d.yViec < 0
      ? "(không thấy)"
      : d.coDinh
        ? "0 màn (cố định)"
        : `${(d.yViec / d.caoMan).toFixed(1)} màn`;
  console.log(
    m.ten.padEnd(12),
    String(d.caoTrang).padStart(10),
    String(soMan).padStart(8),
    String(d.yViec).padStart(16),
    "  " + phaiKeo + `  ← ${m.viec}`,
  );

  await p.screenshot({ path: `${OUT}/${m.ten}.png`, fullPage: true });
}

await b.close();
console.log("\nẢnh:", OUT);
