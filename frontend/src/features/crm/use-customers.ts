import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Customer } from "@/shared/api/types";

export const CUSTOMER_PAGE_SIZE = 50;

/**
 * `GET /customers` — danh sách khách hàng.
 *
 * Backend **không** có tham số tìm kiếm cho khách hàng, và việc đó không phải
 * thiếu sót nhất thời: họ tên và số điện thoại là cột **mã hoá at-rest**, nên
 * `LIKE` trên chúng không chạy được — tìm kiếm thật cần blind index, một việc
 * riêng chưa làm. Vì vậy ô lọc ở màn này lọc **trong trang đang tải**, và màn
 * hình phải nói đúng điều đó thay vì trông như một ô tìm kiếm toàn cục.
 */
export function useCustomers(page: number) {
  const params = new URLSearchParams({
    limit: String(CUSTOMER_PAGE_SIZE),
    offset: String(page * CUSTOMER_PAGE_SIZE),
  });

  return useQuery({
    queryKey: ["crm", "customers", page],
    queryFn: () => apiFetch<Customer[]>(`/customers?${params}`),
    retry: false,
    staleTime: 60_000,
  });
}

/** Lọc trong trang đã tải — xem docstring trên về giới hạn. */
export function filterLoaded(customers: Customer[], term: string): Customer[] {
  const needle = term.trim().toLowerCase();
  if (!needle) return customers;
  return customers.filter(
    (c) =>
      c.full_name.toLowerCase().includes(needle) || (c.phone ?? "").toLowerCase().includes(needle),
  );
}
