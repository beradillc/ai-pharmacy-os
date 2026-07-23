import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { CreateSaleRequest, Sale } from "@/shared/api/types";

import type { CartLine } from "./cart-store";

/**
 * POST /sales — one call creates *and* completes the order (there is no
 * separate `/complete` or `/payments` step; docs/11_API_DESIGN.md documents an
 * older shape that the code does not implement, see shared/api/types.ts).
 *
 * `client_uuid` is generated here, once, before the request — it is the
 * idempotency key `sales.application.service` dedupes on, so retrying this
 * exact mutation object (React Query's default retry, or a resubmit after a
 * timeout) can never double-charge. The offline queue (later step) reuses the
 * same generated id when it replays through `/sync/sales`.
 */
export function useCheckout() {
  return useMutation({
    mutationFn: ({ lines, amountPaid }: { lines: CartLine[]; amountPaid: string }) => {
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
      return apiFetch<Sale>("/sales", { method: "POST", body });
    },
  });
}
