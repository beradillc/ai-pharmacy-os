import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Drug, PriceHistoryEntry } from "@/shared/api/types";

/** Danh mục thuốc kèm hoạt chất. `GET /drugs` chưa có tìm phía máy chủ — lọc tại chỗ. */
export function useCatalogDrugs() {
  return useQuery({
    queryKey: ["catalog", "drugs"],
    queryFn: () => apiFetch<Drug[]>("/drugs?limit=200"),
    staleTime: 60_000,
  });
}

export interface IngredientRow {
  ingredient_id: string;
  amount: string;
  unit: string;
}

/**
 * Đặt lại TOÀN BỘ hoạt chất của một thuốc — `PUT /drugs/{id}/ingredients`.
 *
 * 🔴 Thay cả danh sách, không thêm/xoá từng cái: "sửa" = xoá cái sai + thêm cái đúng, và
 * làm hai lượt thì tồn tại một khoảng thuốc mang danh sách **sai theo cách khác** — trong
 * khoảng đó cảnh báo dị ứng vẫn đang chạy.
 */
export function useReplaceIngredients(drugId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ingredients: IngredientRow[]) =>
      apiFetch<Drug>(`/drugs/${drugId}/ingredients`, {
        method: "PUT",
        body: { ingredients },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["catalog", "drugs"] });
      // Cảnh báo dị ứng ở quầy đọc hoạt chất — sửa xong phải thấy ngay, không đợi hết hạn cache.
      void qc.invalidateQueries({ queryKey: ["allergy-check"] });
    },
  });
}

/** Lịch sử giá của một thuốc, mới nhất trước. Chỉ tải khi thật sự mở bảng giá. */
export function usePriceHistory(drugId: string | null) {
  return useQuery({
    queryKey: ["catalog", "price-history", drugId],
    queryFn: () => apiFetch<PriceHistoryEntry[]>(`/drugs/${drugId}/price-history`),
    enabled: drugId !== null,
    staleTime: 30_000,
  });
}

/**
 * Đặt lại giá bán niêm yết — `PUT /drugs/{id}/price`.
 *
 * 🔴 Quyền `catalog.update` là **cấp chuỗi**: đổi giá ở một chi nhánh là đổi giá của
 * toàn chuỗi. Máy chủ trả 422 nếu đổi giá một mã ĐÃ có giá mà không kèm lý do.
 */
export function useSetPrice(drugId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { new_price: string; reason: string | null }) =>
      apiFetch<Drug>(`/drugs/${drugId}/price`, { method: "PUT", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["catalog", "drugs"] });
      void qc.invalidateQueries({ queryKey: ["catalog", "price-history", drugId] });
      // Quầy điền sẵn đơn giá từ `sale_price` — đổi giá xong phải thấy ngay, nếu không
      // dòng tiếp theo ở quầy sẽ bán giá cũ và bị máy chủ bắt ghi lý do lệch giá.
      void qc.invalidateQueries({ queryKey: ["drugs"] });
    },
  });
}
