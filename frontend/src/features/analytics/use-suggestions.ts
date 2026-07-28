import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Materialize, ReorderRun, ReorderSuggestion, SuggestionStatus } from "@/shared/api/types";

const BASE = "/analytics/reorder/suggestions";

export function suggestionsKey(status: SuggestionStatus, branchId?: string) {
  return ["analytics", "suggestions", status, branchId ?? "self"] as const;
}

export function useSuggestions(status: SuggestionStatus, branchId?: string) {
  const params = new URLSearchParams({ status });
  if (branchId) params.set("branch_id", branchId);

  return useQuery({
    queryKey: suggestionsKey(status, branchId),
    queryFn: () => apiFetch<ReorderSuggestion[]>(`${BASE}?${params}`),
    retry: false,
  });
}

/** Mọi thao tác đổi trạng thái đều làm hỏng cả hai tab lẫn bảng điều hành
 * (ô "đơn mua nháp" đếm PO), nên dọn chung một chỗ thay vì mỗi hook tự nhớ. */
function useInvalidateAnalytics() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["analytics"] });
}

export function useRunReorder(branchId?: string) {
  const invalidate = useInvalidateAnalytics();
  return useMutation({
    mutationFn: () =>
      apiFetch<ReorderRun>(
        `/analytics/reorder/run${branchId ? `?branch_id=${branchId}` : ""}`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

/** Tạo đơn mua nháp. Trả về `po_code` — chuỗi phải hiện nguyên văn. */
export function useMaterialize() {
  const invalidate = useInvalidateAnalytics();
  return useMutation({
    mutationFn: (suggestionId: string) =>
      apiFetch<Materialize>(`${BASE}/${suggestionId}/materialize`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

/**
 * Hoàn tác. Máy chủ **không** đếm 10 giây — giới hạn là trạng thái đơn: còn
 * nháp thì được, đã gửi NCC thì `422` (docs/19 §10.1). Lỗi đó phải hiện ra,
 * không được nuốt.
 */
export function useUndoMaterialize() {
  const invalidate = useInvalidateAnalytics();
  return useMutation({
    mutationFn: (suggestionId: string) =>
      apiFetch<ReorderSuggestion>(`${BASE}/${suggestionId}/undo`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

export function useDismiss() {
  const invalidate = useInvalidateAnalytics();
  return useMutation({
    mutationFn: (suggestionId: string) =>
      apiFetch<ReorderSuggestion>(`${BASE}/${suggestionId}/dismiss`, { method: "POST" }),
    onSuccess: invalidate,
  });
}
