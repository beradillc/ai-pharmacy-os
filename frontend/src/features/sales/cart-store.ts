import { create } from "zustand";

import type { Drug } from "@/shared/api/types";

export interface CartLine {
  drugId: string;
  name: string;
  unitName: string;
  requiresPrescription: boolean;
  /** Decimal-as-string throughout, matching the API contract — avoids float
   * rounding on money before it ever leaves the browser. */
  quantity: string;
  unitPrice: string;
  /** Giá NIÊM YẾT lúc thêm vào giỏ, hoặc `null` khi mã chưa đặt giá. Giữ riêng khỏi
   *  `unitPrice` để biết dòng này có đang bán lệch hay không mà không phải tra lại. */
  listedPrice: string | null;
}

interface CartState {
  lines: CartLine[];
  /** Giá lấy từ `drug.sale_price` (giá NIÊM YẾT, do chủ chuỗi đặt ở màn Danh mục
   * thuốc). Thu ngân vẫn sửa được từng dòng, nhưng từ 2026-07-31 máy chủ trả 422
   * nếu đơn có dòng lệch giá niêm yết mà không kèm lý do — xem ADR-0003.
   *
   * Ghi chú cũ ở đây nói "không module nào có giá bán, thu ngân tự gõ" — đã sai từ
   * Sprint 10 D10; sửa lại để dòng này không tiếp tục nói dối phiên sau. */
  addLine: (drug: Drug, quantity: string, unitPrice: string) => void;
  removeLine: (drugId: string) => void;
  setQuantity: (drugId: string, quantity: string) => void;
  clear: () => void;
}

export const useCartStore = create<CartState>((set) => ({
  lines: [],
  addLine: (drug, quantity, unitPrice) =>
    set((state) => {
      const existing = state.lines.find((l) => l.drugId === drug.id);
      if (existing) {
        return {
          lines: state.lines.map((l) =>
            l.drugId === drug.id
              ? { ...l, quantity: String(Number(l.quantity) + Number(quantity)) }
              : l,
          ),
        };
      }
      return {
        lines: [
          ...state.lines,
          {
            drugId: drug.id,
            name: drug.name,
            unitName: drug.base_unit,
            requiresPrescription: drug.prescription_required,
            quantity,
            unitPrice,
            listedPrice: drug.sale_price,
          },
        ],
      };
    }),
  removeLine: (drugId) =>
    set((state) => ({ lines: state.lines.filter((l) => l.drugId !== drugId) })),
  setQuantity: (drugId, quantity) =>
    set((state) => ({
      lines: state.lines.map((l) => (l.drugId === drugId ? { ...l, quantity } : l)),
    })),
  clear: () => set({ lines: [] }),
}));

export function cartTotal(lines: CartLine[]): number {
  return lines.reduce((sum, l) => sum + Number(l.quantity) * Number(l.unitPrice), 0);
}

/**
 * Số dòng đang bán LỆCH giá niêm yết. `null` = mã chưa đặt giá ⇒ không có gì để lệch.
 *
 * 🔴 So bằng **số**, không bằng chuỗi: máy chủ chuẩn hoá giá về 2 chữ số thập phân, nên
 * `"12000"` và `"12000.00"` là cùng một giá. So chuỗi ở đây sẽ bắt quầy giải thích một
 * khoản lệch không tồn tại.
 */
export function countPriceDeviations(lines: CartLine[]): number {
  return lines.filter(
    (l) => l.listedPrice !== null && Number(l.unitPrice) !== Number(l.listedPrice),
  ).length;
}
