import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import type { CreateSaleRequest, Sale } from "@/shared/api/types";

import { offlineDb, type PendingSale, type RejectedSale } from "./db";

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
 * queued for the next attempt, in the same order.
 *
 * Đơn bị **máy chủ từ chối** (lý do nghiệp vụ: hết hàng, thiếu đơn thuốc, có cảnh báo dị
 * ứng chưa ghi lý do…) thì **chuyển sang `rejectedSales`**, không xoá. Nó phải rời hàng
 * chờ — giữ lại thì mọi đơn xếp sau bị chặn vĩnh viễn vì một lý do sẽ không tự hết —
 * nhưng xoá hẳn là **mất dữ liệu**: thu ngân đã thu tiền của khách rồi.
 *
 * 🔴 Trước 31/07 chỗ này gọi `delete()` và chỉ báo qua một callback mà **không màn nào
 * đọc**. Đơn biến mất không dấu vết. Đó là lý do có bảng `rejectedSales`.
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
        // Ghi vào bảng từ-chối TRƯỚC khi rời hàng chờ. Đảo thứ tự thì một lần tắt máy
        // đúng giữa hai lệnh sẽ làm mất đơn — đúng cái lỗi đang vá.
        await offlineDb.rejectedSales.put({
          clientUuid: sale.clientUuid,
          request: sale.request,
          queuedAt: sale.queuedAt,
          rejectedAt: new Date().toISOString(),
          reason: err.problem.detail ?? err.problem.title ?? "Máy chủ từ chối",
          status: err.problem.status ?? 0,
        });
        await offlineDb.pendingSales.delete(sale.clientUuid);
        onRejected?.(sale, err);
        continue;
      }
      break; // still offline — keep this and everything after it queued
    }
  }

  return { synced, remaining: await pendingSalesCount() };
}

export async function rejectedSales(): Promise<RejectedSale[]> {
  return offlineDb.rejectedSales.orderBy("rejectedAt").reverse().toArray();
}

export async function rejectedSalesCount(): Promise<number> {
  return offlineDb.rejectedSales.count();
}

/**
 * Đưa một đơn bị từ chối **quay lại hàng chờ** để thử lần nữa.
 *
 * Ca dùng thật: đơn bị từ chối vì hết hàng, thủ kho nhập thêm, nay bán được. Giữ nguyên
 * `client_uuid` nên `POST /sync/sales` vẫn idempotent — thử lại không bao giờ thành hai đơn.
 */
export async function retryRejected(clientUuid: string): Promise<void> {
  const sale = await offlineDb.rejectedSales.get(clientUuid);
  if (!sale) return;
  await offlineDb.pendingSales.put({
    clientUuid: sale.clientUuid,
    request: sale.request,
    queuedAt: sale.queuedAt,
  });
  await offlineDb.rejectedSales.delete(clientUuid);
}

/**
 * Bỏ hẳn một đơn bị từ chối — thu ngân đã xử lý ngoài đời (hoàn tiền, bán lại đơn mới).
 *
 * Đây là đường DUY NHẤT làm một đơn biến mất, và nó đòi người bấm. Trước 31/07 việc này
 * xảy ra **tự động, im lặng**.
 */
export async function discardRejected(clientUuid: string): Promise<void> {
  await offlineDb.rejectedSales.delete(clientUuid);
}
