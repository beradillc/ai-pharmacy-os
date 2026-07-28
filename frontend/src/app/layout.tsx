import type { Metadata, Viewport } from "next";
import { Be_Vietnam_Pro, IBM_Plex_Mono } from "next/font/google";

import { QueryProvider } from "@/shared/query-provider";

import "./globals.css";

/**
 * Be Vietnam Pro được thiết kế CHO tiếng Việt — dấu không tụt về font thay thế,
 * vốn là rủi ro thật với một sản phẩm mà mọi nhãn đều có dấu. Nạp qua
 * `next/font/google`: tự host lúc build, runtime không gọi mạng.
 *
 * `subsets` phải có "vietnamese" — thiếu nó thì đúng phần chữ cần nhất bị rơi
 * ra ngoài bộ ký tự được nhúng.
 */
const sans = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-beras-sans",
  display: "swap",
});

/** Giá tiền / số lượng / mã lô — cần chữ số đều cột để so sánh bằng mắt. */
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-beras-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BERAS — Sổ Quản Lý Nhà Thuốc",
  description:
    "BERAS là sổ điện tử quản lý nhà thuốc chuẩn Cloud/SaaS thế hệ mới, tích hợp AI hỗ trợ chuyên sâu nghiệp vụ Dược và đảm bảo vận hành liên tục ngay cả khi mất kết nối Internet.",
};

/**
 * 🔴 Thiếu khai báo này suốt từ đầu dự án tới 2026-07-29 (audit UI PHASE 1).
 *
 * Next không tự chèn thẻ viewport. Không có nó, trình duyệt di động dựng trang ở
 * viewport ảo ~980px rồi thu nhỏ toàn bộ — nghĩa là **mọi media query
 * `width <= 720px` trong dự án chưa từng kích hoạt trên điện thoại thật**, và mọi
 * kết luận "đã responsive" trước hôm nay đều không có căn cứ.
 *
 * `maximumScale` KHÔNG đặt: khoá phóng to là chặn người mắt kém đọc chữ, và
 * WCAG 1.4.4 tính đó là lỗi. Màn POS có bị người dùng lỡ phóng to thì cũng chỉ
 * mất một cử chỉ để trả về.
 */
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // chừa chỗ cho thanh gạt iPhone — dùng với env(safe-area-inset-*)
  themeColor: "#1f3d2b", // = --beras-accent, màu thanh trạng thái trên Android
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
