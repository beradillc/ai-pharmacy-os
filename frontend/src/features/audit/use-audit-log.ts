import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/** Một dòng nhật ký — khớp `AuditEntryResponse` của backend. */
export interface AuditEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  occurred_at: string;
  /** Ngữ cảnh tự do: `branch_id`, `client_ip`… Backend trả `dict[str, str]`. */
  context: Record<string, string>;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

export const AUDIT_PAGE_SIZE = 50;

/**
 * Nhật ký hoạt động của cơ sở (lỗi M-04, UAT 2026-08-01).
 *
 * 🔴 Vì sao chủ quầy cần màn này: khi có **chênh lệch tiền hoặc hàng**, câu hỏi đầu tiên là
 * *"ai đã làm gì, lúc nào"*. Backend ghi đủ từ Sprint 7 và có `GET /audit-dashboard` — nhưng
 * không có màn nào ⇒ dữ liệu nằm đó mà không ai tra được.
 *
 * Quyền `audit.dashboard.read` — **cấp chi nhánh trở lên**, không phải ai đứng quầy cũng
 * xem được ai đã làm gì.
 *
 * ⚠️ Nhật ký hiện ghi *đã xảy ra hành động gì*, **chưa ghi giá trị cũ → mới** (lỗi M-05 còn
 * mở). Với sửa giá và điều chỉnh tồn, phải đối chiếu thêm `price-history`.
 */
export function useAuditLog(params: {
  tuNgay?: string;
  denNgay?: string;
  hanhVi?: string;
  trang: number;
}) {
  const { tuNgay, denNgay, hanhVi, trang } = params;
  return useQuery({
    queryKey: ["audit", "dashboard", tuNgay, denNgay, hanhVi, trang],
    queryFn: () => {
      const q = new URLSearchParams({
        limit: String(AUDIT_PAGE_SIZE),
        offset: String(trang * AUDIT_PAGE_SIZE),
      });
      // Ngày → thời điểm ISO: backend nhận `datetime`, và gửi "2026-08-01" trần thì nó hiểu
      // là 00:00 — đúng cho `từ`, nhưng với `đến` sẽ **cắt mất cả ngày cuối**.
      if (tuNgay) q.set("occurred_from", `${tuNgay}T00:00:00`);
      if (denNgay) q.set("occurred_to", `${denNgay}T23:59:59`);
      if (hanhVi) q.set("action", hanhVi);
      return apiFetch<AuditPage>(`/audit-dashboard?${q.toString()}`);
    },
    staleTime: 15_000,
  });
}
