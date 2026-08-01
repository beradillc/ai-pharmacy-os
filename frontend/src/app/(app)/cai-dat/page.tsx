"use client";

import { useState } from "react";

import Link from "next/link";

import { useTheme } from "@/theme/ThemeProvider";
import { THEMES } from "@/theme/themes";
import { ThongTinCoSo } from "@/features/compliance/ThongTinCoSo";
import { DoiMatKhau } from "@/features/auth/DoiMatKhau";
import { useMe } from "@/features/auth/use-me";
import { useAuthStore } from "@/features/auth/auth-store";
import { formatTime } from "@/shared/format/number";
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
  const [moDoiMatKhau, setMoDoiMatKhau] = useState(false);
  const { theme, setTheme } = useTheme();
  const me = useMe();
  const session = useAuthStore((s) => s.session);
  const chiNhanh = session?.accessible_branches.find((b) => b.id === session.branch_id);

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Cài đặt</h1>
          <p className={styles.subtitle}>Tuỳ chọn hiển thị, lưu trên máy này</p>
        </div>
      </div>

      {/* Tài khoản của tôi — đóng lỗi M-03 (UAT 01/08).

          🔴 Đặt ở ĐÂY chứ không thành mục menu thứ 15: Chain đã yêu cầu gộp menu (lệnh
          ⑤⑥ ngày 01/08), và người dùng đi tìm "tên tôi là gì, tôi đang ở chi nhánh nào"
          ở Cài đặt chứ không ở một mục riêng. Nó cũng nằm ngay trên khối Đổi mật khẩu —
          đúng thứ tự người ta cần: xem mình là ai, rồi đổi mật khẩu của mình. */}
      <section className={styles.panel}>
        <div className={local.section}>
          <h2 className={local.sectionTitle}>Tài khoản của tôi</h2>
          {me.isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}
          {me.error && (
            <p className={styles.error}>Không tải được thông tin tài khoản.</p>
          )}
          {me.data && (
            <dl className={local.hoSo} data-testid="ho-so">
              <div className={local.dong}>
                <dt className={local.nhan}>Họ tên</dt>
                <dd className={local.giaTri}>{me.data.full_name}</dd>
              </div>
              <div className={local.dong}>
                <dt className={local.nhan}>Email đăng nhập</dt>
                <dd className={local.giaTri}>{me.data.email}</dd>
              </div>
              <div className={local.dong}>
                <dt className={local.nhan}>Chi nhánh</dt>
                {/* Tên chi nhánh lấy từ phiên đã ký, không phải từ một lời gọi khác: đây
                    là chi nhánh đang có hiệu lực trong token, đúng thứ mọi thao tác ghi
                    vào. Đổi chi nhánh bằng `POST /auth/switch-branch`, không bằng màn này. */}
                <dd className={local.giaTri}>{chiNhanh ? chiNhanh.name : "—"}</dd>
              </div>
              <div className={local.dong}>
                <dt className={local.nhan}>Đăng nhập lần trước</dt>
                <dd className={local.giaTri}>
                  {me.data.last_login_at ? formatTime(me.data.last_login_at) : "lần đầu"}
                </dd>
              </div>
            </dl>
          )}
          <p className={local.sectionText}>
            Sai tên? Chỉ người quản lý sửa được, ở màn <strong>Nhân viên</strong> — tên trên
            tài khoản đi vào sổ bán thuốc nên không tự sửa được.
          </p>
        </div>
      </section>

      {/* Thông tin cơ sở — đóng lỗi M-02 (UAT 01/08). Đặt NGAY SAU "Tài khoản của tôi"
          vì cùng trả lời một câu: *tôi / cơ sở của tôi là ai*. */}
      <ThongTinCoSo />

      {/* Đổi mật khẩu — lối vào TỰ NGUYỆN. Cửa chặn bắt buộc nằm ở `AppShell` khi tài khoản
          còn cờ `must_change_password`; ở đây là chỗ đổi bất cứ lúc nào sau đó. */}
      <section className={styles.panel}>
        <div className={local.section}>
          <h2 className={local.sectionTitle}>Mật khẩu</h2>
          <p className={local.sectionText}>
            Đổi mật khẩu của tài khoản đang đăng nhập. Nên đổi ngay khi nghi có người khác
            biết — tài khoản này ký vào sổ bán thuốc.
          </p>
          {moDoiMatKhau ? (
            <DoiMatKhau batBuoc={false} onXong={() => setMoDoiMatKhau(false)} />
          ) : (
            <button
              type="button"
              className={styles.button}
              onClick={() => setMoDoiMatKhau(true)}
            >
              Đổi mật khẩu
            </button>
          )}
        </div>
      </section>

      <section className={styles.panel}>
        <div className={local.section}>
          <h2 className={local.sectionTitle}>Lưu trữ</h2>
          <p className={local.sectionText}>
            Ảnh đơn thuốc đã chụp ở quầy. Dữ liệu hiện theo phân quyền — chủ chuỗi xem
            được toàn bộ chi nhánh, dược sĩ chi nhánh chỉ xem chi nhánh mình.
          </p>
          <Link href="/cai-dat/luu-tru" className={styles.button}>
            Mở Lưu trữ
          </Link>
        </div>
      </section>

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
