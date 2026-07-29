import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
};

export default nextConfig;
