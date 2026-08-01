/**
 * Chụp đúng những chỗ Chain nêu trên màn Khách hàng, ở cả hai khổ.
 *
 * Mỗi lượt chụp kèm một phép ĐO, vì ảnh không nói được cái quan trọng nhất ở đây:
 * ô chọn có tràn khỏi khung không, khoảng trắng thừa bao nhiêu pixel, dấu ✓ có nằm
 * giữa ô không. Kỷ luật #15: nhìn ảnh rồi vẫn phải đo.
 *
 * Chạy:  BASE_URL=... EMAIL=... PASSWORD=... OUT_DIR=... node scripts/shot-khach-hang.mjs
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const EMAIL = process.env.EMAIL ?? "trinhthu@nhathuoc650.vn";
const PASSWORD = process.env.PASSWORD ?? "NhaThuoc650@2026";
const OUT = process.env.OUT_DIR ?? "/tmp/shots-kh";
const NHAN = process.env.NHAN ?? "truoc";

const KHO = [
  { ten: "desktop", width: 1440, height: 900, mobile: false },
  { ten: "mobile", width: 390, height: 844, mobile: true },
];

mkdirSync(OUT, { recursive: true });
const bang = [];

for (const kho of KHO) {
  const browser = await firefox.launch();
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
  await page.goto(`${BASE}/khach-hang`, { waitUntil: "load" });
  await page.waitForTimeout(2500);

  const chup = async (ten) =>
    page.screenshot({ path: `${OUT}/${NHAN}-${kho.ten}-${ten}.png`, fullPage: true });

  // ① bảng — dấu ✓ có căn giữa ô không, hai nút bên phải chiếm bao nhiêu
  await chup("1-bang");
  const oBang = await page.evaluate(() => {
    const rows = [...document.querySelectorAll("tbody tr")];
    const r0 = rows[0];
    if (!r0) return null;
    const tds = [...r0.querySelectorAll("td")];
    const oDau = tds.find((td) => /[✓✗]/.test(td.innerText));
    const dau = oDau?.querySelector("span");
    const oCuoi = tds[tds.length - 1];
    const nut = [...(oCuoi?.querySelectorAll("button") ?? [])].map((b) => b.textContent?.trim());
    if (!oDau || !dau) return { nut, tenCot: null };
    const ro = oDau.getBoundingClientRect();
    const rd = dau.getBoundingClientRect();
    return {
      nut,
      oTrai: Math.round(ro.left),
      oRong: Math.round(ro.width),
      dauTam: Math.round(rd.left + rd.width / 2 - ro.left),
      oTam: Math.round(ro.width / 2),
      cotCuoiRong: oCuoi ? Math.round(oCuoi.getBoundingClientRect().width) : null,
    };
  });

  /** Mở "Hồ sơ" của dòng thứ `i` (0-based). Từ 31/07 mỗi dòng chỉ còn MỘT nút. */
  const moHoSo = async (i) => {
    await page.locator("tbody tr").nth(i).locator("button", { hasText: /^Hồ sơ$/ }).click();
    await page.waitForTimeout(1500);
  };
  const dong = async () => {
    await page.locator("button", { hasText: /^Đóng$/ }).last().click().catch(() => {});
    await page.waitForTimeout(800);
  };

  // Dòng nào chưa đồng ý (✗) / đã đồng ý (✓) — hai nhánh khác nhau của bảng Hồ sơ.
  const { iChua, iDa } = await page.evaluate(() => {
    const rows = [...document.querySelectorAll("tbody tr")];
    return {
      iChua: rows.findIndex((r) => r.innerText.includes("✗")),
      iDa: rows.findIndex((r) => r.innerText.includes("✓")),
    };
  });

  // ② panel Đồng ý — nay vào qua Hồ sơ của một khách CHƯA đồng ý
  await moHoSo(iChua);
  await page.locator("button", { hasText: /Hỏi khách để lấy đồng ý/ }).click();
  await page.waitForTimeout(1500);
  await chup("2-dong-y");
  const oDongY = await page.evaluate(() => {
    // 🔴 PHẢI khoanh trong panel. Lần đo đầu (31/07) tôi lọc `button` trên cả trang và
    // bắt trúng 12 nút "Đồng ý" của 12 DÒNG BẢNG phía sau — số liệu "202px trống thừa,
    // xếp dọc" khi ấy là của hai nút thuộc hai dòng khác nhau, tức vô nghĩa. Kỷ luật
    // #15: một kết quả tự mâu thuẫn (370px chứa 168px nút mà vẫn xuống dòng) luôn là
    // lỗi phép đo, không phải lỗi sản phẩm.
    const panel = document.querySelector('dialog[aria-label^="Đồng ý"]');
    if (!panel) return null;
    const muc = panel.querySelectorAll("li");
    const m0 = muc[0];
    if (!m0) return null;
    const chu = m0.querySelector("div");
    const nuts = [...m0.querySelectorAll("button")];
    const rM = m0.getBoundingClientRect();
    const rC = chu?.getBoundingClientRect();
    const rN = nuts[0]?.getBoundingClientRect();
    return {
      soMuc: muc.length,
      soNutMoiMuc: nuts.length,
      mucCao: Math.round(rM.height),
      chuCao: rC ? Math.round(rC.height) : null,
      /** Chỗ trống DỌC giữa đáy khối chữ và đỉnh hàng nút — "khoảng trắng dư thừa". */
      trongDoc: rC && rN ? Math.round(rN.top - rC.bottom) : null,
    };
  });
  await dong();

  // ③ panel Sức khoẻ — khách ĐÃ đồng ý thì mới có ô nhập
  await moHoSo(iDa);
  await chup("3-suc-khoe");
  const oChon = await page.evaluate(() => {
    const sels = [...document.querySelectorAll("select")];
    const vw = window.innerWidth;
    return sels.map((s) => {
      const r = s.getBoundingClientRect();
      const dai = [...s.options].reduce((m, o) => Math.max(m, o.text.length), 0);
      return {
        nhan: s.closest("label")?.querySelector("span")?.textContent?.trim() ?? "?",
        rong: Math.round(r.width),
        phai: Math.round(r.right),
        tran: Math.round(Math.max(0, r.right - vw)),
        soLuaChon: s.options.length,
        chuDaiNhat: dai,
      };
    });
  });
  // ④ Bệnh nền — bấm 3 chip, xem có giữ được cả 3 không (trước chỉ giữ 1)
  const chips = page.locator("[aria-pressed]");
  const soChip = await chips.count();
  for (const i of [0, 1, 2]) await chips.nth(i).click();
  await page.waitForTimeout(500);
  const oBenhNen = await page.evaluate(() => ({
    soChip: document.querySelectorAll("[aria-pressed]").length,
    dangChon: [...document.querySelectorAll('[aria-pressed="true"]')].length,
    nhanNut:
      [...document.querySelectorAll("button")]
        .map((b) => b.textContent?.trim())
        .find((t) => t?.startsWith("Thêm ") && t.includes("bệnh nền")) ?? null,
  }));
  await chup("4-benh-nen");

  // ⑤ Bảng chọn hoạt chất — lớp phủ tự viết, phải KHÔNG kín màn và phải có nút Đóng
  await page.locator("button", { hasText: /chọn hoạt chất/ }).first().click();
  await page.waitForTimeout(900);
  await chup("5-chon-hoat-chat");
  const oBangChon = await page.evaluate(() => {
    const hop = document.querySelector('[role="dialog"] > div');
    if (!hop) return null;
    const r = hop.getBoundingClientRect();
    const nutDong = [...hop.querySelectorAll("button")].some(
      (b) => b.textContent?.trim() === "Đóng",
    );
    return {
      cao: Math.round(r.height),
      vh: window.innerHeight,
      phanTramMan: Math.round((r.height / window.innerHeight) * 100),
      coNutDong: nutDong,
      coOTim: !!hop.querySelector("input"),
      soDong: hop.querySelectorAll("li").length,
    };
  });

  bang.push({ kho: kho.ten, oBang, oDongY, oChon, oBenhNen, oBangChon, soChip });
  await browser.close();
}

for (const b of bang) {
  console.log(`\n════ ${b.kho} ════`);
  console.log(`① Bảng · nút cột cuối: ${JSON.stringify(b.oBang?.nut)} · cột cuối rộng ${b.oBang?.cotCuoiRong}px`);
  console.log(`   dấu ✓: tâm ở ${b.oBang?.dauTam}px, tâm ô ở ${b.oBang?.oTam}px ` +
    `→ lệch ${Math.abs((b.oBang?.dauTam ?? 0) - (b.oBang?.oTam ?? 0))}px ` +
    `${Math.abs((b.oBang?.dauTam ?? 0) - (b.oBang?.oTam ?? 0)) <= 2 ? "✓ giữa" : "🔴 KHÔNG giữa"}`);
  console.log(`② Đồng ý · ${b.oDongY?.soMuc} mục, ${b.oDongY?.soNutMoiMuc} nút/mục · mục cao ${b.oDongY?.mucCao}px ` +
    `(chữ ${b.oDongY?.chuCao}px) → trống dọc thừa ${b.oDongY?.trongDoc}px ` +
    `${(b.oDongY?.trongDoc ?? 0) > 24 ? "🔴" : "✓"}`);
  for (const s of b.oChon ?? []) {
    console.log(`③ Ô chọn "${s.nhan}" · rộng ${s.rong}px · mép phải ${s.phai} · tràn ${s.tran}px ` +
      `${s.tran > 0 ? "🔴" : "✓"} · ${s.soLuaChon} lựa chọn · chữ dài nhất ${s.chuDaiNhat} ký tự`);
  }
  console.log(`④ Bệnh nền · ${b.oBenhNen?.soChip} chip · bấm 3 chip → giữ ${b.oBenhNen?.dangChon} ` +
    `${b.oBenhNen?.dangChon === 3 ? "✓ chọn nhiều được" : "🔴 chỉ giữ được 1"} · nút: "${b.oBenhNen?.nhanNut}"`);
  console.log(`⑤ Bảng chọn hoạt chất · cao ${b.oBangChon?.cao}/${b.oBangChon?.vh}px = ${b.oBangChon?.phanTramMan}% màn ` +
    `${(b.oBangChon?.phanTramMan ?? 100) < 90 ? "✓ không kín màn" : "🔴 KÍN MÀN"} · ` +
    `nút Đóng: ${b.oBangChon?.coNutDong ? "✓" : "🔴 KHÔNG CÓ"} · ô tìm: ${b.oBangChon?.coOTim ? "✓" : "—"} · ${b.oBangChon?.soDong} dòng`);
}
console.log(`\nẢnh: ${OUT}`);
