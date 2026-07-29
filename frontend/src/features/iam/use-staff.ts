import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Role, RoleAssignment, StaffUser } from "@/shared/api/types";

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

/** `GET /users/{id}/roles` — vai trò đang cấp cho một người. */
export function useAssignments(userId: string | null) {
  return useQuery({
    queryKey: ["iam", "assignments", userId],
    queryFn: () => apiFetch<RoleAssignment[]>(`/users/${userId}/roles`),
    enabled: userId !== null,
    retry: false,
    staleTime: 30_000,
  });
}

/**
 * `POST /users/{id}/roles` — cấp một vai.
 *
 * `branch_id: null` nghĩa là cấp cho **toàn chuỗi**, không riêng một chi nhánh
 * (Luật 44/2024 Điều 17a — dược sĩ phụ trách chuỗi). Giao diện phải nói rõ khác
 * biệt đó: cấp nhầm phạm vi chuỗi cho một thu ngân là mở cửa mọi chi nhánh.
 */
export function useAssignRole(userId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { role_id: string; branch_id: string | null }) =>
      apiFetch<RoleAssignment>(`/users/${userId}/roles`, { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["iam", "assignments", userId] }),
  });
}

/** `DELETE /users/{id}/roles/{assignmentId}` — thu hồi một vai. */
export function useRevokeRole(userId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (assignmentId: string) =>
      apiFetch<void>(`/users/${userId}/roles/${assignmentId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["iam", "assignments", userId] }),
  });
}

/** Nhãn tiếng Việt cho vai hệ thống — mã vai là tiếng Anh trong CSDL. */
export const ROLE_LABEL: Record<string, string> = {
  system_admin: "Quản trị hệ thống",
  chain_pharmacist: "Dược sĩ phụ trách chuỗi",
  branch_pharmacist: "Dược sĩ phụ trách cơ sở",
  cashier: "Thu ngân",
  warehouse: "Thủ kho",
};
