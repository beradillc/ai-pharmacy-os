import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { ActiveIngredient, Customer } from "@/shared/api/types";

/**
 * Mức độ dị ứng. Ba bậc, đúng tên backend nhận.
 *
 * Nhãn tiếng Việt nói **hậu quả**, không nói mức độ trừu tượng: người ghi là
 * thu ngân hoặc dược sĩ đang vội, và "vừa" với "nặng" khác nhau ở chỗ nào thì
 * mỗi người hiểu một kiểu. Mô tả bằng triệu chứng thì không.
 */
export const SEVERITIES = [
  { id: "MILD", label: "Nhẹ", hint: "Ngứa, nổi mẩn — khó chịu nhưng không nguy hiểm" },
  { id: "MODERATE", label: "Vừa", hint: "Sưng, khó thở nhẹ — cần theo dõi" },
  { id: "SEVERE", label: "Nặng", hint: "Sốc phản vệ, phù nề đường thở — CẤM dùng" },
] as const;

export type SeverityId = (typeof SEVERITIES)[number]["id"];

/**
 * Danh sách bệnh nền hay gặp ở quầy thuốc, kèm mã ICD-10.
 *
 * 🔴 Đây là **danh sách rút gọn cho tiện tay**, KHÔNG phải bộ ICD-10 đầy đủ —
 * ICD-10 có hơn 14.000 mã. Nên giao diện **luôn** cho gõ mã tay bên cạnh, và
 * phải nói rõ rằng đây chỉ là lối tắt. Trình bày một danh sách 12 mục như thể
 * nó là toàn bộ danh mục là cách làm người ghi chọn đại một mục gần đúng.
 *
 * Chọn 12 bệnh này vì chúng là những bệnh **đổi cách bán thuốc**: chống chỉ
 * định, tương tác, hoặc cần hỏi thêm trước khi đưa thuốc. Không phải 12 bệnh
 * phổ biến nhất nói chung.
 */
export const COMMON_CONDITIONS = [
  { code: "E11", label: "Đái tháo đường type 2" },
  { code: "I10", label: "Tăng huyết áp" },
  { code: "J45", label: "Hen phế quản" },
  { code: "N18", label: "Bệnh thận mạn" },
  { code: "K21", label: "Trào ngược dạ dày — thực quản" },
  { code: "K27", label: "Loét dạ dày — tá tràng" },
  { code: "I25", label: "Bệnh tim thiếu máu cục bộ mạn" },
  { code: "I48", label: "Rung nhĩ" },
  { code: "K74", label: "Xơ gan" },
  { code: "E78", label: "Rối loạn lipid máu" },
  { code: "M10", label: "Gút" },
  { code: "F32", label: "Trầm cảm" },
] as const;

/** `GET /customers/{id}` — bản ĐẦY ĐỦ, có dị ứng và bệnh nền.
 *
 * Khác `GET /customers` (danh sách) ở chỗ có dữ liệu nhạy cảm — và chỉ khi
 * người gọi giữ `crm.sensitive.read`. `staleTime: 0` vì màn này vừa ghi xong là
 * phải thấy ngay. */
export function useCustomerDetail(customerId: string | null) {
  return useQuery({
    queryKey: ["crm", "customer", customerId],
    queryFn: () => apiFetch<Customer>(`/customers/${customerId}`),
    enabled: customerId !== null,
    retry: false,
    staleTime: 0,
  });
}

/** `GET /active-ingredients` — danh mục để CHỌN, không gõ tay tên hoạt chất.
 *
 * 🔴 Backend đòi `ingredient_id` (UUID), không nhận chuỗi. Đó không phải khó
 * tính: dị ứng khoá theo **hoạt chất** thì lần sau bán một biệt dược khác chứa
 * cùng hoạt chất, hệ thống vẫn cảnh báo được. Gõ tay "dị ứng Panadol" thì lần
 * sau bán Hapacol là không ai biết — cùng paracetamol. */
export function useIngredients() {
  return useQuery({
    queryKey: ["catalog", "ingredients"],
    queryFn: () => apiFetch<ActiveIngredient[]>("/active-ingredients"),
    retry: false,
    staleTime: 10 * 60_000,
  });
}

export function useAddAllergy(customerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { ingredient_id: string; severity: SeverityId; note?: string | null }) =>
      apiFetch<Customer>(`/customers/${customerId}/allergies`, { method: "POST", body: input }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}

export function useAddCondition(customerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { condition_code: string; note?: string | null }) =>
      apiFetch<Customer>(`/customers/${customerId}/conditions`, { method: "POST", body: input }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["crm"] }),
  });
}

/** Nhãn tiếng Việt của một mã bệnh nền, hoặc chính mã đó nếu ngoài danh sách rút gọn.
 *
 * Trả về mã thô là **đúng**, không phải thiếu sót: mã do người ta gõ tay thì
 * hệ thống không biết nó là bệnh gì, và bịa ra một cái tên là tệ hơn. */
export function conditionLabel(code: string): string {
  return COMMON_CONDITIONS.find((c) => c.code === code)?.label ?? code;
}

export function severityLabel(id: string): string {
  return SEVERITIES.find((s) => s.id === id)?.label ?? id;
}
