"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import {
  usePrescriptionArchive,
  usePrescriptionImage,
} from "@/features/prescription/use-archive";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Cài đặt → **Lưu trữ** (Chain giao 2026-07-31).
 *
 * Nơi tra lại chứng từ đã lưu. Hôm nay chỉ có **ảnh đơn thuốc**; bố cục đặt sẵn theo
 * "loại chứng từ" để loại sau có chỗ vào mà không phải dựng lại màn.
 *
 * 🔴 Ba điều màn này **không** làm, mỗi điều một lý do:
 *
 * 1. **Không gửi `branch_id` lên máy chủ.** Phạm vi chi nhánh do máy chủ quyết từ quyền
 *    `archive.read.chain`. Cho màn hình chọn chi nhánh là mở một đường để máy khách sửa
 *    tay đòi xem chi nhánh khác.
 * 2. **Không tải sẵn ảnh cho cả danh sách.** Mỗi lượt mở ảnh ghi một dòng audit
 *    `RX_IMAGE_VIEWED`; tải sẵn sẽ biến sổ audit thành vô nghĩa — ai mở màn cũng thành
 *    người đã xem mọi ảnh của bệnh nhân.
 * 3. **Không hiện chẩn đoán trong danh sách.** Nó nằm trong ảnh, và ảnh thì phải bấm mở.
 */
export default function ArchivePage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const xemDuocAnh = quyen.has("rx.image.read");
  const toanChuoi = quyen.has("archive.read.chain");

  const [dangMo, setDangMo] = useState<string | null>(null);
  const ds = usePrescriptionArchive();
  const anh = usePrescriptionImage(dangMo);

  if (!xemDuocAnh) {
    return (
      <div className={styles.page}>
        <div className={styles.head}>
          <div>
            <h1 className={styles.title}>Lưu trữ</h1>
          </div>
        </div>
        <p className={styles.hint}>
          Bạn không có quyền xem ảnh đơn thuốc. Ảnh đơn mang chẩn đoán của khách nên chỉ
          dược sĩ và cấp chuỗi mở được.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Lưu trữ</h1>
          <p className={styles.subtitle}>
            Ảnh đơn thuốc đã chụp ở quầy.{" "}
            {toanChuoi ? (
              <strong>Đang xem toàn bộ chi nhánh.</strong>
            ) : (
              "Chỉ hiện đơn của chi nhánh đang đăng nhập."
            )}
          </p>
        </div>
      </div>

      <p className={local.canhBao}>
        🔒 Ảnh đơn mang <strong>chẩn đoán của khách</strong>. Mỗi lần bấm xem đều được ghi
        vào sổ audit — ai xem, đơn nào, lúc nào. <strong>Người chốt đơn</strong> chịu trách
        nhiệm lưu đơn thuốc; hệ thống ghi lại tên họ ở cột bên dưới.
      </p>

      {ds.isLoading ? (
        <p className={styles.hint}>Đang tải…</p>
      ) : (ds.data ?? []).length === 0 ? (
        <p className={styles.hint}>Chưa có ảnh đơn thuốc nào được lưu.</p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Thời điểm</th>
                <th>Bác sĩ kê đơn</th>
                <th>Người chốt đơn</th>
                <th>Khách</th>
                <th>Trạng thái</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {(ds.data ?? []).map((d) => (
                <tr key={d.id}>
                  <td>{new Date(d.created_at).toLocaleString("vi-VN")}</td>
                  <td>
                    {d.doctor_name.trim() === "" ? (
                      <span className={local.trong}>— không ghi —</span>
                    ) : (
                      d.doctor_name
                    )}
                  </td>
                  {/* 🔴 Trách nhiệm chỉ có nghĩa khi NHÌN THẤY ĐƯỢC. Sổ audit đã ghi từ
                      trước, nhưng không ai mở sổ audit để trả lời một câu hỏi thường ngày. */}
                  <td>
                    {d.created_by === null ? (
                      <span className={local.trong}>— không rõ —</span>
                    ) : (
                      d.created_by.slice(0, 8)
                    )}
                  </td>
                  <td>
                    {d.customer_id === null ? (
                      <span className={local.trong}>— không để lại số —</span>
                    ) : (
                      d.customer_id.slice(0, 8)
                    )}
                  </td>
                  <td>{d.status}</td>
                  <td className={styles.num}>
                    <button
                      type="button"
                      className={styles.ghost}
                      onClick={() => setDangMo(d.id === dangMo ? null : d.id)}
                    >
                      {d.id === dangMo ? "Đóng" : "Xem ảnh"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dangMo !== null && (
        <section className={styles.drawer} aria-label="Ảnh đơn thuốc">
          <div className={styles.drawerHead}>
            <h2 className={styles.drawerTitle}>Ảnh đơn thuốc</h2>
            <button type="button" className={styles.ghost} onClick={() => setDangMo(null)}>
              Đóng
            </button>
          </div>
          {anh.isLoading ? (
            <p className={styles.hint}>Đang tải ảnh…</p>
          ) : anh.data ? (
            /* eslint-disable-next-line @next/next/no-img-element -- ảnh là data URI trong
               bộ nhớ, không phải tệp tĩnh: `next/image` cần một URL để tối ưu và sẽ không
               làm được gì với chuỗi base64 này ngoài việc thêm một lớp trung gian. */
            <img
              className={local.anh}
              src={`data:${anh.data.content_type};base64,${anh.data.image_data}`}
              alt="Ảnh đơn thuốc gốc đã chụp ở quầy"
            />
          ) : (
            <p className={styles.hint}>Không mở được ảnh.</p>
          )}
        </section>
      )}
    </div>
  );
}
