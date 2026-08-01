import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/** Một dòng cần nhặt tại một ô. */
export interface DongLoTrinh {
  drug_id: string;
  lot_no: string;
  expiry_date: string;
  quantity: string;
}

/** Một chặng: tới **một ô**, nhặt hết những gì cần ở đó. */
export interface ChangLay {
  location_id: string;
  location_path: string;
  pick_order: number;
  dong: DongLoTrinh[];
}

export interface LoTrinh {
  chang: ChangLay[];
  /** Mã KHÔNG lấy đủ được từ các ô. Rỗng là bình thường. */
  thieu: string[];
}

/**
 * Lộ trình đi lấy hàng cho **cả giỏ** (BERAS V2 Phase 4).
 *
 * 🔴 Khác `useWhereIs` — cái đó trả lời *"một mã nằm ở đâu"* và đã có từ Phase 2. Cái này
 * trả lời *"đi một vòng thì đi thế nào"*: gộp theo **ô**, sắp theo **đường đi**. Với một
 * giỏ hai mã thì hai câu hỏi cho cùng một đáp án; với giỏ mười mã trải bốn kệ thì không.
 *
 * `POST` chứ không `GET`: một giỏ hai chục mã nhét vào query string sẽ chạm giới hạn độ
 * dài URL của proxy, và hỏng ở đó hiện ra dưới dạng lỗi mạng khó hiểu chứ không phải một
 * thông báo đọc được.
 *
 * KHÔNG cache: giỏ đổi liên tục, và một lộ trình cũ chỉ người ta tới ô đã hết hàng.
 */
export function usePickRoute() {
  return useMutation({
    mutationFn: (dong: { drug_id: string; quantity: string }[]) =>
      apiFetch<LoTrinh>("/inventory/pick-route", { method: "POST", body: { dong } }),
  });
}
