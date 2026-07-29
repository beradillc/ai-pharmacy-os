"use client";

import { useState } from "react";

import {
  COMMON_CONDITIONS,
  conditionLabel,
  SEVERITIES,
  type SeverityId,
  severityLabel,
  useAddAllergy,
  useAddCondition,
  useCustomerDetail,
  useIngredients,
} from "@/features/crm/use-health";
import { ApiError } from "@/shared/api/errors";
import type { Customer } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Hồ sơ sức khoẻ của một khách: **dị ứng** và **bệnh nền**.
 *
 * 🔴 Đây là **dữ liệu cá nhân nhạy cảm** (Luật 91/2025 Điều 26 + NĐ 356/2025
 * Điều 4.1.d liệt kê rõ "tình trạng sức khỏe"). Bốn ràng buộc, tất cả đều
 * không thương lượng:
 *
 * ① **Chưa có đồng ý `HEALTH` thì KHÔNG hiện một ô nhập nào.** Không phải hiện
 *    rồi báo lỗi khi bấm lưu — hiện ô nhập là mời người ta gõ vào, và gõ xong
 *    mới bị từ chối thì lần sau họ sẽ đi tìm đường vòng. Backend cũng chặn, đây
 *    là lớp thứ hai chứ không phải lớp duy nhất.
 *
 * ② **Dị ứng khoá theo HOẠT CHẤT, phải chọn từ danh mục.** Backend đòi
 *    `ingredient_id` (UUID), không nhận chuỗi. Ghi "dị ứng Panadol" thì lần sau
 *    bán Hapacol không ai cảnh báo — cùng paracetamol, khác tên thương mại.
 *    Đây là lý do cả tính năng này tồn tại, nên không có đường gõ tay tên hoạt chất.
 *
 * ③ **Bệnh nền: chọn nhanh HOẶC gõ mã tay, và luôn có ô ghi chú tự do.** Chain
 *    yêu cầu cả hai đường (2026-07-29). Danh sách rút gọn 12 bệnh là **lối tắt**,
 *    không phải toàn bộ ICD-10 — màn hình nói rõ điều đó, vì trình bày 12 mục
 *    như thể là toàn bộ danh mục sẽ làm người ghi chọn đại một mục gần đúng.
 *
 * ④ **Ghi thêm, không sửa, không xoá.** Backend chỉ có `POST`. Hồ sơ sức khoẻ
 *    là thứ người sau đọc để quyết định có bán thuốc hay không; một dòng bị xoá
 *    lặng lẽ là một cảnh báo biến mất mà không ai biết.
 */
export function HealthPanel({ customer, onClose }: { customer: Customer; onClose: () => void }) {
  const detail = useCustomerDetail(customer.id);
  const ingredients = useIngredients();
  const addAllergy = useAddAllergy(customer.id);
  const addCondition = useAddCondition(customer.id);

  const [ingredientId, setIngredientId] = useState("");
  const [severity, setSeverity] = useState<SeverityId>("MODERATE");
  const [allergyNote, setAllergyNote] = useState("");

  const [code, setCode] = useState("");
  const [conditionNote, setConditionNote] = useState("");

  const [error, setError] = useState<string | null>(null);

  const record = detail.data ?? customer;
  const allowed = record.health_data_allowed;
  const allergies = record.allergies ?? [];
  const conditions = record.conditions ?? [];
  const nameOf = (id: string) =>
    ingredients.data?.find((i) => i.id === id)?.name ?? `Hoạt chất ${id.slice(0, 8)}`;

  function report(err: unknown, fallback: string) {
    setError(err instanceof ApiError ? err.problem.detail : fallback);
  }

  async function submitAllergy(e: React.FormEvent) {
    e.preventDefault();
    if (!ingredientId) return;
    setError(null);
    try {
      await addAllergy.mutateAsync({
        ingredient_id: ingredientId,
        severity,
        note: allergyNote.trim() || null,
      });
      setIngredientId("");
      setAllergyNote("");
    } catch (err) {
      report(err, "Không ghi được dị ứng.");
    }
  }

  async function submitCondition(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) return;
    setError(null);
    try {
      await addCondition.mutateAsync({
        condition_code: trimmed,
        note: conditionNote.trim() || null,
      });
      setCode("");
      setConditionNote("");
    } catch (err) {
      report(err, "Không ghi được bệnh nền.");
    }
  }

  return (
    <section className={styles.drawer} aria-label={`Hồ sơ sức khoẻ của ${customer.full_name}`}>
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>Sức khoẻ · {customer.full_name}</h2>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Đóng
        </button>
      </div>

      {!allowed ? (
        // ① Chưa đồng ý ⇒ không một ô nhập nào. Chỉ nói vì sao và chỉ đường.
        <p className={local.warnBox}>
          <strong>Khách chưa đồng ý cho lưu dữ liệu sức khoẻ.</strong> Dị ứng và bệnh nền
          là <strong>dữ liệu nhạy cảm</strong> — phải hỏi và được đồng ý trước khi ghi.
          Đóng bảng này, bấm <strong>“Đồng ý”</strong> ở dòng của khách, hỏi khách mục
          “Lưu dị ứng, bệnh nền”, rồi quay lại.
        </p>
      ) : (
        <>
          {error && (
            <div className={styles.error} role="alert">
              <span>{error}</span>
              <button type="button" className={styles.retry} onClick={() => setError(null)}>
                Đóng
              </button>
            </div>
          )}

          {/* --- Dị ứng ------------------------------------------------------ */}
          <h3 className={local.sectionTitle}>Dị ứng</h3>
          {allergies.length === 0 ? (
            <p className={local.hint}>Chưa ghi nhận dị ứng nào.</p>
          ) : (
            <ul className={local.chipList}>
              {allergies.map((a) => (
                <li key={a.id} className={local.chipRow}>
                  <span
                    className={`${styles.chip} ${
                      a.severity === "SEVERE" ? styles.chipDanger : styles.chipWarn
                    }`}
                  >
                    {severityLabel(a.severity)}
                  </span>
                  <span className={local.chipMain}>{nameOf(a.ingredient_id)}</span>
                  {a.note && <span className={local.hint}>{a.note}</span>}
                </li>
              ))}
            </ul>
          )}

          <form className={local.form} onSubmit={submitAllergy}>
            <div className={local.row}>
              <label className={local.field}>
                <span className={local.label}>Hoạt chất</span>
                <select
                  className={styles.select}
                  value={ingredientId}
                  onChange={(e) => setIngredientId(e.target.value)}
                  required
                >
                  <option value="">— chọn hoạt chất —</option>
                  {(ingredients.data ?? []).map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name}
                    </option>
                  ))}
                </select>
                <span className={local.hint}>
                  Chọn <strong>hoạt chất</strong>, không phải tên thuốc — cùng một hoạt chất
                  nằm trong nhiều biệt dược khác nhau.
                </span>
              </label>

              <label className={local.field}>
                <span className={local.label}>Mức độ</span>
                <select
                  className={styles.select}
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as SeverityId)}
                >
                  {SEVERITIES.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label} — {s.hint}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className={local.field}>
              <span className={local.label}>Khách kể lại (ghi tay, không bắt buộc)</span>
              <input
                className={styles.input}
                value={allergyNote}
                onChange={(e) => setAllergyNote(e.target.value)}
                placeholder="VD: uống xong nổi mề đay khắp người, phải đi cấp cứu"
                aria-label="Ghi chú dị ứng"
              />
            </label>

            <div className={local.actions}>
              <button
                type="submit"
                className={styles.button}
                disabled={!ingredientId || addAllergy.isPending}
              >
                {addAllergy.isPending ? "Đang ghi…" : "Thêm dị ứng"}
              </button>
            </div>
          </form>

          {/* --- Bệnh nền ---------------------------------------------------- */}
          <h3 className={local.sectionTitle}>Bệnh nền</h3>
          {conditions.length === 0 ? (
            <p className={local.hint}>Chưa ghi nhận bệnh nền nào.</p>
          ) : (
            <ul className={local.chipList}>
              {conditions.map((c) => (
                <li key={c.id} className={local.chipRow}>
                  <span className={`${styles.chip} ${styles.chipMuted} ${styles.mono}`}>
                    {c.condition_code}
                  </span>
                  <span className={local.chipMain}>{conditionLabel(c.condition_code)}</span>
                  {c.note && <span className={local.hint}>{c.note}</span>}
                </li>
              ))}
            </ul>
          )}

          <form className={local.form} onSubmit={submitCondition}>
            {/* ③ Chọn nhanh — lối tắt, KHÔNG phải toàn bộ ICD-10. */}
            <span className={local.label}>Chọn nhanh</span>
            <div className={local.quickPick}>
              {COMMON_CONDITIONS.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  className={code === c.code ? local.quickOn : local.quickOff}
                  onClick={() => setCode(c.code)}
                  aria-pressed={code === c.code}
                >
                  {c.label}
                </button>
              ))}
            </div>

            <div className={local.row}>
              <label className={local.field}>
                <span className={local.label}>Mã ICD-10</span>
                <input
                  className={`${styles.input} ${styles.mono}`}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="VD: E11"
                  maxLength={16}
                  required
                  aria-label="Mã bệnh nền ICD-10"
                />
                <span className={local.hint}>
                  Danh sách trên chỉ là <strong>12 bệnh hay gặp</strong>, không phải toàn bộ
                  ICD-10 — bệnh khác thì gõ mã vào đây.
                </span>
              </label>

              <label className={local.field}>
                <span className={local.label}>Ghi chú (ghi tay, không bắt buộc)</span>
                <input
                  className={styles.input}
                  value={conditionNote}
                  onChange={(e) => setConditionNote(e.target.value)}
                  placeholder="VD: đang dùng Metformin, khám lại 3 tháng/lần"
                  aria-label="Ghi chú bệnh nền"
                />
              </label>
            </div>

            <div className={local.actions}>
              <button
                type="submit"
                className={styles.button}
                disabled={!code.trim() || addCondition.isPending}
              >
                {addCondition.isPending ? "Đang ghi…" : "Thêm bệnh nền"}
              </button>
            </div>
          </form>

          {/* ④ Nói thẳng rằng không sửa/xoá được, để người ghi cẩn thận NGAY. */}
          <p className={local.hint}>
            Đã ghi thì <strong>không sửa, không xoá</strong> — người sau đọc hồ sơ này để
            quyết định có bán thuốc hay không, nên một dòng biến mất lặng lẽ là một cảnh
            báo mất theo. Ghi sai thì thêm dòng mới ghi rõ trong ghi chú.
          </p>
        </>
      )}
    </section>
  );
}
