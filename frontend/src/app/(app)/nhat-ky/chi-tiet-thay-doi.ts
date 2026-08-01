/**
 * Đọc `context` của một dòng nhật ký thành thứ người đọc được (lỗi M-05 · M-06, UAT 2026-08-01).
 *
 * Hai câu hỏi mà sổ audit trước 01/08 **không** trả lời được:
 *
 * | Câu hỏi | Trước | Nay |
 * |---|---|---|
 * | *"đổi từ bao nhiêu sang bao nhiêu"* | phải mở `Biến động giá` ở màn khác | đọc thẳng trên dòng |
 * | *"làm từ máy nào"* | chỉ có IP — mà cả quầy đi chung một đường truyền | thêm thiết bị |
 *
 * 🔴 **Không đoán thiết bị ở backend.** Chuỗi `User-Agent` được lưu **thô** vào
 * `context.user_agent`; việc rút ra nhãn dễ đọc nằm ở đây, tại màn hình. Lý do: `audit_logs`
 * là bảng **chỉ-ghi-thêm và không xoá được** — một phép đoán sai lưu vào đó thì nằm đó vĩnh
 * viễn, còn đoán ở màn hình thì sửa lại lúc nào cũng được.
 */

/**
 * Nhãn cho **phần đuôi** của cặp khoá `old_X` / `new_X` (và `X_before` / `X_after`).
 *
 * 🔴 Đây là một bảng nối hai thế giới — kỷ luật #22. Khoá được khai bằng **đối số từ khoá
 * Python** trong các lời gọi `.with_context(...)`, và không trình biên dịch nào nối được hai
 * đầu: gõ sai `old_prices` thì TypeScript vẫn xanh, Python vẫn xanh, chỉ là màn hình **im
 * lặng không hiện gì cả**. Cổng `chi-tiet-thay-doi.test.ts` đọc thẳng tệp Python để canh
 * việc này, cả hai chiều (thiếu nhãn ⇒ lọt mã máy; thừa nhãn ⇒ bên kia đã đổi tên).
 */
export const NHAN_TRUONG: Record<string, string> = {
  price: "Giá bán",
  count: "Số hoạt chất",
  // Thêm lại 2026-08-01 khi `POST /inventory/adjust` (M-07) bắt đầu ghi `old_qty`/`new_qty`.
  // 🔴 Nhãn này từng bị **cổng bắt buộc gỡ bỏ** vài giờ trước, vì lúc ấy tôi đặt nó SẴN cho
  // một tính năng chưa viết — chiều "không nhãn thừa" đỏ đúng lý do. Đó là cổng làm việc
  // của nó: một bảng nhãn trỏ vào thứ backend không ghi là một lời hứa suông.
  qty: "Số lượng tồn",
};

/**
 * Các mã tác nhân **hệ thống** — những UUID cố định mà backend ghi vào `actor_user_id` khi
 * hành vi **không do người nào gây ra**.
 *
 * 🔴 Ảnh chụp 01/08 bắt được cột "Người thực hiện" hiện `Mã 00000000` cho các dòng *"Hệ
 * thống tự đối chiếu dị ứng"*. Không cổng nào đỏ: `00000000` là một mã rút gọn hợp lệ về
 * mọi mặt trừ ý nghĩa. `Mã 00000000` **đọc như một người dùng chưa tra được tên**, trong
 * khi sự thật là **không có người nào** — với sổ audit, hai chuyện đó khác hẳn nhau.
 *
 * 🔴 Và bản vá đầu tiên **sai vì đoán**: tôi cho rằng chỉ có một mã (`UUID(int=0)`), sửa
 * theo đó, cổng vẫn đỏ đúng 4 dòng. Sự thật là **bốn** mã khai ở **bốn tệp Python khác
 * nhau**. Đúng kỷ luật #22: cổng phải **ĐỌC nguồn bên kia**, không chép lại nó — và bản vá
 * chỉ kín khi **phạm vi** của nó đủ, không phải khi vị trí dòng sửa đúng.
 *
 * Ghi riêng từng mã thay vì gộp thành một chữ "hệ thống": *"hệ thống · đối chiếu dị ứng"*
 * trả lời được câu hỏi tiếp theo của người soát sổ, còn *"hệ thống"* thì bắt họ đi tra tiếp.
 */
export const TAC_NHAN_HE_THONG: Record<string, string> = {
  "00000000-0000-0000-0000-000000000000": "hệ thống",
  "00000000-0000-0000-0000-00005a1e5001": "hệ thống · nối module",
  "00000000-0000-0000-0000-00005a1e5002": "hệ thống · đề xuất nhập hàng",
  "00000000-0000-0000-0000-00005a1e5c05": "hệ thống · đồng bộ liên thông",
  // KHÔNG phải tác nhân hệ thống mà là **tài khoản cửa sau dev** (`api/deps.py _DEV_USER`,
  // chỉ sống được khi `SECURITY__ALLOW_DEV_AUTH=true`). Đặt nhãn nói thẳng ra như vậy: một
  // dòng audit mang mã này trên máy thật nghĩa là cửa dev đang mở, và đó là thứ người soát
  // sổ PHẢI thấy ngay chứ không phải một mã hex vô nghĩa.
  "00000000-0000-0000-0000-0000000d0001": "⚠️ tài khoản dev (không xác thực)",
};

/** Tên người thực hiện, hoặc nhãn hệ thống khi hành vi không do người nào gây ra. */
export function tenNguoiThucHien(
  actorUserId: string | null,
  tra: (id: string) => string | undefined,
): string {
  if (!actorUserId) return "hệ thống";
  const heThong = TAC_NHAN_HE_THONG[actorUserId.toLowerCase()];
  if (heThong) return heThong;
  // Không tra được tên thì hiện mã rút gọn, KHÔNG bỏ trống: một dòng nhật ký không có chủ
  // thể là một dòng vô dụng.
  return tra(actorUserId) ?? `Mã ${actorUserId.slice(0, 8)}`;
}

/** Một thay đổi giá trị đã ghép cặp, sẵn sàng để hiện. */
export interface ThayDoi {
  truong: string;
  nhan: string;
  cu: string;
  moi: string;
}

const CAP = [
  { truoc: /^old_(.+)$/, sau: (g: string) => `new_${g}` },
  { truoc: /^(.+)_before$/, sau: (g: string) => `${g}_after` },
] as const;

/**
 * Ghép các khoá `old_X`/`new_X` (và `X_before`/`X_after`) trong `context` thành danh sách
 * thay đổi.
 *
 * **Chỉ ghép khi có ĐỦ cả hai vế.** Một dòng chỉ có `new_price` mà không có `old_price` sẽ
 * không hiện — vì `→ 25.000` đọc như *"giá cũ là rỗng"*, tức là sai theo một cách trông rất
 * giống đúng. Thiếu vế thì đó là lỗi ở chỗ ghi, phải sửa ở đó.
 *
 * Trường chưa có nhãn thì hiện **nguyên tên trường**, không bỏ dòng — cùng kỷ luật với
 * `NHAN` trong `nhan-hanh-vi.ts`: giấu một thay đổi vì thiếu bản dịch là đúng thứ sổ audit
 * không được phép làm.
 */
export function thayDoiGiaTri(context: Record<string, string>): ThayDoi[] {
  const ra: ThayDoi[] = [];
  for (const khoa of Object.keys(context).sort()) {
    for (const { truoc, sau } of CAP) {
      const m = truoc.exec(khoa);
      if (!m) continue;
      const khoaSau = sau(m[1]);
      if (!(khoaSau in context)) continue;
      ra.push({
        truong: m[1],
        nhan: NHAN_TRUONG[m[1]] ?? m[1],
        cu: context[khoa],
        moi: context[khoaSau],
      });
    }
  }
  return ra;
}

/**
 * Nhãn thiết bị rút từ chuỗi `User-Agent` thô.
 *
 * Cố ý **thô sơ**: chỉ đủ để phân biệt *máy quầy* với *điện thoại của ai đó ở nhà* — đúng câu
 * hỏi mà chủ quầy hỏi khi sổ lệch. Không dùng thư viện phân tích UA: thêm một phụ thuộc
 * ngoài để đọc chính xác hơn tên trình duyệt là đổi lấy thứ không ai hỏi.
 *
 * ⚠️ **Chuỗi này do máy khách gửi nên giả mạo được.** Nó là *manh mối*, không phải *bằng
 * chứng* — và không có gì trong hệ thống rẽ nhánh trên nó.
 */
export function nhanThietBi(ua: string | undefined): string | null {
  if (!ua) return null;

  const may = /iPhone|iPod/i.test(ua)
    ? "iPhone"
    : /iPad/i.test(ua)
      ? "iPad"
      : /Android/i.test(ua)
        ? "Điện thoại Android"
        : /Windows|Macintosh|X11|Linux/i.test(ua)
          ? "Máy tính"
          : null;

  // Thứ tự có ý nghĩa: Edge và Chrome đều tự khai "Safari" trong UA của mình, và Edge còn
  // khai cả "Chrome". Đọc từ hiếm tới phổ biến, dừng ở cái đầu tiên khớp.
  const trinhDuyet = /Edg\//i.test(ua)
    ? "Edge"
    : /OPR\/|Opera/i.test(ua)
      ? "Opera"
      : /Firefox\//i.test(ua)
        ? "Firefox"
        : /Chrome\//i.test(ua)
          ? "Chrome"
          : /Safari\//i.test(ua)
            ? "Safari"
            : null;

  if (may && trinhDuyet) return `${may} · ${trinhDuyet}`;
  // Không nhận ra thì hiện 40 ký tự đầu của chuỗi thô, KHÔNG hiện "Không rõ": người soát sổ
  // cần thấy có cái gì đó lạ, còn "Không rõ" đọc y hệt "không có dữ liệu".
  return may ?? trinhDuyet ?? `${ua.slice(0, 40)}…`;
}
