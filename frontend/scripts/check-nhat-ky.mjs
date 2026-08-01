/**
 * Màn **Nhật ký hoạt động** — cổng cho lỗi M-04 (UAT 2026-08-01).
 *
 * 🔴 ĐỌC THUẦN. Không tạo đơn, không đổi dữ liệu nào. Đăng nhập có ghi một dòng
 * `LOGIN_SUCCESS` vào sổ audit — đó là hệ quả của việc đăng nhập, không phải của cổng này.
 *
 * Đo sáu mệnh đề, mỗi mệnh đề là một cách màn này có thể hỏng **mà vẫn trông như chạy**:
 *   1. có lối vào từ menu (`a[href="/nhat-ky"]`) — màn không ai tới được thì bằng không;
 *   2. bảng có dòng thật (`total > 0`), không phải trạng thái rỗng vì lọc sai ngày;
 *   3. cột **Người thực hiện** và **Hoạt động** hiện **tên tiếng Việt**, không phải mã máy
 *      — nếu bản đồ nhãn hỏng thì màn vẫn đầy chữ, chỉ là chữ không ai đọc được;
 *   4. cột "Người thực hiện" **nhìn thấy được** ở khổ điện thoại — kỷ luật #21: đúng cột
 *      là lý do màn này tồn tại, và đúng loại cột đã trượt khỏi màn ở 5/5 bảng hôm 29/07;
 *   5. lọc theo **loại hoạt động** thật sự thu hẹp kết quả (không phải một `select` vô hại
 *      gắn vào không đâu cả);
 *   6. trang không cuộn ngang · không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";

const BASE = process.env.BASE_URL ?? "http://192.168.1.10:3000";
const EMAIL = process.env.EMAIL ?? process.env.BERAS_EMAIL;
const PASSWORD = process.env.PASSWORD ?? process.env.BERAS_PASSWORD;
const OUT = process.env.OUT_DIR ?? "/tmp/nhat-ky";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

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

  // ① Lối vào từ menu. Ở khổ điện thoại mục nằm sau nút "Thêm" ⇒ đếm trong toàn trang chứ
  //    không đòi nó phải đang hiện — cái phải hiện là NỘI DUNG màn, đo ở bước ④.
  const coLoiVao = await p.locator('a[href="/nhat-ky"]').count();

  await p.goto(`${BASE}/nhat-ky`, { waitUntil: "load" });
  await p.waitForTimeout(3500);

  const d = await p.evaluate(() => {
    const rows = [...document.querySelectorAll('[data-testid="ds-nhat-ky"] tbody tr')];
    const cot = (r, nhan) => r.querySelector(`td[data-nhan="${nhan}"]`)?.innerText.trim() ?? "";
    return {
      soDong: rows.length,
      // ③ MÃ MÁY lọt ra màn: `LOGIN_SUCCESS`, `SALE_COMPLETED`… viết hoa toàn bộ có gạch
      //    dưới. Bản đồ nhãn hỏng thì màn vẫn đầy chữ — chỉ là chữ không ai đọc được, và
      //    không phép đếm dòng nào thấy được điều đó.
      maMayLotRa: rows.filter((r) => /^[A-Z][A-Z0-9_]{4,}$/.test(cot(r, "Hoạt động"))).length,
      // 🔴 Ảnh chụp 01/08 bắt được `user · 40977c62` ở cột Đối tượng — CÙNG lỗi, khác cột,
      //    và phép đo trên bỏ qua vì nó chỉ được dặn nhìn cột "Hoạt động". Kỷ luật #20:
      //    phép đo chỉ tìm thứ nó được dặn tìm; ảnh thấy cả những thứ không ai dặn.
      loaiMayLotRa: rows.filter((r) => {
        const t = cot(r, "Đối tượng").split("·")[0].trim();
        return /^[a-z][a-z0-9_]{2,}$/.test(t);
      }).length,
      // Người thực hiện rơi về `Mã xxxxxxxx` khi không tra được tên — chấp nhận được nhưng
      //    phải đếm, vì nếu TẤT CẢ đều vậy thì việc nối tên đã hỏng chứ không phải thiếu.
      chiCoMa: rows.filter((r) => /^Mã [0-9a-f]{8}$/.test(cot(r, "Người thực hiện"))).length,
      noiGioiHan: /chưa ghi.*giá trị cũ/i.test(document.body.innerText),
      tongVanBan: document.body.innerText.match(/(\d+)\s+hoạt động/)?.[1] ?? null,
    };
  });

  await p.screenshot({ path: `${OUT}/${ten}-1-nhat-ky.png`, fullPage: true });

  // ④ Kỷ luật #21 — "có trong DOM" ≠ "nhìn thấy được".
  const oNguoi = await trongKhungNhin(p, p.locator('td[data-nhan="Người thực hiện"]').first());
  const oHoatDong = await trongKhungNhin(p, p.locator('td[data-nhan="Hoạt động"]').first());
  const cuon = await cuonNgangTrang(p);

  // ⑤ Lọc phải THU HẸP thật. So `total` trước/sau: một `select` gắn vào không đâu cả vẫn
  //    đổi được giá trị hiển thị mà danh sách đứng im — và trông y hệt như đang chạy.
  let locHoatDong = null;
  if (d.soDong > 0) {
    await p.selectOption('select[aria-label="Loại hoạt động"]', "LOGIN_SUCCESS");
    await p.waitForTimeout(3000);
    const sau = await p.evaluate(() => {
      const rows = [...document.querySelectorAll('[data-testid="ds-nhat-ky"] tbody tr')];
      const cot = (r) => r.querySelector('td[data-nhan="Hoạt động"]')?.innerText.trim() ?? "";
      return {
        soDong: rows.length,
        // Không chỉ "ít dòng hơn": MỌI dòng còn lại phải đúng loại đã lọc. Một bộ lọc bỏ
        // bớt dòng ngẫu nhiên cũng làm số giảm.
        dungLoai: rows.length > 0 && rows.every((r) => cot(r) === "Đăng nhập"),
        tong: document.body.innerText.match(/(\d+)\s+hoạt động/)?.[1] ?? null,
      };
    });
    locHoatDong = { truoc: d.tongVanBan, ...sau };
    await p.screenshot({ path: `${OUT}/${ten}-2-loc-dang-nhap.png`, fullPage: true });
  }

  const datLoc =
    locHoatDong === null ||
    (locHoatDong.dungLoai && Number(locHoatDong.tong) <= Number(locHoatDong.truoc));

  const dat =
    coLoiVao > 0 &&
    d.soDong > 0 &&
    d.maMayLotRa === 0 &&
    d.loaiMayLotRa === 0 &&
    d.chiCoMa < d.soDong &&
    d.noiGioiHan &&
    oNguoi.dat &&
    oHoatDong.dat &&
    cuon.dat &&
    datLoc &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  lối vào từ menu: ${coLoiVao > 0 ? "✓" : "🔴"} · nói rõ giới hạn cũ→mới: ${d.noiGioiHan ? "✓" : "🔴"}`);
  console.log(`  ${d.soDong} dòng ${d.soDong > 0 ? "✓" : "🔴 (rỗng — lọc ngày sai hay không có quyền?)"} · tổng ${d.tongVanBan ?? "?"}`);
  console.log(`  mã máy lọt ra màn — Hoạt động: ${d.maMayLotRa} · Đối tượng: ${d.loaiMayLotRa} (phải 0) ${d.maMayLotRa === 0 && d.loaiMayLotRa === 0 ? "✓" : "🔴"} · dòng chỉ có mã người: ${d.chiCoMa}/${d.soDong} ${d.chiCoMa < d.soDong ? "✓" : "🔴 (nối tên hỏng)"}`);
  inDong("cột Người thực hiện nhìn thấy được", oNguoi);
  inDong("cột Hoạt động nhìn thấy được", oHoatDong);
  inDong("trang không cuộn ngang", cuon);
  if (locHoatDong) {
    console.log(
      `  lọc "Đăng nhập": ${locHoatDong.truoc} → ${locHoatDong.tong} hoạt động · mọi dòng đúng loại: ${locHoatDong.dungLoai ? "✓" : "🔴"}`,
    );
  }
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(hong === 0 ? "\n✅ Màn Nhật ký tra được, lọc được, đọc được." : `\n🔴 ${hong} khổ có vấn đề.`);
process.exit(hong === 0 ? 0 : 1);
