import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Cùng bí danh với `tsconfig.json` — test import y hệt cách mã sản phẩm import.
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    /**
     * 🔴 GHIM MÚI GIỜ.
     *
     * Nhiều tính chất ở đây nói về "hôm nay theo giờ Việt Nam" — nếu để test chạy
     * theo múi giờ của máy thì nó xanh trên máy chạy UTC và đỏ trên máy ở Việt
     * Nam, tức là **đo môi trường chứ không đo mã**. Đúng loại test tung đồng xu
     * mà kỷ luật #14 sinh ra để chặn.
     */
    env: { TZ: "Asia/Ho_Chi_Minh" },
  },
});
