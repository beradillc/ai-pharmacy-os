/**
 * Danh mục giao diện của BERAS.
 *
 * Chỉ khai báo **danh tính** của từng theme (mã, tên hiển thị, mô tả). Giá trị
 * màu nằm ở CSS (`src/theme/warm.css`), không ở đây — vì đổi theme phải chỉ là
 * đổi một thuộc tính trên thẻ `<html>`, không phải nạp lại một cây React mang
 * theo hàng chục giá trị màu.
 */

export const THEMES = [
  {
    id: "classic",
    name: "BERAS Classic",
    description: "Giao diện gốc — xanh rừng, nền giấy tái sinh.",
    /** Ba màu xem trước trên nút chọn. */
    swatch: ["#1f3d2b", "#5b8c51", "#edefe7"],
  },
  {
    id: "warm",
    name: "BERAS Warm",
    description: "Tông ấm — coral, hổ phách, nền trắng ngà.",
    swatch: ["#C6413A", "#B8730B", "#FDF8F5"],
  },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeId = "classic";

/** Khoá localStorage. Đổi khoá = mọi người dùng quay về Classic, nên đừng đổi. */
export const THEME_STORAGE_KEY = "beras.theme";

export function isThemeId(value: unknown): value is ThemeId {
  return typeof value === "string" && THEMES.some((t) => t.id === value);
}
