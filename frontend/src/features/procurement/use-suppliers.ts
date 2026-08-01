import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/** Nhà cung cấp — khớp `SupplierResponse` của backend. */
export interface Supplier {
  id: string;
  name: string;
  tax_code: string | null;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  is_active: boolean;
}

export interface NewSupplier {
  name: string;
  tax_code?: string | null;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
}

/**
 * Danh sách nhà cung cấp (lỗi M-01, UAT 2026-08-01).
 *
 * 🔴 Vì sao thiếu màn này là Major chứ không Minor: **màn Đơn mua hàng đã tồn tại và chạy
 * được, nhưng dùng không được** — không tạo được đơn mua khi chưa có nhà cung cấp nào. Một
 * màn hoàn chỉnh bị khoá bởi một màn không tồn tại là loại thiếu sót khó nhìn ra từ phía
 * backend, vì ở đó cả hai đều "đã xong".
 */
export function useSuppliers() {
  return useQuery({
    queryKey: ["procurement", "suppliers"],
    queryFn: () => apiFetch<Supplier[]>("/suppliers"),
    staleTime: 60_000,
  });
}

export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NewSupplier) =>
      apiFetch<Supplier>("/suppliers", { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["procurement"] });
    },
  });
}
