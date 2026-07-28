"use client";

import Link from "next/link";

import { bottomNavItems, isActive, type NavItem } from "@/shared/nav";

import { NavIcon } from "./NavIcon";
import styles from "./BottomNavigation.module.css";

/**
 * Thanh điều hướng dưới — chỉ hiện dưới 900px (ẩn bằng CSS, không bằng JS: đo
 * bằng JS thì lượt render đầu luôn đoán sai và người dùng thấy thanh nhấp nháy).
 *
 * Ô thứ năm luôn là "Thêm". Bốn ô kia lấy từ `bottomNavItems()` — nếu người dùng
 * có ít quyền, thanh CO LẠI thay vì độn ô giả.
 */
export function BottomNavigation({
  permissions,
  pathname,
  onOpenMore,
  moreOpen,
}: {
  permissions: readonly string[];
  pathname: string;
  onOpenMore: () => void;
  moreOpen: boolean;
}) {
  const items = bottomNavItems(permissions);

  return (
    <nav className={styles.bar} aria-label="Điều hướng chính">
      {items.map((item) => (
        <BottomNavLink key={item.href} item={item} active={isActive(item, pathname)} />
      ))}
      <button
        type="button"
        className={moreOpen ? styles.itemActive : styles.item}
        onClick={onOpenMore}
        aria-expanded={moreOpen}
        aria-haspopup="dialog"
      >
        <NavIcon name="more" filled={moreOpen} />
        <span className={styles.label}>Thêm</span>
      </button>
    </nav>
  );
}

function BottomNavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={active ? styles.itemActive : styles.item}
      // `aria-current` chứ không chỉ đổi màu: trình đọc màn hình phải biết mục
      // nào đang mở, và yêu cầu mục 11 cấm dùng riêng màu để biểu thị trạng thái.
      aria-current={active ? "page" : undefined}
    >
      <NavIcon name={item.icon} filled={active} />
      <span className={styles.label}>{item.short}</span>
    </Link>
  );
}
