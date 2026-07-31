import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { PrescriptionArchiveRow, PrescriptionImage } from "@/shared/api/types";

/**
 * Đơn thuốc **đã có ảnh**, mới nhất trước — nguồn của màn Cài đặt → Lưu trữ.
 *
 * Phạm vi chi nhánh do **máy chủ** quyết, không phải màn này: ai có `archive.read.chain`
 * thì nhận về toàn bộ chi nhánh, không thì chỉ chi nhánh đang đăng nhập. Màn hình không
 * gửi `branch_id` nào lên — để không có đường nào cho một máy khách sửa tay đòi xem chi
 * nhánh khác.
 */
export function usePrescriptionArchive() {
  return useQuery({
    queryKey: ["archive", "prescriptions"],
    queryFn: () => apiFetch<PrescriptionArchiveRow[]>("/prescriptions/archive?limit=200"),
    staleTime: 30_000,
  });
}

/**
 * Nội dung ảnh của MỘT đơn. Chỉ tải khi người dùng bấm mở.
 *
 * 🔴 `enabled` là một phần của thiết kế quyền riêng tư, không phải tối ưu băng thông: mỗi
 * lượt gọi endpoint này ghi một dòng audit `RX_IMAGE_VIEWED`. Tải sẵn ảnh cho cả danh sách
 * sẽ biến sổ audit thành vô nghĩa — ai mở màn cũng thành người đã xem mọi ảnh.
 */
export function usePrescriptionImage(prescriptionId: string | null) {
  return useQuery({
    queryKey: ["archive", "image", prescriptionId],
    queryFn: () => apiFetch<PrescriptionImage>(`/prescriptions/${prescriptionId}/image`),
    enabled: prescriptionId !== null,
    // Không giữ lại trong bộ nhớ đệm: mở lại phải là một lượt đọc MỚI, có vết mới.
    staleTime: 0,
    gcTime: 0,
  });
}
