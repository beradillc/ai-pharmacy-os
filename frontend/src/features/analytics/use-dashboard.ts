import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Dashboard } from "@/shared/api/types";

/** Số ngày bảng điều hành nhìn lại. 28 chứ không phải "tháng này": đầu tháng
 * thì "tháng này" luôn trông như doanh thu sụt (docs/19 §7.2, Chain chốt). */
export const DASHBOARD_WINDOW_DAYS = 28;

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function dashboardRange(): { date_from: string; date_to: string } {
  return { date_from: isoDaysAgo(DASHBOARD_WINDOW_DAYS - 1), date_to: isoDaysAgo(0) };
}

/**
 * `GET /analytics/dashboard` — bốn ô + thuốc bán chạy.
 *
 * Không `retry`: màn này có ô "Thử lại" riêng cho từng lỗi (docs/19 §4), nên
 * việc thử lại là quyết định của người dùng, không phải của thư viện — thử
 * ngầm chỉ làm màn hình treo lâu hơn mà không nói gì.
 */
export function useDashboard(branchId?: string) {
  const range = dashboardRange();
  const params = new URLSearchParams(range);
  if (branchId) params.set("branch_id", branchId);

  return useQuery({
    queryKey: ["analytics", "dashboard", branchId ?? "self", range.date_from, range.date_to],
    queryFn: () => apiFetch<Dashboard>(`/analytics/dashboard?${params}`),
    retry: false,
    staleTime: 60_000,
  });
}
