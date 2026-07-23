import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import type { CreateSaleRequest, Sale } from "@/shared/api/types";

import { offlineDb, type PendingSale } from "./db";

export async function enqueueSale(request: CreateSaleRequest): Promise<void> {
  await offlineDb.pendingSales.put({
    clientUuid: request.client_uuid,
    request,
    queuedAt: new Date().toISOString(),
  });
}

export async function pendingSalesCount(): Promise<number> {
  return offlineDb.pendingSales.count();
}

/**
 * Replay every queued sale through `POST /sync/sales`, oldest first — that
 * endpoint is idempotent on `client_uuid` (see
 * `modules/sales/interface/router.py::sync_sale`), so a sale already synced
 * by an earlier attempt is a harmless no-op, not a double sale.
 *
 * A sale still unreachable (offline) stops the run here — the rest stay
 * queued for the next attempt, in the same order. A sale the *server*
 * rejects (a real business reason, e.g. stock) is dequeued immediately:
 * retrying it forever would only block every sale queued after it.
 */
export async function flushQueue(
  onRejected?: (sale: PendingSale, error: ApiError) => void,
): Promise<{ synced: number; remaining: number }> {
  const pending = await offlineDb.pendingSales.orderBy("queuedAt").toArray();
  let synced = 0;

  for (const sale of pending) {
    try {
      await apiFetch<Sale>("/sync/sales", { method: "POST", body: sale.request });
      await offlineDb.pendingSales.delete(sale.clientUuid);
      synced += 1;
    } catch (err) {
      if (err instanceof ApiError) {
        await offlineDb.pendingSales.delete(sale.clientUuid);
        onRejected?.(sale, err);
        continue;
      }
      break; // still offline — keep this and everything after it queued
    }
  }

  return { synced, remaining: await pendingSalesCount() };
}
