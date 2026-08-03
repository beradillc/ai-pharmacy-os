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

/**
 * 🔴 **`thuLaiDuoc` mặc định `true` để giữ nguyên hành vi mọi chỗ gọi cũ** — nhưng chỗ nào
 * biết lỗi của mình KHÔNG thử lại được thì phải nói ra (V3-10, Chain nêu 04/08).
 *
 * Trước bản này `ErrorState` mời **Thử lại** cho **mọi** loại lỗi. Với mất mạng hay 5xx thì
 * đúng; với **hết phiên**, **thiếu quyền**, **không tìm thấy** thì nút ấy không bao giờ chữa
 * được gì — nó chỉ gửi lại đúng một yêu cầu sẽ hỏng y như cũ. Chain hỏi thẳng: *"hết hạn thì
 * đăng nhập lại, chứ thử lại cái gì?"*
 *
 * Một nút không bao giờ thành công tệ hơn không có nút: nó **giấu mất việc thật** người dùng
 * cần làm, và biến một lỗi hai giây thành một vòng lặp bấm.
 */
export function ErrorState({
  message,
  onRetry,
  thuLaiDuoc = true,
  goiY,
}: {
  message: string;
  onRetry?: () => void;
  /** `false` khi lỗi thuộc loại bấm lại cũng hỏng y như cũ (401 · 403 · 404 · 422). */
  thuLaiDuoc?: boolean;
  /** Việc người dùng thật sự cần làm, khi Thử lại không phải câu trả lời. */
  goiY?: string;
}) {
  return (
    <div className={styles.error} role="alert">
      <span>{message}</span>
      {/* `.emptyText` chứ không phải `.muted` — `.muted` KHÔNG có trong States.module.css.
          Bẫy kỷ luật #22: `class="undefined"`, chữ rơi về mặc định, không cổng nào đỏ. */}
      {goiY && <span className={styles.emptyText}>{goiY}</span>}
      {onRetry && thuLaiDuoc && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Thử lại
        </button>
      )}
    </div>
  );
}
