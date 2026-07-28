"use client";

import Link from "next/link";

import styles from "./ComplianceCard.module.css";

export type Severity = "critical" | "warning" | "info";

export interface TaskItem {
  id: string;
  severity: Severity;
  title: string;
  description: string;
  actionLabel: string;
  href: string;
}

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Gấp",
  warning: "Cần xem",
  info: "Ghi nhận",
};

/**
 * Thẻ "Cần xử lý" — gộp việc phải làm từ nhiều nguồn về một chỗ.
 *
 * Đặt **trên** biểu đồ trên dashboard, có chủ đích: việc phải làm đứng trước phân
 * tích. Một người mở phần mềm lúc 7 giờ sáng cần biết *hôm nay phải xử lý gì*
 * trước khi cần biết *tháng này bán được bao nhiêu*.
 *
 * Mức độ hiện bằng **nhãn chữ + vạch màu**, không riêng màu (yêu cầu mục 11).
 *
 * 🔴 Dữ liệu gộp ở FE từ các endpoint đã có, KHÔNG có endpoint tổng hợp ở backend
 * (`docs/ui/UI_GAP_REPORT.md` B-03). Chưa gộp ở backend là cố ý: gộp là một quyết
 * định kiến trúc, và nên biết hình dạng thật của danh sách này trước khi đóng nó
 * lại thành một API.
 */
export function ComplianceCard({
  items,
  loading,
}: {
  items: TaskItem[];
  loading?: boolean;
}) {
  return (
    <section className={styles.card} aria-labelledby="task-heading">
      <div className={styles.head}>
        <h2 id="task-heading" className={styles.title}>
          Cần xử lý
        </h2>
        {!loading && items.length > 0 && <span className={styles.count}>{items.length}</span>}
      </div>

      {loading ? (
        <div className={styles.skeleton} aria-hidden />
      ) : items.length === 0 ? (
        <p className={styles.clear}>Không có việc nào cần xử lý. Kho và tuân thủ đều ổn.</p>
      ) : (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={`${styles.item} ${styles[item.severity]}`}>
              <div className={styles.itemBody}>
                <p className={styles.itemHead}>
                  <span className={styles.badge}>{SEVERITY_LABEL[item.severity]}</span>
                  <span className={styles.itemTitle}>{item.title}</span>
                </p>
                <p className={styles.itemDesc}>{item.description}</p>
              </div>
              <Link href={item.href} className={styles.action}>
                {item.actionLabel}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
