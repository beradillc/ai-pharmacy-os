import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Chỉ copy đúng file cần cho production vào `.next/standalone` (kèm
   * `server.js` tối giản, không cần `next start`/`node_modules` đầy đủ trong
   * image) — Dockerfile sản xuất (`infra/docker/frontend.Dockerfile`,
   * chuẩn bị deploy AlmaLinux 2026-08-04) dựa vào đúng thư mục này.
   */
  output: "standalone",

  /**
   * Tắt huy hiệu dev của Next ở góc dưới trái.
   *
   * 🔴 Không phải chuyện thẩm mỹ: trên khổ điện thoại 390px, huy hiệu đó **đè lên
   * ô đầu tiên của thanh điều hướng dưới** ("Tổng quan") — thấy rõ trên ảnh chụp
   * màn hình 29/07. Người thử app trên điện thoại sẽ bấm trúng huy hiệu thay vì
   * bấm nút, rồi kết luận là nút hỏng.
   *
   * Chỉ ảnh hưởng bản `next dev`; bản build sản phẩm vốn không có huy hiệu này.
   */
  devIndicators: false,

  /**
   * 🔴 Nguồn được phép gọi máy chủ dev.
   *
   * Next **chặn mọi request chéo nguồn tới tài nguyên dev** (mặc định chỉ cho
   * `localhost`). Mở app qua LAN IP thì HTML server-render vẫn về, nhưng thời
   * chạy client + HMR bị chặn ⇒ **React KHÔNG BAO GIỜ hydrate**.
   *
   * Hệ quả đúng như Chain báo 29/07: *"Safari iPhone mở lên khoảng trắng"*. Và
   * đo ra thì **không phải lỗi Safari** — Firefox, WebKit, mọi màn cần trạng thái
   * client đều trắng y hệt. Màn đăng nhập hiện được chỉ vì nó là HTML server
   * render; màn trong ứng dụng server render ra `null` (chưa có phiên) rồi trông
   * chờ client tiếp quản — mà client không bao giờ chạy.
   *
   * Danh sách lấy từ biến môi trường `NEXT_PUBLIC_LAN_ORIGIN` do `scripts/lan-dev.sh`
   * truyền vào, vì IP LAN đổi mỗi khi router cấp lại. Ghim cứng một IP vào tệp
   * này là tự đặt một quả bom hẹn giờ cho lần đổi mạng tiếp theo.
   */
  allowedDevOrigins: [
    ...(process.env.NEXT_PUBLIC_LAN_ORIGIN ? [process.env.NEXT_PUBLIC_LAN_ORIGIN] : []),
    // Dải mạng nhà thường gặp — để mở app từ điện thoại vẫn chạy kể cả khi khởi
    // động bằng `npm run dev` trực tiếp thay vì qua script.
    "192.168.0.0/16",
    "10.0.0.0/8",
    "172.16.0.0/12",
  ],
};

export default nextConfig;
