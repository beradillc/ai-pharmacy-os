import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Drug } from "@/shared/api/types";

/**
 * Gắn tên cho một trang dữ liệu chỉ có `drug_id` — MỘT lượt gọi cho cả trang.
 *
 * Vì sao không để backend trả sẵn tên: `inventory` bị contract import-linter cấm
 * import `catalog`, nên tồn kho chỉ biết id. Cách rẻ nhất mà không phá kiến trúc
 * là hỏi catalog đúng những id đang hiển thị (`GET /drugs?ids=…`).
 *
 * Khoá cache theo TẬP id đã sắp xếp: đổi trang mà vẫn cùng bộ thuốc thì không
 * gọi lại. `enabled` tắt khi chưa có id nào — hỏi một danh sách rỗng chỉ tổ
 * thêm một vòng mạng để nhận về `[]`.
 */
export function useDrugNames(drugIds: string[]) {
  const unique = Array.from(new Set(drugIds)).sort();
  const params = new URLSearchParams();
  for (const id of unique) params.append("ids", id);
  params.set("limit", "200");

  const query = useQuery({
    queryKey: ["catalog", "names", unique],
    queryFn: () => apiFetch<Drug[]>(`/drugs?${params}`),
    enabled: unique.length > 0,
    retry: false,
    staleTime: 5 * 60_000,
  });

  const byId = new Map<string, Drug>();
  for (const drug of query.data ?? []) byId.set(drug.id, drug);

  return {
    ...query,
    /** Tên thuốc, hoặc `null` khi catalog không trả về id đó (thuốc đã xoá) —
     * KHÁC với "chưa tải xong", mà người gọi phân biệt bằng `isLoading`. */
    nameOf: (drugId: string): string | null => byId.get(drugId)?.name ?? null,
    drugOf: (drugId: string): Drug | undefined => byId.get(drugId),
  };
}
