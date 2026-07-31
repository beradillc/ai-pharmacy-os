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
