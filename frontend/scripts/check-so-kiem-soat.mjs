/**
 * Màn **Sổ thuốc kiểm soát đặc biệt** — cổng cho lỗi C-03 (UAT 2026-08-01, mức Critical).
 *
 * 🔴 ĐỌC THUẦN. Không ghi bút toán nào, **không ký sổ nào**. Ký là hành vi pháp lý không
 * đảo ngược được (ký rồi thì ngày đó khoá vĩnh viễn) — một cổng tự động không được phép
 * làm việc đó, kể cả trên CSDL kiểm thử, vì thói quen "cổng cứ ghi thoải mái" là thứ sẽ
 * theo người ta sang CSDL thật. Dựng dữ liệu bằng `lib/dung-du-lieu-so-kiem-soat.mjs`.
 *
 * Đo tám mệnh đề, mỗi mệnh đề là một cách màn này hỏng **mà vẫn trông như chạy**:
 *   1. có lối vào từ menu — màn không ai tới được thì bằng không;
 *   2. bảng có dòng thật, không phải trạng thái rỗng vì lọc sai ngày;
 *   3. cột **Tên thuốc** hiện TÊN, không phải mã máy — `compliance` chỉ biết `drug_id`, tên
 *      phải tra qua `catalog`, và chuỗi nối hai module đó không có trình biên dịch nào canh;
 *   4. 🔴 cảnh báo **CHƯA RÀ PHÁP LÝ** hiện ra và **NHÌN THẤY ĐƯỢC**. Đây là điều kiện GĐ
 *      kèm theo việc Chain gác pháp lý (§7dg quyết định 8): ảnh chụp màn này sẽ vào video
 *      hướng dẫn, và một ảnh trông như phần mềm tuân thủ đủ là thứ khó rút lại nhất;
 *   5. cột **Còn lại** nhìn thấy được ở khổ 390px — kỷ luật #21. Đúng cột là lý do màn này
 *      tồn tại, và đúng loại cột đã bị cắt khỏi màn ở `/kiem-ke` hôm 01/08 trong lúc cổng
 *      Playwright báo ✓;
 *   6. 🔴 **cột "Còn lại" cộng đúng** — `tồn cuối = Σnhập − Σxuất`. Đo Ý NGHĨA của màn, không
 *      đếm dòng: một bảng hiện đủ dòng nhưng cột tồn lũy kế sai là **tệ hơn** một bảng rỗng,
 *      vì nó trông đáng tin. Cùng khuôn `check-don-thuoc.mjs` so hai nguồn (§7dg bài học 1);
 *   7. đổi **mẫu sổ** thật sự đổi dữ liệu (PL_VIII ≠ PL_XVI), không phải một `select` gắn
 *      vào không đâu cả;
 *   8. trang không cuộn ngang · không lỗi JS.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";
import { API, BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/so-kiem-soat";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

const KY = "date_from=2026-01-01&date_to=2026-12-31";

// Điều kiện dữ liệu, kiểm TRƯỚC khi mở trình duyệt: một cổng chạy 40 giây rồi mới báo
// "không có dữ liệu" là 40 giây phí, và người đọc dễ nhầm nó với lỗi sản phẩm.
const phien = await (
  await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })
).json();
if (!phien.access_token) {
  console.error("🔴 Đăng nhập API thất bại.");
  process.exit(2);
}
const H = { Authorization: `Bearer ${phien.access_token}` };
const soPlViii = await (
  await fetch(`${API}/compliance/controlled-ledger/books/PL_VIII?${KY}`, { headers: H })
).json();
const soPlXvi = await (
  await fetch(`${API}/compliance/controlled-ledger/books/PL_XVI?${KY}`, { headers: H })
).json();

if (soPlViii.length === 0) {
  console.error(
    [
      "🔴 CHƯA ĐO ĐƯỢC: sổ kiểm soát không có bút toán nào.",
      "",
      "   Đây KHÔNG phải lỗi sản phẩm, nhưng cũng KHÔNG được đọc là đạt — suốt thời gian",
      "   này không ai biết màn sổ pháp lý còn chạy hay không.",
      "",
      "   Dựng dữ liệu:  node scripts/lib/dung-du-lieu-so-kiem-soat.mjs",
    ].join("\n"),
  );
  process.exit(2);
}

/**
 * ⑥ Tồn cuối kỳ đúng theo số học.
 *
 * 🔴 **Bản đầu của phép đo này XANH TRONG LÚC MÀN HÌNH HIỆN `−5`.** Nó so `Σnhập−Σxuất`
 * với `balance` — cả hai lấy từ **cùng một lượt gọi API**, nên nó chỉ chứng minh API nhất
 * quán với chính nó. Đúng kỷ luật #14: *"một tín hiệu xanh chứng minh một mệnh đề KHÁC với
 * mệnh đề người đọc tưởng nó chứng minh"*.
 *
 * Nó cũng che mất một **lỗi sản phẩm có thật từ Sprint 7**: `to_book_rows` khởi động
 * `balance = 0` cho mỗi lượt truy vấn, nên sổ kết xuất cho một kỳ không bắt đầu từ bút toán
 * đầu tiên cho ra cột tồn lũy kế sai — và âm. Trên tệp CSV đem trình thanh tra.
 *
 * Nay đo hai mệnh đề **khác nhau**, mỗi mệnh đề có một nguồn độc lập:
 *   (a) API cộng đúng **kể cả tồn đầu kỳ**: so `balance` cuối với tổng tính từ toàn bộ lịch
 *       sử (kỳ rộng nhất), chứ không phải từ chính các dòng vừa trả về;
 *   (b) **màn hình** hiện đúng con số API trả — đo tách rời, vì màn hiện đúng số sai vẫn là
 *       hỏng, và màn hiện sai số đúng cũng vậy.
 */
const tong = (ds, khoa) =>
  ds.reduce((s, r) => s + (r[khoa] === null ? 0 : Number(r[khoa])), 0);
const tonTinhTay = tong(soPlViii, "quantity_in") - tong(soPlViii, "quantity_out");
const tonCuoiApi = Number(soPlViii.at(-1).balance);
const congDung = Math.abs(tonTinhTay - tonCuoiApi) < 1e-9;

// Không dòng nào của một sổ pháp lý được phép âm — tồn âm nghĩa là đã bán thứ chưa từng
// nhập. Đây là phép kiểm rẻ nhất bắt được đúng lỗi tồn-đầu-kỳ, ở MỌI kỳ, không chỉ kỳ này.
const dongAm = [...soPlViii, ...soPlXvi].filter((r) => Number(r.balance) < 0);

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

  const coLoiVao = await p.locator('a[href="/so-kiem-soat"]').count();

  await p.goto(`${BASE}/so-kiem-soat`, { waitUntil: "load" });
  await p.waitForTimeout(3000);

  // 🔴 ĐẶT ĐÚNG KỲ mà API bên trên đã hỏi, trước khi so hai bên. Bản đầu bỏ bước này và
  // cổng đỏ vì **phép đo**, không phải sản phẩm: màn dùng kỳ mặc định (từ đầu tháng) còn
  // phép kiểm hỏi cả năm — hai kỳ khác nhau thì hai con số khác nhau là ĐÚNG.
  // Lần thứ ba trong phiên này cái đỏ là phép đo chứ không phải sản phẩm (kỷ luật #15).
  await p.fill('input[aria-label="Từ ngày"]', "2026-01-01");
  await p.fill('input[aria-label="Đến ngày"]', "2026-12-31");
  await p.waitForTimeout(3000);

  const d = await p.evaluate(() => {
    const rows = [...document.querySelectorAll('[data-testid="ds-so-kiem-soat"] tbody tr')];
    const cot = (r, nhan) => r.querySelector(`td[data-nhan="${nhan}"]`)?.innerText.trim() ?? "";
    return {
      soDong: rows.length,
      // ③ Tên thuốc rơi về `Mã xxxxxxxx` khi tra không ra. Chấp nhận được từng dòng, nhưng
      //    nếu TẤT CẢ đều vậy thì việc nối `compliance` ↔ `catalog` đã hỏng — mà màn vẫn
      //    đầy chữ, chỉ là chữ không nói được nó nói về thuốc gì.
      chiCoMaThuoc: rows.filter((r) => /^Mã [0-9a-f]{8}$/.test(cot(r, "Tên thuốc"))).length,
      tonCuoiTrenMan: rows.length ? cot(rows[rows.length - 1], "Còn lại") : null,
      // Mọi con số ở cột "Còn lại" mà màn hình thật sự vẽ ra. So với API bên dưới — màn
      // hiện đúng một con số sai vẫn là hỏng, và màn hiện sai một con số đúng cũng vậy.
      moiConLaiTrenMan: rows.map((r) => cot(r, "Còn lại")),
      // `\.\s` chứ không chỉ tên câu: khoảng trắng sau `</strong>` từng bị JSX nuốt và chữ
      // dính thành "pháp lý.Bố cục". Ảnh chụp bắt được, phép đo cũ thì không — nó chỉ được
      // dặn tìm cụm từ, mà cụm từ vẫn còn nguyên.
      noiChuaRa: /Chưa được rà pháp lý\.\s/.test(document.body.innerText),
      noiInCuoiNgay: /in vào cuối MỖI ngày/i.test(document.body.innerText),
    };
  });

  await p.screenshot({ path: `${OUT}/${ten}-1-pl-viii.png`, fullPage: true });

  // ④+⑤ Kỷ luật #21 — "có trong DOM" ≠ "nhìn thấy được". Cảnh báo pháp lý mà nằm ngoài rìa
  //      màn hình thì bằng không có: nó tồn tại đủ để `innerText` thấy, không đủ để người đọc thấy.
  const oChuaRa = await trongKhungNhin(p, p.locator("p").filter({ hasText: "Chưa được rà pháp lý" }));
  const oConLai = await trongKhungNhin(p, p.locator('td[data-nhan="Còn lại"]').first());
  const oTenThuoc = await trongKhungNhin(p, p.locator('td[data-nhan="Tên thuốc"]').first());
  const cuon = await cuonNgangTrang(p);

  // ⑦ Đổi mẫu sổ phải đổi DỮ LIỆU. Không chỉ "số dòng khác": số chứng từ phải khác hẳn —
  //    hai mẫu sổ tình cờ cùng số dòng là chuyện hoàn toàn có thể xảy ra.
  const chungTuTruoc = await p.evaluate(() =>
    [...document.querySelectorAll('td[data-nhan="Số chứng từ"]')].map((e) => e.innerText.trim()),
  );
  await p.selectOption('select[aria-label="Mẫu sổ"]', "PL_XVI");
  await p.waitForTimeout(3000);
  const chungTuSau = await p.evaluate(() =>
    [...document.querySelectorAll('td[data-nhan="Số chứng từ"]')].map((e) => e.innerText.trim()),
  );
  await p.screenshot({ path: `${OUT}/${ten}-2-pl-xvi.png`, fullPage: true });

  const doiMauSo =
    chungTuSau.length > 0 && chungTuSau.every((c) => !chungTuTruoc.includes(c));

  // (b) Màn hình hiện đúng con số API trả. Bỏ dấu chấm ngăn hàng nghìn trước khi so — màn
  //     hiện "1.234" cho số 1234, và so chuỗi trần sẽ đỏ vì lý do sai.
  const soTrenMan = d.moiConLaiTrenMan.map((s) => Number(s.replace(/\./g, "").replace(",", ".")));
  const soCuaApi = soPlViii.map((r) => Number(r.balance));
  const manKhopApi =
    soTrenMan.length === soCuaApi.length &&
    soTrenMan.every((v, i) => Math.abs(v - soCuaApi[i]) < 1e-9);
  const manCoSoAm = soTrenMan.some((v) => v < 0);

  const dat =
    coLoiVao > 0 &&
    d.soDong > 0 &&
    d.chiCoMaThuoc < d.soDong &&
    d.noiChuaRa &&
    d.noiInCuoiNgay &&
    congDung &&
    dongAm.length === 0 &&
    manKhopApi &&
    !manCoSoAm &&
    doiMauSo &&
    oChuaRa.dat &&
    oConLai.dat &&
    oTenThuoc.dat &&
    cuon.dat &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  ① lối vào từ menu: ${coLoiVao > 0 ? "✓" : "🔴"}`);
  console.log(`  ② ${d.soDong} dòng ${d.soDong > 0 ? "✓" : "🔴 (rỗng — lọc ngày sai hay không có quyền?)"}`);
  console.log(
    `  ③ dòng chỉ có mã thuốc: ${d.chiCoMaThuoc}/${d.soDong} ${d.chiCoMaThuoc < d.soDong ? "✓" : "🔴 (nối compliance↔catalog hỏng)"}`,
  );
  console.log(
    `  ④ nói rõ CHƯA RÀ PHÁP LÝ: ${d.noiChuaRa ? "✓" : "🔴 — điều kiện GĐ kèm việc gác pháp lý"} · nói nghĩa vụ in cuối ngày: ${d.noiInCuoiNgay ? "✓" : "🔴"}`,
  );
  console.log(
    `  ⑥a API cộng đúng: Σnhập−Σxuất = ${tonTinhTay} · balance cuối = ${tonCuoiApi} ${congDung ? "✓" : "🔴 CỘT TỒN LŨY KẾ SAI"}`,
  );
  console.log(
    `  ⑥b màn khớp API: [${soTrenMan.join(", ")}] vs [${soCuaApi.join(", ")}] ${manKhopApi ? "✓" : "🔴 MÀN HIỆN KHÁC API"}`,
  );
  console.log(
    `  ⑥c không dòng nào tồn ÂM: API ${dongAm.length} · màn ${soTrenMan.filter((v) => v < 0).length} ${dongAm.length === 0 && !manCoSoAm ? "✓" : "🔴 sổ pháp lý tồn âm = 'bán thuốc chưa từng nhập'"}`,
  );
  console.log(
    `  ⑦ đổi mẫu sổ đổi dữ liệu: PL_VIII ${chungTuTruoc.length} chứng từ → PL_XVI ${chungTuSau.length} ${doiMauSo ? "✓" : "🔴"}`,
  );
  inDong("④ cảnh báo pháp lý nhìn thấy được", oChuaRa);
  inDong("⑤ cột Còn lại nhìn thấy được", oConLai);
  inDong("   cột Tên thuốc nhìn thấy được", oTenThuoc);
  inDong("⑧ trang không cuộn ngang", cuon);
  console.log(`  lỗi JS: ${loi.length}${loi.length ? " · " + loi.join(" | ") : ""}`);
  await ctx.close();
}
await b.close();
console.log(
  hong === 0
    ? "\n✅ Màn Sổ kiểm soát đọc được, cộng đúng, và tự nói rõ giới hạn pháp lý."
    : `\n🔴 ${hong} khổ có vấn đề.`,
);
process.exit(hong === 0 ? 0 : 1);
