"use client";

import { useTheme } from "@/theme/ThemeProvider";
import { THEMES } from "@/theme/themes";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Cài đặt → Giao diện.
 *
 * Màn **mới thêm**, không sửa màn nào đang có. Hiện chỉ có một mục (chọn theme);
 * đặt sẵn khung "Giao diện / Hệ thống" để mục sau có chỗ vào mà không phải dựng
 * lại bố cục.
 *
 * Nút chọn là `radiogroup` thật (`role="radio"` + `aria-checked` + phím mũi tên
 * do trình duyệt lo qua `tabIndex`), không phải mấy cái thẻ bấm được — người dùng
 * bàn phím phải chọn được theme.
 */
export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Cài đặt</h1>
          <p className={styles.subtitle}>Tuỳ chọn hiển thị, lưu trên máy này</p>
        </div>
      </div>

      <section className={styles.panel}>
        <div className={local.section}>
          <h2 className={local.sectionTitle}>Giao diện</h2>
          <p className={local.sectionText}>
            Đổi có hiệu lực ngay, không cần tải lại trang. Lựa chọn lưu trên trình
            duyệt này — máy khác hoặc trình duyệt khác vẫn dùng mặc định.
          </p>

          <div className={local.options} role="radiogroup" aria-label="Chọn giao diện">
            {THEMES.map((t) => {
              const active = theme === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  tabIndex={active ? 0 : -1}
                  className={active ? local.optionActive : local.option}
                  onClick={() => setTheme(t.id)}
                >
                  <span className={local.swatch} aria-hidden>
                    {t.swatch.map((c) => (
                      <span key={c} className={local.chip} style={{ background: c }} />
                    ))}
                  </span>
                  <span className={local.optionBody}>
                    <span className={local.optionName}>
                      {t.name}
                      {/* Trạng thái chọn hiện bằng CHỮ + viền + chấm, không riêng
                          màu — cùng quy tắc a11y đang áp cho chip trạng thái. */}
                      {active && <span className={local.badge}>Đang dùng</span>}
                    </span>
                    <span className={local.optionDesc}>{t.description}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>
    </div>
  );
}
