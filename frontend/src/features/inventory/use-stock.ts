import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { StockRow } from "@/shared/api/types";

export const STOCK_PAGE_SIZE = 50;

/** `GET /inventory/stock` — tồn theo lô, cận hạn lên trước (backend quyết thứ tự). */
export function useStock(page: number, branchId?: string) {
  const params = new URLSearchParams({
    limit: String(STOCK_PAGE_SIZE),
    offset: String(page * STOCK_PAGE_SIZE),
  });
  if (branchId) params.set("branch_id", branchId);

  return useQuery({
    queryKey: ["inventory", "stock", branchId ?? "all", page],
    queryFn: () => apiFetch<StockRow[]>(`/inventory/stock?${params}`),
    retry: false,
    staleTime: 30_000,
  });
}

/** Số ngày còn tới hạn dùng. Âm = ĐÃ hết hạn (lô hết hạn vẫn còn trong kho là
 * việc phải xử lý, không phải việc để ẩn đi). */
export function daysToExpiry(expiryDate: string): number {
  const expiry = new Date(`${expiryDate}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((expiry.getTime() - today.getTime()) / 86_400_000);
}

export type ExpiryTone = "expired" | "urgent" | "soon" | "ok";

/**
 * Ngưỡng cảnh báo hạn dùng. 90 ngày khớp đúng ngưỡng `near_expiry_count` mà ô
 * "Cận hạn dùng" trên Bảng điều hành đang đếm — hai màn nói cùng một con số thì
 * người dùng mới tin được cả hai.
 */
export function expiryTone(days: number): ExpiryTone {
  if (days < 0) return "expired";
  if (days <= 30) return "urgent";
  if (days <= 90) return "soon";
  return "ok";
}
