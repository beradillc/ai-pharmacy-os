"use client";

import { useState } from "react";

import { DetailDialog } from "@/components/overlay/DetailDialog";
import { useAuthStore } from "@/features/auth/auth-store";
import { useCreateSupplier, useSuppliers } from "@/features/procurement/use-suppliers";
import { ApiError, thongDiepLoi } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import { TabManGop } from "@/components/layout/TabManGop";

import local from "./page.module.css";

const TAB_MUA = [
  {
    href: "/don-mua-hang",
    nhan: "Đơn mua hàng",
    moTa: "Đặt hàng từ nhà cung cấp, theo dõi tới lúc nhận đủ.",
  },
  {
    href: "/nha-cung-cap",
    nhan: "Nhà cung cấp",
    moTa: "Nơi quầy nhập hàng về. Phải có ít nhất một thì mới tạo được đơn mua.",
  },
] as const;

/**
 * Màn **Nhà cung cấp** — đóng lỗi M-01 (UAT 2026-08-01).
 *
 * 🔴 Vì sao đây không phải một màn "thêm cho đủ": màn **Đơn mua hàng đã tồn tại và chạy
 * được**, nhưng dùng không được — không tạo được đơn mua khi chưa có nhà cung cấp nào, và
 * không có đường nào tạo nhà cung cấp. Một màn hoàn chỉnh bị khoá bởi một màn không tồn tại
 * là loại thiếu sót **khó nhìn ra từ phía backend**, vì ở đó cả hai đều "đã xong".
 *
 * Backend `/suppliers` có từ Sprint 8 cùng test — thuần nối dây.
 */
export default function NhaCungCapPage() {
  const ds = useSuppliers();
  const tao = useCreateSupplier();
  const [dangThem, setDangThem] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);

  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  /** `procurement.supplier.create` là quyền **cấp chuỗi** — thêm một nhà cung cấp là quyết
   *  định mua hàng, không phải việc của người đứng quầy. */
  const coQuyenThem = quyen.has("procurement.supplier.create");

  const rows = ds.data ?? [];

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Nhà cung cấp</h1>
          <p className={styles.subtitle}>
            Nơi nhập hàng về. Phải có ít nhất một nhà cung cấp thì mới tạo được{" "}
            <strong>Đơn mua hàng</strong>.
          </p>
        </div>
        {coQuyenThem && (
          <button type="button" className={styles.button} onClick={() => setDangThem(true)}>
            + Thêm nhà cung cấp
          </button>
        )}
      </div>
      <TabManGop tabs={TAB_MUA} />

      {ds.isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}

      {ds.error && (
        <p className={styles.error}>
          {ds.error instanceof ApiError ? ds.error.problem.detail : "Không tải được danh sách."}
        </p>
      )}

      {/* 🔴 Trạng thái rỗng nói ra HỆ QUẢ, không chỉ nói "chưa có gì" — bài học U-05: người
          dùng lần đầu không phân biệt được *chưa có dữ liệu* với *phần mềm lỗi*, và một câu
          nói rõ việc tiếp theo cần làm thì đắt hơn một câu thông báo. */}
      {!ds.isLoading && !ds.error && rows.length === 0 && (
        <p className={styles.empty}>
          Chưa có nhà cung cấp nào. Thêm nơi quầy hay nhập hàng — sau đó mới tạo được đơn mua
          hàng và nhận hàng theo đơn.
        </p>
      )}

      {rows.length > 0 && (
        <div className={styles.tableWrap}>
          <table className={`${styles.table} ${local.bangThe}`} data-testid="ds-ncc">
            <thead>
              <tr>
                <th>Nhà cung cấp</th>
                <th>Liên hệ</th>
                <th>Điện thoại</th>
                <th>Mã số thuế</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td data-nhan="Nhà cung cấp">
                    <div>{s.name}</div>
                    {s.address && <div className={local.phu}>{s.address}</div>}
                  </td>
                  <td data-nhan="Liên hệ">{s.contact_name ?? "—"}</td>
                  <td data-nhan="Điện thoại" className={styles.mono}>
                    {s.phone ?? "—"}
                  </td>
                  <td data-nhan="Mã số thuế" className={styles.mono}>
                    {s.tax_code ?? "—"}
                  </td>
                  <td data-nhan="Trạng thái">
                    {s.is_active ? "Đang dùng" : <span className={styles.muted}>Đã ngừng</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dangThem && (
        <ThemNhaCungCap
          onClose={() => {
            setDangThem(false);
            setLoi(null);
          }}
          onLuu={(body) => {
            setLoi(null);
            tao.mutate(body, {
              onSuccess: () => setDangThem(false),
              onError: (e) => setLoi(thongDiepLoi(e)),
            });
          }}
          dangLuu={tao.isPending}
          loi={loi}
        />
      )}
    </div>
  );
}

function ThemNhaCungCap({
  onClose,
  onLuu,
  dangLuu,
  loi,
}: {
  onClose: () => void;
  onLuu: (b: {
    name: string;
    tax_code: string | null;
    contact_name: string | null;
    phone: string | null;
    address: string | null;
  }) => void;
  dangLuu: boolean;
  loi: string | null;
}) {
  const [ten, setTen] = useState("");
  const [mst, setMst] = useState("");
  const [lienHe, setLienHe] = useState("");
  const [dt, setDt] = useState("");
  const [diaChi, setDiaChi] = useState("");

  return (
    <DetailDialog open title="Thêm nhà cung cấp" onClose={onClose}>
      <form
        className={local.form}
        onSubmit={(e) => {
          e.preventDefault();
          onLuu({
            name: ten.trim(),
            // Chuỗi rỗng ≠ "không có". Gửi `null` để backend lưu đúng *chưa biết* thay vì
            // một chuỗi rỗng — về sau lọc "nhà cung cấp chưa có mã số thuế" mới đúng.
            tax_code: mst.trim() || null,
            contact_name: lienHe.trim() || null,
            phone: dt.trim() || null,
            address: diaChi.trim() || null,
          });
        }}
      >
        <label className={local.o}>
          <span className={local.nhan}>Tên nhà cung cấp *</span>
          <input
            className={styles.input}
            value={ten}
            onChange={(e) => setTen(e.target.value)}
            aria-label="Tên nhà cung cấp"
            maxLength={255}
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Người liên hệ</span>
          <input
            className={styles.input}
            value={lienHe}
            onChange={(e) => setLienHe(e.target.value)}
            aria-label="Người liên hệ"
            maxLength={200}
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Điện thoại</span>
          <input
            className={styles.input}
            inputMode="tel"
            value={dt}
            onChange={(e) => setDt(e.target.value)}
            aria-label="Điện thoại nhà cung cấp"
            maxLength={32}
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Mã số thuế</span>
          <input
            className={styles.input}
            value={mst}
            onChange={(e) => setMst(e.target.value)}
            aria-label="Mã số thuế"
            maxLength={32}
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Địa chỉ</span>
          <input
            className={styles.input}
            value={diaChi}
            onChange={(e) => setDiaChi(e.target.value)}
            aria-label="Địa chỉ nhà cung cấp"
          />
        </label>

        {loi && <p className={styles.error}>{loi}</p>}

        <button type="submit" className={styles.button} disabled={ten.trim() === "" || dangLuu}>
          {dangLuu ? "Đang lưu…" : "Lưu nhà cung cấp"}
        </button>
      </form>
    </DetailDialog>
  );
}
