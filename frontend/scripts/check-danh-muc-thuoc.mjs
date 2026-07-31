/**
 * Màn Danh mục thuốc — xem và sửa hoạt chất.
 *
 * 🔴 Vì sao cần: API `PUT /drugs/{id}/ingredients` có từ 30/07 nhưng **không ai chạm được**
 * cho tới khi có màn này. Cổng canh đúng chuyện đó — màn có thật, có dữ liệu, và mở được
 * bảng sửa. Chỉ ĐỌC: lượt lưu thật nằm ở nhóm ghi (`--all`), vì nó đổi hoạt chất trong
 * CSDL và kéo theo hành vi cảnh báo dị ứng.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/danh-muc";
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
  await p.goto(`${BASE}/danh-muc-thuoc`, { waitUntil: "load" }); await p.waitForTimeout(3500);
  await p.screenshot({ path: `${OUT}/${ten}-1-danh-muc.png`, fullPage: true });

  const r = await p.evaluate(() => {
    const rows = [...document.querySelectorAll("tbody tr")];
    const t = document.body.innerText;
    return {
      soDong: rows.length,
      coCotHoatChat: [...document.querySelectorAll("thead th")].some(x => /Hoạt chất/i.test(x.textContent ?? "")),
      soTrong: (t.match(/(\d+) thuốc chưa có hoạt chất/) ?? [])[1] ?? null,
      // ⚠️ ĐỔI NHÃN 2026-07-31: "Sửa" → "Hoạt chất", "Giá" → "Sửa giá". Trên điện thoại
      // hai nút nằm cạnh nhau và "Giá" / "Sửa" không nói được cái nào làm gì; nhãn cũ chỉ
      // đọc được nhờ tiêu đề cột, mà ở bố cục thẻ thì tiêu đề cột không còn.
      coNutSua: rows.some(tr => [...tr.querySelectorAll("button")].some(x => x.textContent?.trim() === "Hoạt chất")),
      // Có thuốc nào hiện được hoạt chất bằng TÊN không (không phải id cụt)?
      coTenHoatChat: rows.some(tr => /Paracetamol|Amoxicillin|Ibuprofen/.test(tr.innerText)),
      tranNgang: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      // 🔴 Ô nhập nở theo chiều cao: `.input` có `flex:1 1 auto`, đặt thẳng vào `.page`
      // (flex CỘT) thì nó ăn hết chỗ trống — lần đầu đo được 250px. Không cổng chữ nào
      // thấy được; ảnh chụp thấy. Nay đo luôn để nó không quay lại im lặng.
      caoOTim: Math.round(document.querySelector('input[aria-label="Tìm thuốc"]')
        ?.getBoundingClientRect().height ?? 0),
      // Cột giá niêm yết (2026-07-31). Đếm dòng hiện được SỐ TIỀN, không chỉ có cột:
      // một cột rỗng vẫn qua được phép kiểm "có tiêu đề".
      coCotGia: [...document.querySelectorAll("thead th")].some(x => /Giá niêm yết/i.test(x.textContent ?? "")),
      soDongCoGia: rows.filter(tr => /\d[\d.]*\s*đ/.test(tr.innerText)).length,
      coNutGia: rows.some(tr => [...tr.querySelectorAll("button")].some(x => x.textContent?.trim() === "Sửa giá")),
      // 🔴 Phép kiểm MỚI, sinh từ đúng lỗi Chain báo: nút phải nằm TRONG khung nhìn, không
      // phải "tồn tại trong DOM". Cổng cũ chỉ đếm nút và đo cuộn ngang CẤP TRANG — trang
      // không cuộn, nhưng bảng bên trong `overflow-x: auto` thì có, nên hai nút bị đẩy ra
      // ngoài mép phải mà mọi phép kiểm vẫn xanh. Một nút chỉ với tới được bằng cách cuộn
      // ngang trong bảng là một nút không tồn tại với người dùng.
      nutTrongKhungNhin: (() => {
        const nut = [...document.querySelectorAll("tbody button")]
          .find(x => x.textContent?.trim() === "Sửa giá");
        if (!nut) return false;
        const r = nut.getBoundingClientRect();
        return r.left >= 0 && r.right <= document.documentElement.clientWidth;
      })(),
    };
  });

  // Mở bảng sửa của một thuốc CÓ hoạt chất
  await p.locator("tbody tr").filter({ hasText: /Paracetamol|Amoxicillin/ }).first()
    .locator("button", { hasText: /^Hoạt chất$/ }).click();
  await p.waitForTimeout(1200);
  await p.screenshot({ path: `${OUT}/${ten}-2-sua-hoat-chat.png`, fullPage: true });
  const bang = await p.evaluate(() => {
    const d = document.querySelector('section[aria-label^="Hoạt chất của"]');
    if (!d) return null;
    return {
      soDong: d.querySelectorAll("li").length,
      coChonThem: !!d.querySelector("select"),
      coNutLuu: [...d.querySelectorAll("button")].some(x => /Lưu hoạt chất/.test(x.textContent ?? "")),
    };
  });

  // Sàn 44px là `--touch-min`; trần 80px cho ô một dòng ở mọi khổ.
  const oTimDung = r.caoOTim >= 44 && r.caoOTim <= 80;
  const dat = r.coCotHoatChat && r.soDong > 0 && r.coNutSua && r.coTenHoatChat &&
              r.coCotGia && r.soDongCoGia > 0 && r.coNutGia && r.nutTrongKhungNhin &&
              !r.tranNgang && oTimDung &&
              bang?.soDong > 0 && bang?.coChonThem && bang?.coNutLuu && loi.length === 0;
  if (!dat) hong++;
  console.log(`\n──${ten}──`);
  console.log(`  danh mục: ${r.soDong} thuốc · cột "Hoạt chất": ${r.coCotHoatChat?"✓":"🔴"} · hiện TÊN hoạt chất: ${r.coTenHoatChat?"✓":"🔴"}`);
  console.log(`  cảnh báo "chưa có hoạt chất": ${r.soTrong ?? "(không hiện)"} thuốc · nút Sửa: ${r.coNutSua?"✓":"🔴"}`);
  console.log(`  cột "Giá niêm yết": ${r.coCotGia?"✓":"🔴"} · dòng hiện giá: ${r.soDongCoGia} · nút Sửa giá: ${r.coNutGia?"✓":"🔴"}`);
  console.log(`  nút NẰM TRONG khung nhìn (không phải chỉ có trong DOM): ${r.nutTrongKhungNhin?"✓":"🔴"}`);
  console.log(`  bảng sửa: ${bang?.soDong} dòng · ô thêm: ${bang?.coChonThem?"✓":"🔴"} · nút Lưu: ${bang?.coNutLuu?"✓":"🔴"}`);
  console.log(`  cuộn ngang: ${r.tranNgang?"🔴 CÓ":"✓ không"} · ô tìm cao ${r.caoOTim}px ${oTimDung?"✓":"🔴 (44–80)"} · lỗi JS: ${loi.length}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Màn Danh mục thuốc chạy đúng thiết kế." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
