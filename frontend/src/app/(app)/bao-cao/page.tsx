"use client";

import { useState } from "react";

import { RevenueChart } from "@/components/data/RevenueChart";
import { ErrorState, LoadingState } from "@/components/feedback/States";
import { DASHBOARD_WINDOW_DAYS } from "@/features/analytics/use-dashboard";
import { useRevenueSeries } from "@/features/analytics/use-revenue-series";
import { useAuthStore } from "@/features/auth/auth-store";
import { useCsvExport } from "@/features/reports/use-export";
import { formatMoney } from "@/shared/format/number";

import styles from "./page.module.css";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  const offset = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 10);
}

/**
 * Màn Báo cáo (đợt U3, 2026-07-29).
 *
 * Ba báo cáo CSV đã có sẵn ở backend từ Sprint 7 (`GET /reports/*`) nhưng **chưa
 * từng có cửa nào để bấm** — muốn lấy phải gọi API bằng tay. Màn này chỉ là cái
 * cửa đó; **không thêm một endpoint nào**.
 *
 * Vì sao có biểu đồ ở đây trong khi Tổng quan cũng có: hai chỗ trả lời hai câu
 * khác nhau. Tổng quan hỏi *"hôm nay thế nào"*; màn này hỏi *"kỳ nào, xuất cho
 * kế toán cái gì"* — nên nó có chọn khoảng ngày, còn Tổng quan thì cố định 28 ngày.
 */
export default function ReportsPage() {
  const session = useAuthStore((s) => s.session);
  const [dateFrom, setDateFrom] = useState(() => isoDaysAgo(DASHBOARD_WINDOW_DAYS - 1));
  const [dateTo, setDateTo] = useState(() => isoDaysAgo(0));
  // Giá trị GỬI ĐI phải khớp enum backend, và enum đó là CHỮ THƯỜNG
  // (`RevenueGranularity` trong sales/application/dto.py). Bản đầu của màn này gửi
  // "DAY" và nhận 422 — bắt được vì gọi thật endpoint chứ không vì đọc lại mã.
  const [granularity, setGranularity] = useState<"day" | "week" | "month">("day");

  const series = useRevenueSeries();
  const csv = useCsvExport();

  const canReadSales = session?.permissions.includes("sales.read") ?? false;
  const canReadStock = session?.permissions.includes("inventory.read") ?? false;
  const range = `date_from=${dateFrom}&date_to=${dateTo}`;
  const total = (series.data?.points ?? []).reduce((sum, p) => sum + p.revenue, 0);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Báo cáo</h1>
          <p className={styles.subtitle}>Xuất CSV mở được bằng Excel hoặc Google Sheets</p>
        </div>
      </header>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Doanh thu {DASHBOARD_WINDOW_DAYS} ngày gần nhất</h2>
          <span className={styles.total}>{formatMoney(String(total))} đ</span>
        </div>
        {series.isLoading ? (
          <LoadingState rows={2} label="Đang tải biểu đồ" />
        ) : series.error ? (
          <ErrorState message="Không tải được biểu đồ." onRetry={() => series.refetch()} />
        ) : (
          <RevenueChart points={series.data?.points ?? []} height={200} />
        )}
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Kỳ báo cáo</h2>
        </div>
        <div className={styles.controls}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Từ ngày</span>
            <input
              type="date"
              className={styles.input}
              value={dateFrom}
              max={dateTo}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Đến ngày</span>
            <input
              type="date"
              className={styles.input}
              value={dateTo}
              min={dateFrom}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </label>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Nhóm theo</span>
            <select
              className={styles.input}
              value={granularity}
              onChange={(e) => setGranularity(e.target.value as typeof granularity)}
            >
              <option value="day">Ngày</option>
              <option value="week">Tuần</option>
              <option value="month">Tháng</option>
            </select>
          </label>
        </div>
      </section>

      {csv.error && <ErrorState message={csv.error} onRetry={csv.clearError} />}

      <section className={styles.cards}>
        <ReportCard
          title="Doanh thu theo kỳ"
          description="Mỗi dòng một kỳ × chi nhánh × loại tiền: số đơn và tổng tiền. Đây là tệp đưa cho kế toán."
          disabled={!canReadSales}
          disabledReason="Cần quyền đọc bán hàng"
          busy={csv.busy === "revenue"}
          onClick={() =>
            csv.download(
              `/reports/revenue/export?${range}&granularity=${granularity}`,
              `doanh-thu-${dateFrom}_${dateTo}.csv`,
              "revenue",
            )
          }
        />
        <ReportCard
          title="Thuốc bán chạy"
          description="Xếp hạng theo số lượng bán trong kỳ, kèm doanh thu từng mặt hàng."
          disabled={!canReadSales}
          disabledReason="Cần quyền đọc bán hàng"
          busy={csv.busy === "top"}
          onClick={() =>
            csv.download(
              `/reports/top-drugs/export?${range}`,
              `thuoc-ban-chay-${dateFrom}_${dateTo}.csv`,
              "top",
            )
          }
        />
        <ReportCard
          title="Tồn kho theo lô"
          description="Tồn hiện tại từng lô kèm hạn dùng, cận hạn xếp trước. Không phụ thuộc kỳ báo cáo."
          disabled={!canReadStock}
          disabledReason="Cần quyền đọc kho"
          busy={csv.busy === "stock"}
          onClick={() =>
            csv.download(
              "/reports/inventory/stock/export",
              `ton-kho-${isoDaysAgo(0)}.csv`,
              "stock",
            )
          }
        />
      </section>
    </div>
  );
}

/**
 * Thẻ một báo cáo.
 *
 * Thiếu quyền thì nút **tắt kèm lý do bằng chữ**, không phải biến mất. Khác với
 * menu — menu ẩn mục để khỏi rối; ở đây người dùng đang chủ động tìm báo cáo, nên
 * "không thấy đâu cả" gây hoang mang hơn là "có nhưng bạn chưa được cấp quyền".
 *
 * Nút tắt ở giao diện KHÔNG phải lớp bảo vệ: backend vẫn kiểm quyền ở service và
 * trả 403. Đây chỉ là phép lịch sự với người dùng.
 */
function ReportCard({
  title,
  description,
  onClick,
  busy,
  disabled,
  disabledReason,
}: {
  title: string;
  description: string;
  onClick: () => void;
  busy: boolean;
  disabled: boolean;
  disabledReason: string;
}) {
  return (
    <article className={styles.card}>
      <h3 className={styles.cardTitle}>{title}</h3>
      <p className={styles.cardText}>{description}</p>
      <button
        type="button"
        className={styles.button}
        onClick={onClick}
        disabled={disabled || busy}
      >
        {busy ? "Đang tạo tệp…" : "Tải CSV"}
      </button>
      {disabled && <p className={styles.cardNote}>{disabledReason}</p>}
    </article>
  );
}
