import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { SaleListItem } from "@/shared/api/types";

/**
 * Số liệu "hôm nay" cho dashboard, dựng từ `GET /sales` đã có (Sprint 10, D1).
 *
 * 🔴 Quyết định GĐ 2026-07-29 (Q2, `docs/ui/ROUTING_PLAN.md` §8): **không thêm
 * endpoint backend nào cho đợt UI này.** `GET /sales` không tham số = hoá đơn hôm
 * nay, mới nhất trước — đủ để tính doanh thu ngày, số đơn, và danh sách giao dịch
 * gần đây từ **một** lời gọi.
 *
 * **Giới hạn đã biết, không giấu:** `limit` tối đa 200. Nhà thuốc bán hơn 200 đơn
 * một ngày sẽ thấy con số bị cắt ngọn. Với quy mô hiện tại (demo ~10 đơn/ngày) thì
 * còn xa mới chạm, nhưng đây là lý do `docs/ui/UI_GAP_REPORT.md` xếp "endpoint
 * doanh thu JSON" vào mục Nâng cấp sau chứ không xoá khỏi danh sách.
 *
 * Đơn **đã huỷ** bị loại khỏi doanh thu nhưng vẫn đếm trong danh sách giao dịch —
 * cùng quy ước với màn Hoá đơn, để hai màn không nói hai con số khác nhau.
 */
export const TODAY_LIMIT = 200;

export interface TodaySummary {
  revenue: number;
  orderCount: number;
  recent: SaleListItem[];
}

export function useToday() {
  return useQuery<SaleListItem[], Error, TodaySummary>({
    queryKey: ["sales", "today"],
    queryFn: () => apiFetch<SaleListItem[]>(`/sales?limit=${TODAY_LIMIT}`),
    retry: false,
    staleTime: 30_000,
    select: (rows) => ({
      revenue: rows
        .filter((r) => r.status !== "CANCELLED")
        .reduce((sum, r) => sum + Number(r.subtotal), 0),
      orderCount: rows.length,
      recent: rows.slice(0, 6),
    }),
  });
}
