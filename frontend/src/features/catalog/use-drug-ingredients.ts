import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Drug } from "@/shared/api/types";

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
