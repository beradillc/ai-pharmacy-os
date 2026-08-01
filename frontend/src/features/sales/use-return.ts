import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Sale } from "@/shared/api/types";

/**
 * Ghi nhận **khách trả hàng** trên một dòng của đơn đã bán (lỗi C-02, UAT 2026-08-01).
 *
 * 🔴 Vì sao đây là Critical: khách trả thuốc là chuyện **gần như chắc chắn xảy ra** trong một
 * tuần bán lẻ. Không có màn ⇒ người bán hoặc bỏ qua (tồn kho và doanh thu sai), hoặc ghi tay
 * ra sổ (hai nguồn số liệu, và không ai đối chiếu). Backend đã có `POST /sales/{id}/returns`
 * cùng test từ trước — thuần là nối dây.
 *
 * Trả theo **DÒNG**, không theo cả đơn: khách mua năm món trả một món là ca thường nhất, và
 * một nút "huỷ cả đơn" sẽ bị dùng nhầm cho ca đó.
 *
 * Sau khi trả, làm mới cả `sales` lẫn `inventory`: hàng quay lại kho **thật**, nên màn Tồn
 * kho đang mở phải thấy ngay chứ không đợi hết `staleTime`.
 */
export function useRegisterReturn(saleId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { line_id: string; quantity: string }) =>
      apiFetch<Sale>(`/sales/${saleId}/returns`, { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sales"] });
      void qc.invalidateQueries({ queryKey: ["inventory"] });
      void qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}
