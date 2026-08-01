import { useMutation } from "@tanstack/react-query";

import { apiFetchBlob } from "@/shared/api/client";

/**
 * In **đúng một** hoá đơn (Chain giao 2026-08-01).
 *
 * 🔴 Trước bản vá, nút In gọi `window.print()` trần ⇒ trình duyệt in **cả trang** màn Hoá
 * đơn: bảng danh sách, bộ lọc ngày, phân trang, thanh điều hướng. Khách cầm về một tờ giấy
 * có doanh thu cả ngày và hai chục đơn của người khác — vừa vô dụng vừa lộ dữ liệu.
 *
 * 🔴 Và KHÔNG viết lại một mẫu hoá đơn mới ở giao diện. `GET /sales/{id}/receipt` đã dựng
 * sẵn mẫu chuyên nghiệp từ Sprint 7: tên nhà thuốc, địa chỉ, MST, mã đơn, ngày giờ, người
 * bán, từng dòng thuốc, tổng cộng, khách đưa, **tiền thối**, ô ký. Kỷ luật #16 — grep
 * composition root trước khi code một tính năng "chưa có"; lần này nó tiết kiệm cả một mục.
 *
 * Khổ mặc định **`pdf_k80`** (Chain chốt): rộng đúng 80mm. Trình duyệt không dò được máy in
 * nhiệt có cắm hay không, và một tệp 80mm phục vụ được cả hai trường hợp — có máy in nhiệt
 * thì hộp thoại in chọn đúng nó, không có thì vẫn in giấy thường hoặc lưu lại.
 */
export type KhoIn = "pdf_k80" | "pdf_a5" | "pdf_a4";

export function useReceiptPrint() {
  return useMutation({
    mutationFn: async ({ saleId, kho = "pdf_k80" }: { saleId: string; kho?: KhoIn }) => {
      const blob = await apiFetchBlob(`/sales/${saleId}/receipt?format=${kho}`);
      const url = URL.createObjectURL(blob);
      // Mở tab mới thay vì nhúng `<iframe>` rồi gọi `print()`: iOS Safari chặn in từ iframe
      // chéo nguồn, và bản dựng LAN thì API nằm ở cổng khác ⇒ đúng là chéo nguồn. Tab mới
      // để người dùng tự bấm in bằng hộp thoại thật của hệ điều hành — chỗ duy nhất chọn
      // được máy in nhiệt.
      const tab = window.open(url, "_blank");
      if (tab === null) {
        // Trình duyệt chặn cửa sổ bật lên ⇒ rơi về tải tệp. Im lặng không làm gì là cách
        // để người đứng quầy bấm In năm lần rồi nghĩ máy hỏng.
        const a = document.createElement("a");
        a.href = url;
        a.download = `hoa-don-${saleId.slice(0, 8)}.pdf`;
        a.click();
      }
      // Thu hồi TRỄ, không thu hồi ngay: tab mới cần thời gian đọc blob, gọi `revokeObjectURL`
      // ngay dòng dưới sẽ cho ra một tab trắng. 60 giây đủ cho cả máy chậm.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      return url;
    },
  });
}
