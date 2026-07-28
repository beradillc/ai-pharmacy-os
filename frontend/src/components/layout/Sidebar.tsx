"use client";

import Link from "next/link";

import { isActive, NAV_GROUP_LABEL, visibleNav, type NavGroup } from "@/shared/nav";

import { NavIcon } from "./NavIcon";
import styles from "./Sidebar.module.css";

const GROUP_ORDER: NavGroup[] = ["ban-hang", "kho", "quan-tri"];

/**
 * Điều hướng cạnh trái — chỉ hiện từ 900px trở lên.
 *
 * Cùng nguồn dữ liệu với `BottomNavigation` (`shared/nav.ts`), khác duy nhất ở
 * cách bày. Đây là chỗ thoả yêu cầu "không tạo hai hệ thống logic khác nhau":
 * hai component, MỘT mô hình.
 *
 * Nhóm không còn mục nào (do thiếu quyền) bị ẩn cả tiêu đề — một tiêu đề trơ
 * không có mục nào bên dưới trông như màn hình bị lỗi.
 */
export function Sidebar({
  permissions,
  pathname,
}: {
  permissions: readonly string[];
  pathname: string;
}) {
  const items = visibleNav(permissions);

  return (
    <nav className={styles.sidebar} aria-label="Điều hướng chính">
      {GROUP_ORDER.map((group) => {
        const inGroup = items.filter((item) => item.group === group);
        if (inGroup.length === 0) return null;
        return (
          <div key={group} className={styles.group}>
            <p className={styles.groupLabel}>{NAV_GROUP_LABEL[group]}</p>
            {inGroup.map((item) => {
              const active = isActive(item, pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? styles.linkActive : styles.link}
                  aria-current={active ? "page" : undefined}
                >
                  <NavIcon name={item.icon} filled={active} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        );
      })}
    </nav>
  );
}
