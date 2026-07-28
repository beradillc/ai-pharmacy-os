import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { PurchaseOrderListItem } from "@/shared/api/types";

export const PO_PAGE_SIZE = 50;

/** Trạng thái đơn mua, đúng tên backend nhận qua `?status=`. */
export const PO_STATUSES = ["DRAFT", "ORDERED", "PARTIALLY_RECEIVED", "CLOSED", "CANCELLED"] as const;
export type PoStatus = (typeof PO_STATUSES)[number];

export const PO_STATUS_LABEL: Record<string, string> = {
  DRAFT: "Nháp",
  ORDERED: "Đã gửi NCC",
  PARTIALLY_RECEIVED: "Nhận một phần",
  CLOSED: "Đã đóng",
  CANCELLED: "Đã huỷ",
};

/** `GET /purchase-orders` — mới nhất trước, kèm tên NCC và tổng tiền đặt. */
export function usePurchaseOrders(status: PoStatus | null, page: number) {
  const params = new URLSearchParams({
    limit: String(PO_PAGE_SIZE),
    offset: String(page * PO_PAGE_SIZE),
  });
  if (status) params.set("status", status);

  return useQuery({
    queryKey: ["procurement", "purchase-orders", status ?? "all", page],
    queryFn: () => apiFetch<PurchaseOrderListItem[]>(`/purchase-orders?${params}`),
    retry: false,
    staleTime: 30_000,
  });
}
