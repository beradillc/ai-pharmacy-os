import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { StockCount } from "@/shared/api/types";

/**
 * Kiểm kê theo ô (BERAS V2 Phase 11).
 *
 * 🔴 Mọi mutation ở đây trả về **cả phiên** chứ không chỉ dòng vừa đổi, và ghi thẳng kết
 * quả đó vào cache. Lý do: sau khi nộp, `system_qty` và `lech` của **mọi** dòng mới có giá
 * trị — làm mới từng dòng sẽ để màn hình ở một trạng thái nửa vời mà không trạng thái nào
 * là trạng thái thật của phiên.
 */
export function useStockCounts(status?: StockCount["status"]) {
  return useQuery({
    queryKey: ["stock-counts", status ?? "tat-ca"],
    queryFn: () =>
      apiFetch<StockCount[]>(`/inventory/counts${status ? `?status=${status}` : ""}`),
    staleTime: 10_000,
  });
}

/** Làm mới cả danh sách lẫn phiên đang mở — một chỗ để khỏi quên một nửa. */
function useLamMoi() {
  const qc = useQueryClient();
  return (phien: StockCount) => {
    qc.setQueryData(["stock-count", phien.id], phien);
    void qc.invalidateQueries({ queryKey: ["stock-counts"] });
  };
}

export function useStockCount(id: string | null) {
  return useQuery({
    queryKey: ["stock-count", id],
    queryFn: () => apiFetch<StockCount>(`/inventory/counts/${id}`),
    enabled: id !== null,
  });
}

export function useOpenCount() {
  const lamMoi = useLamMoi();
  return useMutation({
    mutationFn: (location_id: string) =>
      apiFetch<StockCount>("/inventory/counts", { method: "POST", body: { location_id } }),
    onSuccess: lamMoi,
  });
}

export function useCountLine() {
  const lamMoi = useLamMoi();
  return useMutation({
    mutationFn: ({
      countId,
      batch_id,
      counted_qty,
    }: {
      countId: string;
      batch_id: string;
      counted_qty: string;
    }) =>
      apiFetch<StockCount>(`/inventory/counts/${countId}/lines`, {
        method: "POST",
        body: { batch_id, counted_qty },
      }),
    onSuccess: lamMoi,
  });
}

/** `submit` · `approve` · `reject` — cùng hình dạng, khác đúng một từ trong URL. */
function useChuyenTrangThai(buoc: "submit" | "approve" | "reject") {
  const qc = useQueryClient();
  const lamMoi = useLamMoi();
  return useMutation({
    mutationFn: (countId: string) =>
      apiFetch<StockCount>(`/inventory/counts/${countId}/${buoc}`, { method: "POST" }),
    onSuccess: (phien) => {
      lamMoi(phien);
      // Duyệt là lúc tồn kho thật sự đổi ⇒ mọi màn đọc tồn kho đều lỗi thời.
      if (buoc === "approve") {
        void qc.invalidateQueries({ queryKey: ["stock"] });
        void qc.invalidateQueries({ queryKey: ["location-stock"] });
      }
    },
  });
}

export const useSubmitCount = () => useChuyenTrangThai("submit");
export const useApproveCount = () => useChuyenTrangThai("approve");
export const useRejectCount = () => useChuyenTrangThai("reject");

export const NHAN_TRANG_THAI: Record<StockCount["status"], string> = {
  DANG_DEM: "Đang đếm",
  CHO_DUYET: "Chờ duyệt",
  DA_DUYET: "Đã duyệt",
  TU_CHOI: "Từ chối",
};

/**
 * **Điều chỉnh tồn một lô trong một lượt** — UAT lỗi M-07 (2026-08-01).
 *
 * 🔴 Không phải một đường đổi tồn kho mới. Máy chủ chạy trọn luồng kiểm kê đã có (mở →
 * đếm → nộp → duyệt) và trả về phiếu đã duyệt, nên mọi lượt điều chỉnh vẫn để lại một
 * phiếu tra được — thứ thanh tra hỏi khi tồn sổ khác tồn thực.
 *
 * Vì thế nó cần **cả hai** quyền `inventory.receive` và `inventory.reconcile`: đường tắt
 * bỏ bớt lượt bấm, không bỏ bớt thẩm quyền.
 *
 * `reason` bắt buộc — máy chủ trả 422 nếu rỗng hoặc chỉ toàn dấu cách.
 */
export function useAdjustStock() {
  const lamMoi = useLamMoi();
  return useMutation({
    mutationFn: (v: {
      location_id: string;
      batch_id: string;
      actual_qty: string;
      reason: string;
    }) => apiFetch<StockCount>("/inventory/adjust", { method: "POST", body: v }),
    onSuccess: lamMoi,
  });
}
