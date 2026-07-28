import styles from "./States.module.css";

/**
 * Ba trạng thái mà mọi khối dữ liệu đều phải có, gom một chỗ.
 *
 * Trước đợt này, sáu màn tự viết sáu bản gần giống nhau — và "gần giống" là cách
 * một sản phẩm trông chắp vá mà không ai chỉ được ra chỗ nào sai.
 */

export function LoadingState({ rows = 3, label = "Đang tải…" }: { rows?: number; label?: string }) {
  return (
    // `aria-busy` + nhãn chữ: người dùng trình đọc màn hình phải biết đang chờ,
    // vì với họ mấy khung xám kia hoàn toàn vô hình.
    <div className={styles.loading} aria-busy="true" aria-live="polite">
      <span className={styles.srOnly}>{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={styles.skeleton} aria-hidden />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className={styles.empty}>
      <p className={styles.emptyTitle}>{title}</p>
      {description && <p className={styles.emptyText}>{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className={styles.error} role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Thử lại
        </button>
      )}
    </div>
  );
}
