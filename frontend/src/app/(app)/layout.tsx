"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/features/auth/auth-store";

import styles from "./layout.module.css";

/** Mục menu chỉ hiện khi phiên có ĐỦ quyền của nó. */
const NAV = [
  { href: "/bang-dieu-hanh", label: "Bảng điều hành", permission: "analytics.read" },
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
          <span className={styles.branch}>CN {session.branch_id.slice(0, 8)}</span>
          <button type="button" className={styles.logout} onClick={logout}>
            Đăng xuất
          </button>
        </div>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
