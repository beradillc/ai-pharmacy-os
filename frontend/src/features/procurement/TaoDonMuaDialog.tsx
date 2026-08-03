"use client";

import { useState } from "react";

import { useCatalogDrugs } from "@/features/catalog/use-drug-ingredients";
import { useCreatePurchaseOrder, type DongDonMua } from "@/features/procurement/use-create-po";
import { useSuppliers } from "@/features/procurement/use-suppliers";
import { DetailDialog } from "@/components/overlay/DetailDialog";
import { ApiError } from "@/shared/api/errors";
import { formatMoney } from "@/shared/format/number";

import styles from "@/shared/ui/screen.module.css";

import local from "./tao-don-mua.module.css";

/**
 * Tạo **đơn mua hàng thủ công** (V3-2, Chain duyệt 2026-08-04).
 *
 * 🔴 **Ca nó sinh ra để phục vụ:** trình dược viên chào hàng **tận quầy**. Ca ấy không có đề
 * xuất đặt hàng nào — mà trước bản này *Đề xuất → Tạo đơn nháp* là đường **duy nhất** đẻ ra
 * một đơn mua. Nên người bán đứng trước mặt, hàng có sẵn, và phần mềm **không có chỗ ghi**.
 *
 * **Lưu ở trạng thái NHÁP, không tự đặt.** Tạo đơn là soạn thảo; `ORDERED` là lúc nó thành
 * một **khoản phải trả thật** với nhà cung cấp, và backend ghi audit `PROCUREMENT_PO_ORDERED`
 * đúng ở mốc đó. Gộp hai bước làm một sẽ biến mỗi lần gõ thử thành một cam kết tài chính.
 *
 * **Đơn giá bỏ trống = 0.** Khác hẳn giá bán ở `ThemThuocDialog` (bỏ trống = *chưa định
 * giá*): ở đây `unit_price` là thứ **mình trả cho nhà cung cấp**, backend nhận `ge=0`, và một
 * đơn hàng khuyến mãi giá 0 là chuyện có thật. Không có trạng thái "chưa biết giá nhập" —
 * nếu chưa biết thì chưa đặt được đơn.
 */
export function TaoDonMuaDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated?: (poId: string) => void;
}) {
  const ncc = useSuppliers();
  const thuoc = useCatalogDrugs();
  const tao = useCreatePurchaseOrder();

  const [supplierId, setSupplierId] = useState("");
  const [dong, setDong] = useState<DongDonMua[]>([]);
  const [loi, setLoi] = useState<string | null>(null);

  // Khuôn "chỉnh state khi prop đổi" đặt trong render — xem ghi chú cùng loại ở
  // `ThemThuocDialog`: `useEffect` sẽ để lộ một khung hình mang dữ liệu của lần mở trước.
  const [moTruocDo, setMoTruocDo] = useState(open);
  if (open !== moTruocDo) {
    setMoTruocDo(open);
    if (open) {
      setSupplierId("");
      setDong([]);
      setLoi(null);
    }
  }

  const themDong = () =>
    setDong((d) => [...d, { drug_id: "", quantity_ordered: "", unit_price: "" }]);
  const suaDong = (i: number, thayDoi: Partial<DongDonMua>) =>
    setDong((d) => d.map((x, j) => (j === i ? { ...x, ...thayDoi } : x)));
  const xoaDong = (i: number) => setDong((d) => d.filter((_, j) => j !== i));

  const dongHopLe = dong.filter(
    (d) => d.drug_id !== "" && d.quantity_ordered.trim() !== "" && Number(d.quantity_ordered) > 0,
  );
  const duDe = supplierId !== "" && dongHopLe.length > 0;

  const tongTien = dongHopLe.reduce(
    (t, d) => t + Number(d.quantity_ordered) * Number(d.unit_price || 0),
    0,
  );

  async function luu() {
    setLoi(null);
    try {
      const po = await tao.mutateAsync({
        supplier_id: supplierId,
        // Chỉ gửi dòng hợp lệ: một dòng người dùng thêm rồi bỏ trống là dòng họ đổi ý, không
        // phải lỗi cần chặn — bắt họ bấm xoá mới cho lưu là bắt làm một việc thừa.
        items: dongHopLe.map((d) => ({
          drug_id: d.drug_id,
          quantity_ordered: d.quantity_ordered.trim(),
          unit_price: d.unit_price.trim() === "" ? "0" : d.unit_price.trim(),
        })),
      });
      onCreated?.(po.id);
      onClose();
    } catch (e) {
      setLoi(
        e instanceof ApiError ? e.message : "Không lưu được đơn mua. Kiểm tra kết nối rồi thử lại.",
      );
    }
  }

  return (
    <DetailDialog
      open={open}
      title="Tạo đơn mua hàng"
      subtitle="Lưu ở trạng thái NHÁP — bấm Đặt đơn ở danh sách khi chốt với nhà cung cấp"
      onClose={onClose}
    >
      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      <div className={local.form}>
        <label className={local.o}>
          <span className={local.nhan}>Nhà cung cấp</span>
          <select
            className={styles.select}
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
            aria-label="Chọn nhà cung cấp"
          >
            <option value="">— chọn nhà cung cấp —</option>
            {(ncc.data ?? [])
              .filter((s) => s.is_active)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
          </select>
        </label>

        {dong.length === 0 && (
          <p className={local.trong}>Chưa có mặt hàng nào. Bấm “Thêm mặt hàng” để bắt đầu.</p>
        )}

        {dong.map((d, i) => (
          <div key={i} className={local.dong}>
            <label className={local.o}>
              <span className={local.nhan}>Thuốc</span>
              <select
                className={styles.select}
                value={d.drug_id}
                onChange={(e) => suaDong(i, { drug_id: e.target.value })}
                aria-label={`Thuốc dòng ${i + 1}`}
              >
                <option value="">— chọn thuốc —</option>
                {(thuoc.data ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>

            <div className={local.doi}>
              <label className={local.o}>
                <span className={local.nhan}>Số lượng</span>
                <input
                  className={styles.input}
                  inputMode="numeric"
                  value={d.quantity_ordered}
                  onChange={(e) => suaDong(i, { quantity_ordered: e.target.value })}
                  aria-label={`Số lượng dòng ${i + 1}`}
                />
              </label>
              <label className={local.o}>
                <span className={local.nhan}>Đơn giá (đ)</span>
                <input
                  className={styles.input}
                  inputMode="numeric"
                  value={d.unit_price}
                  onChange={(e) => suaDong(i, { unit_price: e.target.value })}
                  placeholder="0"
                  aria-label={`Đơn giá dòng ${i + 1}`}
                />
              </label>
            </div>

            <button
              type="button"
              className={styles.ghost}
              onClick={() => xoaDong(i)}
              aria-label={`Xoá dòng ${i + 1}`}
            >
              Xoá dòng
            </button>
          </div>
        ))}

        <button type="button" className={styles.ghost} onClick={themDong}>
          + Thêm mặt hàng
        </button>

        {dongHopLe.length > 0 && (
          <p className={local.tong}>
            {dongHopLe.length} mặt hàng · tạm tính <strong>{formatMoney(String(tongTien))} đ</strong>
          </p>
        )}
      </div>

      <div className={local.day}>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Huỷ
        </button>
        <button
          type="button"
          className={styles.button}
          disabled={!duDe || tao.isPending}
          onClick={() => void luu()}
        >
          {tao.isPending ? "Đang lưu…" : "Lưu đơn nháp"}
        </button>
      </div>
    </DetailDialog>
  );
}
