import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { SaleListItem } from "@/shared/api/types";

/** Số ngày biểu đồ nhìn lại — khớp cửa sổ 28 ngày của bảng điều hành. */
export const SERIES_DAYS = 28;

/** Trần một lượt gọi của `GET /sales` (backend chặn `limit <= 200`). */
const PAGE = 200;

/**
 * Chuỗi doanh thu theo ngày, gộp **ở phía client** từ `GET /sales`.
 *
 * 🔴 Đây là hệ quả trực tiếp của quyết định Q2 (không đụng backend trong đợt UI).
 * Đánh đổi ghi rõ để phiên sau không phải đoán:
 *
 * | | Cách này | Endpoint JSON riêng (Nâng cấp sau) |
 * |---|---|---|
 * | Backend | 0 dòng | 1 endpoint đọc |
 * | Lượt gọi | 1–2 cho 28 ngày ở quy mô nhà thuốc | 1, mọi quy mô |
 * | Rủi ro | tải nhiều đơn về chỉ để cộng lại | không |
 *
 * **Chốt chặn thành thật:** chỉ lấy tối đa 2 trang (400 đơn). Chạm trần thì
 * `truncated = true`, và màn hình phải NÓI RA rằng biểu đồ chưa đủ dữ liệu —
 * không được im lặng vẽ một đường thấp hơn sự thật. Một biểu đồ sai mà trông
 * bình thường là thứ tệ hơn cả không có biểu đồ.
 */
export interface RevenueSeries {
  points: { date: string; revenue: number }[];
  truncated: boolean;
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  const offset = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 10);
}

export function useRevenueSeries() {
  const dateFrom = isoDaysAgo(SERIES_DAYS - 1);
  const dateTo = isoDaysAgo(0);

  return useQuery<RevenueSeries>({
    queryKey: ["sales", "series", dateFrom, dateTo],
    retry: false,
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const rows: SaleListItem[] = [];
      let truncated = false;
      for (let page = 0; page < 2; page++) {
        const params = new URLSearchParams({
          date_from: dateFrom,
          date_to: dateTo,
          limit: String(PAGE),
          offset: String(page * PAGE),
        });
        const batch = await apiFetch<SaleListItem[]>(`/sales?${params}`);
        rows.push(...batch);
        if (batch.length < PAGE) break;
        if (page === 1) truncated = true;
      }

      // Khởi tạo đủ 28 ngày với 0 trước khi cộng: ngày không bán được là một sự
      // thật cần thấy trên biểu đồ, không phải một khoảng trống để đường nối tắt.
      const byDay = new Map<string, number>();
      for (let i = SERIES_DAYS - 1; i >= 0; i--) byDay.set(isoDaysAgo(i), 0);

      for (const row of rows) {
        if (row.status === "CANCELLED") continue; // cùng quy ước với màn Hoá đơn
        const day = row.created_at.slice(0, 10);
        if (byDay.has(day)) byDay.set(day, (byDay.get(day) ?? 0) + Number(row.subtotal));
      }

      return {
        points: [...byDay.entries()].map(([date, revenue]) => ({ date, revenue })),
        truncated,
      };
    },
  });
}
