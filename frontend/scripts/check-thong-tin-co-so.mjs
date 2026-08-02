/**
 * **Cài đặt → Thông tin cơ sở** — cổng cho lỗi M-02 (UAT 2026-08-01).
 *
 * 🔴 **L-2 — vá 2026-08-02.** Bản trước của tệp này ghi năm trường thông tin cơ sở rồi
 * **KHÔNG BAO GIỜ trả lại**, trong khi chú thích đầu tệp khẳng định *"nó ghi rồi trả lại
 * nguyên giá trị cũ, không để lại rác"*. Câu đó là **lời khai sai**, và nó chính là cơ sở
 * duy nhất để cổng này được xếp vào **nhóm đọc-thuần** — nhóm chạy mặc định, không hỏi ai.
 *
 * Hậu quả nếu chạy lên CSDL một quầy đang bán thật: tên · địa chỉ · điện thoại · mã số
 * thuế · mã cơ sở do Cục QLD cấp bị thay bằng **số bịa**, im lặng. Không mã lỗi nào, không
 * dòng log nào. Và bốn trường đó là thứ đi thẳng vào **báo cáo gửi cơ quan quản lý** —
 * §7dm ghi rõ một phiên trước đã phải **gỡ đúng loại số bịa này ra** khỏi `qt650`.
 *
 * Ba thứ đổi, và cả ba đều cần thiết:
 *   ① **Chụp nguyên trạng MỘT LẦN** ở khổ đầu, khôi phục về đúng bản chụp đó ở mọi khổ.
 *      Chụp lại mỗi khổ thì khổ sau sẽ khôi phục về giá trị dò của khổ trước nếu khổ trước
 *      chết giữa chừng — nghĩa là cơ chế khôi phục tự nhân bản lỗi của chính nó.
 *   ② **Giá trị dò hiển nhiên là giả** (`KIỂM THỬ`, `KIEMTHU000000`). Bản cũ dò bằng địa
 *      chỉ Q.5 TP.HCM và mã số thuế 10 chữ số **trông y như thật**, trong khi chi nhánh
 *      thật ở Vĩnh Long. Nếu khôi phục hỏng, thứ nằm lại trong sổ pháp lý phải là thứ
 *      người ta **nhìn là biết sai ngay**, không phải thứ đọc lọt.
 *   ③ **Khôi phục trong `finally` + mệnh đề ⑦ đo chính việc khôi phục.** Kỷ luật #24: một
 *      bản vá không kèm cổng của nó là một lỗi sẽ lặp lại. Cổng cũ có sáu mệnh đề và
 *      **không mệnh đề nào** hỏi *"cái tôi vừa ghi đè đã về chỗ cũ chưa"*.
 *
 * Đo bảy mệnh đề:
 *   1. khối có mặt trên màn Cài đặt (`khoi-thong-tin-co-so`);
 *   2. giá trị đã lưu **hiện lại được** sau khi tải lại trang — nếu chỉ ghi mà không đọc
 *      lại thì màn "trông như chạy" trọn vẹn cho tới lần đăng nhập sau;
 *   3. màn **nói rõ hoá đơn CÓ dùng** thông tin này. Mệnh đề ③ trước đây canh chiều
 *      NGƯỢC LẠI — nó đòi màn tự thú *"hoá đơn chưa dùng"*, vì đó là sự thật cho tới
 *      02/08. Nợ N-1 đóng ⇒ câu đó thành **sai**, và một cổng canh một câu đã sai thì
 *      giữ nguyên chỗ hỏng thay vì canh nó. Đổi vế, không xoá mệnh đề: người dùng vẫn
 *      phải đọc được việc mình vừa làm có hiệu lực tới đâu;
 *   4. lời cảnh báo ở ③ **nhìn thấy được**, không chỉ có trong DOM (kỷ luật #21);
 *   5. ô nhập không biến dạng ở khổ 390px — cùng bẫy `flex-basis` đã quay lại bốn lần;
 *   6. trang không cuộn ngang · không lỗi JS;
 *   7. 🔴 **cả sáu trường đã về đúng nguyên trạng** — mệnh đề đóng L-2.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";
import { BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/thong-tin-co-so";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

/**
 * Sáu ô của biểu mẫu, theo đúng `aria-label` trong `ThongTinCoSo.tsx`.
 *
 * 🔴 Phải đủ **SÁU**, không phải năm. Bản cũ ghi năm ô và bỏ quên `ma_co_so_ban_buon` —
 * nghĩa là kể cả khi có khôi phục, nó vẫn để lại một trường sai. Danh sách này là thứ cả
 * phép ghi lẫn phép khôi phục cùng đọc, nên không lệch nhau được.
 */
const O_NHAP = [
  "Tên cơ sở",
  "Địa chỉ",
  "Điện thoại",
  "Mã số thuế",
  "Mã cơ sở bán lẻ (Cục QLD cấp)",
  "Mã cơ sở bán buôn (nếu có)",
];

/** Đọc cả sáu ô thành một object — dùng cho cả bản chụp lẫn phép kiểm khôi phục. */
async function docSauO(p) {
  const r = {};
  for (const nhan of O_NHAP) r[nhan] = await p.inputValue(`input[aria-label="${nhan}"]`);
  return r;
}

/** Điền cả sáu ô rồi bấm Lưu, và chờ máy chủ trả lời xong. */
async function ghiVaLuu(p, giaTri) {
  for (const nhan of O_NHAP) await p.fill(`input[aria-label="${nhan}"]`, giaTri[nhan]);
  await p.locator("button", { hasText: /^Lưu thông tin cơ sở$/ }).click();
  await p.waitForTimeout(3000);
}

/**
 * Giá trị dò — **hiển nhiên là giả**, và vừa giới hạn cột của CSDL.
 *
 * Giới hạn thật (`\d tenant_compliance_configs`): `ma_co_so_ban_le`/`ban_buon` **varchar(12)**,
 * `dien_thoai` varchar(32), `ma_so_thue` varchar(20). Vượt cột thì máy chủ trả 500 và cổng
 * đỏ **vì phép đo**, không phải vì sản phẩm — đúng loại nhầm lẫn §7dg đã mất một lượt vì nó.
 */
function giaTriDo() {
  const dau = Date.now().toString().slice(-6);
  return {
    "Tên cơ sở": `KIỂM THỬ — KHÔNG PHẢI DỮ LIỆU THẬT ${dau}`,
    "Địa chỉ": "KIỂM THỬ — khôi phục ngay sau khi đo",
    "Điện thoại": "KIEM-THU-0000",
    "Mã số thuế": "KIEMTHU000000",
    "Mã cơ sở bán lẻ (Cục QLD cấp)": `KT${dau}`,
    "Mã cơ sở bán buôn (nếu có)": "KT-BB",
  };
}

const b = await firefox.launch();
let hong = 0;

/**
 * Bản chụp nguyên trạng, lấy **một lần** ở khổ đầu và dùng lại cho mọi khổ.
 * `null` = chưa chụp được lần nào ⇒ **cấm ghi**, xem lý do ở chỗ dùng.
 */
let nguyenTrang = null;

/**
 * Ghi bản chụp trở lại rồi **đọc lại từ máy chủ** để chứng minh, không tin lời `Đã lưu`.
 *
 * Kỷ luật #23: hai vế của phép so phải có hai nguồn độc lập. Vế `A` là bản chụp lấy **trước**
 * khi ghi; vế `B` là thứ đọc lại **sau một lượt tải lại trang**, tức đi qua máy chủ và CSDL.
 * So giá trị trong ô ngay sau khi `fill` thì chỉ chứng minh Playwright biết gõ chữ.
 */
async function traLaiNguyenTrang(p) {
  if (nguyenTrang === null) return { dat: false, chiTiet: "không có bản chụp nguyên trạng" };
  await ghiVaLuu(p, nguyenTrang);
  await p.reload({ waitUntil: "load" });
  await p.waitForTimeout(3500);
  const nay = await docSauO(p);
  const lech = O_NHAP.filter((k) => nay[k] !== nguyenTrang[k]);
  return {
    dat: lech.length === 0,
    chiTiet: lech.map((k) => `${k}: "${nay[k]}" ≠ "${nguyenTrang[k]}"`).join(" · "),
  };
}

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

  let daGhi = false;
  let khoiPhuc = { dat: false, chiTiet: "chưa chạy tới" };

  try {
    await p.goto(`${BASE}/login`, { waitUntil: "load" });
    await p.waitForTimeout(1500);
    await p.fill('input[type="email"]', EMAIL);
    await p.fill('input[type="password"]', PASSWORD);
    await p.click('button[type="submit"]');
    await p.waitForTimeout(4000);

    await p.goto(`${BASE}/cai-dat`, { waitUntil: "load" });
    await p.waitForTimeout(3000);

    const coKhoi = (await p.locator('[data-testid="khoi-thong-tin-co-so"]').count()) > 0;

    // 🔴 Chụp nguyên trạng TRƯỚC khi chạm vào bất cứ gì. Nếu không đọc được (khối chưa
    //    render, phiên hỏng, quyền thiếu) thì **thoát mà không ghi** — ghi đè khi không
    //    biết mình đang ghi đè cái gì là đúng hình dạng L-2, chỉ khác chỗ nó im lặng hơn.
    if (!coKhoi) {
      console.log(`\n──${ten}──\n  ① khối Thông tin cơ sở có mặt: 🔴 — KHÔNG GHI GÌ CẢ`);
      hong++;
      await ctx.close();
      continue;
    }
    if (nguyenTrang === null) nguyenTrang = await docSauO(p);

    // ② Ghi một giá trị RIÊNG cho lượt chạy này, rồi tải lại và đọc lại. Dùng một chuỗi duy
    //    nhất chứ không dùng giá trị cố định: một ô giữ nguyên giá trị của lượt trước cũng
    //    "khớp" với một giá trị cố định, và cổng sẽ xanh mà không chứng minh gì.
    const do_ = giaTriDo();

    const oTen = await trongKhungNhin(p, p.locator('input[aria-label="Tên cơ sở"]'));
    // ⑤ Ô nhập không biến dạng — bẫy `flex-basis` trong hộp dọc đã quay lại BỐN lần, lần
    //    gần nhất xuyên qua chính bản vá tuyên bố "sửa ở chỗ khai nên không quay lại được".
    const caoONhap = await p.evaluate(() =>
      Math.max(
        ...[...document.querySelectorAll('[data-testid="khoi-thong-tin-co-so"] input')].map(
          (e) => e.getBoundingClientRect().height,
        ),
      ),
    );

    await p.screenshot({ path: `${OUT}/${ten}-1-truoc-luu.png`, fullPage: true });

    daGhi = true;
    await ghiVaLuu(p, do_);

    await p.reload({ waitUntil: "load" });
    await p.waitForTimeout(3500);
    const sauTaiLai = await p.inputValue('input[aria-label="Tên cơ sở"]');
    const luuThat = sauTaiLai === do_["Tên cơ sở"];

    const noiVaoHoaDon = /Hoá đơn in ra dùng thông tin ở đây/i.test(
      await p.locator("body").innerText(),
    );
    const oCanhBao = await trongKhungNhin(
      p,
      p
        .locator('[data-testid="khoi-thong-tin-co-so"] p')
        .filter({ hasText: "dùng thông tin ở đây" }),
    );
    const cuon = await cuonNgangTrang(p);
    await p.screenshot({ path: `${OUT}/${ten}-2-sau-tai-lai.png`, fullPage: true });

    const oNhapBinhThuong = caoONhap <= 96;

    // ⑦ Khôi phục NGAY, rồi ĐO việc khôi phục. Không để trong `finally` một mình: `finally`
    //    lo ca hỏng bất thường, còn đường chạy bình thường phải khôi phục **và chứng minh**.
    khoiPhuc = await traLaiNguyenTrang(p);
    daGhi = false;
    // 🔴 Ảnh thứ BA, chụp SAU khi khôi phục. Hai ảnh trước chụp giữa lượt dò nên chúng
    //    hiện giá trị `KIỂM THỬ` — đúng cho việc gỡ lỗi cổng, **vô dụng để Chain nghiệm
    //    thu** (kỷ luật #20: ảnh là thứ Chain duyệt). Một ảnh nghiệm thu hiện dữ liệu thử
    //    còn tệ hơn không có ảnh: nó trông y như sản phẩm đang mang dữ liệu rác.
    await p.screenshot({ path: `${OUT}/${ten}-3-nguyen-trang.png`, fullPage: true });

    const dat =
      coKhoi &&
      luuThat &&
      noiVaoHoaDon &&
      oCanhBao.dat &&
      oTen.dat &&
      oNhapBinhThuong &&
      cuon.dat &&
      khoiPhuc.dat &&
      loi.length === 0;
    if (!dat) hong++;

    console.log(`\n──${ten}──`);
    console.log(`  ① khối Thông tin cơ sở có mặt: ${coKhoi ? "✓" : "🔴"}`);
    console.log(
      `  ② lưu rồi TẢI LẠI vẫn đúng: ${luuThat ? "✓" : `🔴 ghi "${do_["Tên cơ sở"]}" · đọc lại "${sauTaiLai}"`}`,
    );
    console.log(
      `  ③ nói rõ hoá đơn CÓ dùng: ${noiVaoHoaDon ? "✓" : "🔴 — màn không nói hiệu lực tới đâu"}`,
    );
    console.log(`  ⑤ ô nhập cao ${Math.round(caoONhap)}px (≤96) ${oNhapBinhThuong ? "✓" : "🔴"}`);
    inDong("④ cảnh báo nhìn thấy được", oCanhBao);
    inDong("   ô Tên cơ sở nhìn thấy được", oTen);
    inDong("⑥ trang không cuộn ngang", cuon);
    console.log(`  ⑦ khôi phục 6/6 trường: ${khoiPhuc.dat ? "✓" : `🔴 ${khoiPhuc.chiTiet}`}`);
    console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  } finally {
    // 🔴 Lưới an toàn cho ca hỏng bất thường (trình duyệt chết, máy chủ 500, mất mạng giữa
    //    chừng). `daGhi` chỉ còn `true` khi đã ghi mà chưa kịp khôi phục ở đường chạy bình
    //    thường — đúng lúc cần lưới. Ném lỗi ở đây thì nuốt, vì `finally` ném sẽ **che mất**
    //    lỗi gốc đang bay ra và biến một sự cố đọc được thành một sự cố không đọc được.
    if (daGhi) {
      try {
        const cuu = await traLaiNguyenTrang(p);
        console.log(`\n  ⚠️ Thoát bất thường sau khi ghi — khôi phục khẩn: ${cuu.dat ? "✓" : `🔴 ${cuu.chiTiet}`}`);
        if (!cuu.dat) hong++;
      } catch (e) {
        console.log(`\n  🔴 KHÔNG KHÔI PHỤC ĐƯỢC — thông tin cơ sở đang là GIÁ TRỊ DÒ: ${e}`);
        console.log(`     Nguyên trạng cần khôi phục tay: ${JSON.stringify(nguyenTrang)}`);
        hong++;
      }
    }
    await ctx.close();
  }
}
await b.close();

console.log(
  hong === 0
    ? "\n✅ Thông tin cơ sở khai được, lưu thật, nói rõ phần còn nợ, và ĐÃ TRẢ LẠI nguyên trạng."
    : `\n🔴 ${hong} khổ có vấn đề.`,
);
process.exit(hong === 0 ? 0 : 1);
