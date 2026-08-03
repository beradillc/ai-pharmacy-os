import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { PurchaseOrderDetail } from "@/shared/api/types";

/**
 * Tạo **đơn mua hàng thủ công** — `POST /purchase-orders` (V3-2, Chain duyệt 2026-08-04).
 *
 * 🔴 **Vì sao tới muộn:** backend có đủ `POST /purchase-orders` · `/place` · `/cancel` ·
 * `/close` từ lâu, nhưng **không dòng frontend nào gọi `POST`** — màn `/don-mua-hang` chỉ có
 * `GET` và luồng nhận hàng. Đường **duy nhất** đẻ ra một đơn là *Đề xuất đặt hàng → Tạo đơn
 * nháp*, mà đề xuất chỉ sinh ra từ phân tích tồn kho.
 *
 * Hệ quả ngoài đời: **trình dược viên chào hàng tận quầy** — ca phổ biến nhất ở nhà thuốc
 * Việt Nam — **không có đề xuất nào**, nên không dựng được đơn. Cùng hình dạng V3-1
 * (`POST /drugs` có mà không ai gọi) và đúng thứ kỷ luật **#26** vừa đặt tên.
 */
export interface DongDonMua {
  drug_id: string;
  quantity_ordered: string;
  unit_price: string;
}

export interface DonMuaMoi {
  supplier_id: string;
  items: DongDonMua[];
}

export function useCreatePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DonMuaMoi) =>
      apiFetch<PurchaseOrderDetail>("/purchase-orders", { method: "POST", body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["procurement", "purchase-orders"] });
    },
  });
}

/**
 * `DRAFT` → `ORDERED` — **cam kết tài chính thật với nhà cung cấp**.
 *
 * Tách khỏi lúc tạo có chủ đích: tạo đơn là soạn thảo, **đặt** đơn là lúc nó thành một khoản
 * phải trả. Backend ghi audit `PROCUREMENT_PO_ORDERED` đúng ở mốc này, không phải lúc tạo.
 */
export function usePlacePurchaseOrder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (poId: string) =>
      apiFetch<PurchaseOrderDetail>(`/purchase-orders/${poId}/place`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["procurement", "purchase-orders"] });
    },
  });
}
