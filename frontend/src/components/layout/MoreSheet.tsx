"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

import { overflowNavItems } from "@/shared/nav";

import { NavIcon } from "./NavIcon";
import styles from "./MoreSheet.module.css";

/**
 * Ngăn kéo "Thêm" — mọi mục không lọt vào 4 ô bottom nav.
 *
 * Là `<dialog>` thật chứ không phải một `<div>` phủ lên: trình duyệt tự lo bẫy
 * tiêu điểm bàn phím, phím Esc, và lớp phủ `::backdrop`. Tự làm ba thứ đó bằng
 * tay là ba chỗ để sai mà không ai kiểm.
 */
export function MoreSheet({
  open,
  permissions,
  onClose,
}: {
  open: boolean;
  permissions: readonly string[];
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const items = overflowNavItems(permissions);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={styles.sheet}
      onClose={onClose}
      // Bấm ra ngoài để đóng: `<dialog>` coi cả vùng backdrop là chính nó, nên
      // so sánh target với dialog là cách phân biệt "bấm nền" với "bấm nội dung".
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      aria-label="Menu thêm"
    >
      <div className={styles.body}>
        <div className={styles.grabber} aria-hidden />
        <h2 className={styles.title}>Thêm</h2>
        {items.length === 0 ? (
          <p className={styles.empty}>Không có mục nào khác trong quyền của bạn.</p>
        ) : (
          <ul className={styles.list}>
            {items.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className={styles.item} onClick={onClose}>
                  <NavIcon name={item.icon} />
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <button type="button" className={styles.close} onClick={onClose}>
          Đóng
        </button>
      </div>
    </dialog>
  );
}
