"use client";

import { useState } from "react";

import { CONSENT_PURPOSES, type ConsentPurposeId, useRecordConsent } from "@/features/crm/use-customers";
import { ApiError } from "@/shared/api/errors";
import type { Customer } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Bảng xin và rút lại đồng ý.
 *
 * 🔴 Đây là màn duy nhất trong cả sản phẩm mà **thiết kế giao diện chính là tuân
 * thủ pháp luật**, không phải trang trí quanh nó. Luật 91/2025 Điều 9 đòi đồng ý
 * **tự nguyện, biết rõ, theo từng mục đích riêng**, và nói thẳng rằng **im lặng
 * không phải đồng ý**. Bốn quyết định dưới đây đều rút thẳng từ đó:
 *
 * ① **Không ô nào tick sẵn.** Một hộp kiểm bật sẵn biến "chưa ai đụng vào" thành
 *    "đã đồng ý" — đúng thứ Điều 9 cấm. Backend cũng đã cắm chốt: `granted`
 *    **không có giá trị mặc định**, ai đó phải thật sự bấm.
 *
 * ② **Ba mục đích tách rời, mỗi cái một nút.** Không có nút "Đồng ý tất cả".
 *    Gộp lại thì tốc độ ở quầy sẽ luôn thắng, và cái thu được là một sự đồng ý
 *    **ghi chép thì đúng, thực chất thì vô giá trị**.
 *
 * ③ **Nói VÌ SAO hỏi, bằng tiếng người.** "Biết rõ" nghĩa là khách hiểu mình
 *    đang cho phép cái gì. Một dòng chữ `HEALTH` cạnh một hộp kiểm không đạt.
 *
 * ④ **Rút lại phải dễ ngang lúc đồng ý** — cùng một chỗ, cùng một cỡ nút. Quyền
 *    rút lại mà giấu trong menu con thì trên giấy là có, ngoài đời là không.
 *
 * Mỗi lần bấm ghi **một dòng mới**, không sửa dòng cũ: để sau này trả lời được
 * *"ngày đó khách có đồng ý không"* — câu đoàn kiểm tra thật sự hỏi.
 */
export function ConsentPanel({ customer, onClose }: { customer: Customer; onClose: () => void }) {
  const record = useRecordConsent(customer.id);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<ConsentPurposeId | null>(null);

  /** Trạng thái hiện tại của một mục đích, suy từ dữ liệu backend trả về.
   *
   * Backend hiện chỉ phơi ra `health_data_allowed`; hai mục đích kia chưa có cờ
   * riêng trên `CustomerResponse`. Nên chỗ nào chưa biết thì hiện **"chưa hỏi"**
   * — KHÔNG hiện "chưa đồng ý", vì hai thứ đó khác nhau và đoán bừa ở đây là
   * đúng loại sai lầm mà mục đích của màn này là để tránh. */
  function stateOf(id: ConsentPurposeId): "granted" | "unknown" {
    if (id === "HEALTH") return customer.health_data_allowed ? "granted" : "unknown";
    return "unknown";
  }

  async function decide(purpose: ConsentPurposeId, granted: boolean) {
    setPending(purpose);
    setError(null);
    try {
      await record.mutateAsync({ purpose, granted });
    } catch (err) {
      setError(err instanceof ApiError ? err.problem.detail : "Không ghi được quyết định đồng ý.");
    } finally {
      setPending(null);
    }
  }

  return (
    <section className={styles.drawer} aria-label={`Đồng ý của ${customer.full_name}`}>
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>Đồng ý · {customer.full_name}</h2>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Đóng
        </button>
      </div>

      <p className={local.hint}>
        Hỏi khách <strong>từng mục một</strong> rồi bấm thay họ. Không mục nào bắt buộc —
        khách từ chối hết vẫn mua hàng bình thường.
      </p>

      {error && (
        <div className={styles.error} role="alert">
          <span>{error}</span>
          <button type="button" className={styles.retry} onClick={() => setError(null)}>
            Đóng
          </button>
        </div>
      )}

      <ul className={local.consentList}>
        {CONSENT_PURPOSES.map((p) => {
          const granted = stateOf(p.id) === "granted";
          const busy = pending === p.id;
          return (
            <li key={p.id} className={local.consentItem}>
              <div className={local.consentText}>
                <span className={local.consentLabel}>
                  {p.label}
                  {"sensitive" in p && p.sensitive && (
                    <span className={`${styles.chip} ${styles.chipWarn} ${local.tag}`}>
                      nhạy cảm
                    </span>
                  )}
                  {granted && (
                    <span className={`${styles.chip} ${styles.chipOk} ${local.tag}`}>đã đồng ý</span>
                  )}
                </span>
                <span className={local.hint}>{p.why}</span>
              </div>
              <div className={local.consentActions}>
                <button
                  type="button"
                  className={styles.button}
                  onClick={() => decide(p.id, true)}
                  disabled={busy}
                >
                  {busy ? "Đang ghi…" : "Khách đồng ý"}
                </button>
                {/* Rút lại đặt NGAY CẠNH, cùng cỡ — xem quyết định ④. */}
                <button
                  type="button"
                  className={styles.ghost}
                  onClick={() => decide(p.id, false)}
                  disabled={busy}
                >
                  Từ chối / rút lại
                </button>
              </div>
            </li>
          );
        })}
      </ul>

      <p className={local.hint}>
        Mỗi lần bấm ghi thêm <strong>một dòng lịch sử</strong>, không sửa dòng cũ — để sau
        này tra được ngày nào khách đồng ý, ngày nào rút lại.
      </p>
    </section>
  );
}
