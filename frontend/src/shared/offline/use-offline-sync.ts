import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/shared/api/errors";

import type { PendingSale } from "./db";
import { flushQueue, pendingSalesCount } from "./sync-queue";

/**
 * Keeps the offline sale queue draining: flushes once on mount (covers a hard
 * refresh while still offline, or a queue left over from the last session)
 * and again on every `online` event (covers the network coming back while
 * the tab stays open). Returns the current pending count so a screen can
 * show the cashier "N đơn chờ đồng bộ" instead of it happening invisibly.
 */
export function useOfflineSync() {
  const [pendingCount, setPendingCount] = useState(0);
  const [rejected, setRejected] = useState<{ sale: PendingSale; error: ApiError }[]>([]);

  const refreshCount = useCallback(() => {
    void pendingSalesCount().then(setPendingCount);
  }, []);

  const flush = useCallback(async () => {
    await flushQueue((sale, error) => {
      setRejected((prev) => [...prev, { sale, error }]);
    });
    refreshCount();
  }, [refreshCount]);

  useEffect(() => {
    refreshCount();
    void flush();

    window.addEventListener("online", flush);
    return () => window.removeEventListener("online", flush);
  }, [flush, refreshCount]);

  return { pendingCount, rejected, refreshCount };
}
