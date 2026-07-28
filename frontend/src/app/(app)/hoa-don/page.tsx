"use client";

import { useState } from "react";

import { useDrugNames } from "@/features/catalog/use-drug-names";
import {
  SALES_PAGE_SIZE,
  todayIso,
  useSaleDetail,
  useSalesList,
} from "@/features/sales/use-sales-list";
import { ApiError } from "@/shared/api/errors";
import { formatMoney, formatQty, formatTime } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Nháp",
  COMPLETED: "Hoàn tất",
  PARTIALLY_RETURNED: "Trả một phần",
  RETURNED: "Đã trả",
  CANCELLED: "Đã huỷ",
};

const STATUS_CLASS: Record<string, string> = {
  DRAFT: styles.chipMuted,
  COMPLETED: styles.chipOk,
  PARTIALLY_RETURNED: styles.chipWarn,
  RETURNED: styles.chipWarn,
  CANCELLED: styles.chipDanger,
};

/**
 * Màn Hoá đơn (Sprint 10, D6) — mặc định là **ca hôm nay**, mới nhất trước.
 *
 * Đơn NHÁP cũng hiện, mang đúng trạng thái của nó: bàn giao ca cần thấy đơn ai
 * đó bấm dở rồi bỏ đi. Con số doanh thu trên Bảng điều hành thì không đếm chúng
 * — hai màn cố ý khác nhau, và cột "Trạng thái" là chỗ giải thích vì sao.
 */
export default function InvoicesPage() {
  const [dateFrom, setDateFrom] = useState(todayIso);
  const [dateTo, setDateTo] = useState(todayIso);
  const [page, setPage] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useSalesList(dateFrom, dateTo, page);
  const rows = data ?? [];
  const detail = useSaleDetail(openId);
  const names = useDrugNames((detail.data?.lines ?? []).map((l) => l.drug_id));

  const dayTotal = rows
    .filter((r) => r.status !== "CANCELLED")
    .reduce((sum, r) => sum + Number(r.subtotal), 0);

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Hoá đơn</h1>
          <p className={styles.subtitle}>
            {rows.length} đơn · tổng {formatMoney(String(dayTotal))} ₫ (không tính đơn đã huỷ)
          </p>
        </div>
        <div className={styles.controls}>
          <input
            type="date"
            className={styles.input}
            value={dateFrom}
            max={dateTo}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(0);
            }}
            aria-label="Từ ngày"
          />
          <input
            type="date"
            className={styles.input}
            value={dateTo}
            min={dateFrom}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(0);
            }}
            aria-label="Đến ngày"
          />
          <button
            type="button"
            className={styles.ghost}
            onClick={() => {
              setDateFrom(todayIso());
              setDateTo(todayIso());
              setPage(0);
            }}
          >
            Hôm nay
          </button>
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error instanceof ApiError ? error.problem.detail : "Không tải được hoá đơn."}</span>
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
          <p className={styles.empty}>Chưa có hoá đơn nào trong khoảng ngày này.</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Mã đơn</th>
                  <th>Trạng thái</th>
                  <th className={styles.num}>Số mặt hàng</th>
                  <th className={styles.num}>Thành tiền</th>
                  <th className={styles.num}>Đã thu</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className={styles.mono}>{formatTime(row.created_at)}</td>
                    <td className={styles.mono}>{row.id.slice(0, 8)}</td>
                    <td>
                      <span className={`${styles.chip} ${STATUS_CLASS[row.status] ?? ""}`}>
                        {STATUS_LABEL[row.status] ?? row.status}
                      </span>
                    </td>
                    <td className={styles.num}>{row.line_count}</td>
                    <td className={styles.num}>{formatMoney(row.subtotal)} ₫</td>
                    <td className={`${styles.num} ${styles.muted}`}>
                      {formatMoney(row.paid_total)} ₫
                    </td>
                    <td className={styles.num}>
                      <button
                        type="button"
                        className={styles.ghost}
                        onClick={() => setOpenId(openId === row.id ? null : row.id)}
                      >
                        {openId === row.id ? "Đóng" : "Xem"}
                      </button>
                    </td>
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
            disabled={isLoading || rows.length < SALES_PAGE_SIZE}
          >
            Sau
          </button>
        </div>
      </div>

      {openId && (
        <section className={styles.drawer} aria-label="Chi tiết hoá đơn">
          <div className={styles.drawerHead}>
            <h2 className={styles.drawerTitle}>Chi tiết đơn {openId.slice(0, 8)}</h2>
            <button type="button" className={styles.ghost} onClick={() => window.print()}>
              In
            </button>
          </div>
          {detail.isLoading && <div className={styles.skeleton} />}
          {detail.error && (
            <p className={styles.muted}>
              {detail.error instanceof ApiError
                ? detail.error.problem.detail
                : "Không tải được chi tiết đơn."}
            </p>
          )}
          {detail.data && (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Thuốc</th>
                    <th className={styles.num}>SL</th>
                    <th className={styles.num}>Đơn giá</th>
                    <th className={styles.num}>Thành tiền</th>
                    <th className={styles.num}>Đã trả lại</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.data.lines.map((line) => (
                    <tr key={line.id}>
                      <td>{names.nameOf(line.drug_id) ?? `Mã ${line.drug_id.slice(0, 8)}`}</td>
                      <td className={styles.num}>{formatQty(line.quantity)}</td>
                      <td className={styles.num}>{formatMoney(line.unit_price)} ₫</td>
                      <td className={styles.num}>{formatMoney(line.line_total)} ₫</td>
                      <td className={`${styles.num} ${styles.muted}`}>
                        {Number(line.returned_quantity) > 0 ? formatQty(line.returned_quantity) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
