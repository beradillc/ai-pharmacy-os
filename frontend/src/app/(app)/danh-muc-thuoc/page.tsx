"use client";

import { useMemo, useState } from "react";

import { useIngredients } from "@/features/crm/use-health";
import {
  useCatalogDrugs,
  useReplaceIngredients,
  type IngredientRow,
} from "@/features/catalog/use-drug-ingredients";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { Drug } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * Danh mục thuốc — xem và **sửa hoạt chất**.
 *
 * 🔴 Vì sao màn này tồn tại. Cho tới 30/07 **không có đường nào** sửa hoạt chất của một
 * thuốc đã tạo: `create_drug` là use-case duy nhất, router chỉ có `POST`. Nghĩa là dược sĩ
 * nhập sai một hoạt chất thì cảnh báo dị ứng **sai người vĩnh viễn**; nhập thiếu thì **im
 * lặng vĩnh viễn**. API đã có từ 30/07 (`PUT /drugs/{id}/ingredients`) nhưng chưa ai chạm
 * được vì thiếu đúng màn này.
 *
 * Cột "Hoạt chất" cố ý để **đầu tiên sau tên**: nó là thứ quyết định cảnh báo dị ứng có
 * kêu hay không, nên nó phải là thứ đập vào mắt, không phải một chi tiết trong trang con.
 */
export default function DrugCatalogPage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  /** Sửa hoạt chất là quyết định CẤP CHUỖI — đổi ở một chi nhánh là đổi hành vi cảnh báo
   *  của toàn chuỗi. Không có quyền thì không thấy nút, thay vì thấy rồi bị từ chối. */
  const coQuyenSua = quyen.has("catalog.update");

  const [tim, setTim] = useState("");
  const [dangSua, setDangSua] = useState<Drug | null>(null);
  const drugs = useCatalogDrugs();
  const ingredients = useIngredients();

  const tenHoatChat = useMemo(
    () => new Map((ingredients.data ?? []).map((i) => [i.id, i.name])),
    [ingredients.data],
  );

  const hienThi = useMemo(() => {
    const needle = tim.trim().toLowerCase();
    const ds = drugs.data ?? [];
    return needle ? ds.filter((d) => d.name.toLowerCase().includes(needle)) : ds;
  }, [drugs.data, tim]);

  const soTrong = (drugs.data ?? []).filter((d) => d.ingredients.length === 0).length;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Danh mục thuốc</h1>
          <p className={styles.subtitle}>
            Hoạt chất quyết định cảnh báo dị ứng ở quầy — thuốc không có hoạt chất thì cảnh
            báo <strong>không bao giờ kêu</strong> cho mã đó.
          </p>
        </div>
      </div>

      {/* 🔴 Ô nhập PHẢI nằm trong `.controls`. `.input` mang `flex: 1 1 auto` — dùng cho
          hàng ngang. Đặt thẳng vào `.page` (flex CỘT) thì nó nở theo CHIỀU CAO: ảnh chụp
          đầu tiên cho một ô tìm kiếm cao ~250px, trong khi lint/tsc/vitest/build xanh hết. */}
      <div className={styles.controls}>
        <input
          className={styles.input}
          value={tim}
          onChange={(e) => setTim(e.target.value)}
          placeholder="Tìm theo tên thuốc…"
          aria-label="Tìm thuốc"
        />
      </div>

      {soTrong > 0 && (
        <p className={local.canhBao}>
          ⚠️ <strong>{soTrong} thuốc chưa có hoạt chất.</strong> Vật tư (băng gạc, khẩu
          trang, nhiệt kế) đúng là không có — nhưng thuốc thì cần, nếu không khách dị ứng
          mua đúng mã đó sẽ đi qua quầy trong im lặng.
        </p>
      )}

      {drugs.isLoading ? (
        <p className={styles.hint}>Đang tải…</p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={`${styles.table} ${local.drugTable}`}>
            <thead>
              <tr>
                <th>Tên thuốc</th>
                <th>Hoạt chất</th>
                {coQuyenSua && <th />}
              </tr>
            </thead>
            <tbody>
              {hienThi.map((d) => (
                <tr key={d.id}>
                  <td>
                    {d.name}
                    {d.prescription_required && (
                      <span className={`${styles.chip} ${styles.chipWarn} ${local.tag}`}>ETC</span>
                    )}
                  </td>
                  <td>
                    {d.ingredients.length === 0 ? (
                      <span className={local.trong}>— chưa có —</span>
                    ) : (
                      d.ingredients
                        .map((i) => tenHoatChat.get(i.ingredient_id) ?? i.ingredient_id.slice(0, 8))
                        .join(" · ")
                    )}
                  </td>
                  {coQuyenSua && (
                    <td className={styles.num}>
                      <button
                        type="button"
                        className={styles.ghost}
                        onClick={() => setDangSua(d)}
                      >
                        Sửa
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dangSua && (
        <EditIngredients
          drug={dangSua}
          tenHoatChat={tenHoatChat}
          onClose={() => setDangSua(null)}
        />
      )}
    </div>
  );
}

/** Bảng sửa hoạt chất của một thuốc. Thay cả danh sách — xem `useReplaceIngredients`. */
function EditIngredients({
  drug,
  tenHoatChat,
  onClose,
}: {
  drug: Drug;
  tenHoatChat: Map<string, string>;
  onClose: () => void;
}) {
  const [rows, setRows] = useState<IngredientRow[]>(
    drug.ingredients.map((i) => ({ ingredient_id: i.ingredient_id, amount: i.amount, unit: i.unit })),
  );
  const [them, setThem] = useState("");
  const [loi, setLoi] = useState<string | null>(null);
  const luu = useReplaceIngredients(drug.id);
  const ingredients = useIngredients();

  const daChon = new Set(rows.map((r) => r.ingredient_id));
  const conLai = (ingredients.data ?? []).filter((i) => !daChon.has(i.id));

  return (
    <section className={styles.drawer} aria-label={`Hoạt chất của ${drug.name}`}>
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>Hoạt chất · {drug.name}</h2>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Đóng
        </button>
      </div>

      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      {rows.length === 0 ? (
        <p className={local.trong}>Chưa có hoạt chất nào.</p>
      ) : (
        <ul className={local.rows}>
          {rows.map((r) => (
            <li key={r.ingredient_id} className={local.row}>
              <span className={local.ten}>
                {tenHoatChat.get(r.ingredient_id) ?? r.ingredient_id.slice(0, 8)}
              </span>
              <input
                className={local.soLuong}
                value={r.amount}
                onChange={(e) =>
                  setRows((p) =>
                    p.map((x) =>
                      x.ingredient_id === r.ingredient_id ? { ...x, amount: e.target.value } : x,
                    ),
                  )
                }
                aria-label={`Hàm lượng ${tenHoatChat.get(r.ingredient_id) ?? ""}`}
              />
              <input
                className={local.donVi}
                value={r.unit}
                onChange={(e) =>
                  setRows((p) =>
                    p.map((x) =>
                      x.ingredient_id === r.ingredient_id ? { ...x, unit: e.target.value } : x,
                    ),
                  )
                }
                aria-label={`Đơn vị ${tenHoatChat.get(r.ingredient_id) ?? ""}`}
              />
              <button
                type="button"
                className={local.boRa}
                onClick={() =>
                  setRows((p) => p.filter((x) => x.ingredient_id !== r.ingredient_id))
                }
                aria-label={`Bỏ ${tenHoatChat.get(r.ingredient_id) ?? ""}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <label className={local.themKhoi}>
        <span className={local.nhan}>Thêm hoạt chất</span>
        <select
          className={styles.select}
          value={them}
          onChange={(e) => {
            const id = e.target.value;
            if (!id) return;
            // Hàm lượng để trống cho người nhập — KHÔNG điền sẵn "1": một con số bịa nằm
            // trong hồ sơ thuốc trông y hệt một con số đã tra.
            setRows((p) => [...p, { ingredient_id: id, amount: "", unit: "mg" }]);
            setThem("");
          }}
        >
          <option value="">— chọn —</option>
          {conLai.map((i) => (
            <option key={i.id} value={i.id}>
              {i.name}
            </option>
          ))}
        </select>
      </label>

      <div className={local.cuoi}>
        <button
          type="button"
          className={styles.button}
          disabled={luu.isPending || rows.some((r) => !r.amount.trim() || !r.unit.trim())}
          onClick={async () => {
            setLoi(null);
            try {
              await luu.mutateAsync(rows);
              onClose();
            } catch (err) {
              setLoi(
                err instanceof ApiError
                  ? err.problem.detail
                  : `Không lưu được — ${err instanceof Error ? err.message : String(err)}`,
              );
            }
          }}
        >
          {luu.isPending ? "Đang lưu…" : "Lưu hoạt chất"}
        </button>
      </div>

      <p className={local.ghiChu}>
        Lưu xong, cảnh báo dị ứng ở quầy đổi theo <strong>ngay</strong> — không cần khởi
        động lại. Mỗi lần lưu được ghi vào sổ audit.
      </p>
    </section>
  );
}
