"use client";

import { useState } from "react";

import { CUSTOMER_PAGE_SIZE, filterLoaded, useCustomers } from "@/features/crm/use-customers";
import { ApiError } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

const GENDER_LABEL: Record<string, string> = { M: "Nam", F: "Nữ", O: "Khác" };

/**
 * Màn Khách hàng (Sprint 10, D7).
 *
 * 🔴 Ô lọc lọc **trong trang đang tải**, không phải tìm toàn bộ khách hàng — và
 * phụ đề nói đúng như vậy. Lý do không phải là chưa kịp làm: họ tên và số điện
 * thoại là **cột mã hoá at-rest**, nên `LIKE` không chạy trên chúng; tìm kiếm
 * thật cần blind index. Một ô tìm kiếm trông như toàn cục mà chỉ lọc 50 dòng là
 * đúng loại lời hứa suông mà kiểm toán 28/07 gọi tên.
 */
export default function CustomersPage() {
  const [page, setPage] = useState(0);
  const [term, setTerm] = useState("");

  const { data, isLoading, error, refetch } = useCustomers(page);
  const rows = data ?? [];
  const visible = filterLoaded(rows, term);

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Khách hàng</h1>
          <p className={styles.subtitle}>Lọc áp dụng cho trang đang xem ({rows.length} khách)</p>
        </div>
        <div className={styles.controls}>
          <input
            className={styles.input}
            placeholder="Lọc theo tên hoặc số điện thoại…"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            aria-label="Lọc theo tên hoặc số điện thoại"
          />
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
        ) : visible.length === 0 ? (
          <p className={styles.empty}>
            {rows.length === 0 ? "Chưa có khách hàng nào." : "Không có khách nào khớp bộ lọc."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Họ tên</th>
                  <th>Điện thoại</th>
                  <th>Giới tính</th>
                  <th>Dữ liệu sức khoẻ</th>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.pager}>
          <span>
            Trang {page + 1} · {visible.length}/{rows.length} hiển thị
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
    </div>
  );
}
