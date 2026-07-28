"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { QuickActionGrid } from "@/components/action/QuickActionGrid";
import { KpiCard } from "@/components/data/KpiCard";
import { RevenueChart } from "@/components/data/RevenueChart";
import { ComplianceCard, type TaskItem } from "@/components/feedback/ComplianceCard";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/States";
import { DASHBOARD_WINDOW_DAYS, useDashboard } from "@/features/analytics/use-dashboard";
import { useRevenueSeries } from "@/features/analytics/use-revenue-series";
import { useToday } from "@/features/analytics/use-today";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { Dashboard, TopDrug } from "@/shared/api/types";
import { formatMoney, formatQty, formatTime } from "@/shared/format/number";

import styles from "./page.module.css";

/** Nhãn hiện thay cho tên khi catalog không tra được (docs/19 §10.2). */
function drugLabel(d: { drug_id: string; drug_name: string | null }): string {
  return d.drug_name ?? `Mã ${d.drug_id.slice(0, 8)}`;
}

function toCsv(rows: TopDrug[]): string {
  const head = "ten_thuoc,ma_thuoc,so_luong_ban,doanh_thu";
  const body = rows.map((r) =>
    [`"${(r.drug_name ?? "").replace(/"/g, '""')}"`, r.drug_id, r.quantity_sold, r.revenue].join(
      ",",
    ),
  );
  return [head, ...body].join("\n");
}

/**
 * Màn Tổng quan — dựng lại theo IA của yêu cầu UI (đợt U2, 2026-07-29):
 *
 *   Hành động nhanh → KPI → Cần xử lý → Doanh thu → Giao dịch gần đây → Bán chạy
 *
 * Hành động nhanh đứng TRƯỚC số liệu, và "Cần xử lý" đứng TRƯỚC biểu đồ: mở phần
 * mềm buổi sáng là để làm việc, không phải để đọc báo cáo.
 *
 * Mỗi khối tự chịu trạng thái của mình — một khối lỗi thì các khối kia vẫn dùng
 * được. Không có màn "toàn trang đang tải".
 *
 * URL giữ nguyên `/bang-dieu-hanh` (quyết định Q1, `docs/ui/ROUTING_PLAN.md` §8).
 */
export default function DashboardPage() {
  const session = useAuthStore((s) => s.session);
  const branches = session?.accessible_branches ?? [];
  const [branchId, setBranchId] = useState<string | undefined>(undefined);

  const dashboard = useDashboard(branchId);
  const today = useToday();
  const series = useRevenueSeries();

  const tasks = useMemo(() => buildTasks(dashboard.data), [dashboard.data]);

  function exportCsv() {
    if (!dashboard.data) return;
    const blob = new Blob([`﻿${toCsv(dashboard.data.top_drugs)}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `thuoc-ban-chay-${dashboard.data.date_from}_${dashboard.data.date_to}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const maxSold = Math.max(
    1,
    ...(dashboard.data?.top_drugs ?? []).map((d) => Number(d.quantity_sold) || 0),
  );

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Tổng quan</h1>
          <p className={styles.subtitle}>{DASHBOARD_WINDOW_DAYS} ngày gần nhất</p>
        </div>
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
      </header>

      <QuickActionGrid permissions={session?.permissions ?? []} />

      {dashboard.error && (
        <ErrorState
          message={
            dashboard.error instanceof ApiError
              ? dashboard.error.problem.detail
              : "Không tải được số liệu."
          }
          onRetry={() => dashboard.refetch()}
        />
      )}

      <section className={styles.tiles}>
        <KpiCard
          title="Doanh thu hôm nay"
          value={today.data ? `${formatMoney(String(today.data.revenue))} ₫` : null}
          hint={`${today.data?.orderCount ?? 0} đơn`}
          status="good"
        />
        <KpiCard
          title={`Doanh thu ${DASHBOARD_WINDOW_DAYS} ngày`}
          value={dashboard.data ? `${formatMoney(dashboard.data.revenue_total)} ₫` : null}
          hint="đã ghi nhận"
        />
        <KpiCard
          title="Sắp hết hàng"
          value={dashboard.data ? String(dashboard.data.low_stock_count) : null}
          hint="dưới điểm đặt"
          status={dashboard.data?.low_stock_count ? "danger" : "neutral"}
        />
        <KpiCard
          title="Cận hạn dùng"
          value={dashboard.data ? String(dashboard.data.near_expiry_count) : null}
          hint="lô trong 90 ngày"
          status={dashboard.data?.near_expiry_count ? "warning" : "neutral"}
        />
      </section>

      <ComplianceCard items={tasks} loading={dashboard.isLoading} />

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Doanh thu {DASHBOARD_WINDOW_DAYS} ngày</h2>
        </div>
        {series.isLoading ? (
          <LoadingState rows={2} label="Đang tải biểu đồ doanh thu" />
        ) : series.error ? (
          <ErrorState message="Không tải được biểu đồ." onRetry={() => series.refetch()} />
        ) : (
          <>
            {series.data?.truncated && (
              // Nói thẳng khi dữ liệu bị cắt ngọn. Một biểu đồ thiếu dữ liệu mà
              // trông bình thường thì tệ hơn cả không có biểu đồ.
              <p className={styles.warn}>
                Quá nhiều đơn trong kỳ — biểu đồ chỉ tính 400 đơn gần nhất.
              </p>
            )}
            <RevenueChart points={series.data?.points ?? []} />
          </>
        )}
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Giao dịch gần đây</h2>
          <Link href="/hoa-don" className={styles.ghost}>
            Xem tất cả
          </Link>
        </div>
        {today.isLoading ? (
          <LoadingState rows={3} label="Đang tải giao dịch" />
        ) : today.error ? (
          <ErrorState message="Không tải được giao dịch." onRetry={() => today.refetch()} />
        ) : (today.data?.recent.length ?? 0) === 0 ? (
          <EmptyState
            title="Chưa có giao dịch nào hôm nay"
            description="Hoá đơn sẽ hiện ở đây ngay khi bán xong đơn đầu tiên."
          />
        ) : (
          <ul className={styles.txnList}>
            {today.data?.recent.map((sale) => (
              <li key={sale.id} className={styles.txn}>
                <span className={styles.txnTime}>{formatTime(sale.created_at)}</span>
                <span className={styles.txnMeta}>{sale.line_count} mặt hàng</span>
                <span className={styles.txnMoney}>{formatMoney(sale.subtotal)} ₫</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Thuốc bán chạy</h2>
          <button
            type="button"
            className={styles.ghost}
            onClick={exportCsv}
            disabled={!dashboard.data || dashboard.data.top_drugs.length === 0}
          >
            Xuất CSV
          </button>
        </div>
        {dashboard.isLoading ? (
          <LoadingState rows={3} label="Đang tải thuốc bán chạy" />
        ) : (dashboard.data?.top_drugs.length ?? 0) === 0 ? (
          <EmptyState title="Chưa có giao dịch nào trong kỳ này" />
        ) : (
          <ul className={styles.rows}>
            {dashboard.data?.top_drugs.map((drug) => (
              <li key={drug.drug_id} className={styles.row}>
                <span className={styles.rowName}>{drugLabel(drug)}</span>
                <span className={styles.barWrap}>
                  <span
                    className={styles.bar}
                    style={{
                      width: `${Math.max(4, (Number(drug.quantity_sold) / maxSold) * 100)}%`,
                    }}
                  />
                </span>
                <span className={styles.rowQty}>{formatQty(drug.quantity_sold)}</span>
                <span className={styles.rowMoney}>{formatMoney(drug.revenue)} ₫</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/**
 * Gộp "việc cần xử lý" từ số liệu bảng điều hành đã có.
 *
 * Chỉ dựng từ dữ liệu THẬT đang có trong tay — không mục nào bịa ra cho thẻ trông
 * đầy đặn. Thiếu nguồn thì thiếu mục, và thẻ nói "không có việc nào cần xử lý".
 */
function buildTasks(data: Dashboard | undefined): TaskItem[] {
  if (!data) return [];
  const tasks: TaskItem[] = [];

  if (data.low_stock_count > 0) {
    tasks.push({
      id: "low-stock",
      severity: "critical",
      title: `${data.low_stock_count} mặt hàng dưới điểm đặt`,
      description: "Hết hàng giữa ca là mất doanh thu và mất khách quen.",
      actionLabel: "Xem đề xuất",
      href: "/de-xuat-dat-hang",
    });
  }

  if (data.near_expiry_count > 0) {
    tasks.push({
      id: "near-expiry",
      severity: "warning",
      title: `${data.near_expiry_count} lô cận hạn dùng`,
      description: "Trong 90 ngày tới. Xử lý sớm còn kịp trả hàng hoặc đẩy bán.",
      actionLabel: "Xem kho",
      href: "/ton-kho",
    });
  }

  if (data.draft_po_count > 0) {
    tasks.push({
      id: "draft-po",
      severity: "info",
      title: `${data.draft_po_count} đơn mua nháp chờ duyệt`,
      description: "Đơn nháp chưa gửi nhà cung cấp thì hàng chưa về.",
      actionLabel: "Xem đơn mua",
      href: "/don-mua-hang",
    });
  }

  return tasks;
}
