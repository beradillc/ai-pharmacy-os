"use client";

import { useState } from "react";

import { useCustomers } from "@/features/crm/use-customers";
import { LOC_TRANG_THAI, NGUON_DON, TRANG_THAI_DON } from "@/features/prescription/nhan-don-thuoc";
import { RX_PAGE_SIZE, useRxSearch } from "@/features/prescription/use-rx-search";
import { thongDiepLoi } from "@/shared/api/errors";
import { formatTime } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

function homNay(): string {
  return new Date().toISOString().slice(0, 10);
}
function truocNgay(n: number): string {
  return new Date(Date.now() - n * 86400e3).toISOString().slice(0, 10);
}

/**
 * Màn **Đơn thuốc** — tra cứu theo khách / ngày / trạng thái. Đóng lỗi M-08 (UAT 01/08).
 *
 * 🔴 Vì sao *Cài đặt → Lưu trữ* không thay được màn này: Lưu trữ lọc `image_data IS NOT
 * NULL` — chỉ đơn **đã chụp ảnh**. Khi thanh tra hỏi *"đơn thuốc của khách X"*, một đơn
 * nhập tay không ảnh **vẫn là một đơn thật** và biến mất khỏi Lưu trữ mà không báo gì.
 * Hai màn trả lời hai câu hỏi khác nhau: Lưu trữ là *chứng từ ảnh*, đây là *lịch sử đơn*.
 */
export default function DonThuocPage() {
  const [khachHang, setKhachHang] = useState("");
  const [tuNgay, setTuNgay] = useState(truocNgay(30));
  const [denNgay, setDenNgay] = useState(homNay());
  const [trangThai, setTrangThai] = useState("");
  const [trang, setTrang] = useState(0);

  const ds = useRxSearch({
    khachHang: khachHang || undefined,
    tuNgay,
    denNgay,
    trangThai: trangThai || undefined,
    trang,
  });
  // Trang 0 đủ tra tên cho một quầy. Không có `crm.read` ⇒ hook lỗi, và cột khách rơi về
  // mã rút gọn — màn vẫn dùng được, chỉ kém dễ đọc.
  const khach = useCustomers(0);
  const tenKhach = new Map((khach.data ?? []).map((k) => [k.id, k.full_name]));

  const rows = ds.data ?? [];

  function doiLoc(dat: () => void) {
    dat();
    setTrang(0);
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Đơn thuốc</h1>
          <p className={styles.subtitle}>
            Lịch sử đơn thuốc của chi nhánh. Gồm <strong>cả đơn chưa chụp ảnh</strong> —
            khác <em>Cài đặt → Lưu trữ</em>, nơi chỉ có đơn đã có ảnh.
          </p>
        </div>
      </div>

      <div className={styles.controls}>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Khách hàng</span>
          <select
            className={styles.select}
            value={khachHang}
            onChange={(e) => doiLoc(() => setKhachHang(e.target.value))}
            aria-label="Khách hàng"
          >
            <option value="">Tất cả khách</option>
            {(khach.data ?? []).map((k) => (
              <option key={k.id} value={k.id}>
                {k.full_name}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Từ ngày</span>
          <input
            className={styles.input}
            type="date"
            value={tuNgay}
            onChange={(e) => doiLoc(() => setTuNgay(e.target.value))}
            aria-label="Từ ngày"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Đến ngày</span>
          <input
            className={styles.input}
            type="date"
            value={denNgay}
            onChange={(e) => doiLoc(() => setDenNgay(e.target.value))}
            aria-label="Đến ngày"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Trạng thái</span>
          <select
            className={styles.select}
            value={trangThai}
            onChange={(e) => doiLoc(() => setTrangThai(e.target.value))}
            aria-label="Trạng thái"
          >
            {LOC_TRANG_THAI.map((t) => (
              <option key={t.ma} value={t.ma}>
                {t.nhan}
              </option>
            ))}
          </select>
        </label>
      </div>

      {ds.isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}
      {ds.error && <p className={styles.error}>{thongDiepLoi(ds.error)}</p>}

      {!ds.isLoading && !ds.error && rows.length === 0 && (
        <p className={styles.empty}>
          Không có đơn thuốc nào trong khoảng ngày đã chọn. Nới rộng khoảng ngày, hoặc bỏ bộ
          lọc khách hàng — đơn thuốc chỉ sinh ra khi bán thuốc kê đơn (ETC).
        </p>
      )}

      {rows.length > 0 && (
        <>
          <p className={styles.subtitle}>
            {rows.length} đơn · trang {trang + 1}
          </p>
          <div className={styles.tableWrap}>
            <table className={`${styles.table} ${local.bangThe}`} data-testid="ds-don-thuoc">
              <thead>
                <tr>
                  <th>Ngày lập</th>
                  <th>Khách hàng</th>
                  <th>Bác sĩ kê đơn</th>
                  <th>Trạng thái</th>
                  <th>Nguồn</th>
                  <th>Ảnh đơn</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.id}>
                    <td data-nhan="Ngày lập" className={styles.mono}>
                      {formatTime(d.created_at)}
                    </td>
                    <td data-nhan="Khách hàng">
                      {d.customer_id
                        ? (tenKhach.get(d.customer_id) ?? `Mã ${d.customer_id.slice(0, 8)}`)
                        : "khách lẻ"}
                    </td>
                    <td data-nhan="Bác sĩ kê đơn">{d.doctor_name}</td>
                    <td data-nhan="Trạng thái">{TRANG_THAI_DON[d.status] ?? d.status}</td>
                    <td data-nhan="Nguồn">{NGUON_DON[d.source] ?? d.source}</td>
                    <td data-nhan="Ảnh đơn">
                      {d.has_image ? (
                        "có"
                      ) : (
                        // Nói rõ *chưa chụp*, không để trống: trống đọc như dữ liệu lỗi,
                        // còn "chưa chụp" là một sự thật nghiệp vụ hợp lệ.
                        <span className={styles.muted}>chưa chụp</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className={styles.pager}>
            <span>Trang {trang + 1}</span>
            <button
              type="button"
              className={styles.ghost}
              onClick={() => setTrang((t) => Math.max(0, t - 1))}
              disabled={trang === 0 || ds.isLoading}
            >
              Trước
            </button>
            <button
              type="button"
              className={styles.ghost}
              onClick={() => setTrang((t) => t + 1)}
              disabled={ds.isLoading || rows.length < RX_PAGE_SIZE}
            >
              Sau
            </button>
          </div>
        </>
      )}
    </div>
  );
}
