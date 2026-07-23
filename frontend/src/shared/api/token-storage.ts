import type { Session } from "./types";

/**
 * Session persistence — localStorage (chốt của sếp 2026-07-23: tốc độ triển
 * khai ưu tiên hơn so với httpOnly cookie ở giai đoạn này).
 *
 * Đánh đổi đã ghi nhận, không lặp lại đề xuất: một lỗ hổng XSS trong ứng dụng
 * sẽ đọc được token trực tiếp. Siết lại (chuyển sang cookie qua route handler)
 * là việc để sau, không phải bây giờ.
 */
const STORAGE_KEY = "beras.session";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getSession(): Session | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    // Corrupted value (manual edit, storage quota edge case, format change
    // across a deploy) — treat as logged out rather than crashing the app.
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function setSession(session: Session): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return getSession()?.access_token ?? null;
}
