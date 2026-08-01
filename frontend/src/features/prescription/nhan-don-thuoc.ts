/**
 * Nhãn tiếng Việt cho trạng thái và nguồn đơn thuốc.
 *
 * 🔴 Chép từ `PrescriptionStatus` / `PrescriptionSource` (Python, `prescription/domain/
 * entities.py`), **không** viết từ trí nhớ — cùng bài học với bảng nhãn nhật ký ngày
 * 01/08, nơi tôi đoán mã và sai gần hết mà không cổng nào đỏ.
 *
 * Màn *Cài đặt → Lưu trữ* trước nay hiện thẳng `{d.status}`, tức là **`DRAFT` nguyên xi**
 * giữa các dòng tiếng Việt. Không phải lỗi mới — chỉ là chưa ai nhìn kỹ. Nay cả hai màn
 * dùng chung bảng này.
 */
export const TRANG_THAI_DON: Record<string, string> = {
  DRAFT: "Chờ dược sĩ duyệt",
  VALIDATED: "Dược sĩ đã duyệt",
  DISPENSED: "Đã cấp phát",
  REJECTED: "Dược sĩ từ chối",
};

export const NGUON_DON: Record<string, string> = {
  MANUAL: "Nhập tay",
  IMAGE: "Chụp ảnh",
  EPRESCRIPTION: "Đơn điện tử",
};

/** Lựa chọn cho bộ lọc trạng thái. Mã rỗng = không lọc. */
export const LOC_TRANG_THAI: { nhan: string; ma: string }[] = [
  { nhan: "Tất cả", ma: "" },
  { nhan: "Chờ dược sĩ duyệt", ma: "DRAFT" },
  { nhan: "Dược sĩ đã duyệt", ma: "VALIDATED" },
  { nhan: "Đã cấp phát", ma: "DISPENSED" },
  { nhan: "Dược sĩ từ chối", ma: "REJECTED" },
];
