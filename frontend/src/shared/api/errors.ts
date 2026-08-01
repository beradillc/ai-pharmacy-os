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
export function thongDiepLoi(err: unknown, mac_dinh = "Đã có lỗi xảy ra"): string {
  if (err instanceof ApiError) {
    const d: unknown = err.problem.detail;
    if (typeof d === "string" && d) return d;
    if (Array.isArray(d)) {
      const dong = d
        .map((x) => (typeof x === "object" && x !== null && "msg" in x ? String(x.msg) : String(x)))
        .filter(Boolean);
      if (dong.length) return dong.join(" · ");
    }
    return err.problem.title || mac_dinh;
  }
  if (err instanceof Error && err.message) return err.message;
  return mac_dinh;
}
