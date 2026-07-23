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
}

interface CartState {
  lines: CartLine[];
  /** No `catalog`/`inventory` module exposes a sell price today (only
   * `inventory.cost_price`, the purchase cost) — the cashier enters the
   * selling price by hand. Noted as a real product gap, not a placeholder to
   * silently paper over. */
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
