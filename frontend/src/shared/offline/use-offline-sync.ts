import { useCallback, useEffect, useState } from "react";

import type { RejectedSale } from "./db";
import {
  discardRejected,
  flushQueue,
  pendingSalesCount,
  rejectedSales,
  retryRejected,
} from "./sync-queue";

/**
 * Keeps the offline sale queue draining: flushes once on mount (covers a hard
 * refresh while still offline, or a queue left over from the last session)
 * and again on every `online` event (covers the network coming back while
 * the tab stays open). Returns the current pending count so a screen can
 * show the cashier "N đơn chờ đồng bộ" instead of it happening invisibly.
 */
export function useOfflineSync() {
  const [pendingCount, setPendingCount] = useState(0);
  const [rejected, setRejected] = useState<RejectedSale[]>([]);

  // 🔴 Đọc từ IndexedDB, KHÔNG tích luỹ vào state. Trước 31/07 danh sách bị-từ-chối chỉ
  // sống trong state của lượt chạy này ⇒ F5 hoặc rời trang là mất, và không màn nào đọc
  // nó cả. Nay nó nằm trong bảng `rejectedSales`, nên mọi tab, mọi lượt tải đều thấy
  // cùng một sự thật.
  const refreshCount = useCallback(() => {
    void pendingSalesCount().then(setPendingCount);
    void rejectedSales().then(setRejected);
  }, []);

  const flush = useCallback(async () => {
    await flushQueue();
    refreshCount();
  }, [refreshCount]);

  useEffect(() => {
    refreshCount();
    void flush();

    window.addEventListener("online", flush);
    return () => window.removeEventListener("online", flush);
  }, [flush, refreshCount]);

  const thuLai = useCallback(
    async (clientUuid: string) => {
      await retryRejected(clientUuid);
      await flush();
    },
    [flush],
  );

  const boHan = useCallback(
    async (clientUuid: string) => {
      await discardRejected(clientUuid);
      refreshCount();
    },
    [refreshCount],
  );

  return { pendingCount, rejected, refreshCount, thuLai, boHan };
}
