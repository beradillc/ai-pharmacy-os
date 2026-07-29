/**
 * Types mirroring backend schemas actually returned over HTTP.
 *
 * Kept hand-written and minimal rather than generated from OpenAPI: the backend
 * has no codegen step wired yet (README §4 lists it as future work), and the
 * fields here are exactly the ones the POS screen touches — not a full mirror of
 * every response field.
 *
 * IMPORTANT: docs/11_API_DESIGN.md is stale for `sales` (documents
 * `/sales-orders` + separate `/payments`/`/complete` endpoints + an
 * `Idempotency-Key` header). The real contract — used here — is
 * `backend/src/pharmacy_os/modules/sales/interface/{router,schemas}.py`:
 * a single `POST /sales` with lines+payments together, idempotent on a
 * `client_uuid` field in the body.
 */

export type RxClass = "OTC" | "ETC" | "CONTROLLED";
export type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "EWALLET";

export interface DrugUnit {
  unit_name: string;
  factor: string;
  is_sellable: boolean;
}

export interface Drug {
  id: string;
  name: string;
  rx_class: RxClass;
  base_unit: string;
  form: string | null;
  strength: string | null;
  barcode: string | null;
  /** Giá bán lẻ một đơn vị lẻ, `null` = chưa định giá (màn bán hàng sẽ hỏi tay). */
  sale_price: string | null;
  prescription_required: boolean;
  units: DrugUnit[];
}

export interface LoginRequest {
  email: string;
  password: string;
  branch_id?: string;
}

export interface BranchOption {
  id: string;
  code: string;
  name: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  tenant_id: string;
  branch_id: string;
  permissions: string[];
  must_change_password: boolean;
  accessible_branches: BranchOption[];
}

export interface SaleLineRequest {
  drug_id: string;
  quantity: string;
  unit_price: string;
  requires_prescription: boolean;
}

export interface PaymentRequest {
  method: PaymentMethod;
  amount: string;
}

export interface CreateSaleRequest {
  client_uuid: string;
  lines: SaleLineRequest[];
  payments: PaymentRequest[];
  currency?: string;
  /** Khách gắn vào đơn. `null` = khách vãng lai — bán hàng KHÔNG cần khách hàng. */
  customer_id?: string | null;
}

export interface SaleLine {
  id: string;
  drug_id: string;
  quantity: string;
  unit_price: string;
  line_total: string;
  requires_prescription: boolean;
  returned_quantity: string;
}

export interface Sale {
  id: string;
  client_uuid: string;
  status: string;
  currency: string;
  subtotal: string;
  paid_total: string;
  prescription_ref: string | null;
  lines: SaleLine[];
}

/** RFC 7807 problem+json — the shape every error response takes
 * (`core/errors.py:_handle_app_error`). `extra` fields (e.g. `branches` on a
 * BranchSelectionRequiredError) are spread onto the object by the backend, not
 * nested, so they're read directly off the parsed body. */
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  [extra: string]: unknown;
}

// --- analytics (Sprint 9) ----------------------------------------------------
// Khớp `modules/analytics/interface/schemas.py`. Số tiền/số lượng giữ nguyên
// dạng `string`: backend trả `Decimal`, và ép sang `number` ở đây là tự chuốc
// lấy sai số dấu phẩy động trên đúng những con số người ta đối chiếu với sổ.

export type SuggestionStatus = "PENDING" | "INSUFFICIENT_DATA" | "MATERIALIZED" | "DISMISSED";

export interface TopDrug {
  drug_id: string;
  quantity_sold: string;
  revenue: string;
  /** `null` = không tra được tên (thuốc đã xoá), KHÔNG phải "chưa tra". */
  drug_name: string | null;
}

export interface Dashboard {
  branch_id: string;
  date_from: string;
  date_to: string;
  revenue_total: string;
  top_drugs: TopDrug[];
  near_expiry_count: number;
  low_stock_count: number;
  draft_po_count: number;
}

export interface ReorderSuggestion {
  id: string;
  drug_id: string;
  drug_name: string | null;
  avg_daily_velocity: string;
  reorder_point: string;
  on_hand_at_calc: string;
  suggested_qty: string;
  status: SuggestionStatus;
  supplier_id: string | null;
  /** `null` cùng lúc với `supplier_id = null` nghĩa là "chưa có NCC"; `null`
   * khi `supplier_id` có giá trị nghĩa là tên không tra được. */
  supplier_name: string | null;
  po_id: string | null;
  can_materialize: boolean;
  calculated_at: string;
}

export interface ReorderRun {
  branch_id: string;
  drugs_evaluated: number;
  suggested: number;
  insufficient_data: number;
}

export interface Materialize {
  suggestion_id: string;
  po_id: string;
  /** Mã người đọc được ("PO-0001"). Cấm tự chế từ `po_id` — docs/19 §10.1. */
  po_code: string;
}

// --- Sprint 10: bốn màn quản lý ------------------------------------------
// Khớp `sales/interface/schemas.py:SaleListItemResponse`,
// `inventory/...:StockRowResponse`, `procurement/...:PurchaseOrderListItemResponse`,
// `crm/...:CustomerResponse`. Tiền/lượng vẫn là `string` — cùng lý do như trên.

/** Một dòng của màn Hoá đơn. KHÔNG có `lines`: danh sách không kéo theo từng
 * dòng hàng của từng đơn (backend cố ý bỏ). Muốn chi tiết thì gọi
 * `GET /sales/{id}`. */
export interface SaleListItem {
  id: string;
  branch_id: string;
  created_at: string;
  status: string;
  currency: string;
  subtotal: string;
  paid_total: string;
  line_count: number;
  customer_id: string | null;
  sold_by_user_id: string | null;
}

/** Một lô còn hàng. Chỉ có `drug_id` — inventory không được import catalog, nên
 * tên thuốc do màn hình gắn bằng `GET /drugs?ids=…`. */
export interface StockRow {
  batch_id: string;
  drug_id: string;
  branch_id: string;
  lot_no: string;
  expiry_date: string;
  quantity: string;
}

export interface PurchaseOrderListItem {
  id: string;
  /** Mã người đọc được ("PO-0001") — thứ dược sĩ đọc cho NCC qua điện thoại. */
  code: string;
  supplier_id: string;
  supplier_name: string | null;
  status: string;
  item_count: number;
  total_amount: string;
  created_at: string;
  ordered_at: string | null;
}

/** Một dòng hàng của đơn mua, từ `GET /purchase-orders/{id}`.
 *
 * `quantity_received` là **số đã nhận cộng dồn qua mọi lần nhận**, không phải
 * lần này — màn Nhận hàng trừ nó ra khỏi `quantity_ordered` để biết còn thiếu
 * bao nhiêu. Chỉ có `drug_id`, tên thuốc do màn hình gắn qua `GET /drugs?ids=…`. */
export interface PurchaseOrderItem {
  id: string;
  drug_id: string;
  quantity_ordered: string;
  unit_price: string;
  quantity_received: string;
}

/** `GET /purchase-orders/{id}` — khác `PurchaseOrderListItem` ở chỗ CÓ `items`
 * nhưng KHÔNG có `supplier_name`/`total_amount` (backend không trả). Muốn tên
 * NCC thì lấy từ dòng danh sách đã có sẵn, đừng gọi thêm. */
export interface PurchaseOrderDetail {
  id: string;
  code: string;
  supplier_id: string;
  status: string;
  items: PurchaseOrderItem[];
  created_at: string;
  ordered_at: string | null;
}

/** Một dòng của phiếu nhập. `lot_no` + `expiry_date` là bắt buộc ở tầng
 * backend — không phải lựa chọn giao diện: thiếu số lô thì thuốc vào kho mà
 * không truy vết được, và thu hồi lô theo công văn Cục Quản lý Dược sẽ không
 * biết phải gọi ai. */
export interface GoodsReceiptItem {
  id: string;
  po_item_id: string;
  drug_id: string;
  quantity_received: string;
  lot_no: string;
  expiry_date: string;
  unit_cost: string;
  mfg_date: string | null;
}

export interface GoodsReceipt {
  id: string;
  po_id: string;
  /** "DRAFT" | "CONFIRMED". Chỉ CONFIRMED mới làm tồn kho tăng. */
  status: string;
  received_by: string;
  received_at: string;
  items: GoodsReceiptItem[];
}

export interface Customer {
  id: string;
  full_name: string;
  phone: string | null;
  dob: string | null;
  gender: string | null;
  national_id: string | null;
  anonymised_at: string | null;
  health_data_allowed: boolean;
}

// --- IAM: nhân viên & vai trò -------------------------------------------
// Khớp `modules/iam/interface/schemas.py`.

export interface StaffUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  /** "ACTIVE" | "DISABLED" | "LOCKED" — hiển thị qua nhãn, không suy từ chuỗi thô. */
  status: string;
  must_change_password: boolean;
  last_login_at: string | null;
  locked_until: string | null;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: string[];
}

export interface RoleAssignment {
  id: string;
  user_id: string;
  role_id: string;
  role_code: string;
  /** `null` = cấp cho TOÀN CHUỖI, không riêng một chi nhánh. */
  branch_id: string | null;
  granted_by: string | null;
  granted_at: string;
}
