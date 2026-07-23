import Dexie, { type Table } from "dexie";

import type { CreateSaleRequest } from "@/shared/api/types";

/** One sale that could not reach the backend, waiting to replay through
 * `POST /sync/sales`. Keyed by `clientUuid` — the same idempotency key the
 * request itself carries, so a sale can never be queued twice. */
export interface PendingSale {
  clientUuid: string;
  request: CreateSaleRequest;
  queuedAt: string;
}

class OfflineDb extends Dexie {
  pendingSales!: Table<PendingSale, string>;

  constructor() {
    super("beras-offline");
    this.version(1).stores({ pendingSales: "clientUuid, queuedAt" });
  }
}

export const offlineDb = new OfflineDb();
