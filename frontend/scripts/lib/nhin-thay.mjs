/**
 * Bộ đo dùng chung cho **kỷ luật #21**: *nhìn thấy được* ≠ *có trên trang*.
 *
 * 🔴 Vì sao tồn tại: `innerText`/`textContent` đọc được **cả phần tràn ra ngoài khung
 * nhìn**. Một cổng khẳng định *"màn hình hiện con số lệch"* bằng `innerText` sẽ xanh trọn
 * vẹn trong lúc con số đó nằm ngoài rìa màn hình điện thoại và không ngón tay nào chạm
 * tới. Ba lần cùng hình dạng, ba màn khác nhau:
 *   · 29/07 cột định danh trượt khỏi màn ở **5/5 bảng**
 *   · 31/07 ba ô nhập cao ~125px mỗi ô ở `/khoi-tao-ton`
 *   · 01/08 cột **Chênh** ở `/kiem-ke` — *đúng cột là lý do màn đó tồn tại* — bị cắt khỏi
 *     màn 390px **trong lúc cổng Playwright báo ✓**
 * Cả ba lần thứ bắt được là **ảnh chụp**, không phải phép đo. Tệp này để phép đo biết cái
 * mà ảnh biết — kỷ luật #10: cưỡng chế bằng máy, không bằng trí nhớ.
 *
 * Hai phép đo, cố ý tách rời:
 *   `cuonNgangTrang`  — cả TRANG có phải cuộn ngang không. Áp cho mọi màn, không cần khai
 *                       báo gì. Đây là lưới an toàn rẻ nhất.
 *   `trongKhungNhin`  — MỘT phần tử cụ thể có nằm trọn trong khung nhìn không. Dùng cho
 *                       thứ người dùng **phải nhìn thấy mới làm việc được**.
 *
 * ⚠️ Bảng cuộn ngang **trong khung riêng của nó** là chấp nhận được và không tính là lỗi —
 * `cuonNgangTrang` chỉ đo `documentElement`, đúng như #21 viết. Cột nào bắt buộc phải thấy
 * thì khai riêng bằng `trongKhungNhin`, đừng cấm mọi thứ cuộn.
 */

/**
 * Có phần tử nào tràn ra ngoài bề ngang khung nhìn không.
 *
 * 🔴 **KHÔNG dùng `documentElement.scrollWidth > clientWidth`** — dù đó đúng là câu chữ kỷ
 * luật #21 viết ra. Dự án này có `html, body { overflow-x: hidden }` trong `globals.css`,
 * nên `scrollWidth` **luôn** bằng `clientWidth` và phép đo đó **không bao giờ đỏ được**.
 * Phát hiện ngay lần đột biến đầu tiên (01/08): chèn một `<div style="width:1200px">` vào
 * `/kiem-ke` mà cổng vẫn xanh trọn vẹn. Một phép đo không thể đỏ là một phép đo không
 * chứng minh gì — đúng họ với 16 ca "niềm tin giả" kiểm toán 26/07 đếm được, và là lý do
 * kỷ luật #14 đòi thấy đỏ **trước** khi tin vào màu xanh.
 *
 * Tệ hơn: `overflow-x: hidden` không làm nội dung vừa màn, nó chỉ **cắt** đi. Người dùng
 * không vuốt tới được nữa — hỏng nặng hơn là cuộn ngang, mà lại lặng lẽ hơn.
 *
 * Nên đo thẳng **hình chữ nhật của từng phần tử**. Bỏ qua phần tử nằm trong một khung cuộn
 * ngang hợp lệ (`overflow-x: auto|scroll`) — bảng rộng tự cuộn trong khung riêng của nó là
 * thiết kế có chủ đích, không phải lỗi; thứ trong đó mà **bắt buộc phải thấy** thì khai
 * riêng bằng {@link trongKhungNhin}.
 */
export async function cuonNgangTrang(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const trongKhungCuon = (e) => {
      for (let a = e.parentElement; a; a = a.parentElement) {
        const ox = getComputedStyle(a).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
      }
      return false;
    };
    const thuPham = [...document.querySelectorAll("body *")]
      .map((e) => ({ e, r: e.getBoundingClientRect() }))
      .filter(({ r }) => r.width > 0 && r.height > 0 && r.right > vw + 1)
      .filter(({ e }) => !trongKhungCuon(e))
      .slice(0, 3)
      .map(({ e, r }) => `${e.tagName.toLowerCase()}.${(e.className || "").toString().split(" ")[0]} → ${Math.round(r.right)}px`);
    return { dat: thuPham.length === 0, vw, thuPham };
  });
}

/**
 * Một phần tử có nằm TRỌN trong khung nhìn theo chiều ngang không.
 *
 * `locator` là Playwright locator đã trỏ đúng phần tử. Trả `{ dat, ly_do, box, vw }`.
 *
 * Ba trường hợp `dat === false`, phân biệt rõ vì cách sửa khác hẳn nhau:
 *   `khong-ton-tai`  — không có phần tử nào khớp. **Không** phải lỗi bố cục; có thể là
 *                      locator sai hoặc màn chưa tải xong. Cổng phải nói ra chứ không nuốt.
 *   `bi-an`          — có trong DOM nhưng `boundingBox()` trả `null` (display:none, hoặc
 *                      nằm trong nhánh chưa mở).
 *   `tran-ra-ngoai`  — đúng cái #21 canh: `x + width > vw`, hoặc `x < 0`.
 */
export async function trongKhungNhin(page, locator) {
  if ((await locator.count()) === 0) {
    return { dat: false, ly_do: "khong-ton-tai", box: null, vw: null };
  }
  const box = await locator.first().boundingBox();
  const vw = page.viewportSize().width;
  if (box === null) return { dat: false, ly_do: "bi-an", box: null, vw };
  const dat = box.x >= 0 && box.x + box.width <= vw + 0.5;
  return { dat, ly_do: dat ? null : "tran-ra-ngoai", box, vw };
}

/** In một dòng kết quả thống nhất giữa mọi cổng, để đọc log không phải đoán. */
export function inDong(ten, kq) {
  if (kq.dat) return console.log(`  ✓ ${ten}`);
  if (kq.ly_do === "khong-ton-tai") return console.log(`  🔴 ${ten} — KHÔNG TÌM THẤY`);
  if (kq.ly_do === "bi-an") return console.log(`  🔴 ${ten} — có trong DOM nhưng bị ẩn`);
  if (kq.ly_do === "tran-ra-ngoai") {
    const { box, vw } = kq;
    return console.log(
      `  🔴 ${ten} — tràn ra ngoài: x=${Math.round(box.x)} + w=${Math.round(box.width)} = ` +
        `${Math.round(box.x + box.width)} > khung ${vw}px`,
    );
  }
  return console.log(
    `  🔴 ${ten} — ${kq.thuPham.length} phần tử tràn khỏi khung ${kq.vw}px: ${kq.thuPham.join(" · ")}`,
  );
}
