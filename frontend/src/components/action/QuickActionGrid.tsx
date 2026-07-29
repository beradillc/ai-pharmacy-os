"use client";

import Link from "next/link";

import { NavIcon } from "@/components/layout/NavIcon";
import { quickActionItems } from "@/shared/nav";

import styles from "./QuickActionGrid.module.css";

/**
 * Lưới hành động nhanh — tối đa 8 ô, 4 cột trên điện thoại.
 *
 * Đọc từ **cùng** `shared/nav.ts` mà thanh dưới và sidebar đọc, nên thêm một màn
 * là thêm một dòng ở một chỗ. Ô thiếu quyền **biến mất** và lưới dồn lại — không
 * để ô xám bấm vào báo lỗi.
 *
 * Đặt TRÊN dãy KPI trên dashboard, có chủ đích: mở phần mềm lúc 7 giờ sáng là để
 * *bán*, không phải để đọc số. Số liệu là thứ người ta xem khi đã rảnh tay.
 */
export function QuickActionGrid({ permissions }: { permissions: readonly string[] }) {
  const items = quickActionItems(permissions).slice(0, 8);

  if (items.length === 0) return null;

  return (
    <nav className={styles.grid} aria-label="Hành động nhanh">
      {items.map((item) => (
        <Link key={item.href} href={item.href} className={styles.item}>
          <span className={styles.iconWrap}>
            <NavIcon name={item.icon} />
          </span>
          <span className={styles.label}>{item.short}</span>
        </Link>
      ))}
    </nav>
  );
}
