import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type {
  LocationStockRow,
  PickCandidate,
  PutAwayResult,
  StorageLocation,
} from "@/shared/api/types";

/**
 * Sơ đồ kho của chi nhánh đang đăng nhập.
 *
 * Máy chủ trả **danh sách phẳng** đã sắp theo thứ tự đi lấy hàng; màn hình dựng cây từ
 * `parent_id`. Không có endpoint đệ quy nào và cũng không cần — một kho vài trăm ô nằm gọn
 * trong một lượt gọi, còn dựng cây trên máy khách thì rẻ hơn nhiều so với một truy vấn đệ
 * quy trên CSDL.
 */
export function useLocations(includeInactive = false) {
  return useQuery({
    queryKey: ["locations", includeInactive],
    queryFn: () =>
      apiFetch<StorageLocation[]>(
        `/locations${includeInactive ? "?include_inactive=true" : ""}`,
      ),
    staleTime: 60_000,
  });
}

export interface NewLocation {
  kind: string;
  code: string;
  name: string | null;
  parent_id: string | null;
  pick_order: number;
}

export function useCreateLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NewLocation) =>
      apiFetch<StorageLocation>("/locations", { method: "POST", body }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["locations"] }),
  });
}

export function useUpdateLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; is_active?: boolean; pick_order?: number }) =>
      apiFetch<StorageLocation>(`/locations/${id}`, { method: "PATCH", body }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["locations"] }),
  });
}

/** Tầng con hợp lệ dưới một tầng cho trước. Bỏ tầng thì được, đảo tầng thì không. */
export const TANG_DUOI: Record<string, { value: string; label: string }[]> = {
  WAREHOUSE: [
    { value: "ZONE", label: "Khu" },
    { value: "SHELF", label: "Kệ" },
    { value: "BIN", label: "Ô" },
  ],
  ZONE: [
    { value: "SHELF", label: "Kệ" },
    { value: "BIN", label: "Ô" },
  ],
  SHELF: [{ value: "BIN", label: "Ô" }],
  BIN: [],
};

export const NHAN_TANG: Record<string, string> = {
  WAREHOUSE: "Kho",
  ZONE: "Khu",
  SHELF: "Kệ",
  BIN: "Ô",
};

// ─── BERAS V2 Phase 2: tồn theo vị trí ─────────────────────────────────────────

/** Ô này đang giữ những lô nào. Chỉ tải khi người dùng mở một ô. */
export function useStockAtLocation(locationId: string | null) {
  return useQuery({
    queryKey: ["location-stock", locationId],
    queryFn: () => apiFetch<LocationStockRow[]>(`/inventory/locations/${locationId}/stock`),
    enabled: locationId !== null,
    staleTime: 15_000,
  });
}

/**
 * Thuốc này lấy ở đâu — **máy chủ đã sắp theo thứ tự lấy hàng**.
 *
 * 🔴 Màn hình **không được sắp lại**: FEFO là quy tắc nghiệp vụ, và mỗi chỗ tự sắp lấy là
 * mỗi chỗ có cơ hội sắp sai một kiểu khác nhau.
 *
 * Trả mảng rỗng nghĩa là **chưa xếp vào ô nào**, KHÔNG phải hết hàng — hai chuyện khác hẳn
 * nhau và màn hình phải nói ra sự khác biệt đó.
 */
export function useWhereIs(drugId: string | null) {
  return useQuery({
    queryKey: ["where-is", drugId],
    queryFn: () => apiFetch<PickCandidate[]>(`/inventory/where?drug_id=${drugId}`),
    enabled: drugId !== null,
    staleTime: 15_000,
  });
}

export function usePutAway() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { batch_id: string; location_id: string; quantity: string }) =>
      apiFetch<PutAwayResult>("/inventory/put-away", { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["location-stock"] });
      void qc.invalidateQueries({ queryKey: ["where-is"] });
    },
  });
}
