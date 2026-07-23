import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import type { CreateSaleRequest, Sale } from "@/shared/api/types";
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
 * generated id when it replays through `/sync/sales`.
 *
 * A response the server actually sent back (`ApiError` — 4xx/5xx) is a real
 * rejection and is re-thrown as-is: a rejected sale must not silently become
 * a queued one. Anything else (`fetch` itself throwing — no network) is
 * treated as offline and queued instead of failing the sale outright.
 */
export function useCheckout() {
  return useMutation({
    mutationFn: async ({
      lines,
      amountPaid,
    }: {
      lines: CartLine[];
      amountPaid: string;
    }): Promise<CheckoutResult> => {
      const body: CreateSaleRequest = {
        client_uuid: crypto.randomUUID(),
        lines: lines.map((l) => ({
          drug_id: l.drugId,
          quantity: l.quantity,
          unit_price: l.unitPrice,
          requires_prescription: l.requiresPrescription,
        })),
        payments: [{ method: "CASH", amount: amountPaid }],
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
  });
}
