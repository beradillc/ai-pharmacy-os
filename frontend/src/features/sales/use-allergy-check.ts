import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { AllergyCheck } from "@/shared/api/types";

/**
 * Hỏi trước khi bán — Đ-7: quầy thấy cảnh báo ngay lúc thêm thuốc vào đơn.
 *
 * 🔴 **Không phải cổng cưỡng chế.** Cổng thật nằm ở `complete_sale` phía máy chủ, quyết
 * lại từ chính đơn đang được lưu. Lượt hỏi ở đây chỉ để **hiện cho người xem** — giỏ có
 * thể đổi sau lượt gọi này, và một client hoàn toàn có thể không gọi. Đừng bao giờ dùng
 * kết quả ở đây để *cho phép* bán; nó chỉ để *cảnh báo sớm*.
 *
 * Bốn trạng thái khác nhau, và giao diện phải phân biệt được cả bốn:
 *
 * | Kết quả | Nghĩa |
 * |---|---|
 * | không gọi (chưa có khách) | chưa có gì để đối chiếu — bán vãng lai bình thường |
 * | `checked: false` | khách không còn hồ sơ |
 * | `consent_granted: false` | 🔴 **phép kiểm CHƯA CHẠY** — không phải "sạch" |
 * | `conflict_count: 0` | đã kiểm, không có xung đột |
 *
 * Gộp hai dòng cuối lại là hệ thống nói dối người bán: cả hai đều `conflict_count = 0`.
 */
export function useAllergyCheck(customerId: string | null, drugIds: string[]) {
  // Sắp xếp + khử trùng để khoá cache ổn định: thêm A rồi B, hay B rồi A, vẫn là một giỏ.
  const ids = [...new Set(drugIds)].sort();

  return useQuery({
    queryKey: ["allergy-check", customerId, ids],
    enabled: customerId !== null && ids.length > 0,
    // Hồ sơ dị ứng đổi rất hiếm trong một ca bán; hỏi lại mỗi lần thêm một hộp thuốc là
    // tốn mạng vô ích. Nhưng KHÔNG để lâu: dược sĩ vừa khai thêm một dị ứng ở màn Khách
    // hàng thì quầy phải thấy trong vòng nửa phút, không phải sau khi F5.
    staleTime: 30_000,
    // Đây là cảnh báo an toàn: thất bại thì im lặng còn tệ hơn chậm, nên thử lại một lần.
    retry: 1,
    queryFn: () =>
      apiFetch<AllergyCheck>("/sales/allergy-check", {
        method: "POST",
        body: { customer_id: customerId, drug_ids: ids },
      }),
  });
}
