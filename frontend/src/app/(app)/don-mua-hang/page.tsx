"use client";

import { useState } from "react";

import {
  PO_PAGE_SIZE,
  PO_STATUS_LABEL,
  PO_STATUSES,
  type PoStatus,
  usePurchaseOrders,
} from "@/features/procurement/use-purchase-orders";
import { ApiError } from "@/shared/api/errors";
import { formatMoney, formatTime } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

const STATUS_CLASS: Record<string, string> = {
  DRAFT: styles.chipMuted,
  ORDERED: styles.chipOk,
  PARTIALLY_RECEIVED: styles.chipWarn,
  CLOSED: styles.chipMuted,
  CANCELLED: styles.chipDanger,
};

/**
 * Màn Đơn mua hàng (Sprint 10, D8).
 *
 * Cột đầu là **mã đơn** ("PO-0001"), không phải UUID: đó là chuỗi dược sĩ đọc
 * cho nhà cung cấp qua điện thoại (khe hở G-2, docs/19). Tổng tiền là tiền
 * **đặt**, nên đơn nháp do máy đề xuất có tổng 0 đ cho tới khi người ta điền
 * giá — màn hình nói rõ chỗ đó thay vì để người đọc tưởng hệ thống cộng sai.
 */
export default function PurchaseOrdersPage() {
  const [status, setStatus] = useState<PoStatus | null>(null);
  const [page, setPage] = useState(0);

  const { data, isLoading, error, refetch } = usePurchaseOrders(status, page);
  const rows = data ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Đơn mua hàng</h1>
          <p className={styles.subtitle}>Mới nhất trước · tổng tiền là tiền ĐẶT, chưa phải tiền nhận</p>
        </div>
        <div className={styles.controls}>
          <select
            className={styles.select}
            value={status ?? ""}
            onChange={(e) => {
              setStatus((e.target.value || null) as PoStatus | null);
              setPage(0);
            }}
            aria-label="Lọc theo trạng thái"
          >
            <option value="">Mọi trạng thái</option>
            {PO_STATUSES.map((s) => (
              <option key={s} value={s}>
                {PO_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          <span>
            {error instanceof ApiError ? error.problem.detail : "Không tải được đơn mua hàng."}
          </span>
          <button type="button" className={styles.ghost} onClick={() => refetch()}>
            Thử lại
          </button>
        </div>
      )}

      <div className={styles.panel}>
        {isLoading ? (
          <>
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
          </>
        ) : rows.length === 0 ? (
          <p className={styles.empty}>
            {status
              ? `Không có đơn nào ở trạng thái "${PO_STATUS_LABEL[status]}".`
              : "Chưa có đơn mua hàng nào."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Mã đơn</th>
                  <th>Nhà cung cấp</th>
                  <th>Trạng thái</th>
                  <th className={styles.num}>Mặt hàng</th>
                  <th className={styles.num}>Tổng đặt</th>
                  <th>Tạo lúc</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((po) => (
                  <tr key={po.id}>
                    <td className={styles.mono}>{po.code}</td>
                    <td>
                      {po.supplier_name ?? (
                        <span className={styles.muted}>Mã {po.supplier_id.slice(0, 8)}</span>
                      )}
                    </td>
                    <td>
                      <span className={`${styles.chip} ${STATUS_CLASS[po.status] ?? ""}`}>
                        {PO_STATUS_LABEL[po.status] ?? po.status}
                      </span>
                    </td>
                    <td className={styles.num}>{po.item_count}</td>
                    <td className={styles.num}>
                      {Number(po.total_amount) === 0 ? (
                        <span className={styles.muted} title="Đơn nháp chưa chốt giá với NCC">
                          chưa chốt giá
                        </span>
                      ) : (
                        `${formatMoney(po.total_amount)} đ`
                      )}
                    </td>
                    <td className={styles.mono}>{formatTime(po.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pager}>
          <span>Trang {page + 1}</span>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isLoading}
          >
            Trước
          </button>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => p + 1)}
            disabled={isLoading || rows.length < PO_PAGE_SIZE}
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
