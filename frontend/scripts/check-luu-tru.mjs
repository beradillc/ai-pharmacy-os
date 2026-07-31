/**
 * Cài đặt → **Lưu trữ** (Chain giao 2026-07-31).
 *
 * 🔴 ĐỌC THUẦN với một ngoại lệ có chủ ý: mở một ảnh **ghi một dòng audit
 * `RX_IMAGE_VIEWED`**. Đó là ghi vào sổ audit chứ không phải vào dữ liệu nghiệp vụ, và
 * chính hành vi ghi vết ấy là thứ cổng này phải chứng minh — không mở ảnh thì không đo
 * được nó. Không tạo đơn, không bán hàng, không đổi dữ liệu nào.
 *
 * Đo bốn mệnh đề:
 *   1. có lối vào từ Cài đặt;
 *   2. danh sách **không** mang nội dung ảnh (không có `<img src="data:...">` khi chưa bấm);
 *   3. bấm "Xem ảnh" thì ảnh hiện ra **và tải được thật** (`naturalWidth > 0`, không phải
 *      một thẻ `img` gãy);
 *   4. màn nói rõ phạm vi đang xem là chi nhánh hay toàn chuỗi.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/luu-tru";
if (!EMAIL || !PASSWORD) { console.error("Thiếu EMAIL / PASSWORD."); process.exit(2); }
mkdirSync(OUT, { recursive: true });

const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [["desktop",1440,900,false],["mobile",390,844,true]]) {
  const ctx = await b.newContext({ viewport:{width:w,height:h}, isMobile:mob, hasTouch:mob, deviceScaleFactor:2 });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 120)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" }); await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]'); await p.waitForTimeout(4000);

  // ① Lối vào từ Cài đặt — Chain đặt Lưu trữ ở trong Cài đặt, không phải một mục nav riêng.
  await p.goto(`${BASE}/cai-dat`, { waitUntil: "load" }); await p.waitForTimeout(2500);
  const coLoiVao = await p.locator('a[href="/cai-dat/luu-tru"]').count();

  await p.goto(`${BASE}/cai-dat/luu-tru`, { waitUntil: "load" }); await p.waitForTimeout(3000);

  const truoc = await p.evaluate(() => ({
    soDong: document.querySelectorAll("tbody tr").length,
    // ② Danh sách KHÔNG được mang ảnh sẵn: mỗi lượt mở ảnh phải là một lượt đọc có vết.
    anhTaiSan: [...document.querySelectorAll("img")].filter(i => i.src.startsWith("data:")).length,
    noiPhamVi: /toàn bộ chi nhánh|chi nhánh đang đăng nhập/i.test(document.body.innerText),
  }));

  await p.screenshot({ path: `${OUT}/${ten}-1-danh-sach.png`, fullPage: true });

  let anhHien = false, anhRong = 0;
  if (truoc.soDong > 0) {
    await p.locator("button", { hasText: /^Xem ảnh$/ }).first().click();
    await p.waitForTimeout(2500);
    const r = await p.evaluate(() => {
      const img = [...document.querySelectorAll("img")].find(i => i.src.startsWith("data:"));
      // ③ `naturalWidth` — một thẻ `img` gãy vẫn tồn tại trong DOM và vẫn khớp mọi phép
      // đếm. Chỉ `naturalWidth > 0` mới chứng minh trình duyệt GIẢI MÃ được ảnh.
      return { co: !!img, rong: img?.naturalWidth ?? 0 };
    });
    anhHien = r.co; anhRong = r.rong;
    await p.screenshot({ path: `${OUT}/${ten}-2-xem-anh.png`, fullPage: true });
  }

  const dat = coLoiVao > 0 && truoc.anhTaiSan === 0 && truoc.noiPhamVi &&
              (truoc.soDong === 0 || (anhHien && anhRong > 0)) && loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  lối vào từ Cài đặt: ${coLoiVao > 0 ? "✓" : "🔴"} · nói rõ phạm vi: ${truoc.noiPhamVi ? "✓" : "🔴"}`);
  console.log(`  danh sách: ${truoc.soDong} dòng · ảnh tải sẵn: ${truoc.anhTaiSan} (phải 0) ${truoc.anhTaiSan === 0 ? "✓" : "🔴"}`);
  console.log(`  bấm Xem ảnh ⇒ ảnh hiện: ${anhHien ? "✓" : (truoc.soDong === 0 ? "(chưa có ảnh nào để mở)" : "🔴")} · rộng ${anhRong}px ${anhRong > 0 || truoc.soDong === 0 ? "✓" : "🔴"}`);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Màn Lưu trữ mở được, ảnh chỉ tải khi bấm." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
