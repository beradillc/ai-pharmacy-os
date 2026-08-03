import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Drug, RxClass } from "@/shared/api/types";

/**
 * Tạo một mã thuốc mới — `POST /drugs` (V3-1, Chain duyệt 2026-08-04).
 *
 * 🔴 **Vì sao hook này tới muộn thế:** endpoint `POST /drugs` đã có từ lâu, nhưng **không
 * một dòng frontend nào gọi nó**. Thuốc vào được CSDL là do chạy seed. Hệ quả ngoài đời:
 * người nhận hàng gặp một mặt hàng chưa có trong danh mục thì **dừng hẳn**, không có đường
 * đi tiếp — đây là lỗ hổng duy nhất trong đợt rà soát V3 làm *dừng* một việc đang làm, ba
 * cái còn lại chỉ gây bất tiện. Cùng hình dạng với `POST /purchase-orders` (V3-2).
 *
 * Bài học để lần sau khỏi lặp: **một endpoint không có chỗ bấm thì bằng không**, và nó
 * không làm đỏ cổng nào — `pytest` xanh vì endpoint đúng, `tsc` xanh vì không ai gọi sai.
 */
export interface CreateDrugBody {
  name: string;
  rx_class: RxClass;
  base_unit: string;
  /** Bỏ trống = chưa định giá; màn bán hàng sẽ hỏi giá tay. Không tự điền 0. */
  sale_price?: string | null;
  form?: string | null;
  strength?: string | null;
  barcode?: string | null;
}

export function useCreateDrug() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateDrugBody) =>
      apiFetch<Drug>("/drugs", { method: "POST", body }),
    onSuccess: () => {
      // Danh mục phải hiện mã mới NGAY: hook này được gọi giữa lúc đang nhập hàng, và
      // người dùng cần chọn đúng cái vừa tạo ở ô ngay bên trên — đợi hết hạn cache
      // (60 giây) thì họ sẽ tưởng việc tạo thất bại và tạo lần thứ hai.
      void qc.invalidateQueries({ queryKey: ["catalog", "drugs"] });
      void qc.invalidateQueries({ queryKey: ["drug-names"] });
    },
  });
}
