/**
 * Nhãn tiếng Việt cho mã hành vi — **chép từ `AuditAction` của backend**
 * (`core/audit/entry.py`), không phải viết từ trí nhớ.
 *
 * 🔴 Bản đầu tiên của bảng này tôi **tự đoán mã** (`STOCK_RECEIVED`, `ROLE_ASSIGNED`…) và
 * đoán sai gần hết — mã thật là `INVENTORY_STOCK_RECEIVED`, `ROLE_GRANTED`. Hệ quả không
 * phải màn trắng mà là màn **đầy chữ không ai đọc được**: mã máy hiện nguyên xi giữa các
 * dòng tiếng Việt. Không cổng nào bắt được (chuỗi nào cũng là chuỗi hợp lệ) cho tới khi
 * cổng trình duyệt đếm mã máy lọt ra màn — cùng họ với `styles.primary` và `sales.refund`.
 *
 * Mã nào thiếu nhãn thì **hiện nguyên mã**, không ẩn dòng — một dòng nhật ký bị giấu vì
 * thiếu bản dịch là đúng thứ sổ audit không được phép làm.
 */
export const NHAN: Record<string, string> = {
  // Đăng nhập · tài khoản
  LOGIN_SUCCESS: "Đăng nhập",
  LOGIN_FAILED: "Đăng nhập thất bại",
  ACCOUNT_LOCKED: "Khoá tài khoản do sai mật khẩu",
  PASSWORD_CHANGED: "Đổi mật khẩu",
  PASSWORD_RESET: "Đặt lại mật khẩu",
  TOKEN_REPLAY_DETECTED: "Phát hiện dùng lại phiên đăng nhập",
  USER_CREATED: "Tạo tài khoản",
  USER_ACTIVATED: "Mở lại tài khoản",
  USER_DEACTIVATED: "Khoá tài khoản",
  ROLE_GRANTED: "Gán vai trò",
  ROLE_REVOKED: "Thu hồi vai trò",
  TWO_FACTOR_ENROLLED: "Đăng ký xác thực 2 lớp",
  TWO_FACTOR_ACTIVATED: "Bật xác thực 2 lớp",
  TWO_FACTOR_DISABLED: "Tắt xác thực 2 lớp",
  TWO_FACTOR_FAILED: "Xác thực 2 lớp thất bại",
  TWO_FACTOR_RESET: "Đặt lại xác thực 2 lớp",
  TWO_FACTOR_BACKUP_CODE_USED: "Dùng mã dự phòng 2 lớp",

  // Danh mục thuốc
  CATALOG_DRUG_CREATED: "Thêm thuốc",
  CATALOG_DRUG_PRICE_CHANGED: "Đổi giá bán",
  CATALOG_DRUG_INGREDIENTS_REPLACED: "Sửa hoạt chất",

  // Bán hàng
  SALE_COMPLETED: "Bán hàng",
  SALE_RETURN_REGISTERED: "Khách trả hàng",
  SALE_PRICE_OVERRIDE: "Sửa giá khi bán",
  SALES_ALLERGY_WARNING_OVERRIDDEN: "Bỏ qua cảnh báo dị ứng",
  SALE_VNPAY_INITIATED: "Bắt đầu thanh toán VNPay",
  SALE_VNPAY_CANCELLED: "Huỷ thanh toán VNPay",

  // Kho
  INVENTORY_STOCK_RECEIVED: "Nhập hàng vào kho",
  INVENTORY_STOCK_DISPENSED: "Xuất hàng khỏi kho",
  INVENTORY_PUT_AWAY: "Sắp xếp vào ô",
  INVENTORY_COUNT_APPROVED: "Duyệt phiếu kiểm kê",
  INVENTORY_COUNT_REJECTED: "Từ chối phiếu kiểm kê",
  INVENTORY_RECONCILIATION_RESOLVED: "Xử lý chênh lệch tồn",
  LOCATION_CREATED: "Tạo ô kho",
  LOCATION_CHANGED: "Đổi ô kho",

  // Đơn thuốc
  PRESCRIPTION_CREATED: "Tạo đơn thuốc",
  PRESCRIPTION_APPROVED: "Dược sĩ duyệt đơn",
  PRESCRIPTION_REJECTED: "Dược sĩ từ chối đơn",
  PRESCRIPTION_DISPENSED: "Cấp phát theo đơn",
  RX_IMAGE_ATTACHED: "Chụp ảnh đơn thuốc",
  RX_IMAGE_VIEWED: "Xem ảnh đơn thuốc",
  DRUG_RETURN_RECORDED: "Ghi nhận trả thuốc",

  // Khách hàng · dữ liệu nhạy cảm
  CONSENT_GRANTED: "Khách đồng ý cho lưu thông tin",
  CONSENT_REVOKED: "Khách rút lại đồng ý",
  CUSTOMER_PHONE_REVEALED: "Xem số điện thoại khách",
  CUSTOMER_SENSITIVE_READ: "Xem thông tin sức khoẻ khách",
  CUSTOMER_SENSITIVE_WRITE: "Ghi thông tin sức khoẻ khách",
  CUSTOMER_SENSITIVE_AUTO_CHECK: "Hệ thống tự đối chiếu dị ứng",
  CUSTOMER_MEDICATION_HISTORY_RECORDED: "Ghi lịch sử dùng thuốc",
  CUSTOMER_ERASED: "Xoá dữ liệu khách theo yêu cầu",
  CLINICAL_INTERACTION_CHECKED: "Kiểm tương tác thuốc",
  CLINICAL_RECOMMENDATION_ACCEPTED: "Chấp nhận khuyến cáo lâm sàng",

  // Mua hàng · phân tích
  PROCUREMENT_PO_ORDERED: "Gửi đơn mua hàng",
  PROCUREMENT_GRN_CONFIRMED: "Xác nhận nhận hàng",
  ANALYTICS_REORDER_RUN: "Tính đề xuất đặt hàng",
  ANALYTICS_SUGGESTION_MATERIALIZED: "Tạo đơn nháp từ đề xuất",
  ANALYTICS_SUGGESTION_UNDONE: "Hoàn tác đơn nháp",
  ANALYTICS_SUGGESTION_DISMISSED: "Bỏ qua đề xuất",

  // Tuân thủ · kiểm soát đặc biệt
  CONTROLLED_LEDGER_ENTRY_RECORDED: "Ghi sổ thuốc kiểm soát",
  LEDGER_DAILY_CLOSURE_EXPORTED: "Chốt sổ trong ngày",
  LEDGER_BOOK_SIGNED: "Ký sổ",
  PERIODIC_REPORT_EXPORTED: "Xuất báo cáo định kỳ",
  TENANT_COMPLIANCE_CONFIG_SET: "Đổi cấu hình tuân thủ",
  ENCRYPTION_KEY_ROTATED: "Xoay khoá mã hoá",
};

/** Nhóm hành vi để lọc nhanh — chủ quầy hỏi theo NHÓM, không theo từng mã. */
export const NHOM: { nhan: string; ma: string }[] = [
  { nhan: "Tất cả", ma: "" },
  { nhan: "Bán hàng", ma: "SALE_COMPLETED" },
  { nhan: "Khách trả hàng", ma: "SALE_RETURN_REGISTERED" },
  { nhan: "Sửa giá khi bán", ma: "SALE_PRICE_OVERRIDE" },
  { nhan: "Đổi giá bán", ma: "CATALOG_DRUG_PRICE_CHANGED" },
  { nhan: "Nhập hàng vào kho", ma: "INVENTORY_STOCK_RECEIVED" },
  { nhan: "Duyệt phiếu kiểm kê", ma: "INVENTORY_COUNT_APPROVED" },
  { nhan: "Dược sĩ duyệt đơn", ma: "PRESCRIPTION_APPROVED" },
  { nhan: "Xem số điện thoại khách", ma: "CUSTOMER_PHONE_REVEALED" },
  { nhan: "Đăng nhập", ma: "LOGIN_SUCCESS" },
];

/**
 * Nhãn tiếng Việt cho **loại đối tượng** (`target_type`).
 *
 * Cùng lỗi, khác cột: ảnh chụp 01/08 cho thấy cột Đối tượng hiện `user · 40977c62` giữa các
 * dòng tiếng Việt — cổng khi đó chỉ đếm mã máy ở cột *Hoạt động* nên không thấy. Đây là lý
 * do kỷ luật #20 nói *luôn phải có ảnh*: phép đo chỉ tìm thứ nó được dặn tìm.
 *
 * Mã lấy từ backend (`target_type=` và `_record(ctx, …, "…")`), không đoán.
 */
export const DOI_TUONG: Record<string, string> = {
  ai_recommendation: "Khuyến nghị của AI",
  batch: "Lô thuốc",
  branch: "Chi nhánh",
  controlled_ledger_entry: "Bút toán sổ kiểm soát",
  customer: "Khách hàng",
  drug: "Thuốc",
  drug_return_record: "Phiếu trả thuốc",
  goods_receipt_note: "Phiếu nhập kho",
  ledger_book_signature: "Chữ ký sổ",
  ledger_daily_closure: "Chốt sổ ngày",
  location: "Ô kho",
  periodic_report: "Báo cáo định kỳ",
  prescription: "Đơn thuốc",
  purchase_order: "Đơn mua hàng",
  refresh_token: "Phiên đăng nhập",
  reorder_suggestion: "Đề xuất đặt hàng",
  sale: "Đơn bán",
  stock_count: "Phiếu kiểm kê",
  stock_reconciliation_needed: "Chênh lệch tồn",
  tenant_compliance_config: "Thông tin cơ sở",
  user: "Tài khoản",
  user_role: "Vai trò tài khoản",
};
