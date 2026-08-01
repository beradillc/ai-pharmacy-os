import { ApiError } from "./errors";
import { getAccessToken } from "./token-storage";
import type { ProblemDetail } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip attaching `Authorization` — only /auth/login needs this, since it
   * runs before any session exists. */
  skipAuth?: boolean;
}

/**
 * Thin fetch wrapper: JSON in, JSON out, bearer token attached, RFC 7807
 * errors turned into {@link ApiError} instead of being handled ad hoc per call
 * site. No caching, no retries — POS actions (create sale, login) must never be
 * silently replayed by a framework layer the way GET reads safely can be.
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { body, skipAuth, headers, ...rest } = options;

  const finalHeaders = new Headers(headers);
  finalHeaders.set("Content-Type", "application/json");
  if (!skipAuth) {
    const token = getAccessToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const parsed: unknown = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    throw new ApiError(parsed as ProblemDetail);
  }
  return parsed as T;
}


/**
 * Tải một tệp NHỊ PHÂN từ API (hoá đơn PDF), kèm bearer token.
 *
 * 🔴 Vì sao không dùng `apiFetch`: nó `JSON.parse` mọi phản hồi, mà một tệp PDF thì
 * `JSON.parse` sẽ ném — và lỗi hiện ra dưới dạng *"Unexpected token %"*, một câu không
 * chỉ được về đây.
 *
 * 🔴 Và vì sao không mở thẳng `<a href="{BASE_URL}/sales/…/receipt">`: trình duyệt điều
 * hướng theo thẻ `a` **không mang theo header `Authorization`**, nên đường đó luôn trả
 * 401. Token nằm trong bộ nhớ của ứng dụng, không phải cookie — đó là lựa chọn có chủ
 * đích của `token-storage`, và cái giá phải trả là mọi lượt tải tệp đều phải đi qua đây.
 */
export async function apiFetchBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { headers });
  if (!res.ok) {
    // Máy chủ trả lỗi thì phần thân là RFC 7807 chứ không phải tệp — đọc bằng `text()`
    // rồi mới parse, để một phản hồi lỗi KHÔNG phải JSON cũng không nuốt mất mã trạng thái.
    const text = await res.text();
    let problem: ProblemDetail;
    try {
      problem = JSON.parse(text) as ProblemDetail;
    } catch {
      problem = {
        type: "about:blank",
        title: "Không tải được tệp",
        status: res.status,
        detail: text.slice(0, 200) || `Máy chủ trả ${res.status}`,
        instance: path,
      };
    }
    throw new ApiError(problem);
  }
  return res.blob();
}
