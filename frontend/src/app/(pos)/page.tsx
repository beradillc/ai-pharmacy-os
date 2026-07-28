"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/overlay/ConfirmDialog";

import { cartTotal, useCartStore } from "@/features/sales/cart-store";
import { useCheckout } from "@/features/sales/use-checkout";
import { useDrugs } from "@/features/sales/use-drugs";
import { ApiError } from "@/shared/api/errors";
import type { Drug } from "@/shared/api/types";
import { useOfflineSync } from "@/shared/offline/use-offline-sync";

import styles from "./page.module.css";

export default function PosPage() {
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
  /** Thuốc chưa có giá, đang chờ thu ngân nhập đơn giá. */
  const [priceAsk, setPriceAsk] = useState<Drug | null>(null);
  const { refreshCount } = useOfflineSync();

  const total = cartTotal(lines);

  function handleAdd(drug: Drug) {
    // Giá lấy từ `drug.sale_price` (cột catalog, Sprint 10 D10). Chỉ hỏi khi mặt
    // hàng CHƯA được định giá — trước đây hỏi MỌI dòng, kể cả hộp Paracetamol
    // bán mười lần một ngày, vì backend không có chỗ nào giữ giá bán. Thu ngân
    // vẫn sửa được giá từng dòng trong giỏ sau khi thêm.
    if (drug.sale_price !== null) {
      addLine(drug, "1", drug.sale_price);
      return;
    }
    // Hỏi bằng hộp thoại của ứng dụng, KHÔNG `window.prompt`: một số webview
    // nuốt lời gọi đó và trả `null` lặng lẽ ⇒ thu ngân bấm "Thêm" mà không có gì
    // xảy ra, cũng không có thông báo lỗi nào. Trên máy tính bảng đặt ở quầy đó
    // là lỗi vừa khó chịu vừa khó chẩn đoán.
    setPriceAsk(drug);
  }

  function confirmPrice(value: string) {
    if (priceAsk) addLine(priceAsk, "1", value.trim() || "0");
    setPriceAsk(null);
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
      {/* Không còn header riêng ở đây. Thương hiệu, chi nhánh, số đơn chờ đồng bộ
          và nút Đăng xuất nay do `AppShell` lo — dùng chung với mọi màn khác, nên
          chúng chỉ tồn tại một bản. Lối quay lại khu quản lý cũng không cần nút
          "Quản lý" nữa: sidebar (desktop) và thanh dưới (mobile) luôn có mặt. */}
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

      <ConfirmDialog
        open={priceAsk !== null}
        title={`"${priceAsk?.name ?? ""}" chưa có giá bán`}
        description="Nhập đơn giá cho lần bán này. Muốn khỏi hỏi lại, đặt giá bán cho mặt hàng trong danh mục thuốc."
        confirmLabel="Thêm vào giỏ"
        input={{
          label: `Đơn giá (VND/${priceAsk?.base_unit ?? ""})`,
          defaultValue: "0",
          type: "number",
          suffix: "₫",
        }}
        onConfirm={confirmPrice}
        onCancel={() => setPriceAsk(null)}
      />
    </div>
  );
}
