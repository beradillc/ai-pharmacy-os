import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/** `GET /auth/me` — khớp `MeResponse` của backend. */
export interface Me {
  user_id: string;
  tenant_id: string;
  branch_id: string;
  permissions: string[];
  email: string;
  full_name: string;
  last_login_at: string | null;
  must_change_password: boolean;
}

/**
 * Hồ sơ của **chính người đang đăng nhập** — nguồn của mục *Tài khoản của tôi* (lỗi M-03,
 * UAT 2026-08-01).
 *
 * 🔴 Không gác quyền, có chủ đích: đọc tên của chính mình không phải là quản lý nhân sự.
 * Đường còn lại là `GET /users`, đòi `iam.user.read` — tức là **thu ngân không xem được
 * tên của chính mình**. Vì thế `/auth/me` được bổ sung `email`/`full_name` ở backend thay
 * vì màn này đi vòng qua danh sách nhân viên.
 *
 * Dữ liệu này đổi rất hiếm (đổi tên, đổi mật khẩu) nhưng `last_login_at` thì đổi mỗi lần
 * đăng nhập ⇒ để `staleTime` ngắn, không cache dài.
 */
export function useMe() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => apiFetch<Me>("/auth/me"),
    staleTime: 30_000,
  });
}
