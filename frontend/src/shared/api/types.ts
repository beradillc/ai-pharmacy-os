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
