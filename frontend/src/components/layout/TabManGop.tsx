"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./TabManGop.module.css";

/**
 * Dải tab của hai màn được **gộp thành một mục menu** (Chain giao 2026-08-01).
 *
 * 🔴 Vì sao gộp ở tầng menu chứ không dựng một route mới chứa hai tab: kỷ luật #17 cấm đổi
 * tên route cũ, và bốn đường dẫn `/nhap-nhanh` `/khoi-tao-ton` `/kiem-ke` `/so-do-kho` đang
 * nằm trong dấu trang, trong tài liệu và trong **tám cổng trình duyệt**. Hai màn vẫn là hai
 * màn — chúng chỉ vào chung một cửa. Không route nào chết, không có chuyển hướng nào.
 *
 * Dùng `Link` chứ không `router.push`: giữ được bấm-giữa-để-mở-tab-mới và menu chuột phải,
 * hai thứ người đứng quầy dùng thật khi đối chiếu hai màn cạnh nhau.
 */
export interface TabMan {
  href: string;
  nhan: string;
  /** Một câu nói rõ tab này khác tab kia chỗ nào — hiện thành tooltip khi rê chuột.
   *  🔴 UAT 01/08 (lỗi U-06): hai tab "Nhập hàng nhanh" và "Khởi tạo tồn kho" tên gần giống
   *  nhau nhưng **hệ quả kế toán khác hẳn** — khởi tạo KHÔNG hỏi giá vốn, nhập mua thì có.
   *  Dùng nhầm ⇒ sai giá vốn bình quân ⇒ sai lãi gộp. Mô tả nằm trong màn thì chỉ ai đã vào
   *  mới đọc được; người đang chọn tab thì chưa. */
  moTa?: string;
}

export function TabManGop({ tabs }: { tabs: readonly TabMan[] }) {
  const pathname = usePathname();
  return (
    <nav className={styles.dai} aria-label="Chuyển màn trong nhóm">
      {tabs.map((t) => {
        const dangO = t.href === pathname;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`${styles.tab} ${dangO ? styles.tabDangO : ""}`}
            // `aria-current="page"` chứ không chỉ đổi màu: người dùng trình đọc màn hình
            // cũng phải biết mình đang ở tab nào, và màu thì họ không nghe được.
            aria-current={dangO ? "page" : undefined}
            title={t.moTa}
          >
            {t.nhan}
          </Link>
        );
      })}
    </nav>
  );
}
