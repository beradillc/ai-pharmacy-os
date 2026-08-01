/**
 * Cài đặt → **Tài khoản của tôi** — cổng cho lỗi M-03 (UAT 2026-08-01).
 *
 * 🔴 ĐỌC THUẦN. Không đổi mật khẩu, không đổi gì.
 *
 * Đo bốn mệnh đề:
 *   1. bốn dòng hồ sơ có mặt **và có giá trị thật** — không dòng nào là `—` hay rỗng.
 *      Một khối hồ sơ toàn gạch ngang trông y hệt một khối hồ sơ đang chạy;
 *   2. họ tên và email **khớp đúng thứ API trả** — cổng tự gọi `/auth/me` bằng token của
 *      chính nó và so, thay vì tin bất cứ chuỗi nào đọc được trên màn;
 *   3. giá trị **nhìn thấy được** ở khổ điện thoại (kỷ luật #21), trang không cuộn ngang;
 *   4. không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";
import { API, BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/tai-khoan";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

// Sự thật để đối chiếu, lấy thẳng từ API — không phải từ màn hình đang kiểm.
const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
const thatSu = await (
  await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${phien.access_token}` } })
).json();
if (!thatSu.full_name || !thatSu.email) {
  // Tự kiểm chính phép đo (kỷ luật #15): nếu API không trả hai trường này thì mọi so sánh
  // bên dưới thành đúng vô nghĩa, và cổng sẽ xanh trong lúc màn hình rỗng.
  console.error(`🔴 /auth/me KHÔNG trả full_name/email — không có gì để đối chiếu.`);
  process.exit(2);
}

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

  await p.goto(`${BASE}/cai-dat`, { waitUntil: "load" });
  await p.waitForTimeout(3000);

  const d = await p.evaluate(() => {
    const doc = [...document.querySelectorAll('[data-testid="ho-so"] > div')];
    const cap = doc.map((r) => [
      r.querySelector("dt")?.innerText.trim() ?? "",
      r.querySelector("dd")?.innerText.trim() ?? "",
    ]);
    return {
      soDong: cap.length,
      // Giá trị RỖNG hay `—` = khối hồ sơ không nói được gì, mà nhìn thì vẫn như đang chạy.
      trong: cap.filter(([, v]) => v === "" || v === "—").map(([k]) => k),
      hoTen: cap.find(([k]) => k === "Họ tên")?.[1] ?? null,
      email: cap.find(([k]) => k === "Email đăng nhập")?.[1] ?? null,
    };
  });

  await p.screenshot({ path: `${OUT}/${ten}-1-tai-khoan.png`, fullPage: true });

  const oHoTen = await trongKhungNhin(p, p.locator('[data-testid="ho-so"] dd').first());
  const cuon = await cuonNgangTrang(p);

  const khopTen = d.hoTen === thatSu.full_name;
  const khopEmail = d.email === thatSu.email;

  const dat =
    d.soDong === 4 &&
    d.trong.length === 0 &&
    khopTen &&
    khopEmail &&
    oHoTen.dat &&
    cuon.dat &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  ${d.soDong}/4 dòng hồ sơ ${d.soDong === 4 ? "✓" : "🔴"} · dòng trống: ${d.trong.length ? "🔴 " + d.trong.join(", ") : "0 ✓"}`);
  console.log(`  họ tên "${d.hoTen}" khớp API: ${khopTen ? "✓" : `🔴 (API nói "${thatSu.full_name}")`}`);
  console.log(`  email  "${d.email}" khớp API: ${khopEmail ? "✓" : `🔴 (API nói "${thatSu.email}")`}`);
  inDong("giá trị đầu nhìn thấy được", oHoTen);
  inDong("trang không cuộn ngang", cuon);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Tài khoản của tôi hiện đúng người đang đăng nhập." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
