"use client";

import Link from "next/link";

import styles from "./AppHeader.module.css";

/**
 * Thanh trên cùng: thương hiệu · chi nhánh · chuông · đăng xuất.
 *
 * Thay cho HAI header từng tồn tại song song (`(app)/layout.module.css` và
 * `(pos)/page.module.css`) — xem `docs/ui/UI_CURRENT_STATE.md` §2.
 *
 * Trên mobile, header KHÔNG chứa điều hướng: bottom nav lo việc đó. Nhồi menu vào
 * đây rồi lại có bottom nav là đúng thứ "hai hệ thống" mà yêu cầu cấm.
 */
export function AppHeader({
  branchName,
  pendingCount = 0,
  onLogout,
}: {
  branchName: string;
  /** Số đơn offline đang chờ đồng bộ — 0 thì không hiện gì. */
  pendingCount?: number;
  onLogout: () => void;
}) {
  return (
    <header className={styles.bar}>
      <Link href="/bang-dieu-hanh" className={styles.brand}>
        BERAS
      </Link>

      <span className={styles.branch} title="Chi nhánh đang làm việc">
        {branchName}
      </span>

      {pendingCount > 0 && (
        <span className={styles.pending} role="status">
          {/* Chữ + số, không phải chấm đỏ đơn thuần: một chấm đỏ không nói được
              "ba đơn chưa lên máy chủ", mà đó mới là điều thu ngân cần biết. */}
          {pendingCount} đơn chờ đồng bộ
        </span>
      )}

      <button type="button" className={styles.logout} onClick={onLogout}>
        Đăng xuất
      </button>
    </header>
  );
}
