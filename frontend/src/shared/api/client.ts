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
