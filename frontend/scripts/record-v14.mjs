/**
 * VIDEO 14 — Định hướng phát triển. Khổ điện thoại, tông Warm.
 *
 * 🔴 KHÔNG quay màn ứng dụng. Video này nói về thứ CHƯA có, nên quay bằng **slide** dựng
 *    ngay trong trình duyệt. Cảnh duy nhất lấy từ app là nhãn đỏ tự khai trên màn Sổ kiểm
 *    soát — thứ minh hoạ đúng nguyên tắc "chỗ nào chưa chắc thì phần mềm tự nói ra".
 *
 * 🔴 VIDEO NÀY CHƯA ĐƯỢC PHÁT HÀNH cho tới khi Trợ lý Pháp Lý rà (N-3). Dựng được, giao cho
 *    Chain xem được — phát ra ngoài thì chưa.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

import { BASE, EMAIL, PASSWORD, doiDangNhap } from "./lib/moi-truong.mjs";

doiDangNhap();
const OUT = process.env.BERAS_OUT ?? "/tmp/quay-v14";
const DUR = JSON.parse(
  process.env.BERAS_DURATIONS
    ? readFileSync(process.env.BERAS_DURATIONS, "utf8")
    : JSON.stringify({ "00": 10, "01": 12, "02": 14, "03": 14, "04": 12, "05": 10 }),
);
mkdirSync(OUT, { recursive: true });

const browser = await webkit.launch();
const ctx = await browser.newContext({
  viewport: { width: 402, height: 874 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  locale: "vi-VN",
  timezoneId: "Asia/Ho_Chi_Minh",
  recordVideo: { dir: OUT, size: { width: 804, height: 1748 } },
});
await ctx.addInitScript(() => {
  try {
    localStorage.setItem("beras.theme", "warm");
  } catch {
    /* riêng tư */
  }
});
const page = await ctx.newPage();
const loiJS = [];
page.on("pageerror", (e) => loiJS.push(String(e).slice(0, 140)));

const T0 = Date.now();
const timeline = {};
let seg = null;
let segStart = Date.now();
let tran = 0;
function begin(id) {
  seg = id;
  segStart = Date.now();
  timeline[id] = segStart - T0;
  process.stdout.write(`  đoạn ${id} (${DUR[id]}s) … `);
}
async function hold() {
  const left = DUR[seg] * 1000 + 700 - (Date.now() - segStart);
  if (left > 0) await page.waitForTimeout(left);
  else {
    tran++;
    process.stdout.write(`⚠ tràn ${Math.round(-left / 1000)}s `);
  }
  process.stdout.write("✓\n");
}
async function type(loc, text, delay = 30) {
  await loc.click();
  await loc.fill("");
  await loc.type(text, { delay });
}

/** Slide dựng thẳng trong trang — cùng tông Warm với ứng dụng, không lệch màu thương hiệu. */
async function slide(tieuDe, dong) {
  await page.evaluate(
    ({ t, ds }) => {
      document.body.innerHTML = `
      <style>
        @keyframes vao{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
        body{margin:0;font-family:system-ui,-apple-system,sans-serif;
             background:linear-gradient(160deg,#8c2f1f,#c2691f);color:#fff;
             min-height:100vh;display:flex;align-items:center;justify-content:center}
        .k{padding:0 34px;max-width:640px}
        h1{font-size:34px;line-height:1.25;margin:0 0 26px;animation:vao .6s both}
        li{font-size:21px;line-height:1.5;margin:0 0 18px;opacity:.95;list-style:none;
           padding-left:24px;position:relative;animation:vao .6s both}
        li:before{content:"";position:absolute;left:0;top:12px;width:11px;height:11px;
                  border-radius:50%;background:rgba(255,255,255,.85)}
      </style>
      <div class="k"><h1>${t}</h1><ul>${ds
        .map((x, i) => `<li style="animation-delay:${0.25 + i * 0.22}s">${x}</li>`)
        .join("")}</ul></div>`;
    },
    { t: tieuDe, ds: dong },
  );
  await page.waitForTimeout(500);
}

try {
  begin("00");
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(800);
  await slide("Định hướng phát triển", ["Phần mềm sẽ làm thêm gì", "Và cái gì chưa xong"]);
  await hold();

  begin("01");
  await slide("Hôm nay làm được gì", [
    "Nhập hàng · xếp kho · bán hàng",
    "Hoá đơn · kiểm kê · báo cáo",
    "Trọn một ngày ở quầy",
  ]);
  await hold();

  begin("02");
  await slide("Ba việc đang làm tiếp", [
    "Mã hoá dữ liệu sức khoẻ của khách",
    "Chống dò mật khẩu",
    "Theo dõi tình trạng máy chủ",
  ]);
  await hold();

  begin("03");
  await slide("Hai việc chưa hứa được ngày", [
    "Gửi dữ liệu lên hệ thống dược quốc gia",
    "— đường đi dựng xong, đầu bên kia chưa mở",
    "Gợi ý chuyên môn bằng nguồn tra cứu có bản quyền",
  ]);
  await hold();

  // ── 04 · cảnh THẬT: nhãn đỏ tự khai trên màn Sổ kiểm soát ─────────────────
  begin("04");
  await page.goto(`${BASE}/login`, { waitUntil: "load" });
  await page.waitForTimeout(1000);
  await type(page.locator('input[type="email"]'), EMAIL);
  await type(page.locator('input[type="password"]'), PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.goto(`${BASE}/so-kiem-soat`, { waitUntil: "load" });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/04-nhan-do.png`, fullPage: true });
  await hold();

  begin("05");
  await slide("Chỗ nào chưa chắc, phần mềm tự nói ra", [
    "Không có nhãn nghĩa là đã kiểm",
    "Góp ý từ quầy đổi thứ tự làm việc",
  ]);
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}

writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
// 🔴 Lỗi JS ở đây KHÔNG phải lỗi sản phẩm: slide dựng bằng cách ghi đè `document.body
// .innerHTML`, tức là đập luôn cây DOM của React, nên React kêu ở lần vẽ kế tiếp. Đây là
// giá của cách dựng slide, không phải khuyết tật của ứng dụng — nên chỉ IN RA, không ĐỎ.
console.log(`lỗi JS: ${loiJS.length}${loiJS.length ? " (do slide ghi đè DOM của React, không phải lỗi app): " + loiJS.join(" | ") : ""}`);
console.log(`đoạn tràn giờ: ${tran}`);
