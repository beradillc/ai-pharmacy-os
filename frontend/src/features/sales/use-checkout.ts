import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import type { CreateSaleRequest, Sale } from "@/shared/api/types";
import { randomUuid } from "@/shared/id/uuid";
import { enqueueSale } from "@/shared/offline/sync-queue";

import type { CartLine } from "./cart-store";

export interface CheckoutResult {
  /** `true` when the network was unreachable and the sale was written to the
   * offline queue instead of the server — the cashier still gets a receipt
   * point (`clientUuid`), but no server-assigned `sale.id` yet. */
  queued: boolean;
  sale?: Sale;
  clientUuid: string;
}

/**
 * POST /sales — one call creates *and* completes the order (there is no
 * separate `/complete` or `/payments` step; docs/11_API_DESIGN.md documents an
 * older shape that the code does not implement, see shared/api/types.ts).
 *
 * `client_uuid` is generated here, once, before the request — it is the
 * idempotency key `sales.application.service` dedupes on, so retrying this
 * exact mutation object (React Query's default retry, or a resubmit after a
 * timeout) can never double-charge. The offline queue reuses the same
 * generated id when it replays through `/sync/sales`. Sinh bằng `randomUuid()`
 * chứ KHÔNG phải `crypto.randomUUID()`: cái sau **không tồn tại** khi mở qua
 * địa chỉ LAN (ngữ cảnh không bảo mật) ⇒ điện thoại bấm Thanh toán là ném lỗi
 * trước khi kịp gửi request. Xem `shared/id/uuid.ts` để có bảng đo.
 *
 * A response the server actually sent back (`ApiError` — 4xx/5xx) is a real
 * rejection and is re-thrown as-is: a rejected sale must not silently become
 * a queued one. Anything else (`fetch` itself throwing — no network) is
 * treated as offline and queued instead of failing the sale outright.
 */
export function useCheckout() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async ({
      lines,
      amountPaid,
      customerId = null,
    }: {
      lines: CartLine[];
      amountPaid: string;
      /** `null` = khách vãng lai. Bán hàng KHÔNG cần khách hàng — xem `CustomerCapture`. */
      customerId?: string | null;
    }): Promise<CheckoutResult> => {
      const body: CreateSaleRequest = {
        client_uuid: randomUuid(),
        lines: lines.map((l) => ({
          drug_id: l.drugId,
          quantity: l.quantity,
          unit_price: l.unitPrice,
          requires_prescription: l.requiresPrescription,
        })),
        payments: [{ method: "CASH", amount: amountPaid }],
        customer_id: customerId,
      };
      try {
        const sale = await apiFetch<Sale>("/sales", { method: "POST", body });
        return { queued: false, sale, clientUuid: body.client_uuid };
      } catch (err) {
        if (err instanceof ApiError) throw err;
        await enqueueSale(body);
        return { queued: true, clientUuid: body.client_uuid };
      }
    },
    /**
     * 🔴 Bán xong phải LÀM MỚI mọi màn đọc lại số liệu vừa đổi.
     *
     * Trước bản vá, mutation này không đụng gì tới cache. Bán một đơn rồi mở
     * màn Hoá đơn trong vòng 15 giây (`staleTime` của `useSalesList`) thì React
     * Query trả về **danh sách cũ, không có đơn vừa bán** — không gọi mạng, nên
     * cũng không có gì để nghi. Đúng khoảng thời gian người bán thật sự mở màn
     * đó ra: ngay sau khi bán, để đối chiếu.
     *
     * Đơn xếp hàng chờ đồng bộ (`queued`) thì KHÔNG làm mới: chưa có gì trên
     * máy chủ để đọc, gọi lại chỉ tổ nhận về đúng danh sách cũ rồi ghi đè bản
     * cache vừa hết hạn — tức là kéo dài thêm sự nhầm lẫn.
     */
    onSuccess: (result) => {
      if (result.queued) return;
      void qc.invalidateQueries({ queryKey: ["sales"] });
      void qc.invalidateQueries({ queryKey: ["inventory"] });
      void qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}
