import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { PurchaseOrderListItem } from "@/shared/api/types";

export const PO_PAGE_SIZE = 50;

/**
 * Trạng thái đơn mua, đúng tên backend nhận qua `?status=`.
 *
 * 🔴 Danh sách này TỪNG THIẾU `RECEIVED` (phát hiện 29/07 khi dựng màn Nhận
 * hàng). Hệ quả: đơn nhận đủ hàng rơi khỏi mọi bộ lọc và hiện mã thô
 * "RECEIVED" thay vì tiếng Việt — đúng những đơn *thành công* thì biến mất.
 * Không cổng nào bắt được vì cả hai đầu đều là chuỗi hợp lệ về kiểu.
 *
 * `src/features/procurement/use-purchase-orders.test.ts` nay đối chiếu danh
 * sách này với enum trong `procurement/domain/entities.py` — đọc file Python
 * thật, không chép tay sang một bản sao rồi so bản sao với chính nó.
 */
export const PO_STATUSES = [
  "DRAFT",
  "ORDERED",
  "PARTIALLY_RECEIVED",
  "RECEIVED",
  "CLOSED",
  "CANCELLED",
] as const;
export type PoStatus = (typeof PO_STATUSES)[number];

export const PO_STATUS_LABEL: Record<string, string> = {
  DRAFT: "Nháp",
  ORDERED: "Đã gửi NCC",
  PARTIALLY_RECEIVED: "Nhận một phần",
  RECEIVED: "Đã nhận đủ",

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
