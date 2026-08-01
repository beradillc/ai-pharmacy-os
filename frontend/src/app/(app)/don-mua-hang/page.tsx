"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import {
  PO_PAGE_SIZE,
  PO_STATUS_LABEL,
  PO_STATUSES,
  type PoStatus,
  usePurchaseOrders,
} from "@/features/procurement/use-purchase-orders";
import { ApiError } from "@/shared/api/errors";
import { formatMoney, formatTime } from "@/shared/format/number";
import type { PurchaseOrderListItem } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import { ReceiveDrawer } from "./ReceiveDrawer";
import { TabManGop } from "@/components/layout/TabManGop";

import local from "./page.module.css";

const STATUS_CLASS: Record<string, string> = {
  DRAFT: styles.chipMuted,
  ORDERED: styles.chipOk,
  PARTIALLY_RECEIVED: styles.chipWarn,
  RECEIVED: styles.chipOk,
  CLOSED: styles.chipMuted,
  CANCELLED: styles.chipDanger,
};

/** Chỉ đơn ĐÃ GỬI NCC mới nhận hàng được — `apply_receipt` ở domain từ chối mọi
 * trạng thái khác. Đơn nháp phải "Gửi NCC" trước; đơn đã nhận đủ/đóng/huỷ thì
 * hết việc. Hiện nút cho những đơn đó là mời người dùng bấm để lấy về một lỗi. */
const RECEIVABLE = new Set(["ORDERED", "PARTIALLY_RECEIVED"]);

/** Vì sao dòng này không có nút — hiện qua `title`, đỡ hơn một gạch ngang câm. */
const WHY_NOT: Record<string, string> = {
  DRAFT: "Đơn còn nháp — phải gửi cho NCC trước khi nhận hàng",
  RECEIVED: "Đơn đã nhận đủ hàng",
  CLOSED: "Đơn đã đóng sau khi đối chiếu",
  CANCELLED: "Đơn đã huỷ",
};

/**
 * Màn Đơn mua hàng (Sprint 10, D8).
 *
 * Cột đầu là **mã đơn** ("PO-0001"), không phải UUID: đó là chuỗi dược sĩ đọc
 * cho nhà cung cấp qua điện thoại (khe hở G-2, docs/19). Tổng tiền là tiền
 * **đặt**, nên đơn nháp do máy đề xuất có tổng 0 đ cho tới khi người ta điền
 * giá — màn hình nói rõ chỗ đó thay vì để người đọc tưởng hệ thống cộng sai.
 *
 * 29/07: thêm cột **Nhận hàng**, đóng nốt vòng *đơn mua → nhận hàng → tồn kho
 * tăng*. Trước đó ba endpoint `goods-receipts` chạy được nhưng không đường nào
 * gọi tới, nên câu hỏi "đặt xong thì hàng về kho bằng cách nào" không có câu
 * trả lời trên giao diện.
 */
const TAB_MUA = [
  {
    href: "/don-mua-hang",
    nhan: "Đơn mua hàng",
    moTa: "Đặt hàng từ nhà cung cấp, theo dõi tới lúc nhận đủ.",
  },
  {
    href: "/nha-cung-cap",
    nhan: "Nhà cung cấp",
    moTa: "Nơi quầy nhập hàng về. Phải có ít nhất một thì mới tạo được đơn mua.",
  },
] as const;

export default function PurchaseOrdersPage() {
  const [status, setStatus] = useState<PoStatus | null>(null);
  const [page, setPage] = useState(0);
  const [receiving, setReceiving] = useState<PurchaseOrderListItem | null>(null);

  // Quyền do backend cấp; đây chỉ là ẩn nút cho đỡ vướng mắt. Người không có
  // quyền mà gọi thẳng API vẫn bị 403 — giao diện KHÔNG phải chỗ quyết
  // authorization, chỉ phản ánh nó.
  const canReceive = new Set(useAuthStore((s) => s.session)?.permissions ?? []).has(
    "procurement.grn.create",
  );

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
      <TabManGop tabs={TAB_MUA} />

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
                  {canReceive && <th />}
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
                    {canReceive && (
                      <td className={styles.num}>
                        {RECEIVABLE.has(po.status) ? (
                          <button
                            type="button"
                            className={styles.ghost}
                            onClick={() => setReceiving(po)}
                          >
                            Nhận hàng
                          </button>
                        ) : (
                          <span className={local.hint} title={WHY_NOT[po.status]}>
                            —
                          </span>
                        )}
                      </td>
                    )}
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

      {receiving && <ReceiveDrawer po={receiving} onClose={() => setReceiving(null)} />}
    </div>
  );
}
