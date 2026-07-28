import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Sale, SaleListItem } from "@/shared/api/types";

export const SALES_PAGE_SIZE = 50;

/**
 * `GET /sales` — hoá đơn trong khoảng ngày, mới nhất trước.
 *
 * `staleTime` ngắn (15 s) chứ không 60 s như bảng điều hành: đây là màn người
 * bán mở ra ngay sau khi bán để đối chiếu, nên một danh sách "hơi cũ" ở đây gây
 * hoang mang chứ không tiết kiệm được gì đáng kể.
 */
export function useSalesList(dateFrom: string, dateTo: string, page: number) {
  const params = new URLSearchParams({
    date_from: dateFrom,
    date_to: dateTo,
    limit: String(SALES_PAGE_SIZE),
    offset: String(page * SALES_PAGE_SIZE),
  });

  return useQuery({
    queryKey: ["sales", "list", dateFrom, dateTo, page],
    queryFn: () => apiFetch<SaleListItem[]>(`/sales?${params}`),
    retry: false,
    staleTime: 15_000,
  });
}

/** `GET /sales/{id}` — chi tiết một hoá đơn, chỉ tải khi người dùng mở nó ra. */
export function useSaleDetail(orderId: string | null) {
  return useQuery({
    queryKey: ["sales", "detail", orderId],
    queryFn: () => apiFetch<Sale>(`/sales/${orderId}`),
    enabled: orderId !== null,
    retry: false,
    staleTime: 60_000,
  });
}

export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
