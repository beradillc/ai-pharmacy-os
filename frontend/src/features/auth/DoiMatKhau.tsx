"use client";

import { useState } from "react";

import { thongDiepLoi } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import { useAuthStore } from "./auth-store";
import { useChangePassword } from "./use-change-password";
import local from "./DoiMatKhau.module.css";

/** Độ dài tối thiểu — khớp `MIN_PASSWORD_LENGTH` của backend. Chặn ở đây chỉ để đỡ một lượt
 *  đi mạng chắc chắn bị từ chối; cưỡng chế thật vẫn ở máy chủ. */
const DAI_TOI_THIEU = 12;

/**
 * Màn đổi mật khẩu — **cửa chặn** khi tài khoản còn cờ `must_change_password` (lỗi C-01).
 *
 * 🔴 Vì sao là cửa chặn chứ không phải một mục trong Cài đặt: mật khẩu do người khác đặt thì
 * **không còn là mật khẩu của mình**. Người tạo tài khoản biết nó, và trong một quầy thuốc
 * thì "người tạo tài khoản" là người có toàn quyền trên mọi sổ sách. Để nó thành một mục tuỳ
 * chọn nghĩa là phần lớn người dùng sẽ không bao giờ đổi.
 *
 * Nhưng **không đăng xuất** người dùng: token hiện tại vẫn hợp lệ, và đá họ ra ngay sau khi
 * vừa làm đúng là một hình phạt không lý do.
 *
 * Đây cũng là chỗ người dùng **tự nguyện** đổi mật khẩu (từ Cài đặt) — cùng một biểu mẫu,
 * khác ở chỗ có nút Đóng hay không.
 *
 * 📌 Đặt ở `features/auth/` chứ không `components/`: nó **gọi API**, mà `components/*` là
 * tầng trình bày thuần (docs/ui/UI_ARCHITECTURE.md §2). Cổng eslint bắt được ngay lượt đầu —
 * tôi đã đặt sai chỗ.
 */
export function DoiMatKhau({ batBuoc, onXong }: { batBuoc: boolean; onXong?: () => void }) {
  const session = useAuthStore((s) => s.session);
  const doi = useChangePassword();
  const [cu, setCu] = useState("");
  const [moi, setMoi] = useState("");
  const [lai, setLai] = useState("");
  const [loi, setLoi] = useState<string | null>(null);
  const [xong, setXong] = useState(false);

  const dat =
    cu.trim() !== "" && moi.length >= DAI_TOI_THIEU && moi === lai && moi !== cu;

  return (
    <div className={local.khoi}>
      <h1 className={styles.title}>
        {batBuoc ? "Đổi mật khẩu trước khi bắt đầu" : "Đổi mật khẩu"}
      </h1>

      {batBuoc && (
        <p className={styles.subtitle}>
          Mật khẩu hiện tại do người khác đặt cho tài khoản này. Đổi sang mật khẩu chỉ mình
          biết rồi mới vào phần mềm — đây là tài khoản ký vào sổ bán thuốc, nên nó phải là của
          riêng mình.
        </p>
      )}

      {xong && !batBuoc && <p className={styles.success}>Đã đổi mật khẩu.</p>}

      <form
        className={local.form}
        onSubmit={(e) => {
          e.preventDefault();
          setLoi(null);
          doi.mutate(
            { current_password: cu, new_password: moi },
            {
              onSuccess: () => {
                setXong(true);
                setCu("");
                setMoi("");
                setLai("");
                onXong?.();
              },
              onError: (err) => setLoi(thongDiepLoi(err)),
            },
          );
        }}
      >
        <label className={local.o}>
          <span className={local.nhan}>Mật khẩu hiện tại</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="current-password"
            value={cu}
            onChange={(e) => setCu(e.target.value)}
            aria-label="Mật khẩu hiện tại"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Mật khẩu mới — ít nhất {DAI_TOI_THIEU} ký tự</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="new-password"
            value={moi}
            onChange={(e) => setMoi(e.target.value)}
            aria-label="Mật khẩu mới"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Gõ lại mật khẩu mới</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="new-password"
            value={lai}
            onChange={(e) => setLai(e.target.value)}
            aria-label="Gõ lại mật khẩu mới"
          />
        </label>

        {/* Nói ra ĐIỀU KIỆN CHƯA ĐẠT, không chỉ vô hiệu hoá nút. Một nút xám không giải
            thích là chỗ người dùng bấm ba lần rồi nghĩ phần mềm hỏng. */}
        {moi !== "" && moi.length < DAI_TOI_THIEU && (
          <p className={local.nhac}>Còn thiếu {DAI_TOI_THIEU - moi.length} ký tự.</p>
        )}
        {lai !== "" && moi !== lai && <p className={local.nhac}>Hai ô chưa khớp nhau.</p>}
        {moi !== "" && moi === cu && (
          <p className={local.nhac}>Mật khẩu mới phải khác mật khẩu cũ.</p>
        )}

        {loi && <p className={styles.error}>{loi}</p>}

        <div className={local.nut}>
          <button type="submit" className={styles.button} disabled={!dat || doi.isPending}>
            {doi.isPending ? "Đang đổi…" : "Đổi mật khẩu"}
          </button>
          {!batBuoc && onXong && (
            <button type="button" className={styles.ghost} onClick={onXong}>
              Đóng
            </button>
          )}
        </div>
      </form>

      {batBuoc && (
        <p className={local.nhac}>
          Đang đăng nhập bằng <strong>{session?.user_id.slice(0, 8)}</strong>. Quên mật khẩu
          hiện tại thì nhờ người quản trị đặt lại.
        </p>
      )}
    </div>
  );
}
