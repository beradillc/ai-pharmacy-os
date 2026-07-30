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

/**
 * Đơn đã tới được máy chủ nhưng bị **TỪ CHỐI** vì một lý do nghiệp vụ — hết hàng, thuốc
 * kê đơn thiếu đơn, có cảnh báo dị ứng mà chưa ghi lý do…
 *
 * 🔴 Bảng này sinh ra để vá một lỗi MẤT DỮ LIỆU thật (phát hiện 31/07). Trước đó
 * `flushQueue` **xoá** đơn bị từ chối khỏi IndexedDB rồi đẩy vào một biến state React mà
 * **không màn nào đọc** — state chết khi rời trang, và đơn biến mất không để lại dấu vết
 * nào. Thu ngân đã thu tiền của khách, đơn không tồn tại ở đâu cả, và không ai biết.
 *
 * Vẫn phải **rời khỏi hàng chờ**: giữ nó ở đó thì mọi đơn xếp sau bị chặn vĩnh viễn vì
 * một lý do sẽ không bao giờ tự hết. Nên: chuyển chỗ, không xoá.
 */
export interface RejectedSale {
  clientUuid: string;
  request: CreateSaleRequest;
  queuedAt: string;
  /** Lúc máy chủ từ chối — khác `queuedAt` (lúc bán) có khi hàng giờ. */
  rejectedAt: string;
  /** Nguyên văn lý do máy chủ trả về. KHÔNG rút gọn: thu ngân cần đọc đúng câu đó để
   *  biết phải sửa gì, và để chụp màn hình gửi kỹ thuật nếu không hiểu. */
  reason: string;
  status: number;
}

class OfflineDb extends Dexie {
  pendingSales!: Table<PendingSale, string>;
  rejectedSales!: Table<RejectedSale, string>;

  constructor() {
    super("beras-offline");
    this.version(1).stores({ pendingSales: "clientUuid, queuedAt" });
    // v2 (31/07): THÊM bảng, không đụng bảng cũ ⇒ Dexie nâng cấp tại chỗ, đơn đang chờ
    // của người dùng giữ nguyên. Không có bước lùi nào cần thiết vì không mất gì.
    this.version(2).stores({
      pendingSales: "clientUuid, queuedAt",
      rejectedSales: "clientUuid, rejectedAt",
    });
  }
}

export const offlineDb = new OfflineDb();
