"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { cartTotal, useCartStore } from "@/features/sales/cart-store";
import { useCheckout } from "@/features/sales/use-checkout";
import { useDrugs } from "@/features/sales/use-drugs";
import { ApiError } from "@/shared/api/errors";
import type { Drug } from "@/shared/api/types";
import { useOfflineSync } from "@/shared/offline/use-offline-sync";

import styles from "./page.module.css";

export default function PosPage() {
  const session = useAuthStore((s) => s.session);
  const logout = useAuthStore((s) => s.logout);
  const [search, setSearch] = useState("");
  const { drugs, isLoading } = useDrugs(search);

  const lines = useCartStore((s) => s.lines);
  const addLine = useCartStore((s) => s.addLine);
  const removeLine = useCartStore((s) => s.removeLine);
  const setQuantity = useCartStore((s) => s.setQuantity);
  const clearCart = useCartStore((s) => s.clear);

  const checkout = useCheckout();
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ id: string; queued: boolean } | null>(null);
  const { pendingCount, refreshCount } = useOfflineSync();

  const total = cartTotal(lines);

  function handleAdd(drug: Drug) {
    // Giá bán chưa có nguồn dữ liệu nào trong backend (catalog/inventory chỉ
    // có cost_price — giá vốn), nên thu ngân nhập tay từng dòng. Ghi nhận là
    // khoảng trống sản phẩm thật, không phải chỗ thiếu code.
    const priceStr = window.prompt(`Đơn giá bán "${drug.name}" (VND/${drug.base_unit}):`, "0");
    if (priceStr === null) return;
    addLine(drug, "1", priceStr || "0");
  }

  async function handleCheckout() {
    setCheckoutError(null);
    try {
      const result = await checkout.mutateAsync({ lines, amountPaid: String(total) });
      setLastResult({ id: result.sale?.id ?? result.clientUuid, queued: result.queued });
      if (result.queued) refreshCount();
      clearCart();
    } catch (err) {
      setCheckoutError(err instanceof ApiError ? err.problem.detail : "Thanh toán thất bại");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.brand}>BERAS</span>
        <span className={styles.branchTag}>Chi nhánh: {session?.branch_id.slice(0, 8)}</span>
        {pendingCount > 0 && (
          <span className={styles.pendingTag}>{pendingCount} đơn chờ đồng bộ</span>
        )}
        <button className={styles.logout} onClick={logout}>
          Đăng xuất
        </button>
      </header>

      <div className={styles.body}>
        <section className={styles.catalog}>
          <input
            className={styles.search}
            placeholder="Tìm thuốc theo tên hoặc quét mã vạch..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
          {isLoading && <p className={styles.hint}>Đang tải danh mục...</p>}
          <ul className={styles.drugList}>
            {drugs.map((drug) => (
              <li key={drug.id} className={styles.drugRow}>
                <div>
                  <div className={styles.drugName}>
                    {drug.name}
                    {drug.rx_class !== "OTC" && (
                      <span className={styles.rxBadge}>{drug.rx_class}</span>
                    )}
                  </div>
                  <div className={styles.drugMeta}>
                    {drug.strength ?? ""} · {drug.base_unit}
                  </div>
                </div>
                <button className={styles.addButton} onClick={() => handleAdd(drug)}>
                  Thêm
                </button>
              </li>
            ))}
            {!isLoading && drugs.length === 0 && (
              <p className={styles.hint}>Không tìm thấy thuốc phù hợp.</p>
            )}
          </ul>
        </section>

        <section className={styles.cart}>
          <h2 className={styles.cartTitle}>Giỏ hàng</h2>
          {lines.length === 0 ? (
            <p className={styles.hint}>Chưa có thuốc trong giỏ.</p>
          ) : (
            <ul className={styles.cartList}>
              {lines.map((line) => (
                <li key={line.drugId} className={styles.cartRow}>
                  <div className={styles.cartLineInfo}>
                    <div>{line.name}</div>
                    <div className={styles.drugMeta}>
                      {line.unitPrice} đ × {line.unitName}
                    </div>
                  </div>
                  <input
                    className={styles.qtyInput}
                    type="number"
                    min="1"
                    value={line.quantity}
                    onChange={(e) => setQuantity(line.drugId, e.target.value)}
                  />
                  <button
                    className={styles.removeButton}
                    onClick={() => removeLine(line.drugId)}
                    aria-label={`Xóa ${line.name}`}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className={styles.total}>
            <span>Tổng cộng</span>
            <strong>{total.toLocaleString("vi-VN")} đ</strong>
          </div>

          {checkoutError && <p className={styles.error}>{checkoutError}</p>}
          {lastResult &&
            (lastResult.queued ? (
              <p className={styles.hint}>
                Không có mạng — đã lưu đơn tại máy, sẽ tự đồng bộ khi có mạng lại (mã tạm{" "}
                {lastResult.id.slice(0, 8)})
              </p>
            ) : (
              <p className={styles.success}>Đã bán thành công — mã đơn {lastResult.id.slice(0, 8)}</p>
            ))}

          <button
            className={styles.checkoutButton}
            disabled={lines.length === 0 || checkout.isPending}
            onClick={handleCheckout}
          >
            {checkout.isPending ? "Đang xử lý..." : "Thanh toán"}
          </button>
        </section>
      </div>
    </div>
  );
}
