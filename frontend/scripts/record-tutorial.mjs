/**
 * Quay video hướng dẫn cơ bản — khổ iPhone, có chấm chạm, khớp nhịp giọng đọc.
 *
 * Video ĐƯỢC ĐỒNG BỘ THEO GIỌNG, không phải ngược lại: mỗi đoạn thuyết minh đã
 * biết trước dài bao nhiêu giây (đo bằng `ffprobe`), và `hold()` giữ màn hình
 * cho tới khi đủ thời lượng đó. Cách này khỏi phải đoán "chắc chỗ này 8 giây" —
 * đoán thì tới đoạn 12 là lệch hẳn một câu, và lệch tiếng nói với hình ở video
 * hướng dẫn thì tệ hơn không có tiếng.
 *
 * Chạy:
 *   cd frontend
 *   BERAS_EMAIL=… BERAS_PASSWORD=… BERAS_DURATIONS=/đường/dẫn/durations.json \
 *   BERAS_OUT=/đường/dẫn/quay node scripts/record-tutorial.mjs
 *
 * KHÔNG nhúng mật khẩu — đọc từ biến môi trường (yêu cầu số 7 của Chain).
 */
import { readFileSync, writeFileSync } from "node:fs";

import { webkit } from "playwright-core";

const BASE = process.env.BERAS_BASE ?? "http://192.168.1.10:3000";
const EMAIL = process.env.BERAS_EMAIL;
const PASSWORD = process.env.BERAS_PASSWORD;
const OUT = process.env.BERAS_OUT;
const DUR = JSON.parse(readFileSync(process.env.BERAS_DURATIONS, "utf8"));

if (!EMAIL || !PASSWORD || !OUT) {
  console.error("Thiếu BERAS_EMAIL / BERAS_PASSWORD / BERAS_OUT.");
  process.exit(2);
}

/** iPhone 17 — 6,3", 1206×2622 vật lý ở @3x ⇒ 402×874 điểm.
 * Quay ở gấp đôi cho nét, ffmpeg khỏi phải phóng lên sau. */
const VIEWPORT = { width: 402, height: 874 };
const VIDEO = { width: 804, height: 1748 };

/** Khoảng lặng giữa hai đoạn nói — không có nó thì câu nọ dính câu kia. */
const GAP_MS = 700;

/** Quay bằng **WebKit** — đúng engine Safari trên iPhone, tức là đúng thứ người
 * xem sẽ thấy khi họ tự làm theo.
 *
 * 🔴 Không phải chọn cho có: ô `<input type="date">` vẽ theo **vùng miền của
 * trình duyệt**, không theo `lang` của trang. Đo cả ba cách:
 *
 * | Cách quay | Ô ngày hiện ra |
 * |---|---|
 * | Firefox mặc định | `09 / 20 / 2026` — kiểu Mỹ |
 * | Firefox + `LC_ALL=vi_VN` + `use_OS_locale` | `09 / 20 / 2026` — **không đổi** |
 * | **WebKit** | **`20/09/2026`** — đúng kiểu Việt Nam |
 *
 * (`navigator.language` và `toLocaleDateString()` đều đúng `vi-VN` ở cả ba —
 * nên nhìn qua thì tưởng đã đặt locale xong. Chỉ ô ngày mới lộ ra.) Bản Firefox
 * Playwright đóng gói không có gói ngôn ngữ tiếng Việt nên `intl.locale.requested`
 * không có tác dụng. Đây KHÔNG phải lỗi sản phẩm — `html lang="vi"` vốn đúng và
 * máy Chain đặt tiếng Việt sẽ ra `dd/mm/yyyy` — nhưng để nguyên trong video thì
 * người mới sẽ tưởng phần mềm ghi ngày kiểu Mỹ. */
const browser = await webkit.launch();
const ctx = await browser.newContext({
  viewport: VIEWPORT,
  deviceScaleFactor: 2,
  locale: "vi-VN",
  timezoneId: "Asia/Ho_Chi_Minh",
  recordVideo: { dir: OUT, size: VIDEO },
});
/** Bật giao diện **Warm** trước khi trang kịp vẽ.
 *
 * Ghi thẳng vào `localStorage` chứ không bấm qua Cài đặt → Giao diện: bấm qua
 * màn Cài đặt thì khung hình đầu tiên vẫn là Classic rồi mới đổi, tức là video
 * mở màn bằng đúng cái theme KHÔNG định giới thiệu. `ThemeProvider` đọc khoá này
 * trong `THEME_INIT_SCRIPT` đặt ở `<head>`, nên đặt sẵn là không có nháy màu. */
await ctx.addInitScript(() => {
  try {
    localStorage.setItem("beras.theme", "warm");
  } catch {
    /* chế độ riêng tư — kệ, chỉ mất theme chứ không hỏng gì */
  }
});

const page = await ctx.newPage();

/** Mốc 0 của cuốn phim. Playwright bắt đầu quay từ lúc trang được tạo, nên mọi
 * thứ sau dòng này đo được bằng mili-giây so với khung hình đầu tiên.
 *
 * 🔴 Cần cái này vì ghép tiếng theo TỔNG thời lượng là sai: giữa các đoạn còn
 * `goto`, còn hiệu ứng gỡ bìa, còn thời gian trình duyệt tải. Lượt ghép đầu
 * lệch **7,1 giây** (hình 187,2s · tiếng 180,0s) — tới đoạn cuối thì giọng nói
 * về một màn hình đã trôi qua. Nên script XUẤT RA mốc thật của từng đoạn, và
 * khâu ghép đặt từng câu vào đúng mốc đó thay vì nối đuôi nhau. */
const T0 = Date.now();
const timeline = {};

/** Chấm chạm: video không quay được con trỏ, nên người xem sẽ thấy giao diện tự
 * đổi mà không biết vừa bấm vào đâu. Vẽ một vòng tròn lan toả tại đúng điểm bấm. */
await page.addInitScript(() => {
  window.__tap = (x, y) => {
    const d = document.createElement("div");
    d.style.cssText = `position:fixed;left:${x - 26}px;top:${y - 26}px;width:52px;height:52px;
      border-radius:50%;border:3px solid rgba(45,122,90,.9);background:rgba(45,122,90,.18);
      z-index:2147483647;pointer-events:none;transition:transform .45s ease-out,opacity .45s ease-out`;
    document.body.appendChild(d);
    requestAnimationFrame(() => {
      d.style.transform = "scale(1.7)";
      d.style.opacity = "0";
    });
    setTimeout(() => d.remove(), 500);
  };
});

let segStart = Date.now();
let seg = null;

/** Mở một đoạn: ghi mốc thời gian để `hold()` biết đã trôi bao lâu. */
function begin(id) {
  seg = id;
  segStart = Date.now();
  timeline[id] = segStart - T0;
  process.stdout.write(`  đoạn ${id} (${DUR[id]}s) … `);
}

/** Giữ màn hình cho tới khi hết đoạn thuyết minh. Nếu thao tác đã lâu hơn giọng
 * đọc thì KHÔNG cắt ngắn — báo ra để còn biết mà viết lại lời thoại. */
async function hold() {
  const need = DUR[seg] * 1000 + GAP_MS;
  const left = need - (Date.now() - segStart);
  if (left > 0) await page.waitForTimeout(left);
  else process.stdout.write(`⚠ tràn ${Math.round(-left / 1000)}s `);
  console.log("✓");
}

async function tap(locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (box) await page.evaluate(([x, y]) => window.__tap(x, y), [box.x + box.width / 2, box.y + box.height / 2]);
  await page.waitForTimeout(280);
  await locator.click();
}

/** Gõ chậm như người thật. Điền một phát thì người xem không kịp thấy gõ gì. */
async function type(locator, text, delay = 55) {
  await locator.scrollIntoViewIfNeeded();
  await locator.click();
  await locator.fill("");
  await locator.type(text, { delay });
}

/**
 * Bìa mở có hoạt hình — chữ hiện dần, vạch sáng quét ngang, rồi mờ đi.
 *
 * Ba giây là ngắn, nên mọi thứ phải xong trong khoảng đó: chữ vào ở 0,15s, vạch
 * quét 0,5→1,4s, dòng phụ 1,0s. Dùng nền coral→hổ phách của chính theme Warm
 * đang giới thiệu, không phải một màu thương hiệu khác — bìa mở lệch tông với
 * sản phẩm là thứ người xem nhận ra ngay dù không gọi tên được.
 */
async function intro() {
  await page.evaluate(() => {
    const el = document.createElement("div");
    el.id = "__intro";
    el.innerHTML = `
      <style>
        @keyframes bIn{from{opacity:0;transform:translateY(14px) scale(.965)}to{opacity:1;transform:none}}
        @keyframes bSweep{from{transform:translateX(-130%)}to{transform:translateX(130%)}}
        @keyframes bBar{from{width:0}to{width:112px}}
      </style>
      <div style="position:relative;display:flex;flex-direction:column;
                  align-items:center;gap:16px;padding:0 30px;text-align:center">
        <div style="font-size:13px;letter-spacing:.52em;opacity:0;animation:bIn .7s .15s both;
                    text-indent:.52em">PHẦN MỀM QUẢN LÝ NHÀ THUỐC</div>
        <div style="font-size:58px;font-weight:800;letter-spacing:.06em;opacity:0;
                    animation:bIn .8s .3s both">BERAS</div>
        <div style="height:3px;border-radius:2px;background:rgba(255,255,255,.85);
                    animation:bBar .7s .75s both"></div>
        <div style="font-size:17px;opacity:0;animation:bIn .8s 1s both;line-height:1.5">
          Nhà thuốc 650<br><span style="opacity:.8;font-size:14px">Bản thử nghiệm</span></div>
      </div>
      <div style="position:absolute;inset:0;pointer-events:none;
                  background:linear-gradient(105deg,transparent 42%,rgba(255,255,255,.30) 50%,transparent 58%);
                  animation:bSweep 1.5s .5s both"></div>`;
    el.style.cssText = `position:fixed;inset:0;z-index:2147483646;display:flex;align-items:center;
      justify-content:center;overflow:hidden;color:#fff;font-family:system-ui,sans-serif;
      background:radial-gradient(120% 90% at 30% 15%,#E0574C 0%,#C6413A 45%,#B8730B 100%)`;
    document.body.appendChild(el);
  });
}

/** Tấm bìa đầu/cuối — vẽ chồng lên trang, gỡ ngay sau đó. */
async function card(title, subtitle) {
  await page.evaluate(
    ([t, s]) => {
      const el = document.createElement("div");
      el.id = "__card";
      el.style.cssText = `position:fixed;inset:0;z-index:2147483646;display:flex;flex-direction:column;
        align-items:center;justify-content:center;gap:14px;text-align:center;padding:0 34px;
        background:linear-gradient(160deg,#C6413A,#B8730B);color:#fff;
        font-family:system-ui,sans-serif;opacity:0;transition:opacity .5s`;
      el.innerHTML =
        `<div style="font-size:15px;letter-spacing:.34em;opacity:.75">B E R A S</div>` +
        `<div style="font-size:31px;font-weight:700;line-height:1.25">${t}</div>` +
        `<div style="font-size:16px;opacity:.85;line-height:1.5">${s}</div>`;
      document.body.appendChild(el);
      requestAnimationFrame(() => (el.style.opacity = "1"));
    },
    [title, subtitle],
  );
}

async function uncard() {
  await page.evaluate(() => {
    const el = document.getElementById("__card");
    if (!el) return;
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 500);
  });
  await page.waitForTimeout(520);
}

const go = async (path) => {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
};

try {
  // ── 00 · intro 3 giây ─────────────────────────────────────────────────────
  await go("/login");
  begin("00");
  await intro();
  await hold();
  await page.evaluate(() => {
    const el = document.getElementById("__intro");
    if (!el) return;
    el.style.transition = "opacity .55s";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 600);
  });
  await page.waitForTimeout(560);

  // ── 01 · lời chào ─────────────────────────────────────────────────────────
  begin("01");
  await card("Nhà thuốc 650", "Bản thử nghiệm · nhập hàng → tồn kho → bán hàng → hoá đơn");
  await hold();
  await uncard();

  // ── 02 · đăng nhập ────────────────────────────────────────────────────────
  begin("02");
  await type(page.locator('input[type="email"]'), EMAIL, 42);
  await page.waitForTimeout(400);
  await type(page.locator('input[type="password"]'), PASSWORD, 42);
  await page.waitForTimeout(500);
  await tap(page.locator('button[type="submit"]'));
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 25_000 });
  await page.waitForResponse((r) => r.url().includes("/drugs"), { timeout: 15_000 }).catch(() => {});
  await hold();

  // ── 03 · tổng quan ────────────────────────────────────────────────────────
  begin("03");
  await go("/bang-dieu-hanh");
  await page.waitForTimeout(1800);
  await page.mouse.wheel(0, 420);
  await page.waitForTimeout(1400);
  await page.mouse.wheel(0, 420);
  await hold();

  // ── 04 · đơn mua hàng ─────────────────────────────────────────────────────
  begin("04");
  await go("/don-mua-hang");
  const receiveBtn = page.locator('button:has-text("Nhận hàng")').first();
  await receiveBtn.waitFor({ timeout: 25_000 });
  await page.waitForTimeout(2200);
  await tap(receiveBtn);
  const drawer = page.locator('dialog[aria-label*="Nhận hàng"]');
  await drawer.locator("tbody tr").first().waitFor({ timeout: 25_000 });
  await hold();

  // ── 05 · điền dòng 1: số lô + hạn dùng còn xa ─────────────────────────────
  begin("05");
  await drawer.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  await type(page.locator('input[aria-label^="Số lượng nhận"]').first(), "100", 90);
  await page.waitForTimeout(350);
  await type(page.locator('input[aria-label^="Số lô"]').first(), "L2026A", 80);
  await page.waitForTimeout(350);
  await page.locator('input[aria-label^="Hạn dùng"]').first().fill("2028-03-31");
  await hold();

  // ── 06 · dòng 2: hạn gần ⇒ cảnh báo · nhận thiếu ⇒ "một phần" ─────────────
  begin("06");
  await type(page.locator('input[aria-label^="Số lượng nhận"]').nth(1), "60", 90);
  await page.waitForTimeout(300);
  await type(page.locator('input[aria-label^="Số lô"]').nth(1), "L2026B", 80);
  await page.waitForTimeout(300);
  await page.locator('input[aria-label^="Hạn dùng"]').nth(1).fill("2026-09-20");
  await page.waitForTimeout(1400);
  await hold();

  // ── 07 · chốt phiếu ───────────────────────────────────────────────────────
  begin("07");
  await tap(page.locator('button:has-text("Nhận hàng & chốt phiếu")'));
  await page.locator("text=Đã nhận hàng và chốt phiếu").waitFor({ timeout: 25_000 });
  await hold();

  // ── 08 · tồn kho ──────────────────────────────────────────────────────────
  begin("08");
  await go("/ton-kho");
  await page.locator("tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1200);
  await type(page.locator('input[placeholder*="Lọc theo tên thuốc"]'), "L2026", 100);
  await page.waitForTimeout(2000);
  await hold();

  // ── 09 · bán hàng: tìm thuốc ─────────────────────────────────────────────
  begin("09");
  await go("/");
  // Thuốc KHÔNG kê đơn. Thuốc ETC bị backend chặn đúng theo quy định
  // ("cần đơn thuốc hợp lệ") — quay cảnh đó vào video hướng dẫn CƠ BẢN thì
  // người mới sẽ tưởng phần mềm hỏng.
  const search = page.locator('input[placeholder*="Tìm thuốc"]');
  await search.waitFor({ timeout: 25_000 });
  await page.waitForTimeout(900);
  await type(search, "Berberin", 110);
  await page.waitForTimeout(1500);
  await hold();

  // ── 10 · thêm vào giỏ ────────────────────────────────────────────────────
  begin("10");
  await tap(page.locator('button:has-text("Thêm")').first());
  await page.waitForTimeout(1400);
  await hold();

  // ── 11 · thêm hai loại nữa ───────────────────────────────────────────────
  begin("11");
  for (const q of ["Efferalgan", "Cetirizin"]) {
    await type(search, q, 70);
    await page.waitForTimeout(900);
    await tap(page.locator('button:has-text("Thêm")').first());
    await page.waitForTimeout(700);
  }
  await page.mouse.wheel(0, 700);
  await hold();

  // ── 12 · thanh toán ──────────────────────────────────────────────────────
  begin("12");
  const pay = page.locator('button:has-text("Thanh toán")');
  await tap(pay);
  await page.locator("text=Đã bán thành công").waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1200);
  await hold();

  // ── 13 · hoá đơn ─────────────────────────────────────────────────────────
  begin("13");
  await go("/hoa-don");
  await page.locator("tbody tr").first().waitFor({ timeout: 25_000 });
  await page.waitForTimeout(1600);
  await page.mouse.wheel(0, 300);
  await hold();

  // ── 14 · báo cáo ─────────────────────────────────────────────────────────
  begin("14");
  await go("/bao-cao");
  await page.waitForTimeout(2200);
  await page.mouse.wheel(0, 350);
  await hold();

  // ── 15 · bìa kết ─────────────────────────────────────────────────────────
  begin("15");
  await card("Xong một vòng", "Nhập hàng · Tồn kho · Bán hàng · Hoá đơn · Báo cáo");
  await hold();
} finally {
  await ctx.close();
  await browser.close();
}
writeFileSync(`${OUT}/timeline.json`, JSON.stringify(timeline, null, 2));
console.log("Mốc thời gian từng đoạn đã ghi ra timeline.json");
console.log("Đã quay xong.");
