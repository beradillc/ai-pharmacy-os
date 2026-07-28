import styles from "./KpiCard.module.css";

export type KpiStatus = "neutral" | "good" | "warning" | "danger";
export type KpiTrend = "up" | "down" | "flat";

export interface KpiCardProps {
  title: string;
  /** Giá trị đã định dạng sẵn. Component KHÔNG tự định dạng số — việc đó thuộc
   * `shared/format`, và để nó ở đây là kéo một mẩu nghiệp vụ lên tầng trình bày. */
  value: string | null;
  /** Câu so sánh, ví dụ "so với hôm qua". `undefined` ⇒ không hiện dòng nào. */
  comparison?: string;
  trend?: KpiTrend;
  status?: KpiStatus;
  hint?: string;
  /** `null` ở `value` nghĩa là ĐANG TẢI ⇒ tự hiện khung xám. */
  icon?: React.ReactNode;
}

const TREND_MARK: Record<KpiTrend, string> = { up: "▲", down: "▼", flat: "■" };

/**
 * Thẻ chỉ số.
 *
 * Nâng từ hàm `Tile` cục bộ trong `bang-dieu-hanh/page.tsx` (Sprint 9) — giữ
 * nguyên ý tưởng vạch màu bên trái vì nó đọc lướt bắt được trước cả chữ, thêm
 * `comparison`/`trend`/`icon` mà bản cũ không có.
 *
 * Xu hướng hiện bằng **ký hiệu + chữ + màu**, không riêng màu: đỏ-xanh là đúng
 * cặp màu mà người mù màu đỏ-lục không phân biệt được, và đây lại là con số họ
 * nhìn nhiều nhất trong ngày.
 *
 * `trend` KHÔNG suy ra `status`: doanh thu giảm là xấu, còn "cảnh báo kho" giảm
 * là tốt. Người gọi biết ngữ cảnh, component thì không.
 */
export function KpiCard({
  title,
  value,
  comparison,
  trend,
  status = "neutral",
  hint,
  icon,
}: KpiCardProps) {
  const loading = value === null;

  return (
    <article className={`${styles.card} ${styles[status]}`}>
      <div className={styles.head}>
        <p className={styles.title}>{title}</p>
        {icon && <span className={styles.icon}>{icon}</span>}
      </div>

      {loading ? (
        <div className={styles.skeleton} aria-hidden />
      ) : (
        <p className={styles.value}>{value}</p>
      )}

      {!loading && comparison && (
        <p className={`${styles.comparison} ${trend ? styles[`trend-${trend}`] : ""}`}>
          {trend && <span aria-hidden>{TREND_MARK[trend]} </span>}
          {comparison}
        </p>
      )}

      {hint && !comparison && <p className={styles.hint}>{hint}</p>}
    </article>
  );
}
