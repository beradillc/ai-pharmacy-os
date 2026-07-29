"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/overlay/ConfirmDialog";
import {
  CUSTOMER_PAGE_SIZE,
  filterLoaded,
  looksLikePhone,
  useCreateCustomer,
  useCustomerByPhone,
  useCustomers,
} from "@/features/crm/use-customers";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { Customer } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import { ConsentPanel } from "./ConsentPanel";
import { HealthPanel } from "./HealthPanel";
import local from "./page.module.css";

const GENDER_LABEL: Record<string, string> = { M: "Nam", F: "Nữ", O: "Khác" };

/**
 * Màn Khách hàng (Sprint 10, D7).
 *
 * 🔴 Ô tìm kiếm đi HAI ĐƯỜNG KHÁC NHAU, và màn hình nói rõ đang ở đường nào:
 *
 * | Gõ vào | Đi đâu | Phạm vi |
 * |---|---|---|
 * | **số điện thoại** (≥8 chữ số, không lẫn chữ) | hỏi máy chủ | **toàn bộ** khách hàng |
 * | **tên** | lọc tại chỗ | chỉ trang đang tải |
 *
 * Không phải chọn cho tiện. Cả hai cột đều **mã hoá at-rest**, nhưng số điện
 * thoại có thêm cột **dấu vân tay** (băm tất định, có chỉ mục) nên so khớp chính
 * xác vẫn chạy; tên thì không có cột đó — tìm theo tên phải giải mã toàn bảng,
 * tức là đọc tên của **mọi** khách hàng để trả về một người.
 *
 * Điều quan trọng là **nói ra**: một ô trông như tìm toàn cục mà chỉ lọc 50 dòng
 * là đúng loại lời hứa suông kiểm toán 28/07 đã gọi tên. Nay phụ đề đổi theo
 * từng đường, không nói chung chung nữa.
 */
export default function CustomersPage() {
  const [page, setPage] = useState(0);
  const [term, setTerm] = useState("");
  const [creating, setCreating] = useState(false);
  const [consentFor, setConsentFor] = useState<Customer | null>(null);
  const [healthFor, setHealthFor] = useState<Customer | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const canCreate = new Set(useAuthStore((s) => s.session)?.permissions ?? []).has("crm.create");

  const { data, isLoading, error, refetch } = useCustomers(page);
  const byPhone = useCustomerByPhone(term);
  const create = useCreateCustomer();

  const phoneMode = looksLikePhone(term);
  const rows = data ?? [];
  // Ở chế độ số điện thoại, danh sách là kết quả MÁY CHỦ trả về — không lọc
  // thêm tại chỗ, vì lọc tại chỗ sẽ bóp kết quả toàn cục về đúng trang đang tải.
  const visible = phoneMode ? (byPhone.data ?? []) : filterLoaded(rows, term);
  const searching = phoneMode && byPhone.isLoading;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Khách hàng</h1>
          <p className={styles.subtitle}>
            {phoneMode
              ? "Tra theo số điện thoại — tìm trong TOÀN BỘ khách hàng"
              : `Gõ tên: lọc trang đang xem (${rows.length} khách) · gõ số điện thoại: tìm toàn bộ`}
          </p>
        </div>
        <div className={styles.controls}>
          <input
            className={styles.input}
            placeholder="Số điện thoại, hoặc tên trong trang này…"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            aria-label="Tìm khách theo số điện thoại, hoặc lọc theo tên"
          />
          {canCreate && (
            <button type="button" className={styles.button} onClick={() => setCreating(true)}>
              Thêm khách
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className={styles.error} role="alert">
          <span>
            {error instanceof ApiError ? error.problem.detail : "Không tải được danh sách khách."}
          </span>
          <button type="button" className={styles.ghost} onClick={() => refetch()}>
            Thử lại
          </button>
        </div>
      )}

      <div className={styles.panel}>
        {isLoading ? (
          <>
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
            <div className={styles.skeleton} />
          </>
        ) : searching ? (
          <div className={styles.skeleton} />
        ) : visible.length === 0 ? (
          <p className={styles.empty}>
            {phoneMode
              ? "Không có khách nào mang số này. Bấm “Thêm khách” để tạo mới."
              : rows.length === 0
                ? "Chưa có khách hàng nào."
                : "Không có tên nào khớp trong trang này — thử gõ số điện thoại để tìm toàn bộ."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={`${styles.table} ${local.customerTable}`}>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Điện thoại</th>
                  <th>Giới tính</th>
                  <th className={local.healthCol}>Dữ liệu sức khoẻ</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visible.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      {customer.full_name}
                      {customer.anonymised_at && (
                        <span className={`${styles.chip} ${styles.chipMuted}`}> đã ẩn danh</span>
                      )}
                    </td>
                    <td className={styles.mono}>{customer.phone ?? "—"}</td>
                    <td>{customer.gender ? (GENDER_LABEL[customer.gender] ?? customer.gender) : "—"}</td>
                    <td>
                      {/* Đồng ý xử lý dữ liệu sức khoẻ là một trạng thái PHÁP LÝ
                          (Luật 91/2025), nên nó hiện thành chữ, không thành icon
                          mờ ai đoán cũng được. */}
                      <span
                        className={`${styles.chip} ${
                          customer.health_data_allowed ? styles.chipOk : styles.chipMuted
                        }`}
                      >
                        {customer.health_data_allowed ? "Đã đồng ý" : "Chưa đồng ý"}
                      </span>
                    </td>
                    <td className={styles.num}>
                      <button
                        type="button"
                        className={styles.ghost}
                        onClick={() => setConsentFor(customer)}
                        disabled={customer.anonymised_at !== null}
                        title={
                          customer.anonymised_at !== null
                            ? "Hồ sơ đã ẩn danh — không còn gì để đồng ý"
                            : undefined
                        }
                      >
                        Đồng ý
                      </button>
                      <button
                        type="button"
                        className={`${styles.ghost} ${local.spaced}`}
                        onClick={() => setHealthFor(customer)}
                        disabled={customer.anonymised_at !== null}
                        title={
                          customer.health_data_allowed
                            ? "Dị ứng và bệnh nền"
                            : "Khách chưa đồng ý cho lưu dữ liệu sức khoẻ — mở ra sẽ thấy hướng dẫn"
                        }
                      >
                        Sức khoẻ
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pager}>
          <span>
            {phoneMode
              ? `${visible.length} kết quả cho số này`
              : `Trang ${page + 1} · ${visible.length}/${rows.length} hiển thị`}
          </span>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || isLoading}
          >
            Trước
          </button>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => setPage((p) => p + 1)}
            disabled={isLoading || rows.length < CUSTOMER_PAGE_SIZE}
          >
            Sau
          </button>
        </div>
      </div>

      {consentFor && (
        <ConsentPanel customer={consentFor} onClose={() => setConsentFor(null)} />
      )}

      {healthFor && <HealthPanel customer={healthFor} onClose={() => setHealthFor(null)} />}

      <CreateCustomerDialog
        open={creating}
        pending={create.isPending}
        initialPhone={looksLikePhone(term) ? term.trim() : ""}
        onCancel={() => setCreating(false)}
        onSubmit={async (input) => {
          setActionError(null);
          try {
            const made = await create.mutateAsync(input);
            setCreating(false);
            // Mở ngay bảng đồng ý: tạo hồ sơ xong mà chưa hỏi đồng ý thì hồ sơ đó
            // chưa dùng được vào việc gì — và người ta sẽ quên quay lại hỏi.
            setConsentFor(made);
          } catch (err) {
            setActionError(
              err instanceof ApiError ? err.problem.detail : "Không tạo được khách hàng.",
            );
          }
        }}
      />

      <ConfirmDialog
        open={actionError !== null}
        title="Không tạo được khách hàng"
        description={actionError ?? ""}
        confirmLabel="Đóng"
        onConfirm={() => setActionError(null)}
        onCancel={() => setActionError(null)}
      />
    </div>
  );
}

/** Hộp thoại thêm khách — ba trường, và KHÔNG có ô đồng ý nào ở đây. */
function CreateCustomerDialog({
  open,
  pending,
  initialPhone,
  onSubmit,
  onCancel,
}: {
  open: boolean;
  pending: boolean;
  initialPhone: string;
  onSubmit: (input: { full_name: string; phone?: string | null }) => void;
  onCancel: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState(initialPhone);

  if (!open) return null;

  return (
    <section className={styles.drawer} aria-label="Thêm khách hàng">
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>Thêm khách hàng</h2>
      </div>
      <form
        className={local.form}
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({ full_name: fullName.trim(), phone: phone.trim() || null });
        }}
      >
        <label className={local.field}>
          <span className={local.label}>Họ tên</span>
          <input
            className={styles.input}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            autoFocus
            maxLength={255}
          />
        </label>
        <label className={local.field}>
          <span className={local.label}>Số điện thoại</span>
          <input
            className={styles.input}
            type="tel"
            inputMode="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            maxLength={32}
          />
          <span className={local.hint}>
            Không bắt buộc — nhưng <strong>không có số thì lần sau không tra ra</strong>, vì
            tìm kiếm chỉ chạy trên số điện thoại.
          </span>
        </label>
        <p className={local.hint}>
          Bấm Tạo xong sẽ mở ngay bảng <strong>xin đồng ý</strong>. Chưa hỏi đồng ý thì hồ
          sơ này chưa dùng được vào việc gì.
        </p>
        <div className={local.actions}>
          <button type="button" className={styles.ghost} onClick={onCancel}>
            Huỷ
          </button>
          <button type="submit" className={styles.button} disabled={pending}>
            {pending ? "Đang tạo…" : "Tạo khách hàng"}
          </button>
        </div>
      </form>
    </section>
  );
}
