"use client";

import { AppShell } from "@/components/layout/AppShell";

/**
 * Khung màn Bán hàng.
 *
 * 🔴 Sửa 2026-07-29 lần hai, theo phản hồi của Chain: *"mục Bán hàng thiếu danh
 * mục bên trái, mỗi lần về phải bấm vào Quản lý thấy bất tiện."*
 *
 * Trước đó màn này cố ý không có sidebar (quyết định Q1), với lập luận thu ngân
 * cần tối đa diện tích. Lập luận đó là **giả định của tôi**; người dùng thật đã
 * trả lời ngược lại. Nay dùng chung `AppShell` như mọi màn khác — chỉ khác `wide`
 * để lưới danh mục + giỏ hàng không bị bó trong 1120px.
 */
export default function PosLayout({ children }: { children: React.ReactNode }) {
  return <AppShell wide>{children}</AppShell>;
}
