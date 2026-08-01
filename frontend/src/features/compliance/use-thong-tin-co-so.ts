"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/**
 * Thông tin cơ sở — UAT lỗi M-02 (2026-08-01).
 *
 * Trước đó tên/địa chỉ/điện thoại/mã số thuế là **biến môi trường toàn cục**
 * (`core.config.OrgSettings`): mọi nhà thuốc dùng chung một bản triển khai đều in ra cùng
 * một tên trên hoá đơn, và không ai đổi được từ trong ứng dụng.
 *
 * 🔴 Dùng lại endpoint `/compliance/tenant-config` đã có chứ không dựng một endpoint mới:
 * bốn trường này nằm trên **cùng một tờ giấy chứng nhận đủ điều kiện kinh doanh dược** với
 * mã cơ sở do Cục QLD cấp. Tách ra hai chỗ là chia đôi hồ sơ pháp lý của cơ sở, và chỗ thứ
 * hai sẽ lệch với chỗ thứ nhất.
 */
export interface ThongTinCoSo {
  ma_co_so_ban_le: string;
  ma_co_so_ban_buon: string | null;
  ten_co_so: string | null;
  dia_chi: string | null;
  dien_thoai: string | null;
  ma_so_thue: string | null;
}

/**
 * `null` = **chưa khai bao giờ** (backend trả 404), khác hẳn với "đã khai nhưng để trống".
 * Màn hình phải phân biệt hai thứ đó: một cơ sở chưa khai cần được mời khai, còn một cơ sở
 * đã khai rồi xoá đi là một lựa chọn của người dùng.
 */
export function useThongTinCoSo() {
  return useQuery({
    queryKey: ["compliance", "tenant-config"],
    queryFn: async () => {
      try {
        return await apiFetch<ThongTinCoSo>("/compliance/tenant-config");
      } catch (e) {
        if (e instanceof Error && "problem" in e) {
          const p = (e as { problem?: { status?: number } }).problem;
          if (p?.status === 404) return null;
        }
        throw e;
      }
    },
    staleTime: 60_000,
  });
}

export function useLuuThongTinCoSo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: ThongTinCoSo) =>
      apiFetch<ThongTinCoSo>("/compliance/tenant-config", { method: "PUT", body: v }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["compliance", "tenant-config"] });
    },
  });
}
