"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/overlay/ConfirmDialog";

import { useAuthStore } from "@/features/auth/auth-store";
import { severityLabel } from "@/features/crm/use-health";
import { useAllergyCheck } from "@/features/sales/use-allergy-check";
import { cartTotal, countPriceDeviations, useCartStore } from "@/features/sales/cart-store";
import { useCheckout } from "@/features/sales/use-checkout";
import { useDrugs } from "@/features/sales/use-drugs";
import { useWhereIs } from "@/features/location/use-locations";
import { useRxApprove } from "@/features/prescription/use-rx-approve";
import { useRxPhoto } from "@/features/prescription/use-rx-photo";
import { ApiError } from "@/shared/api/errors";
import type { Customer, Drug } from "@/shared/api/types";
import { formatMoney, formatQty, money } from "@/shared/format/number";
import { useOfflineSync } from "@/shared/offline/use-offline-sync";

import { CustomerCapture } from "./CustomerCapture";
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
  const [customer, setCustomer] = useState<Customer | null>(null);
  // Tăng sau mỗi lần bán để `CustomerCapture` dựng lại từ đầu — xoá cả số điện
  // thoại của khách trước, không chỉ bỏ gắn.
  const [saleSeq, setSaleSeq] = useState(0);
  /** Thuốc chưa có giá, đang chờ thu ngân nhập đơn giá. */
  const [priceAsk, setPriceAsk] = useState<Drug | null>(null);
  const { refreshCount } = useOfflineSync();

  const total = cartTotal(lines);

  // Đ-7: hỏi ngay khi giỏ hoặc khách đổi, để còn kịp đổi thuốc TRƯỚC khi thu tiền.
  const diUng = useAllergyCheck(
    customer?.id ?? null,
    lines.map((l) => l.drugId),
  );
  const soCanhBao = diUng.data?.conflict_count ?? 0;
  const canGhiLyDo = soCanhBao > 0;
  const [lyDoDiUng, setLyDoDiUng] = useState("");

  // ADR-0003: bán lệch giá niêm yết thì máy chủ đòi lý do. Đếm ở đây chỉ để HỎI cho
  // đúng lúc — cưỡng chế thật nằm ở máy chủ, tính lại từ đơn đang lưu.
  const soDongLechGia = countPriceDeviations(lines);
  const canGhiLyDoGia = soDongLechGia > 0;
  const [lyDoLechGia, setLyDoLechGia] = useState("");

  // Tiền mặt: khách đưa & thối lại. KHÔNG gửi lên máy chủ — `payments[].amount` vẫn là
  // tổng đơn. `SaleOrder.complete()` chấp nhận trả THỪA mà không báo gì, nên gửi tiền
  // khách đưa vào đó sẽ thổi `paid_total` và in sai hoá đơn.
  const [tienNhan, setTienNhan] = useState("");

  // Giỏ hàng trên điện thoại: thu lại thành thanh đáy, bấm mới mở (Chain báo 31/07 —
  // đo được nút Thanh toán nằm cách 3,9 màn hình). Trên máy tính CSS bỏ qua trạng thái
  // này, giỏ luôn hiện — không có nhánh JS riêng cho hai khổ.
  const [gioMo, setGioMo] = useState(false);

  // 🔴 Xác nhận hai bước trước khi chốt đơn (Chain yêu cầu 31/07). Chain cho chọn giữa
  // "hỏi lại xác nhận" và "cho sửa trong 10 giây sau khi chốt"; GĐ chọn hỏi lại, vì hoàn
  // tác sau khi chốt là **huỷ một đơn đã trừ tồn kho và đã ghi doanh thu** — một thao tác
  // đụng tiền và hàng, không phải một mẹo giao diện. Làm nửa vời còn tệ hơn hỏi một câu.
  const [dangXacNhan, setDangXacNhan] = useState(false);

  // Ảnh đơn thuốc (Chain giao 31/07). Chỉ hiện khi giỏ CÓ thuốc kê đơn — một nút "Chụp
  // đơn" trên giỏ toàn thuốc thường là nhiễu, và nhiễu thì người ta học cách bỏ qua.
  const dongETC = lines.filter((l) => l.requiresPrescription);
  const canChupDon = dongETC.length > 0;
  const [tenBacSi, setTenBacSi] = useState("");
  const [rxLoi, setRxLoi] = useState<string | null>(null);
  const chupDon = useRxPhoto();
  const duyetDon = useRxApprove();

  /**
   * 🔴 Đơn thuốc đã chụp cho giỏ NÀY (Chain giao 01/08 — lỗi "chụp rồi vẫn báo cần đơn").
   *
   * Trước bản vá, `useRxPhoto` trả về mã đơn và màn này **vứt đi**: `handleCheckout` không
   * gửi `prescription_ref` nào ⇒ `ensure_rx_for_etc` chặn đúng theo luật, và người đứng
   * quầy thấy một thông báo trái ngược hẳn với việc mình vừa làm.
   *
   * `chuKy` là chữ ký của **tập dòng ETC lúc chụp**. Giỏ đổi sau khi chụp (thêm một thuốc kê
   * đơn khác, sửa số lượng) thì tờ đơn đã lưu **không còn phủ** giỏ hiện tại ⇒ tự hết hiệu
   * lực, phải chụp lại. Suy ra từ trạng thái chứ không dùng `useEffect`: một hiệu ứng chạy
   * sau khi vẽ sẽ có đúng một nhịp mà nút Thanh toán tin vào tờ đơn đã cũ.
   */
  const chuKyETC = dongETC.map((l) => `${l.drugId}:${l.quantity}`).join("|");
  const [rx, setRx] = useState<{ id: string; chuKy: string; daDuyet: boolean } | null>(null);
  const rxConHieuLuc = rx !== null && rx.chuKy === chuKyETC;
  /** `rx.approve` KHÔNG có trong vai thu ngân — ràng buộc Luật Dược Điều 6.5.h, xem
   *  `use-rx-approve.ts`. Hỏi quyền trước khi hiện nút, không hiện nút rồi trả 403. */
  const coQuyenDuyet = new Set(useAuthStore((s) => s.session)?.permissions ?? []).has(
    "rx.approve",
  );
  const soTienNhan = Number(tienNhan.replace(/[^\d]/g, "")) || 0;
  const thoiLai = soTienNhan - total;

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
      const result = await checkout.mutateAsync({
        lines,
        amountPaid: String(total),
        customerId: customer?.id ?? null,
        // Tờ đơn vừa chụp cho đúng giỏ này. Gửi cả khi chưa duyệt: máy chủ trả về
        // *"Đơn thuốc chưa cho phép bán (trạng thái DRAFT…)"* — một câu nói rõ còn thiếu
        // gì, khác hẳn *"cần đơn thuốc hợp lệ"* của trường hợp không gửi gì cả.
        prescriptionRef: rxConHieuLuc ? rx.id : null,
        // Máy chủ QUYẾT LẠI từ chính đơn đang lưu — gửi lý do lên không phải để xin
        // phép, mà để lượt quyết đó có cái mà chấp nhận. Không có cảnh báo thì gửi
        // `null`: một lý do trơ trọi trên đơn sạch chỉ làm bẩn sổ audit.
        allergyAcknowledgement: canGhiLyDo ? lyDoDiUng.trim() : null,
        priceOverrideReason: canGhiLyDoGia ? lyDoLechGia.trim() : null,
      });
      setLastResult({ id: result.sale?.id ?? result.clientUuid, queued: result.queued });
      if (result.queued) refreshCount();
      clearCart();
      setLyDoDiUng("");
      setLyDoLechGia("");
      setTienNhan("");
      setTenBacSi("");
      setRxLoi(null);
      setRx(null);
      setDangXacNhan(false);
      setGioMo(false);
      // Bỏ gắn khách sau khi bán xong: người tiếp theo ở quầy là một người KHÁC.
      // Giữ lại là cách gắn nhầm hoá đơn cho khách trước — và không ai nhận ra.
      setCustomer(null);
      setSaleSeq((n) => n + 1);
    } catch (err) {
      // 🔴 KHÔNG nuốt lý do. Backend từ chối bán có những lý do thu ngân PHẢI
      // đọc được — "thuốc kê đơn cần đơn thuốc hợp lệ", "không đủ tồn" — chứ
      // một dòng "Thanh toán thất bại" trơ trọi thì họ chỉ biết bấm lại. Lỗi
      // không phải từ máy chủ (mất mạng đã được xếp vào hàng chờ ở tầng dưới)
      // thì kèm nguyên văn để còn chụp màn hình gửi kỹ thuật.
      setCheckoutError(
        err instanceof ApiError
          ? err.problem.detail
          : `Thanh toán thất bại — ${err instanceof Error ? err.message : String(err)}`,
      );
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
                    {/* Không nối "· " khi thuốc không có hàm lượng — bản cũ hiện
                        ra dòng "· viên" cụt đầu (thấy trên ảnh chụp 29/07). */}
                    {drug.strength ? `${drug.strength} · ` : ""}
                    {drug.base_unit}
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

        {/* 🔴 Xác nhận bán xong nằm NGOÀI giỏ — ảnh chụp 01/08 bắt được. Bán xong thì
            `setGioMo(false)` đóng giỏ lại, mà trên điện thoại `.cart { display: none }`
            khi giỏ đóng ⇒ dòng "Đã bán thành công" đi theo giỏ vào chỗ khuất và **người
            bán không thấy xác nhận nào**. Cổng của chính tôi vẫn xanh vì nó đếm phần tử
            trong DOM chứ không đo *nhìn thấy được* — đúng hình dạng kỷ luật #21, lần thứ
            tư. Xác nhận một đơn đã trừ tồn và đã ghi doanh thu thuộc về TRANG, không
            thuộc về giỏ. */}
        {lastResult &&
          (lastResult.queued ? (
            <p className={`${styles.hint} ${styles.thongBaoBan}`}>
              Không có mạng — đã lưu đơn tại máy, sẽ tự đồng bộ khi có mạng lại (mã tạm{" "}
              {lastResult.id.slice(0, 8)})
            </p>
          ) : (
            <p className={`${styles.success} ${styles.thongBaoBan}`}>
              Đã bán thành công — mã đơn {lastResult.id.slice(0, 8)}
            </p>
          ))}

        {lines.length > 0 && !gioMo && (
          <div className={styles.gioBar}>
            <span>
              {lines.length} món{canGhiLyDoGia ? " · ⚠️ lệch giá" : ""}
            </span>
            <strong className={styles.gioBarTien}>{money(String(total))}</strong>
            <button
              type="button"
              className={styles.checkoutButton}
              style={{ width: "auto" }}
              onClick={() => setGioMo(true)}
            >
              Xem giỏ
            </button>
          </div>
        )}

        <section className={`${styles.cart} ${gioMo ? styles.cartMo : ""}`}>
          <div className={styles.cartHead}>
            <h2 className={styles.cartTitle}>Giỏ hàng</h2>
            <button
              type="button"
              className={`${styles.ghost} ${styles.dongGio}`}
              onClick={() => setGioMo(false)}
            >
              Thu gọn
            </button>
          </div>

          {/* Hỏi số điện thoại NGAY TRÊN giỏ, không giấu sau một nút: Chain chốt
              29/07 rằng khách đưa số lúc lên đơn chính là xác nhận cung cấp
              thông tin, nên chỗ hỏi phải nằm đúng trong luồng bán hàng. */}
          <CustomerCapture key={saleSeq} value={customer} onChange={setCustomer} />
          {lines.length === 0 ? (
            <p className={styles.hint}>Chưa có thuốc trong giỏ.</p>
          ) : (
            <ul className={styles.cartList}>
              {lines.map((line) => (
                <li key={line.drugId} className={styles.cartRow}>
                  <div className={styles.cartLineInfo}>
                    <div>{line.name}</div>
                    <div className={styles.drugMeta}>
                      {money(line.unitPrice)} × {line.unitName}
                    </div>
                    <ViTriLay drugId={line.drugId} />
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

          {/* 🔴 Cảnh báo dị ứng — Đ-7. Đặt NGAY TRÊN tổng tiền và nút thanh toán, không
              giấu trong một biểu tượng nhỏ: thứ này phải chặn được mắt người bán trên
              đường tay họ đi tới nút Thanh toán.

              Phân biệt đủ BỐN trạng thái. Gộp "chưa được phép kiểm" với "đã kiểm và
              sạch" là hệ thống nói dối người bán — cả hai đều trả `conflict_count = 0`. */}
          {customer && lines.length > 0 && (
            <div className={styles.allergyBox}>
              {diUng.isLoading ? (
                <p className={styles.hint}>Đang đối chiếu dị ứng…</p>
              ) : diUng.isError ? (
                <p className={styles.allergyUnknown}>
                  ⚠️ <strong>Chưa đối chiếu được dị ứng.</strong> Không có nghĩa là khách
                  không dị ứng — hỏi lại khách trước khi bán.
                </p>
              ) : diUng.data?.checked === false ? (
                <p className={styles.allergyUnknown}>
                  ⚠️ Khách này không còn hồ sơ — không đối chiếu được.
                </p>
              ) : diUng.data?.consent_granted === false ? (
                <p className={styles.allergyUnknown}>
                  ⚠️ <strong>Chưa kiểm được.</strong> Khách chưa đồng ý cho lưu dữ liệu sức
                  khoẻ, nên hệ thống không được phép đọc dị ứng. Vẫn bán bình thường — nhưng
                  đây <em>không phải</em> “đã kiểm và không sao”.
                </p>
              ) : soCanhBao === 0 ? (
                <p className={styles.allergyClear}>✓ Đã đối chiếu — không có dị ứng nào.</p>
              ) : (
                <>
                  <p className={styles.allergyAlert}>
                    🔴 <strong>{soCanhBao} cảnh báo dị ứng</strong>
                    {diUng.data?.worst_severity
                      ? // Dùng lại nhãn tiếng Việt của màn Sức khoẻ (`severityLabel`) thay
                        // vì in mã thô: thu ngân đọc "MODERATE" phải tự dịch, mà đây là
                        // lúc họ cần quyết nhanh nhất.
                        ` — nặng nhất: ${severityLabel(diUng.data.worst_severity)}`
                      : ""}
                    .
                    Đổi thuốc, hoặc ghi lý do vẫn bán.
                  </p>
                  <label className={styles.allergyReason}>
                    <span>Lý do vẫn bán (bắt buộc, sẽ lưu vào sổ)</span>
                    <input
                      className={styles.qtyInput}
                      value={lyDoDiUng}
                      onChange={(e) => setLyDoDiUng(e.target.value)}
                      placeholder="VD: bác sĩ đã chỉ định, khách dùng nhiều lần không sao"
                      maxLength={500}
                      aria-label="Lý do vẫn bán dù có cảnh báo dị ứng"
                    />
                  </label>
                </>
              )}
            </div>
          )}

          <div className={styles.total}>
            <span>Thành tiền</span>
            <strong>{money(String(total))}</strong>
          </div>

          {/* 🔴 Lý do bán lệch giá niêm yết (ADR-0003). Đặt TRÊN nút Thanh toán, trên
              đường tay thu ngân đi tới nút — cùng chỗ và cùng lý do với cảnh báo dị ứng. */}
          {canGhiLyDoGia && (
            <div className={styles.lechGia}>
              <span>
                ⚠️ <strong>{soDongLechGia} dòng bán lệch giá niêm yết.</strong> Ghi lý do
                để hoàn tất — mỗi lần lệch được ghi vào sổ audit.
              </span>
              <input
                className={styles.tienNhan}
                style={{ width: "100%", textAlign: "left" }}
                value={lyDoLechGia}
                onChange={(e) => setLyDoLechGia(e.target.value)}
                placeholder="Vì sao bán khác giá niêm yết?"
                aria-label="Lý do bán lệch giá niêm yết"
              />
            </div>
          )}

          {/* 🔴 Ảnh đơn thuốc — Điều 74 Luật Dược: "Đơn thuốc là căn cứ để bán thuốc".
              Đặt TRÊN bảng tiền: chụp tờ đơn xong mới tới chuyện thu tiền, đúng thứ tự
              tay người đứng quầy đi. */}
          {canChupDon && (
            <div className={styles.lechGia}>
              <span>
                💊 <strong>{dongETC.length} thuốc kê đơn trong giỏ.</strong> Chụp lại tờ
                đơn — <strong>người chốt đơn chịu trách nhiệm lưu</strong>, hệ thống ghi
                lại tên bạn.{" "}
                {customer === null && (
                  <em>
                    Khách chưa để lại số — ảnh vẫn lưu được, nhưng sẽ không tra lại được
                    theo khách.
                  </em>
                )}
              </span>

              <>
                  <input
                    className={styles.tienNhan}
                    style={{ width: "100%", textAlign: "left" }}
                    value={tenBacSi}
                    onChange={(e) => setTenBacSi(e.target.value)}
                    placeholder="Tên bác sĩ (không bắt buộc)"
                    aria-label="Tên bác sĩ kê đơn"
                  />
                  <label className={styles.menhGiaNut} style={{ textAlign: "center" }}>
                    {chupDon.isPending
                      ? "Đang lưu ảnh…"
                      : rxConHieuLuc
                        ? "✓ Đã lưu ảnh đơn — chụp lại"
                        : "📷 Chụp đơn thuốc"}
                    {/* `capture="environment"` mở THẲNG camera sau trên điện thoại thay vì
                        bắt chọn tệp. Trên máy tính nó bị bỏ qua và quay về hộp chọn tệp —
                        đúng hành vi mong muốn, không cần nhánh riêng. */}
                    <input
                      type="file"
                      accept="image/*"
                      capture="environment"
                      hidden
                      aria-label="Chụp đơn thuốc"
                      // Chain chốt 2026-07-31: "chỉ cần có hình chụp bất kỳ". Tên bác sĩ
                      // không còn chặn nút — người đứng quầy không phải lúc nào cũng đọc
                      // được chữ bác sĩ, và một cái tên đoán mò còn tệ hơn để trống.
                      disabled={chupDon.isPending}
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        e.target.value = "";
                        if (!file) return;
                        setRxLoi(null);
                        try {
                          const rxId = await chupDon.mutateAsync({
                            // Chain chốt 31/07: không có số điện thoại thì vẫn chụp được.
                            // Cái mất — không tra lại được theo khách, không xoá theo yêu
                            // cầu chủ thể được — đã ghi ở `Prescription.customer_id`.
                            customerId: customer?.id ?? null,
                            doctorName: tenBacSi.trim(),
                            lines: dongETC.map((l) => ({
                              drugId: l.drugId,
                              quantity: l.quantity,
                            })),
                            file,
                          });
                          setRx({ id: rxId, chuKy: chuKyETC, daDuyet: false });
                        } catch (err) {
                          setRxLoi(
                            err instanceof ApiError
                              ? err.problem.detail
                              : `Không lưu được ảnh — ${
                                  err instanceof Error ? err.message : String(err)
                                }`,
                          );
                        }
                      }}
                    />
                  </label>

                  {/* 🔴 Bước duyệt của dược sĩ — Chain chốt 01/08. Chỉ hiện khi ĐÃ có ảnh
                      cho đúng giỏ này: một nút "duyệt" trên tờ đơn chưa tồn tại là một nút
                      bấm vào để nhận lỗi. */}
                  {rxConHieuLuc &&
                    !rx.daDuyet &&
                    (coQuyenDuyet ? (
                      <button
                        type="button"
                        className={styles.menhGiaNut}
                        style={{ textAlign: "center" }}
                        disabled={duyetDon.isPending}
                        onClick={async () => {
                          setRxLoi(null);
                          try {
                            await duyetDon.mutateAsync(rx.id);
                            setRx((r) => (r === null ? r : { ...r, daDuyet: true }));
                          } catch (err) {
                            setRxLoi(
                              err instanceof ApiError
                                ? err.problem.detail
                                : `Không duyệt được đơn — ${
                                    err instanceof Error ? err.message : String(err)
                                  }`,
                            );
                          }
                        }}
                      >
                        {duyetDon.isPending ? "Đang duyệt…" : "✍️ Dược sĩ duyệt đơn"}
                      </button>
                    ) : (
                      <em>
                        Ảnh đã lưu. Thuốc kê đơn cần <strong>dược sĩ duyệt</strong> mới bán
                        được — tài khoản đang đăng nhập không có quyền đó (Luật Dược Điều
                        6.5.h). Nhờ dược sĩ đăng nhập và bấm duyệt.
                      </em>
                    ))}

                  {rxConHieuLuc && rx.daDuyet && (
                    <strong>✓ Dược sĩ đã duyệt — bán được</strong>
                  )}

              {rxLoi && <p className={styles.error}>{rxLoi}</p>}
              </>
            </div>
          )}

          {lines.length > 0 && (
            <div className={styles.tienKhoi}>
              <div className={styles.menhGia}>
                {[10000, 20000, 50000, 100000, 200000, 500000].map((m) => (
                  <button
                    key={m}
                    type="button"
                    className={styles.menhGiaNut}
                    onClick={() => setTienNhan(String(soTienNhan + m))}
                  >
                    +{formatMoney(String(m))}
                  </button>
                ))}
                {/* Khách đưa đúng số tiền là ca phổ biến nhất — một nút, không phải gõ. */}
                <button
                  type="button"
                  className={styles.menhGiaNut}
                  onClick={() => setTienNhan(String(total))}
                >
                  Đủ tiền
                </button>
                <button
                  type="button"
                  className={styles.menhGiaNut}
                  onClick={() => setTienNhan("")}
                  aria-label="Xoá tiền khách đưa"
                >
                  Xoá
                </button>
              </div>

              <label className={styles.tienHang}>
                <span>Khách đưa</span>
                <input
                  className={styles.tienNhan}
                  inputMode="numeric"
                  value={soTienNhan === 0 ? "" : formatMoney(String(soTienNhan))}
                  onChange={(e) => setTienNhan(e.target.value)}
                  placeholder="0"
                  aria-label="Tiền khách đưa"
                />
              </label>

              <div className={styles.tienHang}>
                <span>Thối lại</span>
                {/* Thiếu tiền hiện số ÂM chứ không hiện 0: thu ngân cần biết còn thiếu
                    bao nhiêu, và một số 0 ở đây đọc y hệt "vừa đủ". */}
                <strong
                  className={thoiLai < 0 ? styles.thoiLaiThieu : styles.thoiLai}
                  data-testid="thoi-lai"
                >
                  {money(String(thoiLai))}
                </strong>
              </div>
            </div>
          )}

          {checkoutError && <p className={styles.error}>{checkoutError}</p>}

          {dangXacNhan && (
            <div className={styles.xacNhanKhoi}>
              <span>
                Bán <strong>{lines.length} món</strong> ·{" "}
                <strong>{money(String(total))}</strong>
                {thoiLai > 0 && ` · thối lại ${money(String(thoiLai))}`}
              </span>
              <button
                type="button"
                className={styles.ghost}
                onClick={() => setDangXacNhan(false)}
              >
                Sửa lại đơn
              </button>
            </div>
          )}

          <button
            className={styles.checkoutButton}
            disabled={
              lines.length === 0 ||
              checkout.isPending ||
              // Chặn ở đây chỉ để đỡ một lượt đi mạng chắc chắn bị từ chối. Cưỡng chế
              // THẬT vẫn ở máy chủ (422) — nút này không phải cổng.
              (canGhiLyDo && lyDoDiUng.trim() === "") ||
              (canGhiLyDoGia && lyDoLechGia.trim() === "")
            }
            onClick={() => {
              // Bước một chỉ mở phần xác nhận, KHÔNG gọi máy chủ. Người bấm nhầm ở bước
              // này không mất gì; ở bước hai thì đã đọc lại số tiền một lần.
              if (!dangXacNhan) {
                setDangXacNhan(true);
                return;
              }
              void handleCheckout();
            }}
          >
            {checkout.isPending
              ? "Đang xử lý..."
              : canGhiLyDo && lyDoDiUng.trim() === ""
                ? "Ghi lý do để bán"
                : "Thanh toán"}
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
          suffix: "đ",
        }}
        onConfirm={confirmPrice}
        onCancel={() => setPriceAsk(null)}
      />
    </div>
  );
}


/**
 * Chỗ lấy thuốc, hiện ngay dưới dòng hàng trong giỏ (Chain giao 2026-07-31).
 *
 * 🔴 Ba điều cố ý:
 *
 * 1. **Không sắp lại** danh sách máy chủ trả về. FEFO là quy tắc nghiệp vụ và máy chủ đã
 *    sắp; mỗi màn hình tự sắp lấy là mỗi màn hình có cơ hội sắp sai một kiểu khác nhau.
 * 2. **Chỉ hiện chỗ đầu tiên**, kèm "+N chỗ khác" nếu còn. Người đứng quầy cần MỘT địa chỉ
 *    để đi, không cần một bảng để đọc — liệt kê hết là biến thông tin thành nhiễu.
 * 3. **"Chưa xếp ô" KHÁC "hết hàng".** Rỗng ở đây nghĩa là hàng có nhưng chưa ai xếp vào
 *    chỗ nào; nói "hết hàng" là nói sai, và người ta sẽ đi từ chối một khách còn mua được.
 */
function ViTriLay({ drugId }: { drugId: string }) {
  const cho = useWhereIs(drugId);
  if (cho.isLoading) return null;

  const ds = cho.data ?? [];
  if (ds.length === 0) {
    return <div className={styles.drugMeta}>📍 chưa xếp ô — hỏi kho</div>;
  }

  const dau = ds[0];
  return (
    <div className={styles.drugMeta} data-testid="vi-tri-lay">
      📍 <strong>{dau.location_path}</strong> · lô {dau.lot_no} · HSD{" "}
      {new Date(dau.expiry_date).toLocaleDateString("vi-VN")} · còn{" "}
      {formatQty(dau.quantity)}
      {ds.length > 1 && ` · +${ds.length - 1} chỗ khác`}
    </div>
  );
}
