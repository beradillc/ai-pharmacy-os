import type { Metadata } from "next";

import { QueryProvider } from "@/shared/query-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "BERAS — Sổ Quản Lý Nhà Thuốc",
  description:
    "BERAS là sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới, tích hợp AI hỗ trợ chuyên sâu nghiệp vụ Dược và đảm bảo vận hành liên tục ngay cả khi mất kết nối Internet.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
