import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/**
 * Dược sĩ duyệt một đơn thuốc: `DRAFT` → `VALIDATED`.
 *
 * 🔴 Vì sao bước này tồn tại thay vì để ảnh chụp tự có hiệu lực (Chain chốt 2026-08-01):
 * `Prescription.validate()` ghi `validated_by = ctx.user_id` — tức là **ghi tên một con
 * người vào một hành vi chuyên môn**. Đặt nó tự động ngay sau khi lưu ảnh nghĩa là hệ thống
 * khai *"dược sĩ X đã duyệt"* trong khi không ai đọc tờ đơn. Đó là loại sai lệch không hiện
 * ra cho tới lúc thanh tra hỏi. Một chạm rẻ hơn một dòng khai sai trong sổ.
 *
 * Quyền `rx.approve` **không** có trong vai thu ngân (`_CASHIER_PERMISSIONS`) — đó là ràng
 * buộc pháp lý (Luật Dược Điều 6.5.h), không phải tuỳ chọn cấu hình. Màn quầy vì thế phải
 * hỏi quyền trước khi hiện nút, và nói rõ khi không có — chứ không hiện một nút bấm vào là
 * 403.
 */
export function useRxApprove() {
  return useMutation({
    mutationFn: async (prescriptionId: string): Promise<string> => {
      const rx = await apiFetch<{ id: string; status: string }>(
        `/prescriptions/${prescriptionId}/validate`,
        { method: "POST" },
      );
      return rx.status;
    },
  });
}
