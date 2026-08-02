"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { thongDiepLoi } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import {
  type ThongTinCoSo as ThongTinCoSoData,
  useLuuThongTinCoSo,
  useThongTinCoSo,
} from "./use-thong-tin-co-so";

/**
 * Khối **Thông tin cơ sở** trong Cài đặt — đóng lỗi M-02 (UAT 2026-08-01).
 *
 * 🔴 Đặt ở Cài đặt chứ không thành mục menu thứ 16: Chain đã yêu cầu gộp menu (lệnh ⑤⑥
 * ngày 01/08), và đây là thứ khai **một lần rồi thôi** — không phải việc hằng ngày. Cùng
 * chỗ với "Tài khoản của tôi" (M-03) vì cùng một câu hỏi: *tôi/cơ sở của tôi là ai*.
 *
 * ⚠️ **Nợ đã biết, nói ra chứ không giấu:** hoá đơn in ra **CHƯA** đọc bốn trường này — nó
 * vẫn lấy từ biến môi trường `APP__ORG__*`. Nối được đòi một read-port cross-module
 * (`sales` không được import `compliance`), là việc riêng chưa làm. Màn này nói thẳng điều
 * đó, vì một màn "Thông tin cơ sở" mà người dùng tưởng đã đổi được hoá đơn là đúng cái bẫy
 * *"thứ đang chạy tốt trả lời một câu hỏi khác"* (§7dg bài học 1).
 */
export function ThongTinCoSo() {
  const ds = useThongTinCoSo();
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  if (!quyen.has("compliance.config.read")) return null;

  return (
    <section className={styles.panel} data-testid="khoi-thong-tin-co-so">
      <div style={{ padding: "var(--space-3)" }}>
        <h2 className={styles.title} style={{ fontSize: "var(--text-lg)" }}>
          Thông tin cơ sở
        </h2>
        <p className={styles.subtitle}>
          Tên, địa chỉ và mã số trên{" "}
          <strong>giấy chứng nhận đủ điều kiện kinh doanh dược</strong>. Khai
          một lần, dùng cho báo cáo gửi cơ quan quản lý.
        </p>

        {/* Dòng này trước đây là một lời XIN LỖI: "hoá đơn in ra chưa dùng thông tin ở
            đây". Nợ N-1 đã đóng 02/08 — hoá đơn nay đọc thẳng bản khai này qua một cổng
            đọc cross-module. Giữ lại một dòng, nhưng đổi nội dung: người dùng cần biết
            việc mình vừa làm có hiệu lực tới đâu, và "tới đâu" nay là một câu khẳng
            định chứ không phải một câu cáo lỗi. */}
        <p className={styles.hint} style={{ marginTop: "var(--space-2)" }}>
          ✓ <strong>Hoá đơn in ra dùng thông tin ở đây</strong> — đổi tên hoặc
          địa chỉ tại màn này thì tờ hoá đơn tiếp theo in ra theo giá trị mới.
          Trường nào để trống thì hoá đơn bỏ hẳn dòng đó.
        </p>

        {ds.isLoading && (
          <div className={styles.skeleton} aria-label="Đang tải" />
        )}
        {ds.error && <p className={styles.error}>{thongDiepLoi(ds.error)}</p>}

        {!ds.isLoading && !ds.error && (
          /* 🔴 `key` đổi theo dữ liệu server ⇒ React **dựng lại** biểu mẫu với giá trị mới,
             thay vì gọi `setState` trong `useEffect` (eslint `react-hooks/set-state-in-effect`
             chặn — và chặn đúng: đồng bộ bằng effect sẽ giật mất chữ đang gõ mỗi lần
             react-query làm mới nền). Trạng thái ban đầu là **prop**, không phải hiệu ứng. */
          <BieuMau
            key={ds.data ? JSON.stringify(ds.data) : "chua-khai"}
            banDau={ds.data}
            suaDuoc={quyen.has("compliance.config.write")}
          />
        )}
      </div>
    </section>
  );
}

function BieuMau({
  banDau,
  suaDuoc,
}: {
  banDau: ThongTinCoSoData | null | undefined;
  suaDuoc: boolean;
}) {
  const luu = useLuuThongTinCoSo();
  const [form, setForm] = useState({
    ma_co_so_ban_le: banDau?.ma_co_so_ban_le ?? "",
    ma_co_so_ban_buon: banDau?.ma_co_so_ban_buon ?? "",
    ten_co_so: banDau?.ten_co_so ?? "",
    dia_chi: banDau?.dia_chi ?? "",
    dien_thoai: banDau?.dien_thoai ?? "",
    ma_so_thue: banDau?.ma_so_thue ?? "",
  });
  const [loi, setLoi] = useState<string | null>(null);
  const [daLuu, setDaLuu] = useState(false);

  const o = (
    khoa: keyof typeof form,
    nhan: string,
    goiY: string,
    kieu: "text" | "tel" = "text",
  ) => (
    <label className={styles.field}>
      <span className={styles.fieldLabel}>{nhan}</span>
      <input
        className={styles.input}
        type={kieu}
        value={form[khoa]}
        placeholder={goiY}
        disabled={!suaDuoc}
        onChange={(e) => {
          setForm((f) => ({ ...f, [khoa]: e.target.value }));
          setDaLuu(false);
        }}
        aria-label={nhan}
      />
    </label>
  );

  return (
    <>
      {banDau == null && (
        <p className={styles.empty}>
          Cơ sở chưa khai thông tin nào. Điền vào bên dưới rồi bấm Lưu — mã cơ
          sở bán lẻ do Cục Quản lý Dược cấp là trường bắt buộc.
        </p>
      )}

      <div className={styles.controls}>
        {o("ten_co_so", "Tên cơ sở", "Nhà thuốc Quầy thuốc 650")}
        {o("dia_chi", "Địa chỉ", "650 Nguyễn Trãi, P.11, Q.5")}
        {o("dien_thoai", "Điện thoại", "028 3822 1234", "tel")}
        {o("ma_so_thue", "Mã số thuế", "0312345678")}
        {o("ma_co_so_ban_le", "Mã cơ sở bán lẻ (Cục QLD cấp)", "01234")}
        {o(
          "ma_co_so_ban_buon",
          "Mã cơ sở bán buôn (nếu có)",
          "để trống nếu không có",
        )}
      </div>

      {suaDuoc && (
        <button
          type="button"
          className={styles.button}
          disabled={form.ma_co_so_ban_le.trim() === "" || luu.isPending}
          onClick={async () => {
            setLoi(null);
            setDaLuu(false);
            try {
              await luu.mutateAsync({
                ma_co_so_ban_le: form.ma_co_so_ban_le.trim(),
                // Chuỗi rỗng → `null`: backend phân biệt "chưa khai" với "khai rỗng", và
                // gửi `""` sẽ ghi một chuỗi rỗng vào chỗ lẽ ra phải là "không có".
                ma_co_so_ban_buon: form.ma_co_so_ban_buon.trim() || null,
                ten_co_so: form.ten_co_so.trim() || null,
                dia_chi: form.dia_chi.trim() || null,
                dien_thoai: form.dien_thoai.trim() || null,
                ma_so_thue: form.ma_so_thue.trim() || null,
              });
              setDaLuu(true);
            } catch (err) {
              setLoi(thongDiepLoi(err));
            }
          }}
        >
          {luu.isPending ? "Đang lưu…" : "Lưu thông tin cơ sở"}
        </button>
      )}
      {!suaDuoc && (
        <p className={styles.hint}>
          Bạn chỉ có quyền xem. Sửa thông tin cơ sở cần quyền quản trị chuỗi.
        </p>
      )}
      {loi && <p className={styles.error}>{loi}</p>}
      {daLuu && <p className={styles.hint}>✓ Đã lưu thông tin cơ sở.</p>}
    </>
  );
}
