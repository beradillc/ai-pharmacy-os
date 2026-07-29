import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { GoodsReceipt, PurchaseOrderDetail } from "@/shared/api/types";

/** `GET /purchase-orders/{id}` — bản đầy đủ, CÓ từng dòng hàng. */
export function usePurchaseOrder(poId: string | null) {
  return useQuery({
    queryKey: ["procurement", "purchase-order", poId],
    queryFn: () => apiFetch<PurchaseOrderDetail>(`/purchase-orders/${poId}`),
    enabled: poId !== null,
    retry: false,
    // Không cache: mở lại đơn ngay sau khi nhận hàng phải thấy số đã nhận MỚI,
    // không phải số cũ 30 giây trước.
    staleTime: 0,
  });
}

export interface ReceiveLineInput {
  po_item_id: string;
  drug_id: string;
  quantity_received: string;
  lot_no: string;
  expiry_date: string;
  unit_cost: string;
  mfg_date?: string | null;
}

/**
 * 🔴 Lỗi hai-nửa-việc — lý do hàm này tồn tại thay vì hai `useMutation` rời.
 *
 * Nhận hàng ở backend là **hai lệnh gọi**: `POST /goods-receipts` tạo phiếu
 * **DRAFT** (chưa động gì tới tồn kho), rồi `POST /{id}/confirm` mới chốt và
 * làm tồn kho tăng.
 *
 * Nếu lệnh 1 thành công mà lệnh 2 hỏng (mạng rớt giữa chừng, token vừa hết hạn),
 * người dùng thấy một thông báo lỗi và **bấm lại** — tạo thêm một phiếu DRAFT
 * thứ hai. Chưa ai được nhận hàng hai lần, nhưng kho đã có hai phiếu nháp cho
 * cùng một lần giao hàng, và người đối chiếu sau đó không biết cái nào là thật.
 *
 * Nên khi lệnh 2 hỏng, hàm này **không** ném lỗi trần: nó ném kèm mã phiếu đã
 * tạo và nói rõ *"phiếu đã tạo, chưa chốt"* để màn hình bảo người dùng **chốt
 * lại phiếu đó**, đừng nhập lại từ đầu.
 *
 * Vì sao không gộp thành một endpoint ở backend: hai bước là **có chủ đích** —
 * nhà thuốc thật nhập phiếu lúc dỡ hàng rồi mới đối chiếu hoá đơn NCC trước khi
 * chốt. Gộp lại là bỏ mất bước đối chiếu, tức là sửa nghiệp vụ, mà nghiệp vụ
 * không phải quyết định của giao diện.
 */
export class ReceiptNotConfirmedError extends Error {
  constructor(
    readonly grnId: string,
    readonly cause: unknown,
  ) {
    super("Phiếu nhập đã tạo nhưng CHƯA chốt.");
    this.name = "ReceiptNotConfirmedError";
  }
}

export function useReceiveGoods() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (input: {
      po_id: string;
      items: ReceiveLineInput[];
    }): Promise<GoodsReceipt> => {
      const draft = await apiFetch<GoodsReceipt>("/goods-receipts", {
        method: "POST",
        body: input,
      });
      try {
        return await apiFetch<GoodsReceipt>(`/goods-receipts/${draft.id}/confirm`, {
          method: "POST",
        });
      } catch (err) {
        throw new ReceiptNotConfirmedError(draft.id, err);
      }
    },
    onSuccess: () => {
      // Nhận hàng đụng cả hai màn: đơn mua đổi trạng thái, tồn kho tăng.
      void qc.invalidateQueries({ queryKey: ["procurement"] });
      void qc.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}

/** Chốt lại một phiếu DRAFT đã tạo — đường thoát cho {@link ReceiptNotConfirmedError}. */
export function useConfirmReceipt() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (grnId: string) =>
      apiFetch<GoodsReceipt>(`/goods-receipts/${grnId}/confirm`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["procurement"] });
      void qc.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}

/** Số còn phải nhận của một dòng. Trả chuỗi để không mất chữ số qua `number`. */
export function remainingOf(item: { quantity_ordered: string; quantity_received: string }): number {
  return Number(item.quantity_ordered) - Number(item.quantity_received);
}
