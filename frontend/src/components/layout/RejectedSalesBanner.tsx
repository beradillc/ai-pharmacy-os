"use client";

import { useState } from "react";

import type { RejectedSale } from "@/shared/offline/db";

import styles from "./RejectedSalesBanner.module.css";

/**
 * Đơn offline bị máy chủ **từ chối** — hiện ở MỌI màn cho tới khi có người xử lý.
 *
 * 🔴 Vì sao nó dai đến vậy. Đây là tiền **đã thu của khách**: thu ngân bấm Thanh toán lúc
 * mất mạng, đưa thuốc, nhận tiền; rồi khi có mạng lại máy chủ từ chối. Nếu chuyện này chỉ
 * hiện một lần rồi biến mất, kết quả là hàng bán ra không có hoá đơn và không ai biết —
 * đúng thứ vừa xảy ra trước 31/07, khi đơn bị từ chối bị **xoá thẳng** và chỉ báo qua một
 * callback không màn nào đọc.
 *
 * Không có nút "đóng". Hai lối ra duy nhất đều là một QUYẾT ĐỊNH có người bấm:
 *   · **Thử lại** — nguyên nhân đã hết (nhập thêm hàng, khai xong dị ứng…)
 *   · **Bỏ hẳn** — đã xử lý ngoài đời (hoàn tiền, bán lại đơn mới)
 */
export function RejectedSalesBanner({
  rejected,
  onThuLai,
  onBoHan,
}: {
  rejected: RejectedSale[];
  onThuLai: (clientUuid: string) => void;
  onBoHan: (clientUuid: string) => void;
}) {
  const [mo, setMo] = useState(false);
  if (rejected.length === 0) return null;

  return (
    <div className={styles.banner} role="alert">
      <div className={styles.head}>
        <span className={styles.count}>
          🔴 <strong>{rejected.length} đơn KHÔNG đồng bộ được</strong>
        </span>
        <button type="button" className={styles.toggle} onClick={() => setMo((v) => !v)}>
          {mo ? "Thu gọn" : "Xem và xử lý"}
        </button>
      </div>
      <p className={styles.why}>
        Đơn đã bán lúc mất mạng, nay máy chủ từ chối. <strong>Tiền có thể đã thu</strong> —
        phải xử lý từng đơn, không tự biến mất.
      </p>

      {mo && (
        <ul className={styles.list}>
          {rejected.map((r) => (
            <li key={r.clientUuid} className={styles.item}>
              <div className={styles.info}>
                <span className={styles.code}>{r.clientUuid.slice(0, 8)}</span>
                <span className={styles.reason}>{r.reason}</span>
                <span className={styles.meta}>
                  {r.request.lines.length} dòng · bán {khi(r.queuedAt)} · từ chối{" "}
                  {khi(r.rejectedAt)}
                </span>
              </div>
              <div className={styles.actions}>
                <button type="button" className={styles.retry} onClick={() => onThuLai(r.clientUuid)}>
                  Thử lại
                </button>
                <button type="button" className={styles.drop} onClick={() => onBoHan(r.clientUuid)}>
                  Bỏ hẳn
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Giờ phút ngày — đủ để đối chiếu với ca trực, không cần giây. */
function khi(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "?"
    : d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
