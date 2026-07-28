"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/layout/AppHeader";
import { BottomNavigation } from "@/components/layout/BottomNavigation";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { PageTransition } from "@/components/layout/PageTransition";
import { Sidebar } from "@/components/layout/Sidebar";
import { useAuthStore } from "@/features/auth/auth-store";
import { useOfflineSync } from "@/shared/offline/use-offline-sync";

import styles from "@/components/layout/AppShell.module.css";

/**
 * Khung cho các màn quản lý.
 *
 * Đổi ở đợt U1 (2026-07-29): menu ngang tự vẽ → `AppHeader` + `Sidebar` (desktop)
 * + `BottomNavigation` (mobile), tất cả đọc từ MỘT mô hình `shared/nav.ts`.
 *
 * Hai thứ CỐ Ý giữ nguyên vì đang chạy đúng:
 *  • cách canh đăng nhập — đọc localStorage sau khi mount, vì lượt render phía
 *    máy chủ không có `window`; chuyển hướng sớm hơn sẽ đá văng người đang đăng
 *    nhập mỗi lần F5;
 *  • gating theo QUYỀN, không theo tên vai — thiếu quyền thì mục không hiện,
 *    chứ không hiện rồi báo lỗi khi bấm.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const session = useAuthStore((s) => s.session);
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const logout = useAuthStore((s) => s.logout);
  const { pendingCount } = useOfflineSync();
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !session) router.replace("/login");
  }, [hydrated, session, router]);

  if (!hydrated || !session) return null;

  const branchName =
    session.accessible_branches.find((b) => b.id === session.branch_id)?.name ??
    `CN ${session.branch_id.slice(0, 8)}`;

  return (
    <div className={styles.shell}>
      <AppHeader branchName={branchName} pendingCount={pendingCount} onLogout={logout} />

      <div className={styles.body}>
        <Sidebar permissions={session.permissions} pathname={pathname} />
        <main className={styles.main}>
          <div className={styles.inner}>
            <PageTransition>{children}</PageTransition>
          </div>
        </main>
      </div>

      <BottomNavigation
        permissions={session.permissions}
        pathname={pathname}
        moreOpen={moreOpen}
        onOpenMore={() => setMoreOpen((v) => !v)}
      />
      <MoreSheet
        open={moreOpen}
        permissions={session.permissions}
        onClose={() => setMoreOpen(false)}
      />
    </div>
  );
}
