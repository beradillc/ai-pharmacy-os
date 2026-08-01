"use client";

import { useState } from "react";

import { AUDIT_PAGE_SIZE, useAuditLog } from "@/features/audit/use-audit-log";
import { useStaff } from "@/features/iam/use-staff";
import { formatQty, formatTime } from "@/shared/format/number";
import { thongDiepLoi } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import { nhanThietBi, tenNguoiThucHien, thayDoiGiaTri } from "./chi-tiet-thay-doi";
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
 * **M-05 · M-06 đóng ngày 2026-08-01:** hai cột **Thay đổi** (giá trị cũ → mới) và **Thiết
 * bị** nay đọc thẳng từ `context` của dòng nhật ký. Dòng cảnh báo giới hạn trước đây đã gỡ
 * — giữ lại một cảnh báo đã hết đúng còn tệ hơn không có, vì nó dạy người đọc bỏ qua cảnh
 * báo trên màn này.
 *
 * ⚠️ Vẫn còn một giới hạn **thật**, và vẫn nói ra: không phải hành vi nào cũng ghi được cặp
 * cũ → mới; chỗ nào chưa ghi thì cột để trống chứ **không đoán**.
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

      {/* ⚠️ Giới hạn CÒN THẬT nói NGAY TRÊN MÀN, không giấu trong tài liệu — nhưng chỉ nói
          phần còn đúng. Cảnh báo cũ ("chưa ghi giá trị cũ → mới") đã gỡ khi M-05 đóng. */}
      <p className={local.gioiHan}>
        ⚠️ Cột <strong>Thiết bị</strong> đọc từ chuỗi máy khách tự khai, nên nó là{" "}
        <strong>manh mối, không phải bằng chứng</strong> — một máy cố tình có thể khai khác
        đi. Cột <strong>Thay đổi</strong> chỉ hiện với hoạt động có ghi được cả giá trị cũ
        lẫn mới; chỗ trống nghĩa là <em>chưa ghi</em>, không phải <em>không đổi</em>.
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
                  <th>Thay đổi</th>
                  <th>Thiết bị</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.id}>
                    <td data-nhan="Thời gian" className={styles.mono}>
                      {formatTime(e.occurred_at)}
                    </td>
                    <td data-nhan="Người thực hiện">
                      {tenNguoiThucHien(e.actor_user_id, (id) => tenNguoi.get(id))}
                    </td>
                    <td data-nhan="Hoạt động">{NHAN[e.action] ?? e.action}</td>
                    <td data-nhan="Đối tượng">
                      {DOI_TUONG[e.target_type] ?? e.target_type}
                      {e.target_id && (
                        <span className={local.ma}> · {e.target_id.slice(0, 8)}</span>
                      )}
                    </td>
                    {/* Ô RỖNG THÌ KHÔNG DỰNG Ô. Ở khổ điện thoại bảng thành thẻ và mỗi `td`
                        tự in nhãn của nó qua `::before`, nên một ô rỗng vẫn chiếm một dòng
                        chỉ để hiện chữ "Thay đổi" rồi bỏ trống — nhân với 50 dòng là nửa
                        màn hình nhãn không nội dung. Ảnh chụp 390px thấy điều này; không
                        phép đo nào trong cổng thấy. */}
                    {(() => {
                      const doi = thayDoiGiaTri(e.context);
                      return doi.length === 0 ? (
                        <td className={local.oRong} />
                      ) : (
                        <td data-nhan="Thay đổi">
                          {doi.map((t) => (
                            <span key={t.truong} className={local.thayDoi}>
                              <span className={local.truong}>{t.nhan}</span>
                              <span className={local.cu}>{formatQty(t.cu)}</span>
                              <span aria-hidden="true">→</span>
                              <span className={local.moi}>{formatQty(t.moi)}</span>
                            </span>
                          ))}
                        </td>
                      );
                    })()}
                    {(() => {
                      const may = nhanThietBi(e.context.user_agent);
                      const ip = e.context.client_ip;
                      return !may && !ip ? (
                        <td className={local.oRong} />
                      ) : (
                        <td data-nhan="Thiết bị">
                          {/* `title` giữ chuỗi thô để soát khi cần, nhưng nhãn ngắn mới là
                              thứ NHÌN THẤY được trên khổ 390px (kỷ luật #21). */}
                          {may && (
                            <span
                              className={local.thietBi}
                              title={e.context.user_agent ?? undefined}
                            >
                              {may}
                            </span>
                          )}
                          {/* Dấu `·` chỉ là dấu NGĂN, nên chỉ tồn tại khi có hai thứ để
                              ngăn. Ảnh chụp bắt được một cột đầy dòng "· 192.168.1.10"
                              mở đầu bằng một dấu chấm mồ côi. */}
                          {ip && (
                            <span className={local.ma}>
                              {may ? " · " : ""}
                              {ip}
                            </span>
                          )}
                        </td>
                      );
                    })()}
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
