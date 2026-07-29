import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  /**
   * 🔴 RANH GIỚI TẦNG — cưỡng chế bằng MÁY, không bằng tài liệu.
   *
   * `docs/ui/UI_ARCHITECTURE.md` §2 đặt luật: `components/*` là tầng TRÌNH BÀY
   * thuần — nhận dữ liệu qua props, **không** tự gọi API, **không** biết tới
   * `features/*`. Luật đó tới hôm nay chỉ nằm trong tài liệu, mà tài liệu thì
   * không chặn được ai.
   *
   * Backend giữ đúng luật tương đương bằng `import-linter` (18 contract, chạy ở
   * mọi commit). Đây là bản frontend của nó.
   *
   * Vì sao quan trọng: một component lỡ `import { useDashboard }` là nó hết tái
   * dùng được, và bắt đầu kéo nghiệp vụ lên tầng giao diện — đúng thứ yêu cầu UI
   * cấm ("No business logic moved into UI"). Lỗi đó không làm build đỏ, không làm
   * test đỏ, và chỉ lộ ra khi đã muộn.
   *
   * NavIcon là ngoại lệ có tên: nó đọc KIỂU `NavIconName` từ `shared/nav`, không
   * đọc dữ liệu. Cấm kiểu thì phải nhân bản định nghĩa, tệ hơn.
   */
  {
    files: ["src/components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/features/*", "**/features/*"],
              message:
                "components/* là tầng trình bày thuần — nhận dữ liệu qua props, không import features/*. Xem docs/ui/UI_ARCHITECTURE.md §2.",
            },
            {
              group: ["@/shared/api/*", "**/shared/api/*"],
              message:
                "components/* không được tự gọi API. Truyền dữ liệu xuống bằng props. Xem docs/ui/UI_ARCHITECTURE.md §2.",
            },
          ],
        },
      ],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
