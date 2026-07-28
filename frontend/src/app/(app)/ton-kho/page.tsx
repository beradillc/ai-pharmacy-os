"use client";

import { useMemo, useState } from "react";

import { useDrugNames } from "@/features/catalog/use-drug-names";
import {
  daysToExpiry,
  expiryTone,
  STOCK_PAGE_SIZE,
  useStock,
} from "@/features/inventory/use-stock";
import { ApiError } from "@/shared/api/errors";
import { formatQty } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

const TONE_CLASS: Record<string, string> = {
  expired: styles.chipDanger,
  urgent: styles.chipDanger,
  soon: styles.chipWarn,
  ok: styles.chipMuted,
};

function expiryLabel(days: number): string {
  if (days < 0) return `Hết hạn ${-days} ngày`;
  if (days === 0) return "Hết hạn hôm nay";
  if (days <= 90) return `Còn ${days} ngày`;
  return `Còn ${Math.round(days / 30)} tháng`;
}

/**
 * Màn Tồn kho — tồn theo LÔ, cận hạn lên trước (Sprint 10, D5).
 *
 * Theo lô chứ không gộp theo thuốc: hai lô cùng một thuốc có hạn dùng khác nhau
 * là hai thứ khác nhau đối với người bán hàng, và gộp lại đúng là cách một hệ
 * thống giấu mất lô sắp hết hạn giữa một con số tổng trông rất khoẻ.
 *
 * Ô tìm kiếm lọc **trong trang đang xem** — nói thẳng ở phụ đề. Tìm toàn kho cần
 * một endpoint tìm theo tên bên inventory (chưa có, và nó phải đi qua catalog vì
 * inventory không được biết tên thuốc).
 */
export default function StockPage() {
  const [page, setPage] = useState(0);
  const [term, setTerm] = useState("");
  const [onlyNearExpiry, setOnlyNearExpiry] = useState(false);

  const { data, isLoading, error, refetch } = useStock(page);
  const rows = useMemo(() => data ?? [], [data]);
  const names = useDrugNames(rows.map((r) => r.drug_id));

  const visible = rows.filter((row) => {
    const days = daysToExpiry(row.expiry_date);
    if (onlyNearExpiry && days > 90) return false;
    const needle = term.trim().toLowerCase();
    if (!needle) return true;
    const name = names.nameOf(row.drug_id) ?? "";
    return name.toLowerCase().includes(needle) || row.lot_no.toLowerCase().includes(needle);
  });

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Tồn kho</h1>
          <p className={styles.subtitle}>
            Theo lô, cận hạn lên trước · bộ lọc áp dụng cho trang đang xem
          </p>
        </div>
        <div className={styles.controls}>
          <input
            className={styles.input}
            placeholder="Lọc theo tên thuốc hoặc số lô…"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            aria-label="Lọc theo tên thuốc hoặc số lô"
          />
          <button
            type="button"
            className={onlyNearExpiry ? styles.button : styles.ghost}
            onClick={() => setOnlyNearExpiry((v) => !v)}
            aria-pressed={onlyNearExpiry}
          >
            Chỉ lô cận hạn
          </button>
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error instanceof ApiError ? error.problem.detail : "Không tải được tồn kho."}</span>
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
        ) : visible.length === 0 ? (
          <p className={styles.empty}>
            {rows.length === 0
              ? "Chưa có lô nào còn hàng."
              : "Không có lô nào khớp bộ lọc trong trang này."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Thuốc</th>
                  <th>Số lô</th>
                  <th>Hạn dùng</th>
                  <th className={styles.num}>Tồn</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => {
                  const days = daysToExpiry(row.expiry_date);
                  const tone = expiryTone(days);
                  const name = names.nameOf(row.drug_id);
                  return (
                    <tr key={row.batch_id}>
                      <td>
                        {name ?? (
                          <span className={styles.muted}>
                            {names.isLoading ? "Đang tải tên…" : `Mã ${row.drug_id.slice(0, 8)}`}
                          </span>
                        )}
                      </td>
                      <td className={styles.mono}>{row.lot_no}</td>
                      <td>
                        <span className={`${styles.chip} ${TONE_CLASS[tone]}`}>
                          {row.expiry_date} · {expiryLabel(days)}
                        </span>
                      </td>
                      <td className={styles.num}>{formatQty(row.quantity)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pager}>
          <span>
            Trang {page + 1} · {visible.length}/{rows.length} lô hiển thị
          </span>
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
            disabled={isLoading || rows.length < STOCK_PAGE_SIZE}
          >
            Sau
          </button>
        </div>
      </div>
    </div>
  );
}
