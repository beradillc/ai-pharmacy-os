/**
 * Gộp doanh thu theo ngày — **test hồi quy cho một lỗi thật**.
 *
 * Lỗi: bản đầu gom bằng `created_at.slice(0, 10)` = ngày **UTC**. Việt Nam UTC+7
 * nên đơn bán lúc 00:10 sáng nay mang dấu thời gian UTC của hôm qua và rơi vào
 * cột hôm qua. Ảnh chụp 29/07 bắt tận mắt: ô KPI ghi *"Doanh thu hôm nay
 * 536.300 đ"* trong khi biểu đồ ngay dưới ghi *"Thấp nhất 29/07 · 0 đ"* — hai
 * khối trên **cùng một màn** nói ngược nhau.
 *
 * Không cổng nào bắt được: `tsc` thấy kiểu đúng, `lint` thấy cú pháp đúng, `build`
 * chạy ngon. Chỉ mắt người nhìn ảnh, hoặc test này.
 *
 * 🔴 Test chạy với `TZ=Asia/Ho_Chi_Minh` (đặt ở `vitest.config.ts`). Không ghim
 * múi giờ thì nó xanh ở máy chạy UTC và đỏ ở máy Việt Nam — tức là một test đo
 * môi trường chứ không đo mã.
 */
import { describe, expect, it } from "vitest";

import type { SaleListItem } from "@/shared/api/types";

import { bucketByDay } from "./use-revenue-series";

function sale(createdAt: string, subtotal: string, status = "COMPLETED"): SaleListItem {
  return {
    id: createdAt,
    branch_id: "b",
    created_at: createdAt,
    status,
    currency: "VND",
    subtotal,
    paid_total: subtotal,
    line_count: 1,
    customer_id: null,
    sold_by_user_id: null,
  };
}

/** Ngày địa phương hôm nay, dạng YYYY-MM-DD. */
function today(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

describe("gom theo ngày", () => {
  it("🔴 đơn lúc 00:10 SÁNG NAY vào cột HÔM NAY, không phải hôm qua", () => {
    // 00:10 giờ Việt Nam = 17:10 UTC của ngày hôm trước. Đây chính là ca đã sai.
    const local0010 = new Date(`${today()}T00:10:00+07:00`).toISOString();
    const points = bucketByDay([sale(local0010, "536300")], 28);

    const todayPoint = points.find((p) => p.date === today());
    expect(todayPoint?.revenue).toBe(536300);
    expect(points.reduce((s, p) => s + p.revenue, 0)).toBe(536300);
  });

  it("đơn lúc 23:50 tối nay KHÔNG nhảy sang ngày mai", () => {
    const local2350 = new Date(`${today()}T23:50:00+07:00`).toISOString();
    const points = bucketByDay([sale(local2350, "1000")], 28);
    expect(points.find((p) => p.date === today())?.revenue).toBe(1000);
  });

  it("giữ ĐỦ số ngày, ngày không bán mang giá trị 0", () => {
    // Bỏ ngày rỗng đi thì đường biểu đồ nối tắt qua khoảng trống, và một tuần ế
    // trông y hệt một tuần bình thường.
    const points = bucketByDay([], 28);
    expect(points.length).toBe(28);
    expect(points.every((p) => p.revenue === 0)).toBe(true);
  });

  it("ngày tăng dần — biểu đồ vẽ theo đúng thứ tự này", () => {
    const dates = bucketByDay([], 28).map((p) => p.date);
    expect(dates).toEqual([...dates].sort());
  });

  it("cộng dồn nhiều đơn cùng ngày", () => {
    const t = new Date(`${today()}T09:00:00+07:00`).toISOString();
    const points = bucketByDay([sale(t, "100"), sale(t, "250")], 28);
    expect(points.find((p) => p.date === today())?.revenue).toBe(350);
  });

  it("BỎ đơn đã huỷ — cùng quy ước với màn Hoá đơn", () => {
    const t = new Date(`${today()}T09:00:00+07:00`).toISOString();
    const points = bucketByDay([sale(t, "100"), sale(t, "999", "CANCELLED")], 28);
    expect(points.find((p) => p.date === today())?.revenue).toBe(100);
  });

  it("đơn ngoài cửa sổ bị bỏ, không làm hỏng tổng", () => {
    const points = bucketByDay([sale("2020-01-01T09:00:00+07:00", "999")], 28);
    expect(points.reduce((s, p) => s + p.revenue, 0)).toBe(0);
  });
});
