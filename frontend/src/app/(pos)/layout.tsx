"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BottomNavigation } from "@/components/layout/BottomNavigation";
import { MoreSheet } from "@/components/layout/MoreSheet";
import { useAuthStore } from "@/features/auth/auth-store";

/**
 * Khung màn bán hàng.
 *
 * Canh đăng nhập: đọc localStorage **sau khi mount** (`hydrate()`) — lượt render
 * phía máy chủ không có `window`, nên chuyển hướng sớm hơn sẽ đá văng thu ngân
 * đang đăng nhập mỗi lần F5.
 *
 * 🔴 Sửa 2026-07-29 (Chain báo): màn này **thiếu thanh điều hướng dưới**. Đợt U1
 * thêm bottom nav cho nhóm `(app)` nhưng để nguyên `(pos)`, nên bấm "Bán hàng"
 * trên thanh là thanh biến mất — người dùng rơi vào ngõ cụt, đúng thứ mà chính
 * quyết định Q1 ("một mô hình điều hướng") nói là phải tránh.
 *
 * Vì sao vẫn KHÔNG gộp POS vào `(app)`: màn bán hàng cố ý không có sidebar và
 * không có header quản lý — thu ngân cần diện tích. Cái phải dùng chung là **mô
 * hình** (`shared/nav.ts`), không phải khung hình. Nên ở đây chỉ gắn đúng thanh
 * dưới + ngăn "Thêm", giữ nguyên header riêng của POS.
 */
export default function PosLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const session = useAuthStore((s) => s.session);
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);
  const [moreOpen, setMoreOpen] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !session) {
      router.replace("/login");
    }
  }, [hydrated, session, router]);

  if (!hydrated || !session) {
    return null;
  }

  return (
    <>
      {children}
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
    </>
  );
}
