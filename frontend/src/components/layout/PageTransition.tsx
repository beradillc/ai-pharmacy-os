"use client";

import { usePathname } from "next/navigation";

import styles from "./PageTransition.module.css";

/**
 * Hiệu ứng chuyển trang: fade + trượt lên 8px, 200ms.
 *
 * Cách làm rẻ nhất mà vẫn đúng: đổi `key` theo đường dẫn ⇒ React thay cây con ⇒
 * animation CSS chạy lại. Không thư viện, không giữ trạng thái, không đo đạc.
 *
 * Chỉ animate `transform` và `opacity` — hai thuộc tính trình duyệt xử lý trên
 * lớp hợp thành, không ép tính lại bố cục. Animate `height`/`top` sẽ làm đúng
 * thứ yêu cầu mục 12 cấm: một hiệu ứng khiến cả dashboard vẽ lại từng khung hình.
 *
 * Người tắt hiệu ứng ở cấp hệ điều hành được `globals.css` xử lý một chỗ
 * (`prefers-reduced-motion` ⇒ 1ms) — không cần nhánh riêng ở đây.
 */
export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div key={pathname} className={styles.page}>
      {children}
    </div>
  );
}
