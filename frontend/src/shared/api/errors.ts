import type { ProblemDetail } from "./types";

/** Thrown by {@link apiFetch} for any non-2xx response. Carries the parsed
 * problem+json body so callers can branch on `type` (see error_type constants
 * in `core/errors.py` / `modules/iam/application/errors.py`) without re-parsing. */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(problem: ProblemDetail) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }

  /** `https://errors.pharmacy-os/branch-required` — login succeeded but the
   * account reaches several branches; `problem.branches` holds the picker list. */
  get isBranchSelectionRequired(): boolean {
    return this.problem.type === "https://errors.pharmacy-os/branch-required";
  }

  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}


/**
 * Thông điệp lỗi **luôn là chuỗi**, hợp cho mọi lỗi ném ra từ tầng API.
 *
 * 🔴 Vì sao cần hàm này chứ không dùng thẳng `err.problem.detail`: với lỗi **422** của
 * FastAPI/Pydantic, `detail` KHÔNG phải chuỗi mà là một **mảng object**
 * `{type, loc, msg, input, ctx}`. Đưa thẳng vào JSX thì React ném
 * *"Objects are not valid as a React child"* và **vỡ cả cây** — người dùng mất luôn màn
 * hình đang đứng, chỉ vì một lỗi lẽ ra chỉ cần hiện một dòng chữ đỏ.
 *
 * Bắt được ngày 01/08 bằng cổng trình duyệt (`check-hoa-don`), sau khi backend trả 422 cho
 * một giá trị enum chưa có. Không cổng nào khác thấy: `tsc` chiều lòng vì `ProblemDetail`
 * khai `detail: string`, và **máy chủ thì không đọc khai báo TypeScript của máy khách**.
 */

/**
 * 🔴 **Lỗi 422 hiện NGUYÊN VĂN TIẾNG ANH và không nói ô nào.** (02/08)
 *
 * Bản vá 01/08 chỉ chữa **hình dạng** (mảng object làm vỡ cây React), không chữa **nội dung**:
 * nó lấy `x.msg` rồi in thẳng. Dược sĩ ở quầy bấm Lưu và nhận được đúng dòng này:
 *
 *     String should have at most 12 characters
 *
 * Tiếng Anh · không nói **ô nào** · không nói **phải làm gì**. Ba thứ thiếu, mà `x.loc` —
 * chứa đúng tên ô — thì bị vứt đi. Lộ ra khi quay video 02 (mã cơ sở bán lẻ dài 14 ký tự).
 *
 * Nay: ghép **tên ô** (từ `loc`) với **thông điệp đã dịch** (từ `msg`). Không dịch được thì
 * giữ nguyên văn — thà một câu tiếng Anh có kèm tên ô còn hơn một câu tiếng Việt đoán sai.
 */
const NHAN_O: Record<string, string> = {
  ten_co_so: "Tên cơ sở",
  dia_chi: "Địa chỉ",
  dien_thoai: "Điện thoại",
  ma_so_thue: "Mã số thuế",
  ma_co_so_ban_le: "Mã cơ sở bán lẻ",
  ma_co_so_ban_buon: "Mã cơ sở bán buôn",
  email: "Email",
  password: "Mật khẩu",
  full_name: "Họ tên",
  quantity: "Số lượng",
  unit_price: "Đơn giá",
  lot_no: "Số lô",
  expiry_date: "Hạn dùng",
};

/** Mẫu thông điệp Pydantic hay gặp → tiếng Việt. Bắt theo **hình dạng**, không chép cả câu. */
function dichThongDiep(msg: string): string {
  let m: RegExpMatchArray | null;
  if ((m = msg.match(/at most (\d+) characters?/i))) return `tối đa ${m[1]} ký tự`;
  if ((m = msg.match(/at least (\d+) characters?/i))) return `cần ít nhất ${m[1]} ký tự`;
  if (/field required/i.test(msg)) return "chưa điền";
  if (/should be a valid email/i.test(msg)) return "email không hợp lệ";
  if (/should be a valid (integer|number|decimal)/i.test(msg)) return "phải là một con số";
  if (/greater than 0|should be greater than 0/i.test(msg)) return "phải lớn hơn 0";
  if (/should be a valid date/i.test(msg)) return "ngày không hợp lệ";
  return msg; // không dịch được thì giữ nguyên — đừng đoán
}

function dichMotLoi(x: unknown): string {
  if (typeof x !== "object" || x === null) return String(x);
  const o = x as { msg?: unknown; loc?: unknown };
  const msg = "msg" in o ? String(o.msg) : "";
  if (!msg) return "";
  // `loc` là mảng kiểu ["body", "ma_co_so_ban_le"] — lấy phần tử chuỗi CUỐI CÙNG, bỏ "body".
  const loc = Array.isArray(o.loc)
    ? [...o.loc].reverse().find((v) => typeof v === "string" && v !== "body")
    : undefined;
  const ten = typeof loc === "string" ? (NHAN_O[loc] ?? loc) : "";
  const dich = dichThongDiep(msg);
  return ten ? `${ten}: ${dich}` : dich;
}

export function thongDiepLoi(err: unknown, mac_dinh = "Đã có lỗi xảy ra"): string {
  if (err instanceof ApiError) {
    const d: unknown = err.problem.detail;
    if (typeof d === "string" && d) return d;
    if (Array.isArray(d)) {
      const dong = d.map(dichMotLoi).filter(Boolean);
      if (dong.length) return dong.join(" · ");
    }
    return err.problem.title || mac_dinh;
  }
  if (err instanceof Error && err.message) return err.message;
  return mac_dinh;
}

/**
 * Lỗi này bấm lại có ích không?
 *
 * Mất mạng và 5xx thì có — máy chủ có thể đã tỉnh lại. 4xx thì **không**: yêu cầu sai ở phía
 * người gọi, gửi lại y hệt sẽ hỏng y hệt. Trả `true` cho lỗi **không phải** `ApiError` (mất
 * mạng, `JSON.parse` hỏng): những lỗi đó đúng là loại thử lại được.
 */
export function thuLaiDuocKhong(loi: unknown): boolean {
  if (!(loi instanceof ApiError)) return true;
  return loi.status >= 500;
}
