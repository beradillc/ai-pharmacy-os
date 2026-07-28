"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/features/auth/auth-store";

import styles from "./layout.module.css";

/** Mục menu chỉ hiện khi phiên có ĐỦ quyền của nó.
 *
 * Thứ tự theo nhịp một ngày làm việc, không theo module: mở máy xem số (bảng
 * điều hành) → bán → tra hàng → xem hoá đơn ca → khách quen → đặt hàng. Sắp theo
 * module là sắp theo cách LẬP TRÌNH VIÊN nhìn hệ thống. */
const NAV = [
  { href: "/bang-dieu-hanh", label: "Bảng điều hành", permission: "analytics.read" },
  { href: "/", label: "Bán hàng", permission: "sales.create" },
  { href: "/ton-kho", label: "Tồn kho", permission: "inventory.read" },
  { href: "/hoa-don", label: "Hoá đơn", permission: "sales.read" },
  { href: "/khach-hang", label: "Khách hàng", permission: "crm.read" },
  { href: "/don-mua-hang", label: "Đơn mua hàng", permission: "procurement.po.read" },
  { href: "/de-xuat-dat-hang", label: "Đề xuất đặt hàng", permission: "analytics.read" },
] as const;

/**
 * Khung cho hai màn quản lý Sprint 9. Cùng cách canh đăng nhập như `(pos)`:
 * đọc localStorage sau khi mount, vì lượt render phía máy chủ không có
 * `window` — chuyển hướng sớm hơn sẽ đá văng người đang đăng nhập mỗi lần F5.
 *
 * Gating theo QUYỀN, không theo tên vai (docs/19 §4): thiếu `analytics.read`
 * thì **không hiện mục trong menu**, chứ không phải hiện rồi báo lỗi khi bấm —
 * một nút chỉ để từ chối người bấm là một lời hứa suông.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const session = useAuthStore((s) => s.session);
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !session) router.replace("/login");
  }, [hydrated, session, router]);

  if (!hydrated || !session) return null;

  const permissions = new Set(session.permissions);
  const visible = NAV.filter((item) => permissions.has(item.permission));
  const branchName =
    session.accessible_branches.find((b) => b.id === session.branch_id)?.name ??
    `CN ${session.branch_id.slice(0, 8)}`;

  return (
    <div className={styles.shell}>
      <header className={styles.bar}>
        <Link href="/" className={styles.brand}>
          BERAS
        </Link>
        <nav className={styles.nav}>
          {visible.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname === item.href ? styles.linkActive : styles.link}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className={styles.right}>
          {/* Tên chi nhánh THẬT, không phải 8 ký tự đầu của UUID. Tên đã nằm sẵn
              trong `accessible_branches` của phiên đăng nhập từ Sprint 9 — bản
              trước hiện UUID không phải vì thiếu dữ liệu mà vì không ai tra. */}
          <span className={styles.branch}>{branchName}</span>
          <button type="button" className={styles.logout} onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
