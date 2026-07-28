"use client";

import { useState } from "react";

import { useDashboard, DASHBOARD_WINDOW_DAYS } from "@/features/analytics/use-dashboard";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { TopDrug } from "@/shared/api/types";
import { formatMoney, formatQty } from "@/shared/format/number";

import styles from "./page.module.css";

/** Nhãn hiện thay cho tên khi catalog không tra được (docs/19 §10.2). */
function drugLabel(d: { drug_id: string; drug_name: string | null }): string {
  return d.drug_name ?? `Mã ${d.drug_id.slice(0, 8)}`;
}

function toCsv(rows: TopDrug[]): string {
  const head = "ten_thuoc,ma_thuoc,so_luong_ban,doanh_thu";
  const body = rows.map((r) =>
    [`"${(r.drug_name ?? "").replace(/"/g, '""')}"`, r.drug_id, r.quantity_sold, r.revenue].join(","),
  );
  return [head, ...body].join("\n");
}

export default function DashboardPage() {
  const session = useAuthStore((s) => s.session);
  const branches = session?.accessible_branches ?? [];
  const [branchId, setBranchId] = useState<string | undefined>(undefined);
  const { data, isLoading, error, refetch } = useDashboard(branchId);

  function exportCsv() {
    if (!data) return;
    const blob = new Blob([`﻿${toCsv(data.top_drugs)}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `thuoc-ban-chay-${data.date_from}_${data.date_to}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const maxSold = Math.max(1, ...(data?.top_drugs ?? []).map((d) => Number(d.quantity_sold) || 0));

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <h1 className={styles.title}>Bảng điều hành</h1>
        <div className={styles.controls}>
          {branches.length > 1 && (
            <select
              className={styles.select}
              value={branchId ?? ""}
              onChange={(e) => setBranchId(e.target.value || undefined)}
              aria-label="Chi nhánh"
            >
              <option value="">Chi nhánh của tôi</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          )}
          <span className={styles.window}>{DASHBOARD_WINDOW_DAYS} ngày gần nhất</span>
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          <span>
            {error instanceof ApiError ? error.problem.detail : "Không tải được số liệu."}
          </span>
          <button type="button" className={styles.retry} onClick={() => refetch()}>
            Thử lại
          </button>
        </div>
      )}

      <section className={styles.tiles}>
        <Tile
          tone="accent"
          label="Doanh thu kỳ"
          value={isLoading ? null : `${formatMoney(data?.revenue_total ?? "0")} ₫`}
          hint={`${DASHBOARD_WINDOW_DAYS} ngày`}
        />
        <Tile
          tone="danger"
          label="Sắp hết hàng"
          value={isLoading ? null : String(data?.low_stock_count ?? 0)}
          hint="dưới điểm đặt"
          muted={data?.low_stock_count === 0}
        />
        <Tile
          tone="warning"
          label="Cận hạn dùng"
          value={isLoading ? null : String(data?.near_expiry_count ?? 0)}
          hint="lô trong 90 ngày"
          muted={data?.near_expiry_count === 0}
        />
        <Tile
          tone="plain"
          label="Đơn mua nháp"
          value={isLoading ? null : String(data?.draft_po_count ?? 0)}
          hint="chờ duyệt"
        />
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Thuốc bán chạy</h2>
          <button
            type="button"
            className={styles.ghost}
            onClick={exportCsv}
            disabled={!data || data.top_drugs.length === 0}
          >
            Xuất CSV
          </button>
        </div>

        {isLoading && <div className={styles.skeletonRows} aria-hidden />}

        {!isLoading && data && data.top_drugs.length === 0 && (
          <p className={styles.empty}>Chưa có giao dịch nào trong kỳ này.</p>
        )}

        {!isLoading &&
          data?.top_drugs.map((d) => (
            <div key={d.drug_id} className={styles.row}>
              <span className={styles.rowName}>{drugLabel(d)}</span>
              <span className={styles.barWrap}>
                <span
                  className={styles.bar}
                  style={{ width: `${((Number(d.quantity_sold) || 0) / maxSold) * 100}%` }}
                />
              </span>
              <span className={styles.rowQty}>{formatQty(d.quantity_sold)}</span>
              <span className={styles.rowMoney}>{formatMoney(d.revenue)} ₫</span>
            </div>
          ))}
      </section>
    </div>
  );
}

/** `value === null` = đang tải ⇒ khung xám. Ô rỗng-tốt (0) bỏ vạch màu: im
 * lặng là tín hiệu tốt, tô đỏ số 0 là báo động giả (docs/19 §4). */
function Tile({
  tone,
  label,
  value,
  hint,
  muted = false,
}: {
  tone: "accent" | "danger" | "warning" | "plain";
  label: string;
  value: string | null;
  hint: string;
  muted?: boolean;
}) {
  const toneClass = muted ? styles.tonePlain : styles[`tone${tone[0].toUpperCase()}${tone.slice(1)}`];
  return (
    <article className={`${styles.tile} ${toneClass}`}>
      <span className={styles.tileLabel}>{label}</span>
      {value === null ? (
        <span className={styles.skeleton} aria-label="Đang tải" />
      ) : (
        <span className={styles.tileValue}>{value}</span>
      )}
      <span className={styles.tileHint}>{hint}</span>
    </article>
  );
}
