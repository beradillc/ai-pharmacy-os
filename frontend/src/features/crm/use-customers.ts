import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { Customer } from "@/shared/api/types";

export const CUSTOMER_PAGE_SIZE = 50;

/** Phiên bản điều khoản đang hiệu lực — phải khớp `DEFAULT_TERMS_VERSION` ở backend. */
export const TERMS_VERSION = "v1";

/**
 * Ba mục đích đồng ý, đúng tên backend nhận.
 *
 * 🔴 Ba việc **khác nhau**, không phải ba mức của một việc. Luật 91/2025 Điều 9
 * đòi đồng ý theo từng mục đích riêng và cấm coi im lặng là đồng ý — nên màn
 * hình phải hỏi từng cái một, và **không được tick sẵn cái nào**.
 */
export const CONSENT_PURPOSES = [
  {
    id: "BASIC",
    label: "Lưu tên và số điện thoại",
    why: "Để ghi tên người mua lên hoá đơn và gọi lại khi cần.",
  },
  {
    id: "LOYALTY",
    label: "Theo dõi lịch sử mua để tích điểm",
    why: "Không có mục này thì vẫn mua bán bình thường, chỉ là không cộng điểm.",
  },
  {
    id: "HEALTH",
    label: "Lưu dị ứng, bệnh nền, lịch sử dùng thuốc",
    why: "Dữ liệu NHẠY CẢM. Chỉ xin khi khách cần dược sĩ tư vấn an toàn thuốc.",
    sensitive: true,
  },
] as const;

export type ConsentPurposeId = (typeof CONSENT_PURPOSES)[number]["id"];

/** `GET /customers` — một trang khách hàng. */
export function useCustomers(page: number) {
  const params = new URLSearchParams({
    limit: String(CUSTOMER_PAGE_SIZE),
    offset: String(page * CUSTOMER_PAGE_SIZE),
  });

  return useQuery({
    queryKey: ["crm", "customers", page],
    queryFn: () => apiFetch<Customer[]>(`/customers?${params}`),
    retry: false,
    staleTime: 60_000,
  });
}

/**
 * Chuẩn hoá y hệt `normalize_for_index` ở backend: bỏ mọi ký tự không phải chữ-số.
 *
 * Dùng để **quyết định** người dùng đang gõ số điện thoại hay gõ tên, chứ không
 * gửi bản chuẩn hoá này lên máy chủ — backend tự chuẩn hoá lần nữa khi băm.
 */
export function digitsOf(term: string): string {
  return term.replace(/\D/g, "");
}

/** Đủ dài để coi là một số điện thoại đang gõ dở, chứ không phải một con số vu vơ. */
export const PHONE_MIN_DIGITS = 8;

export function looksLikePhone(term: string): boolean {
  const digits = digitsOf(term);
  // Có chữ cái ⇒ đang gõ tên, dù có lẫn vài con số.
  return digits.length >= PHONE_MIN_DIGITS && !/[a-zà-ỹ]/i.test(term);
}

/**
 * `GET /customers?phone=` — tra **đúng** một số điện thoại trên máy chủ.
 *
 * 🔴 Vì sao chỉ tra được số điện thoại, không tra được tên: cả hai cột đều **mã
 * hoá at-rest**, nhưng số điện thoại có thêm một cột **dấu vân tay** (băm tất
 * định, có chỉ mục) nên so khớp chính xác vẫn chạy. Tên thì không có cột đó —
 * muốn tìm phải giải mã toàn bảng, tức là đọc tên của **mọi** khách hàng để trả
 * về một người.
 *
 * ⇒ Màn hình chia đôi đường: gõ **số** thì hỏi máy chủ (tìm được trong toàn bộ
 * khách hàng), gõ **chữ** thì lọc trong trang đang tải. Và phải **nói rõ** đang
 * ở đường nào, đừng để một ô trông như tìm toàn cục mà chỉ lọc 50 dòng.
 */
export function useCustomerByPhone(term: string) {
  const enabled = looksLikePhone(term);
  const phone = term.trim();

  return useQuery({
    queryKey: ["crm", "customers", "by-phone", digitsOf(term)],
    queryFn: () => apiFetch<Customer[]>(`/customers?phone=${encodeURIComponent(phone)}`),
    enabled,
    retry: false,
    staleTime: 30_000,
  });
}

/** Lọc theo TÊN trong trang đã tải — xem docstring `useCustomerByPhone`. */
export function filterLoaded(customers: Customer[], term: string): Customer[] {
  const needle = term.trim().toLowerCase();
  if (!needle) return customers;
  return customers.filter(
    (c) =>
      c.full_name.toLowerCase().includes(needle) || (c.phone ?? "").toLowerCase().includes(needle),
  );
}

export interface CreateCustomerInput {
  full_name: string;
  phone?: string | null;
  dob?: string | null;
  gender?: string | null;
}

export function useCreateCustomer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateCustomerInput) =>
      apiFetch<Customer>("/customers", { method: "POST", body: input }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}

/**
 * `POST /customers/{id}/consents` — ghi MỘT quyết định đồng ý.
 *
 * Mỗi lần bấm là **một dòng mới**, không sửa dòng cũ: đây là lịch sử chỉ-ghi-thêm
 * để sau này trả lời được câu *"ngày đó khách có đồng ý không"* — câu mà đoàn
 * kiểm tra thật sự hỏi. Rút lại đồng ý cũng là một dòng mới với `granted=false`.
 */
export function useRecordConsent(customerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { purpose: ConsentPurposeId; granted: boolean }) =>
      apiFetch<Customer>(`/customers/${customerId}/consents`, {
        method: "POST",
        body: { ...input, terms_version: TERMS_VERSION },
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}
