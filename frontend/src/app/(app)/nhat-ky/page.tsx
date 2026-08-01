"use client";

import { useState } from "react";

import { AUDIT_PAGE_SIZE, useAuditLog } from "@/features/audit/use-audit-log";
import { useStaff } from "@/features/iam/use-staff";
import { formatTime } from "@/shared/format/number";
import { thongDiepLoi } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import { DOI_TUONG, NHAN, NHOM } from "./nhan-hanh-vi";
import local from "./page.module.css";

function homNay(): string {
  return new Date().toISOString().slice(0, 10);
}
function truocNgay(n: number): string {
  return new Date(Date.now() - n * 86400e3).toISOString().slice(0, 10);
}

/**
 * Màn **Nhật ký hoạt động** — đóng lỗi M-04 (UAT 2026-08-01).
 *
 * 🔴 Vì sao chủ quầy cần: khi có **chênh lệch tiền hoặc hàng**, câu hỏi đầu tiên luôn là
 * *"ai đã làm gì, lúc nào"*. Backend ghi đủ từ Sprint 7 — nhưng không có màn nào ⇒ dữ liệu
 * nằm đó mà không ai tra được.
 *
 * ⚠️ **Nói rõ giới hạn ngay trên màn** (lỗi M-05 còn mở): nhật ký ghi *đã xảy ra hành động
 * gì*, **chưa ghi giá trị cũ → mới**. Giấu giới hạn đó đi thì người dùng tin sổ này trả lời
 * được nhiều hơn thực tế — và họ chỉ phát hiện ra đúng lúc cần nó nhất.
 */
export default function NhatKyPage() {
  const [tuNgay, setTuNgay] = useState(truocNgay(7));
  const [denNgay, setDenNgay] = useState(homNay());
  const [hanhVi, setHanhVi] = useState("");
  const [trang, setTrang] = useState(0);

  const ds = useAuditLog({ tuNgay, denNgay, hanhVi: hanhVi || undefined, trang });
  // Trang 0 (50 người) đủ tra tên cho một quầy; tra không ra thì rơi về mã rút gọn bên dưới.
  // Hook đòi `iam.user.read` — người chỉ có `audit.dashboard.read` sẽ nhận 403 và thấy mã.
  const nhanVien = useStaff(0);
  const tenNguoi = new Map((nhanVien.data ?? []).map((u) => [u.id, u.full_name]));

  const rows = ds.data?.items ?? [];
  const tong = ds.data?.total ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Nhật ký hoạt động</h1>
          <p className={styles.subtitle}>
            Ai đã làm gì, lúc nào. Dòng nhật ký <strong>không sửa và không xoá được</strong> —
            kể cả bằng tài khoản quản trị.
          </p>
        </div>
      </div>

      <div className={styles.controls}>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Từ ngày</span>
          <input
            className={styles.input}
            type="date"
            value={tuNgay}
            onChange={(e) => {
              setTuNgay(e.target.value);
              setTrang(0);
            }}
            aria-label="Từ ngày"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Đến ngày</span>
          <input
            className={styles.input}
            type="date"
            value={denNgay}
            onChange={(e) => {
              setDenNgay(e.target.value);
              setTrang(0);
            }}
            aria-label="Đến ngày"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Loại hoạt động</span>
          <select
            className={styles.select}
            value={hanhVi}
            onChange={(e) => {
              setHanhVi(e.target.value);
              setTrang(0);
            }}
            aria-label="Loại hoạt động"
          >
            {NHOM.map((n) => (
              <option key={n.ma} value={n.ma}>
                {n.nhan}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* ⚠️ Giới hạn nói NGAY TRÊN MÀN, không giấu trong tài liệu. Người dùng tin sổ này trả
          lời được nhiều hơn thực tế thì họ chỉ phát hiện ra đúng lúc cần nó nhất. */}
      <p className={local.gioiHan}>
        ⚠️ Nhật ký ghi <strong>đã xảy ra hoạt động gì</strong>, chưa ghi{" "}
        <strong>giá trị cũ → giá trị mới</strong>. Muốn biết giá đổi từ bao nhiêu sang bao
        nhiêu, xem <em>Danh mục thuốc → Sửa giá → Biến động giá</em>.
      </p>

      {ds.isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}
      {ds.error && <p className={styles.error}>{thongDiepLoi(ds.error)}</p>}

      {!ds.isLoading && !ds.error && rows.length === 0 && (
        <p className={styles.empty}>
          Không có hoạt động nào trong khoảng ngày đã chọn. Thử nới rộng khoảng ngày, hoặc bỏ
          bộ lọc loại hoạt động.
        </p>
      )}

      {rows.length > 0 && (
        <>
          <p className={styles.subtitle}>
            {tong} hoạt động · đang xem {trang * AUDIT_PAGE_SIZE + 1}–
            {trang * AUDIT_PAGE_SIZE + rows.length}
          </p>
          <div className={styles.tableWrap}>
            <table className={`${styles.table} ${local.bangThe}`} data-testid="ds-nhat-ky">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Người thực hiện</th>
                  <th>Hoạt động</th>
                  <th>Đối tượng</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id}>
                    <td data-nhan="Thời gian" className={styles.mono}>
                      {formatTime(e.occurred_at)}
                    </td>
                    <td data-nhan="Người thực hiện">
                      {e.actor_user_id
                        ? // Không tra được tên thì hiện mã rút gọn, KHÔNG bỏ trống: một dòng
                          // nhật ký không có chủ thể là một dòng vô dụng.
                          (tenNguoi.get(e.actor_user_id) ?? `Mã ${e.actor_user_id.slice(0, 8)}`)
                        : "hệ thống"}
                    </td>
                    <td data-nhan="Hoạt động">{NHAN[e.action] ?? e.action}</td>
                    <td data-nhan="Đối tượng">
                      {DOI_TUONG[e.target_type] ?? e.target_type}
                      {e.target_id && (
                        <span className={local.ma}> · {e.target_id.slice(0, 8)}</span>
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
              disabled={ds.isLoading || rows.length < AUDIT_PAGE_SIZE}
            >
              Sau
            </button>
          </div>
        </>
      )}
    </div>
  );
}
