/**
 * **Sáu màn ở trạng thái RỖNG** — U-05, đo trên `qt650` (0 đơn, 0 khách, 0 lô).
 *
 * Vì sao cần một CSDL rỗng thật: một màn thiếu trạng thái rỗng **trông y hệt** một màn đang
 * chạy tốt khi CSDL có dữ liệu. Chỉ `qt650` phơi ra được lỗi này, và nó cũng chính là CSDL
 * sẽ lên hình — người xem video 11 (Báo cáo) nhìn đúng cái màn này ở đúng trạng thái này.
 *
 * `01_BAO_CAO_UAT.md` §3: *"người mới không phân biệt được 'chưa có dữ liệu' với 'phần mềm
 * lỗi' — và luôn đoán vế thứ hai."*
 *
 * Đo bốn thứ mỗi màn, mỗi khổ:
 *   ① màn KHÔNG trắng — có chữ nhìn thấy được;
 *   ② có câu giải thích trạng thái rỗng, và câu đó **nằm trong khung nhìn** (kỷ luật #21:
 *      "có trong DOM" ≠ "nhìn thấy được");
 *   ③ nút hành động chính (nếu có) cao ≥ 44px — vùng chạm, và quay cận cảnh sẽ lộ nút nhỏ;
 *   ④ trang không cuộn ngang · không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { API, BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";
import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";

doiDangNhap();
const OUT = process.env.OUT_DIR ?? "/tmp/man-rong";
mkdirSync(OUT, { recursive: true });

const MAN = [
  { duong: "/bao-cao", ten: "Báo cáo" },
  { duong: "/de-xuat-dat-hang", ten: "Đề xuất đặt hàng" },
  { duong: "/nhap-nhanh", ten: "Nhập hàng" },
  { duong: "/khoi-tao-ton", ten: "Khởi tạo tồn" },
  { duong: "/cai-dat", ten: "Cài đặt" },
  { duong: "/nhan-vien", ten: "Nhân viên" },
];

// Tự kiểm phép đo trước khi tin nó (kỷ luật #15): CSDL phải THẬT SỰ rỗng, nếu không mọi
// khẳng định "màn rỗng nói gì" ở dưới là đúng vô nghĩa — nó đang đo một màn có dữ liệu.
const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
if (!phien.access_token) {
  console.error("🔴 Đăng nhập API thất bại — không kiểm được điều kiện dữ liệu.");
  process.exit(2);
}
// 🔴 `/sales` trả về MỘT MẢNG, không phải `{total}`. Lượt chạy đầu hỏi `.total` ⇒ `undefined`
//    ⇒ cổng tự dừng ở bước tiền kiểm. Đó là phép đo hỏng, không phải sản phẩm hỏng — kỷ luật
//    #15: một kết quả vô nghĩa luôn đáng dừng lại đọc kỹ trước khi sửa sản phẩm.
const donBan = await (
  await fetch(`${API}/sales?limit=5`, {
    headers: { Authorization: `Bearer ${phien.access_token}` },
  })
).json();
if (!Array.isArray(donBan)) {
  console.error(`🔴 /sales trả về ${typeof donBan}, không phải mảng — phép đo lạc hậu, dừng.`);
  process.exit(2);
}
const soDon = donBan.length;
console.log(
  `điều kiện: CSDL có ${soDon} đơn bán ${soDon === 0 ? "✓ (rỗng, đúng thứ cần đo)" : "🔴 KHÔNG rỗng — đây không phải phép đo trạng thái rỗng"}`,
);
if (soDon !== 0) process.exit(2);

const b = await firefox.launch();
let hong = 0;

for (const [ten, w, h, mob] of [
  ["desktop", 1440, 900, false],
  ["mobile", 390, 844, true],
]) {
  const ctx = await b.newContext({
    viewport: { width: w, height: h },
    isMobile: mob,
    hasTouch: mob,
    deviceScaleFactor: 2,
  });
  const p = await ctx.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e).slice(0, 120)));

  await p.goto(`${BASE}/login`, { waitUntil: "load" });
  await p.waitForTimeout(1500);
  await p.fill('input[type="email"]', EMAIL);
  await p.fill('input[type="password"]', PASSWORD);
  await p.click('button[type="submit"]');
  await p.waitForTimeout(4000);

  console.log(`\n──${ten}──`);
  for (const { duong, ten: tenMan } of MAN) {
    await p.goto(`${BASE}${duong}`, { waitUntil: "load" });
    await p.waitForTimeout(3000);

    // 🔴 HAI LỖI PHÉP ĐO của lượt chạy đầu, cùng một họ — cả hai cho ra kết quả ĐỒNG LOẠT
    //    12/12 đỏ, và một kết quả đồng loạt như thế gần như luôn là lỗi thước đo:
    //
    //    (a) locator dùng `hasText: /\S{25,}/` — `\S{25,}` đòi **25 ký tự liền không dấu
    //        cách**. Mọi câu tiếng Việt đều có dấu cách, nên nó không khớp câu nào cả và
    //        `.first()` rơi vào một phần tử khác hẳn phần tử mà `evaluate` vừa tìm được;
    //    (b) nút đo bằng `p.locator("button")` toàn trang — ở khổ điện thoại nó bắt trúng
    //        nút **Thêm của thanh điều hướng** (60px), không phải nút của màn đang đo.
    //
    //    Cách chữa cho cả hai: đo **một** phần tử, ngay trong `evaluate`, và đo luôn hình
    //    học của chính nó — không để hai lượt tìm khác nhau trả về hai phần tử khác nhau.
    const d = await p.evaluate(() => {
      const chu = document.body.innerText.trim();
      const noiDung = document.querySelector("main") ?? document.body;
      const trongKhung = (e) => {
        const r = e.getBoundingClientRect();
        return (
          r.width > 0 &&
          r.height > 0 &&
          r.top >= 0 &&
          r.left >= 0 &&
          r.right <= window.innerWidth &&
          r.bottom <= window.innerHeight
        );
      };
      // Câu giải thích trạng thái rỗng: một đoạn văn xuôi đủ dài, KHÔNG phải nhãn nút hay
      // tiêu đề cột. Bắt theo hình dạng — ≥25 ký tự VÀ có dấu cách — thay vì chép nguyên
      // văn câu hiện tại, để đổi lời văn không làm đỏ cổng vì lý do sai.
      const ung = [...noiDung.querySelectorAll("p, [class*='rong'], [class*='empty']")].filter(
        (e) => {
          const t = e.innerText?.trim() ?? "";
          return t.length >= 25 && t.includes(" ");
        },
      );
      // Nút hành động của MÀN, tìm trong vùng nội dung — không tính thanh điều hướng.
      const nut = [...noiDung.querySelectorAll("button")].find((e) =>
        /^(Thêm|Tạo|\+)/.test(e.innerText?.trim() ?? ""),
      );
      return {
        trang: chu.length < 40,
        soChu: chu.length,
        coCauGiaiThich: ung.length > 0,
        // "Nhìn thấy được" tính trên BẤT KỲ câu giải thích nào — chỉ cần một câu lọt vào
        // khung nhìn là người dùng đọc được lời giải thích (kỷ luật #21).
        cauNhinThay: ung.some(trongKhung),
        cau: ung[0]?.innerText.trim().slice(0, 70) ?? "",
        caoNut: nut ? Math.round(nut.getBoundingClientRect().height) : null,
      };
    });

    const oCau = { dat: d.cauNhinThay, ly_do: d.coCauGiaiThich ? "khuất ngoài khung nhìn" : "không có câu giải thích nào" };
    const hopNut = d.caoNut === null ? null : { height: d.caoNut };
    const nutDat = hopNut === null || hopNut.height >= 44;

    const cuon = await cuonNgangTrang(p);
    const dat = !d.trang && d.coCauGiaiThich && oCau.dat && nutDat && cuon.dat;
    if (!dat) hong++;

    await p.screenshot({ path: `${OUT}/${ten}-${duong.slice(1)}.png`, fullPage: true });
    console.log(
      `  ${tenMan.padEnd(18)} ${dat ? "✓" : "🔴"}  ${d.soChu} ký tự · ` +
        `giải thích: ${d.coCauGiaiThich ? (oCau.dat ? "✓ nhìn thấy" : "🔴 có nhưng KHUẤT") : "🔴 KHÔNG CÓ"}` +
        ` · nút: ${hopNut ? `${Math.round(hopNut.height)}px ${nutDat ? "✓" : "🔴"}` : "—"}` +
        ` · cuộn ngang: ${cuon.dat ? "✓" : "🔴"}` +
        (d.cau ? `\n${" ".repeat(21)}"${d.cau}…"` : ""),
    );
  }
  if (loi.length) {
    console.log(`  🔴 lỗi JS: ${loi.join(" | ")}`);
    hong++;
  }
  await ctx.close();
}

await b.close();
console.log(`\nẢnh: ${OUT}`);
if (hong > 0) {
  console.log(`🔴 ${hong} chỗ có vấn đề.`);
  process.exit(1);
}
console.log("✅ Sáu màn đều nói rõ khi rỗng.");
