"use client";

import { AppShell } from "@/app/_shell/AppShell";

/**
 * Khung cho các màn quản lý. Toàn bộ phần khung nằm ở `AppShell` — dùng chung
 * với màn Bán hàng, nên header/sidebar/thanh dưới chỉ có MỘT bản.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
