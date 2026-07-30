"use client";

import { useEffect, useState } from "react";

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
export function HealthPanel({
  customer,
  onClose,
  onXinDongY,
}: {
  customer: Customer;
  onClose: () => void;
  onXinDongY: () => void;
}) {
  const detail = useCustomerDetail(customer.id);
  const ingredients = useIngredients();
  const addAllergy = useAddAllergy(customer.id);
  const addCondition = useAddCondition(customer.id);

  const [ingredientId, setIngredientId] = useState("");
  const [moChonHoatChat, setMoChonHoatChat] = useState(false);
  /** Bệnh nền chọn được NHIỀU cùng lúc (Chain nêu 31/07) — trước chỉ một mã mỗi lượt. */
  const [maDaChon, setMaDaChon] = useState<Set<string>>(new Set());
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
    // Gộp mã gõ tay với các mã bấm nhanh; `Set` khử trùng nếu gõ đúng mã vừa bấm.
    const goTay = code.trim().toUpperCase();
    const ds = [...new Set([...maDaChon, ...(goTay ? [goTay] : [])])];
    if (ds.length === 0) return;
    setError(null);
    try {
      // Ghi TUẦN TỰ, không `Promise.all`: mỗi lượt là một dòng hồ sơ sức khoẻ có ghi
      // vết audit riêng, và nếu mã thứ ba hỏng thì hai mã đầu vẫn phải đã vào — gom
      // song song rồi hỏng giữa chừng sẽ để lại trạng thái không ai đoán được.
      for (const ma of ds) {
        await addCondition.mutateAsync({
          condition_code: ma,
          // Ghi chú gõ tay chỉ gắn cho mã gõ tay: dán chung một ghi chú cho năm bệnh
          // khác nhau là làm hồ sơ sai, không phải làm nhanh.
          note: ma === goTay ? conditionNote.trim() || null : null,
        });
      }
      setCode("");
      setConditionNote("");
      setMaDaChon(new Set());
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
        <div className={local.warnBox}>
          <p>
            <strong>Khách chưa đồng ý cho lưu dữ liệu sức khoẻ.</strong> Dị ứng và bệnh
            nền là <strong>dữ liệu nhạy cảm</strong> — phải hỏi và được đồng ý trước khi
            ghi.
          </p>
          {/* Trước đây chỗ này bảo người dùng "đóng bảng này, bấm Đồng ý ở dòng của
              khách" — một chỉ dẫn ba bước cho việc lẽ ra là một cú bấm. Nay bấm thẳng. */}
          <button type="button" className={styles.button} onClick={onXinDongY}>
            Hỏi khách để lấy đồng ý
          </button>
        </div>
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
            <div className={local.field}>
              <span className={local.label}>Hoạt chất</span>
              {/* 🔴 KHÔNG dùng `<select>` nữa (Chain nêu 31/07): trên điện thoại nó mở
                  bộ chọn của hệ điều hành, phủ kín màn và không phải máy nào cũng có
                  nút đóng thấy được. Đây là bảng chọn của chính ứng dụng — có ô tìm,
                  có nút Đóng, và bấm ra ngoài cũng đóng. */}
              <button
                type="button"
                className={local.chonNut}
                onClick={() => setMoChonHoatChat(true)}
              >
                {ingredientId ? nameOf(ingredientId) : "— chọn hoạt chất —"}
              </button>
              <span className={local.hint}>
                Chọn <strong>hoạt chất</strong>, không phải tên thuốc — cùng một hoạt chất
                nằm trong nhiều biệt dược khác nhau.
              </span>
            </div>

            <div className={local.field}>
              <span className={local.label}>Mức độ</span>
              {/* Ba lựa chọn thì một danh sách xổ là thừa — và chính nó gây lỗi Chain
                  nêu: chuỗi "Vừa — Sưng, khó thở nhẹ — cần theo dõi" dài 52 ký tự làm ô
                  chọn rộng 452px trên khung 390px, tràn 95px (đo 31/07). Ba nút thì
                  không có gì để tràn, và thấy được cả ba mức cùng lúc. */}
              <div className={local.mucDo} role="radiogroup" aria-label="Mức độ dị ứng">
                {SEVERITIES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    role="radio"
                    aria-checked={severity === s.id}
                    className={severity === s.id ? local.mucOn : local.mucOff}
                    onClick={() => setSeverity(s.id as SeverityId)}
                  >
                    <span className={local.mucTen}>{s.label}</span>
                    <span className={local.mucY}>{s.hint}</span>
                  </button>
                ))}
              </div>
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
            <span className={local.label}>Chọn nhanh — bấm nhiều bệnh rồi thêm một lượt</span>
            <div className={local.quickPick}>
              {COMMON_CONDITIONS.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  className={maDaChon.has(c.code) ? local.quickOn : local.quickOff}
                  onClick={() =>
                    setMaDaChon((truoc) => {
                      const sau = new Set(truoc);
                      if (sau.has(c.code)) sau.delete(c.code);
                      else sau.add(c.code);
                      return sau;
                    })
                  }
                  aria-pressed={maDaChon.has(c.code)}
                >
                  {c.label}
                </button>
              ))}
            </div>

            <div className={local.row}>
              <label className={local.field}>
                <span className={local.label}>Bệnh khác — mã ICD-10 (không bắt buộc)</span>
                <input
                  className={`${styles.input} ${styles.mono}`}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="VD: E11"
                  maxLength={16}
                  aria-label="Mã bệnh nền ICD-10"
                />
                {/* 🔴 Bỏ `required` (Chain chốt 31/07: "mã ICD-10 tự động lấy theo tên,
                    không phải nhập tay"). Chọn ở danh sách trên là ĐÃ CÓ mã — mỗi mục
                    mang sẵn cặp (tên bệnh, mã), nên gõ lại mã là gõ thừa. Ô này chỉ còn
                    để dành cho bệnh KHÔNG có trong 12 mục.

                    KHÔNG mở rộng danh sách bằng cách tự đoán thêm mã: ICD-10 có hơn
                    14.000 mã và một mã bịa ra sẽ nằm im trong hồ sơ bệnh nhân. Muốn tra
                    theo tên cho toàn bộ ICD-10 thì phải nhập một bộ mã có nguồn — việc
                    riêng, không làm lẫn vào đây. */}
                <span className={local.hint}>
                  Chọn ở danh sách trên là <strong>đã có mã</strong> — ô này chỉ dùng khi
                  bệnh không nằm trong 12 mục đó.
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
                disabled={(maDaChon.size === 0 && !code.trim()) || addCondition.isPending}
              >
                {addCondition.isPending
                  ? "Đang ghi…"
                  : maDaChon.size > 1
                    ? `Thêm ${maDaChon.size} bệnh nền`
                    : "Thêm bệnh nền"}
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

      {moChonHoatChat && (
        <ChonHoatChat
          dsHoatChat={ingredients.data ?? []}
          dangChon={ingredientId}
          onChon={(id) => {
            setIngredientId(id);
            setMoChonHoatChat(false);
          }}
          onDong={() => setMoChonHoatChat(false)}
        />
      )}
    </section>
  );
}

/**
 * Bảng chọn hoạt chất của CHÍNH ứng dụng, thay cho `<select>` gốc.
 *
 * 🔴 Vì sao phải tự viết (Chain nêu 31/07): `<select>` trên điện thoại mở bộ chọn của
 * hệ điều hành — phủ kín màn hình, và không phải máy nào cũng có nút đóng thấy được.
 * Người dùng bị kẹt trong một lớp phủ mà chính ứng dụng không điều khiển được.
 *
 * Ba lối thoát, cố ý dư: nút **Đóng**, bấm ra **nền mờ**, và phím **Esc**. Một bảng chọn
 * phủ kín màn mà chỉ có một lối thoát là một cái bẫy — đúng thứ vừa phải sửa.
 *
 * Có ô tìm vì danh mục đã 27 hoạt chất và còn dài ra; cuộn tay qua 27 dòng ở quầy trong
 * lúc khách đứng đợi là chuyện khác hẳn với gõ ba chữ.
 */
function ChonHoatChat({
  dsHoatChat,
  dangChon,
  onChon,
  onDong,
}: {
  dsHoatChat: { id: string; name: string }[];
  dangChon: string;
  onChon: (id: string) => void;
  onDong: () => void;
}) {
  const [tim, setTim] = useState("");
  const loc = dsHoatChat.filter((i) =>
    i.name.toLowerCase().includes(tim.trim().toLowerCase()),
  );

  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDong();
    };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onDong]);

  return (
    <div
      className={local.lopPhu}
      role="dialog"
      aria-modal="true"
      aria-label="Chọn hoạt chất"
      onClick={onDong}
    >
      <div className={local.bangChon} onClick={(e) => e.stopPropagation()}>
        <div className={local.bangChonDau}>
          <strong>Chọn hoạt chất</strong>
          <button type="button" className={styles.ghost} onClick={onDong}>
            Đóng
          </button>
        </div>
        <input
          className={styles.input}
          value={tim}
          onChange={(e) => setTim(e.target.value)}
          placeholder="Gõ để tìm — VD: para"
          aria-label="Tìm hoạt chất"
          autoFocus
        />
        {loc.length === 0 ? (
          <p className={local.hint}>Không có hoạt chất nào khớp “{tim}”.</p>
        ) : (
          <ul className={local.bangChonDs}>
            {loc.map((i) => (
              <li key={i.id}>
                <button
                  type="button"
                  className={i.id === dangChon ? local.dongChonOn : local.dongChon}
                  onClick={() => onChon(i.id)}
                >
                  {i.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
