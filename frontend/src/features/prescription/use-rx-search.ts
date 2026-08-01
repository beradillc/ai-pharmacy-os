import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { PrescriptionArchiveRow } from "@/shared/api/types";

export const RX_PAGE_SIZE = 50;

export interface RxSearchParams {
  khachHang?: string;
  tuNgay?: string;
  denNgay?: string;
  trangThai?: string;
  trang: number;
}

/**
 * `GET /prescriptions` — tra cứu đơn thuốc của chi nhánh đang đăng nhập (lỗi M-08,
 * UAT 2026-08-01).
 *
 * 🔴 **Khác `useArchive` ở một điểm quyết định:** Lưu trữ lọc `image_data IS NOT NULL`,
 * tức là chỉ đơn **đã chụp ảnh**. Rất dễ nhìn màn Lưu trữ rồi kết luận *"tra cứu đơn thuốc
 * có rồi"* — nhưng khi thanh tra hỏi *"đơn thuốc của khách X"*, một đơn nhập tay không ảnh
 * **vẫn là một đơn thật** và nó biến mất khỏi Lưu trữ mà không báo gì.
 *
 * Quyền `rx.read` — cùng quyền đã dùng để mở một đơn. Phạm vi chi nhánh do **máy chủ**
 * khoá theo token, màn này không gửi `branch_id` lên.
 */
export function useRxSearch(p: RxSearchParams) {
  return useQuery({
    queryKey: ["rx", "search", p.khachHang, p.tuNgay, p.denNgay, p.trangThai, p.trang],
    queryFn: () => {
      const q = new URLSearchParams({
        limit: String(RX_PAGE_SIZE),
        offset: String(p.trang * RX_PAGE_SIZE),
      });
      if (p.khachHang) q.set("customer_id", p.khachHang);
      // "2026-08-01" trần được hiểu là 00:00 — đúng cho `từ`, nhưng với `đến` sẽ **cắt mất
      // cả ngày cuối**. Cùng cái bẫy đã xử ở màn Nhật ký.
      if (p.tuNgay) q.set("created_from", `${p.tuNgay}T00:00:00`);
      if (p.denNgay) q.set("created_to", `${p.denNgay}T23:59:59`);
      if (p.trangThai) q.set("status", p.trangThai);
      return apiFetch<PrescriptionArchiveRow[]>(`/prescriptions?${q.toString()}`);
    },
    staleTime: 15_000,
  });
}
