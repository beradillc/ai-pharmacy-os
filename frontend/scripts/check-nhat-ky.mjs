/**
 * Màn **Nhật ký hoạt động** — cổng cho lỗi M-04 (UAT 2026-08-01).
 *
 * 🔴 ĐỌC THUẦN. Không tạo đơn, không đổi dữ liệu nào. Đăng nhập có ghi một dòng
 * `LOGIN_SUCCESS` vào sổ audit — đó là hệ quả của việc đăng nhập, không phải của cổng này.
 *
 * Đo tám mệnh đề, mỗi mệnh đề là một cách màn này có thể hỏng **mà vẫn trông như chạy**:
 *   1. có lối vào từ menu (`a[href="/nhat-ky"]`) — màn không ai tới được thì bằng không;
 *   2. bảng có dòng thật (`total > 0`), không phải trạng thái rỗng vì lọc sai ngày;
 *   3. cột **Người thực hiện** và **Hoạt động** hiện **tên tiếng Việt**, không phải mã máy
 *      — nếu bản đồ nhãn hỏng thì màn vẫn đầy chữ, chỉ là chữ không ai đọc được;
 *   4. cột "Người thực hiện" **nhìn thấy được** ở khổ điện thoại — kỷ luật #21: đúng cột
 *      là lý do màn này tồn tại, và đúng loại cột đã trượt khỏi màn ở 5/5 bảng hôm 29/07;
 *   5. lọc theo **loại hoạt động** thật sự thu hẹp kết quả (không phải một `select` vô hại
 *      gắn vào không đâu cả);
 *   6. **(M-06, 01/08)** cột **Thiết bị** hiện nhãn người đọc được cho dòng đăng nhập vừa
 *      tạo — và chính trình duyệt đang chạy cổng này là nguồn dữ liệu, nên không cần dựng
 *      gì thêm: nếu chuỗi `User-Agent` không tới được sổ audit, ô này rỗng;
 *   7. **(M-05, 01/08)** cột **Thay đổi** hiện `cũ → mới` cho ít nhất một dòng. Cổng
 *      **tự dựng dữ liệu** cho mệnh đề này (đổi giá một thuốc qua API thật) thay vì ghi chú
 *      *"chưa đo được vì thiếu dữ liệu"* — §7dg bài học 4: một cổng ở trạng thái *chưa đo
 *      được* đọc y hệt một cổng *đã đo và tốt*;
 *   8. trang không cuộn ngang · không lỗi JS.
 *
 * ⚠️ Mệnh đề ⑦ **có ghi**: nó đổi giá bán một thuốc rồi đổi lại. Chỉ chạy trên CSDL kiểm
 * thử. Đặt `SKIP_GHI=1` để bỏ qua — nhưng khi bỏ qua, cổng nói rõ nó **chưa đo được** ⑦
 * chứ không tính là đạt.
 */
import { firefox } from "playwright-core";
import { mkdirSync } from "node:fs";

import { cuonNgangTrang, inDong, trongKhungNhin } from "./lib/nhin-thay.mjs";
import { API, BASE, EMAIL, PASSWORD } from "./lib/moi-truong.mjs";

const OUT = process.env.OUT_DIR ?? "/tmp/nhat-ky";
const SKIP_GHI = process.env.SKIP_GHI === "1";
if (!EMAIL || !PASSWORD) {
  console.error("Thiếu EMAIL / PASSWORD.");
  process.exit(2);
}
mkdirSync(OUT, { recursive: true });

/**
 * ⑦ cần trong sổ **ít nhất một** dòng `CATALOG_DRUG_PRICE_CHANGED` — hành vi duy nhất hiện
 * ghi được cặp `old_price`/`new_price`.
 *
 * 🔴 Cổng **KHÔNG tự dựng** dữ liệu đó, dù dựng thì tiện hơn: tệp này nằm nhóm **ĐỌC
 * THUẦN** của `ui-gates.sh`, và một cổng đọc-thuần lặng lẽ ghi là cách chắc chắn để lần sau
 * không ai còn tin nhãn "đọc thuần" nữa. Thiếu dữ liệu thì **thoát mã 2 kèm đúng lệnh phải
 * gõ** — cùng khuôn `check-don-thuoc.mjs`, và cùng lý lẽ §7dg bài học 4: việc phải làm là
 * *dựng dữ liệu*, không phải *ghi chú thích rồi coi như xanh*.
 */
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
const soDoiGia = (
  await (
    await fetch(`${API}/audit-dashboard?action=CATALOG_DRUG_PRICE_CHANGED&limit=1`, {
      headers: { Authorization: `Bearer ${phien.access_token}` },
    })
  ).json()
).total;

if (!SKIP_GHI && !soDoiGia) {
  console.error(
    [
      "🔴 CHƯA ĐO ĐƯỢC mệnh đề ⑦ (cột Thay đổi): sổ audit không có dòng đổi giá nào.",
      "",
      "   Đây KHÔNG phải lỗi sản phẩm, nhưng cũng KHÔNG được đọc là đạt — suốt thời gian",
      "   này không ai biết cột 'giá trị cũ → mới' còn chạy hay không.",
      "",
      "   Dựng dữ liệu (đổi giá rồi trả lại nguyên giá cũ ⇒ doanh thu không lệch):",
      "     node scripts/lib/dung-du-lieu-doi-gia.mjs",
      "",
      "   Hoặc SKIP_GHI=1 để bỏ qua ⑦ — cổng sẽ nói rõ nó chưa đo được.",
    ].join("\n"),
  );
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
      // Giới hạn CÒN THẬT sau khi M-05 đóng: cột Thiết bị là manh mối, không phải bằng
      // chứng. Cổng vẫn đòi màn nói ra — nhưng đòi đúng câu còn đúng, không đòi câu cũ.
      noiGioiHan: /manh mối, không phải bằng chứng/i.test(document.body.innerText),
      // 🔴 Cổng cũ đòi câu "chưa ghi giá trị cũ" — câu đó nay SAI. Khẳng định nó biến mất,
      //    vì một cảnh báo đã hết đúng dạy người đọc bỏ qua mọi cảnh báo trên màn này.
      conCanhBaoCu: /chưa ghi.*giá trị cũ/i.test(document.body.innerText),
      // ⑥ M-06 — thiết bị. Phép đo phải là "có nhãn NGƯỜI ĐỌC ĐƯỢC", không phải "ô không
      //    rỗng": ô chứa nguyên chuỗi `Mozilla/5.0 (X11; Linux…` cũng không rỗng.
      coThietBi: rows.filter((r) =>
        /(iPhone|iPad|Điện thoại Android|Máy tính) · (Safari|Chrome|Firefox|Edge|Opera)/.test(
          cot(r, "Thiết bị"),
        ),
      ).length,
      // ⑦ M-05 — giá trị cũ → mới. Đòi mũi tên VÀ hai con số hai bên: một mũi tên đơn độc
      //    (`→ 25000`) là đúng ca mà `thayDoiGiaTri` cố ý từ chối hiện.
      coThayDoi: rows.filter((r) => /\d[\d.,]*\s*→\s*\d/.test(cot(r, "Thay đổi"))).length,
      // 🔴 Ba lỗi ẢNH bắt được mà phép đo cũ bỏ qua (01/08) — nay đo luôn:
      //   (a) ô "Thay đổi"/"Thiết bị" rỗng vẫn chiếm một dòng chỉ để in cái nhãn của nó
      //       ở khổ điện thoại (50 dòng × 2 = nửa màn chữ không nội dung);
      nhanRong: rows.filter((r) =>
        ["Thay đổi", "Thiết bị"].some((n) => {
          const o = r.querySelector(`td[data-nhan="${n}"]`);
          return o !== null && o.innerText.trim() === "";
        }),
      ).length,
      //   (b) dấu `·` mồ côi khi không có nhãn thiết bị, chỉ có IP;
      chamMoCoi: rows.filter((r) => /^·/.test(cot(r, "Thiết bị"))).length,
      //   (c) tác nhân hệ thống hiện ra như một người dùng chưa tra được tên.
      maHeThong: rows.filter((r) => /^Mã 0{8}$/.test(cot(r, "Người thực hiện"))).length,
      tongVanBan: document.body.innerText.match(/(\d+)\s+hoạt động/)?.[1] ?? null,
    };
  });

  await p.screenshot({ path: `${OUT}/${ten}-1-nhat-ky.png`, fullPage: true });

  // ④ Kỷ luật #21 — "có trong DOM" ≠ "nhìn thấy được".
  const oNguoi = await trongKhungNhin(p, p.locator('td[data-nhan="Người thực hiện"]').first());
  const oHoatDong = await trongKhungNhin(p, p.locator('td[data-nhan="Hoạt động"]').first());
  // Hai cột mới cũng phải NHÌN THẤY ĐƯỢC, không chỉ có trong DOM — thêm cột là đúng thao
  // tác đã đẩy cột cuối ra khỏi màn 390px ở 5/5 bảng hôm 29/07 (kỷ luật #21).
  const oThietBi = await trongKhungNhin(p, p.locator('td[data-nhan="Thiết bị"]').first());
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

  // ⑦ M-05 — đo trên màn ĐÃ LỌC, không trên 50 dòng mới nhất.
  //
  // 🔴 LỖI PHÉP ĐO, lộ ra 02/08. Bước tiền kiểm hỏi API *"sổ audit có dòng đổi giá nào
  //    không"* — tức TOÀN BỘ lịch sử — rồi khẳng định trên MÀN, vốn chỉ vẽ 50 dòng mới
  //    nhất. Hai nguồn khác nhau, và cổng ngầm giả định cái trước kéo theo cái sau. Ngày
  //    01/08 giả định ấy đúng vì dòng đổi giá vừa được dựng xong nên còn nằm đầu bảng.
  //    Hôm sau, 1248 sự kiện sau, nó đã trôi xuống dưới ⇒ cổng ĐỎ vì **phép đo**, không vì
  //    sản phẩm — mà log đỏ vì phép đo đọc y hệt log đỏ vì sản phẩm. Kỷ luật #23 gọi đúng
  //    tên chuyện này: hai vế của một phép so phải là hai nguồn ĐỘC LẬP, và ở đây chúng
  //    không những không độc lập, chúng còn không nói về cùng một tập dòng.
  //
  //    Nay: lọc cho đúng dòng ấy HIỆN RA rồi mới đo. Mệnh đề không đổi (*"cột Thay đổi hiện
  //    cũ → mới, và nhìn thấy được"*) — chỗ đo mới đúng thứ mệnh đề nói tới.
  let doiGia = { soDong: 0, coThayDoi: 0, chonDuoc: false };
  let oThayDoi = { dat: false, ly_do: "chưa đo" };
  if (d.soDong > 0) {
    // `selectOption` NÉM khi không có lựa chọn khớp (§7dg bài học 4). Bắt lấy và nói rõ, vì
    // "bản đồ nhãn đổi tên mã hành vi" là một kết luận khác hẳn "cột Thay đổi hỏng".
    try {
      await p.selectOption('select[aria-label="Loại hoạt động"]', "CATALOG_DRUG_PRICE_CHANGED");
      doiGia.chonDuoc = true;
    } catch {
      doiGia.chonDuoc = false;
    }
    if (doiGia.chonDuoc) {
      await p.waitForTimeout(3000);
      const sau = await p.evaluate(() => {
        const rows = [...document.querySelectorAll('[data-testid="ds-nhat-ky"] tbody tr')];
        const cot = (r) => r.querySelector('td[data-nhan="Thay đổi"]')?.innerText.trim() ?? "";
        return {
          soDong: rows.length,
          // Vẫn đòi mũi tên VÀ hai con số hai bên: `→ 25000` là đúng ca mà sản phẩm cố ý từ
          // chối hiện, nên nó không được tính là đạt.
          coThayDoi: rows.filter((r) => /\d[\d.,]*\s*→\s*\d/.test(cot(r))).length,
        };
      });
      doiGia = { ...doiGia, ...sau };
      oThayDoi = await trongKhungNhin(p, p.locator('td[data-nhan="Thay đổi"]').first());
      await p.screenshot({ path: `${OUT}/${ten}-3-loc-doi-gia.png`, fullPage: true });
    }
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
    !d.conCanhBaoCu &&
    d.coThietBi > 0 &&
    d.nhanRong === 0 &&
    d.chamMoCoi === 0 &&
    d.maHeThong === 0 &&
    // Bỏ qua bước dựng dữ liệu ⇒ mệnh đề ⑦ **chưa đo được**, và cổng KHÔNG tính là đạt
    // bằng cách lờ nó đi. Nó chỉ được miễn khi người chạy tự nói là mình bỏ qua.
    (SKIP_GHI || (doiGia.chonDuoc && doiGia.coThayDoi > 0)) &&
    oNguoi.dat &&
    oHoatDong.dat &&
    oThietBi.dat &&
    oThayDoi.dat &&
    cuon.dat &&
    datLoc &&
    loi.length === 0;
  if (!dat) hong++;

  console.log(`\n──${ten}──`);
  console.log(`  lối vào từ menu: ${coLoiVao > 0 ? "✓" : "🔴"} · nói rõ giới hạn cũ→mới: ${d.noiGioiHan ? "✓" : "🔴"}`);
  console.log(`  ${d.soDong} dòng ${d.soDong > 0 ? "✓" : "🔴 (rỗng — lọc ngày sai hay không có quyền?)"} · tổng ${d.tongVanBan ?? "?"}`);
  console.log(`  mã máy lọt ra màn — Hoạt động: ${d.maMayLotRa} · Đối tượng: ${d.loaiMayLotRa} (phải 0) ${d.maMayLotRa === 0 && d.loaiMayLotRa === 0 ? "✓" : "🔴"} · dòng chỉ có mã người: ${d.chiCoMa}/${d.soDong} ${d.chiCoMa < d.soDong ? "✓" : "🔴 (nối tên hỏng)"}`);
  console.log(
    `  ⑥ thiết bị đọc được: ${d.coThietBi}/${d.soDong} dòng ${d.coThietBi > 0 ? "✓" : "🔴 (User-Agent không tới được sổ audit)"}`,
  );
  console.log(
    `  ⑦ thay đổi cũ→mới (màn đã LỌC đổi giá): ${doiGia.coThayDoi}/${doiGia.soDong} dòng ${
      !doiGia.chonDuoc
        ? '🔴 không chọn được "Đổi giá" trong bộ lọc — bản đồ nhãn đổi tên mã hành vi?'
        : doiGia.coThayDoi > 0
          ? "✓"
          : SKIP_GHI
            ? "⏭️ CHƯA ĐO ĐƯỢC (SKIP_GHI=1) — không tính là đạt"
            : "🔴"
    }   ·   (50 dòng mới nhất, chỉ để tham khảo: ${d.coThayDoi})`,
  );
  console.log(
    `  cảnh báo cũ đã gỡ: ${d.conCanhBaoCu ? '🔴 vẫn còn "chưa ghi giá trị cũ" — nay là câu SAI' : "✓"}`,
  );
  console.log(
    `  ba lỗi ẢNH bắt được: nhãn rỗng ${d.nhanRong} · dấu · mồ côi ${d.chamMoCoi} · "Mã 00000000" ${d.maHeThong} (phải 0/0/0) ${
      d.nhanRong === 0 && d.chamMoCoi === 0 && d.maHeThong === 0 ? "✓" : "🔴"
    }`,
  );
  inDong("cột Người thực hiện nhìn thấy được", oNguoi);
  inDong("cột Hoạt động nhìn thấy được", oHoatDong);
  inDong("cột Thiết bị nhìn thấy được", oThietBi);
  inDong("cột Thay đổi nhìn thấy được", oThayDoi);
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
