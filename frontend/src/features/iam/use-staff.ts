import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Role, StaffUser } from "@/shared/api/types";

export const STAFF_PAGE_SIZE = 50;

/** `GET /users` — nhân viên của tenant. Đòi `iam.user.read`. */
export function useStaff(page: number) {
  const params = new URLSearchParams({
    limit: String(STAFF_PAGE_SIZE),
    offset: String(page * STAFF_PAGE_SIZE),
  });
  return useQuery({
    queryKey: ["iam", "users", page],
    queryFn: () => apiFetch<StaffUser[]>(`/users?${params}`),
    retry: false,
    staleTime: 30_000,
  });
}

/** `GET /roles` — danh mục vai trò. Đòi `iam.role.read`. */
export function useRoles() {
  return useQuery({
    queryKey: ["iam", "roles"],
    queryFn: () => apiFetch<Role[]>("/roles"),
    retry: false,
    // Vai trò hệ thống gần như không đổi — hỏi lại mỗi 30 giây là phí.
    staleTime: 10 * 60_000,
  });
}

export interface CreateStaffInput {
  email: string;
  password: string;
  full_name: string;
}

/**
 * `POST /users` — tạo nhân viên.
 *
 * Backend đặt `must_change_password = true` cho tài khoản mới, nên mật khẩu người
 * quản lý gõ ở đây chỉ là **mật khẩu lần đầu**: nhân viên buộc phải đổi khi đăng
 * nhập. Màn hình phải nói đúng điều đó — nếu không, người quản lý tưởng mình vừa
 * đặt mật khẩu vĩnh viễn cho người khác và sẽ đi nhắn nó qua tin nhắn.
 */
export function useCreateStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateStaffInput) => apiFetch<StaffUser>("/users", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["iam", "users"] }),
  });
}

/** `PUT /users/{id}/active` — bật/tắt tài khoản. Đòi `iam.user.write`. */
export function useSetStaffActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      apiFetch<StaffUser>(`/users/${id}/active`, { method: "PUT", body: { active } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["iam", "users"] }),
  });
}

export const STAFF_STATUS_LABEL: Record<string, string> = {
  ACTIVE: "Đang hoạt động",
  DISABLED: "Đã tắt",
  LOCKED: "Đang khoá",
};
