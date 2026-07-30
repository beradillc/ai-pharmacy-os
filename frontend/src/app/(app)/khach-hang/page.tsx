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
  useRevealPhone,
} from "@/features/crm/use-customers";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { Customer } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import { ConsentPanel } from "./ConsentPanel";
import { HealthPanel } from "./HealthPanel";
import local from "./page.module.css";

/** `3450000` → `3,4tr`. Cột hẹp trên điện thoại không chứa nổi "3.450.000 đ". */
function diemGon(raw: string): string {
  const n = Number(raw ?? 0);
  if (!Number.isFinite(n) || n <= 0) return "—";
  if (n < 1_000_000) return `${Math.round(n / 1000)}k`;
  return `${(n / 1_000_000).toFixed(1).replace(".", ",")}tr`;
}

/** Số đầy đủ + số hộp đã đạt, để trong `title` — con số rút gọn không được làm mất nó.
 *
 * 🔴 Số hộp lấy THẲNG từ backend (`boxes_this_year`), không tự chia cho mốc 2 triệu. Rà
 * soát 31/07 bắt được mốc đó đang khai ở hai ngôn ngữ; đổi một bên thì bên kia im lặng
 * sai — và sai theo hướng tệ nhất: quầy hứa với khách một con số hệ thống không công nhận.
 */
function diemDayDu(c: { accrued_this_year: string; boxes_this_year: number }): string {
  const n = Number(c.accrued_this_year ?? 0);
  if (!Number.isFinite(n) || n <= 0) return "Chưa mua gì trong năm nay";
  return `${n.toLocaleString("vi-VN")} đ trong năm nay · đạt ${c.boxes_this_year} hộp khẩu trang`;
}

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

  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const canCreate = quyen.has("crm.create");
  /** Chỉ cấp chuỗi mới xem được số đầy đủ (Chain chốt 31/07). Người khác không thấy nút —
   *  hiện nút rồi báo lỗi khi bấm là bày ra một lối đi không có thật. */
  const coQuyenXem = quyen.has("crm.pii.reveal");

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
                  <th className={local.giua}>Điểm</th>
                  <th className={`${local.healthCol} ${local.giua}`}>Dữ liệu</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((customer) => (
                  <tr key={customer.id}>
                    <td>
                      {/* Bấm TÊN để mở hồ sơ (Chain chốt 31/07) — bỏ hẳn cột nút riêng.
                          Vẫn là `<button>` chứ không phải `<td onClick>`: bàn phím tab
                          tới được, trình đọc màn hình đọc ra là nút, và nó không biến cả
                          hàng thành một vùng bấm mà người ta vô tình chạm khi cuộn. */}
                      <button
                        type="button"
                        className={local.moHoSo}
                        onClick={() => {
                          setConsentFor(null);
                          setHealthFor(customer);
                        }}
                        disabled={customer.anonymised_at !== null}
                        title="Mở hồ sơ: dị ứng, bệnh nền, đồng ý dữ liệu"
                      >
                        {customer.full_name}
                      </button>
                      {customer.anonymised_at && (
                        <span className={`${styles.chip} ${styles.chipMuted}`}> đã ẩn danh</span>
                      )}
                    </td>
                    <td className={styles.mono}>
                      <PhoneCell customer={customer} coQuyenXem={coQuyenXem} />
                    </td>
                    <td className={`${local.giua} ${styles.mono}`} title={diemDayDu(customer)}>
                      {diemGon(customer.accrued_this_year)}
                    </td>
                    <td className={local.giua}>
                      {/* Chain chốt 31/07: ký hiệu thay cho chữ, để bảng vừa màn hẹp.
                          Đồng ý xử lý dữ liệu sức khoẻ vẫn là một trạng thái PHÁP LÝ
                          (Luật 91/2025), nên KHÔNG mã hoá bằng riêng màu: ✓ và ✗ là hai
                          HÌNH khác nhau (đọc được cả khi mù màu, cả khi in đen trắng), và
                          chữ đầy đủ vẫn còn ở `aria-label` + `title` cho trình đọc màn
                          hình và cho người rê chuột. */}
                      <span
                        className={
                          customer.health_data_allowed ? local.dauCo : local.dauKhong
                        }
                        title={customer.health_data_allowed ? "Đã đồng ý" : "Chưa đồng ý"}
                        aria-label={
                          customer.health_data_allowed
                            ? "Đã đồng ý cho lưu dữ liệu sức khoẻ"
                            : "Chưa đồng ý cho lưu dữ liệu sức khoẻ"
                        }
                        role="img"
                      >
                        {customer.health_data_allowed ? "✓" : "✗"}
                      </span>
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

      {healthFor && (
        <HealthPanel
          customer={healthFor}
          onClose={() => setHealthFor(null)}
          onXinDongY={() => {
            setHealthFor(null);
            setConsentFor(healthFor);
          }}
        />
      )}

      {/* 🔴 Gắn khi MỞ, không gắn sẵn rồi ẩn. Trước đây hộp thoại luôn nằm trong cây và
          `useState(initialPhone)` chỉ chạy đúng một lần lúc tải trang — nên số vừa gõ ở ô
          tìm KHÔNG BAO GIỜ vào được ô số điện thoại. Đó chính là chỗ Chain nêu 31/07:
          tìm không thấy, bấm Thêm, phải gõ lại số. */}
      {creating && (
      <CreateCustomerDialog
        pending={create.isPending}
        initialPhone={looksLikePhone(term) ? term.trim() : ""}
        onCancel={() => setCreating(false)}
        onSubmit={async (input) => {
          setActionError(null);
          try {
            const made = await create.mutateAsync(input);
            setCreating(false);
            // Có số ⇒ đồng ý BASIC đã ghi ngay lúc tạo (cơ sở COUNTER), nên mở thẳng hồ
            // sơ sức khoẻ — thứ DUY NHẤT còn cần hỏi. Không số ⇒ chưa có hành vi khẳng
            // định nào, vẫn phải qua bảng đồng ý.
            if (input.phone) setHealthFor(made);
            else setConsentFor(made);
          } catch (err) {
            setActionError(
              err instanceof ApiError ? err.problem.detail : "Không tạo được khách hàng.",
            );
          }
        }}
      />
      )}

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
/**
 * Ô số điện thoại: mặc định `*494`, bấm mới ra số đầy đủ — và chỉ cấp chuỗi bấm được.
 *
 * 🔴 Số đã che đến từ **server**, không phải cắt ở đây. Cắt ở đây thì số đầy đủ vẫn nằm
 * trong phản hồi HTTP, mở tab Network là đọc được — che kiểu đó không chặn được ai.
 *
 * Số hiện ra rồi thì **không tự ẩn lại**: nó chỉ sống trong state của một dòng, mất khi
 * rời trang. Ẩn lại sau vài giây nghe có vẻ an toàn hơn nhưng chỉ khiến người ta bấm
 * nhiều lần — mà mỗi lần bấm là một dòng audit, nên làm vậy là làm bẩn chính sổ audit.
 */
function PhoneCell({ customer, coQuyenXem }: { customer: Customer; coQuyenXem: boolean }) {
  const [soDayDu, setSoDayDu] = useState<string | null>(null);
  const reveal = useRevealPhone();

  if (!customer.phone) return <>—</>;
  if (soDayDu) return <>{soDayDu}</>;

  return (
    <>
      {customer.phone}
      {coQuyenXem && (
        <button
          type="button"
          className={local.xemSo}
          onClick={() =>
            reveal.mutate(customer.id, { onSuccess: (r) => setSoDayDu(r.phone) })
          }
          disabled={reveal.isPending}
          title="Xem số đầy đủ — lượt xem này được ghi vào sổ audit"
        >
          {reveal.isPending ? "…" : "xem"}
        </button>
      )}
    </>
  );
}

function CreateCustomerDialog({
  pending,
  initialPhone,
  onSubmit,
  onCancel,
}: {
  pending: boolean;
  initialPhone: string;
  onSubmit: (input: { full_name: string; phone?: string | null }) => void;
  onCancel: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState(initialPhone);

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
