/**
 * UAT + UX + Mobile audit — CHỈ ĐỌC, không bấm nút ghi, không đổi dữ liệu.
 *
 * Sinh dữ liệu THẬT cho báo cáo: mỗi màn × mỗi khổ × mỗi engine, ghi lại nút/ô nhập/bảng/
 * trạng thái rỗng/lỗi JS/tràn khung nhìn. Báo cáo viết từ tệp JSON này, không viết từ trí nhớ.
 */
import { firefox, webkit } from "playwright-core";
import { writeFileSync, mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL, PASSWORD = process.env.PASSWORD;
const OUT = process.env.OUT_DIR ?? "../docs/testing";
mkdirSync(`${OUT}/anh`, { recursive: true });

const MAN = [
  ["/", "Bán hàng"], ["/bang-dieu-hanh", "Tổng quan"], ["/hoa-don", "Hoá đơn"],
  ["/khach-hang", "Khách hàng"], ["/ton-kho", "Kho"], ["/danh-muc-thuoc", "Danh mục thuốc"],
  ["/nhap-nhanh", "Nhập hàng"], ["/khoi-tao-ton", "Khởi tạo tồn"], ["/kiem-ke", "Kiểm kê"],
  ["/so-do-kho", "Sơ đồ kho"], ["/don-mua-hang", "Đơn mua hàng"],
  ["/de-xuat-dat-hang", "Đề xuất đặt hàng"], ["/bao-cao", "Báo cáo"],
  ["/nhan-vien", "Nhân viên"], ["/cai-dat", "Cài đặt"], ["/cai-dat/luu-tru", "Lưu trữ"],
];

const KHO = [
  ["dt-doc", 390, 844, true],      // iPhone dọc
  ["dt-ngang", 844, 390, true],    // iPhone ngang
  ["tablet", 820, 1180, true],     // iPad dọc
  ["laptop", 1440, 900, false],
];

const ketQua = [];

for (const [tenEngine, engine] of [["webkit", webkit], ["firefox", firefox]]) {
  const b = await engine.launch();
  for (const [khoTen, w, h, mob] of KHO) {
    // WebKit + firefox × 4 khổ = 8 lượt; chỉ chụp ảnh ở WebKit để khỏi phình thư mục.
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: mob, hasTouch: mob, deviceScaleFactor: mob ? 2 : 1 });
    const p = await ctx.newPage();
    const loiToanCuc = [];
    p.on("pageerror", (e) => loiToanCuc.push(String(e).slice(0, 160)));

    await p.goto(`${BASE}/login`, { waitUntil: "load" }).catch(() => {});
    await p.waitForTimeout(2000);
    await p.fill('input[type="email"]', EMAIL).catch(() => {});
    await p.fill('input[type="password"]', PASSWORD).catch(() => {});
    await p.click('button[type="submit"]').catch(() => {});
    await p.waitForTimeout(5000);

    for (const [duong, ten] of MAN) {
      const loiTruoc = loiToanCuc.length;
      await p.goto(`${BASE}${duong}`, { waitUntil: "load" }).catch(() => {});
      await p.waitForTimeout(2600);

      const d = await p.evaluate(() => {
        const vw = document.documentElement.clientWidth;
        const nut = [...document.querySelectorAll("button")]
          .filter((e) => e.getBoundingClientRect().height > 0)
          .map((e) => (e.innerText || e.getAttribute("aria-label") || "").trim())
          .filter(Boolean);
        const oNhap = [...document.querySelectorAll("input:not([type=hidden]), select, textarea")]
          .filter((e) => e.getBoundingClientRect().height > 0)
          .map((e) => e.getAttribute("aria-label") || e.getAttribute("placeholder") || e.type || "?");
        const cao = [...document.querySelectorAll("input:not([type=hidden]), select")]
          .map((e) => ({ n: e.getAttribute("aria-label") || e.type, h: Math.round(e.getBoundingClientRect().height) }))
          .filter((x) => x.h > 96);
        const nhoHon44 = [...document.querySelectorAll("button, a[href]")]
          .map((e) => ({ n: (e.innerText || e.getAttribute("aria-label") || "").trim().slice(0, 24), r: e.getBoundingClientRect() }))
          .filter((x) => x.r.height > 0 && x.r.height < 44 && x.n)
          .map((x) => `${x.n}=${Math.round(x.r.height)}px`);
        const tran = [...document.querySelectorAll("body *")]
          .map((e) => ({ e, r: e.getBoundingClientRect() }))
          .filter(({ r }) => r.width > 0 && r.height > 0 && r.right > vw + 1)
          .filter(({ e }) => { for (let a = e.parentElement; a; a = a.parentElement) { const ox = getComputedStyle(a).overflowX; if (ox === "auto" || ox === "scroll") return false; } return true; })
          .slice(0, 2).map(({ e, r }) => `${e.tagName.toLowerCase()}→${Math.round(r.right)}px`);
        const chu = (document.body.innerText || "");
        return {
          soNut: nut.length, nut: [...new Set(nut)].slice(0, 30),
          soONhap: oNhap.length, oNhap: [...new Set(oNhap)].slice(0, 20),
          soDongBang: document.querySelectorAll("tbody tr").length,
          oNhapCao: cao, chamNhoHon44: [...new Set(nhoHon44)].slice(0, 8),
          tranKhungNhin: tran,
          cuonNgangTrang: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          rong: /chưa có|không có|chưa tìm thấy|trống|Chưa mã nào|0 đơn|— chưa/i.test(chu),
          coLoading: /Đang tải|Đang đọc|Đang tính/i.test(chu),
          chuDai: chu.length,
        };
      }).catch(() => null);

      ketQua.push({ engine: tenEngine, kho: khoTen, duong, ten, ...(d ?? { loi: "không đọc được trang" }), loiJS: loiToanCuc.length - loiTruoc });

      if (tenEngine === "webkit") {
        await p.screenshot({ path: `${OUT}/anh/${khoTen}${duong.replace(/\//g, "_") || "_ban-hang"}.png` }).catch(() => {});
      }
    }
    await ctx.close();
  }
  await b.close();
}

writeFileSync(`${OUT}/uat-raw.json`, JSON.stringify(ketQua, null, 2));
const loi = ketQua.filter((r) => r.loiJS > 0).length;
const tran = ketQua.filter((r) => (r.tranKhungNhin ?? []).length > 0).length;
const cao = ketQua.filter((r) => (r.oNhapCao ?? []).length > 0).length;
const nho = ketQua.filter((r) => (r.chamNhoHon44 ?? []).length > 0).length;
console.log(`Đã đo ${ketQua.length} lượt (màn × khổ × engine)`);
console.log(`  lỗi JS: ${loi} · tràn khung nhìn: ${tran} · ô nhập cao bất thường: ${cao} · chạm <44px: ${nho}`);
