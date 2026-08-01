import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

import { useAuthStore } from "./auth-store";

/**
 * Đổi mật khẩu của **chính mình** (lỗi C-01, UAT 2026-08-01).
 *
 * 🔴 Vì sao đây là lỗi Critical chứ không phải thiếu sót nhỏ: backend đặt
 * `must_change_password = true` cho **mọi tài khoản mới**, và trả cờ đó ngay trong phản hồi
 * đăng nhập — nhưng giao diện **không có chỗ nào để đổi** và **không chặn gì**. Nghĩa là
 * người dùng dùng vĩnh viễn mật khẩu do người tạo tài khoản đặt, và **người tạo biết mật
 * khẩu của họ**. Với một quầy thuốc sắp chạy thật, đó là lỗ hổng ở ngày đầu tiên.
 *
 * Backend đã có đủ từ trước (`POST /auth/change-password`, 204). Đây thuần là nối dây.
 *
 * Sau khi đổi thành công, **cập nhật cờ trong phiên đang mở** thay vì bắt đăng nhập lại:
 * token cũ vẫn hợp lệ (đổi mật khẩu không thu hồi phiên hiện tại), và đá người dùng ra
 * ngoài ngay sau khi họ vừa làm đúng là một hình phạt không có lý do.
 */
export function useChangePassword() {
  const session = useAuthStore((s) => s.session);
  const login = useAuthStore((s) => s.login);

  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      apiFetch<void>("/auth/change-password", { method: "POST", body }),
    onSuccess: () => {
      if (session) login({ ...session, must_change_password: false });
    },
  });
}
