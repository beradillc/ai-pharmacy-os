"use client";

import { useMemo, useState } from "react";

import { useDrugNames } from "@/features/catalog/use-drug-names";
import {
  ReceiptNotConfirmedError,
  type ReceiveLineInput,
  remainingOf,
  useConfirmReceipt,
  usePurchaseOrder,
  useReceiveGoods,
} from "@/features/procurement/use-goods-receipt";
import { ApiError } from "@/shared/api/errors";
import type { PurchaseOrderItem, PurchaseOrderListItem } from "@/shared/api/types";
import { formatMoney, formatQty, formatSo } from "@/shared/format/number";
import { DetailDialog } from "@/components/overlay/DetailDialog";

import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/** Một dòng người dùng đang điền. Giữ dạng chuỗi y như người ta gõ — đổi sang
 * `number` sớm là chỗ mất chữ số và là chỗ "0" hoá thành ô trống. */
interface DraftLine {
  quantity: string;
  lot_no: string;
  expiry_date: string;
  unit_cost: string;
}

const EMPTY: DraftLine = { quantity: "", lot_no: "", expiry_date: "", unit_cost: "" };

/** Hôm nay theo giờ ĐỊA PHƯƠNG. `toISOString().slice(0,10)` là giờ UTC — ở
 * Việt Nam, từ 00:00 đến 07:00 nó trả về NGÀY HÔM QUA. Đúng lỗi đã làm hỏng
 * cửa sổ "hôm nay" của màn Hoá đơn (§7bw). */
function todayLocal(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/**
 * Ngăn Nhận hàng — đóng nốt vòng mua hàng: đơn mua → **nhận hàng** → tồn kho tăng.
 *
 * Trước màn này, ba endpoint `goods-receipts` chạy được nhưng **không đường nào
 * gọi tới từ giao diện**: đặt hàng xong thì hàng về kho bằng cách nào không ai
 * trả lời được trong buổi demo.
 *
 * Ba quyết định đáng ghi:
 *
 * ① **Số lô và hạn dùng là bắt buộc, không phải tuỳ chọn.** Backend đã đòi; màn
 *    này đòi sớm hơn để người ta biết trước khi bấm chứ không phải sau khi nhận
 *    422. Thiếu số lô thì thuốc vào kho mà không truy vết được, và khi có công
 *    văn thu hồi lô thì không biết phải gọi ai.
 *
 * ② **Hàng cận hạn/quá hạn: CẢNH BÁO, không CHẶN.** Nhà thuốc thật vẫn phải ghi
 *    nhận một lô giao nhầm hạn để còn trả lại NCC — chặn ở giao diện là buộc họ
 *    ghi sai cho qua cửa. Backend không cấm; giao diện cấm hơn backend nghĩa là
 *    giao diện đang tự quyết nghiệp vụ, đúng thứ bản yêu cầu cấm. Cảnh báo hiện
 *    ngay dưới ô hạn dùng, đỏ khi đã quá hạn, vàng khi dưới 90 ngày.
 *
 * ③ **Nhận thiếu là chuyện thường, nhận thừa thì không.** NCC giao thiếu suốt —
 *    đơn chuyển sang "Nhận một phần" và nhận tiếp lần sau. Còn nhận quá số đặt
 *    thì backend `OverReceiptError` từ chối cả phiếu, nên ô số lượng chặn tại
 *    chỗ kèm số còn lại, đừng để người ta gõ xong 8 dòng rồi mới biết.
 */
export function ReceiveDrawer({
  po,
  onClose,
}: {
  po: PurchaseOrderListItem;
  onClose: () => void;
}) {
  const detail = usePurchaseOrder(po.id);
  const receive = useReceiveGoods();
  const confirmAgain = useConfirmReceipt();

  const [draft, setDraft] = useState<Record<string, DraftLine>>({});
  const [error, setError] = useState<string | null>(null);
  const [pendingGrn, setPendingGrn] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const items = useMemo(
    () => (detail.data?.items ?? []).filter((it) => remainingOf(it) > 0),
    [detail.data],
  );
  const names = useDrugNames(items.map((it) => it.drug_id));

  const lineOf = (id: string): DraftLine => draft[id] ?? EMPTY;
  const setLine = (id: string, patch: Partial<DraftLine>) =>
    setDraft((d) => ({ ...d, [id]: { ...lineOf(id), ...patch } }));

  /** Dòng "đang nhận" = có số lượng > 0. Bỏ trống một dòng là **không nhận dòng
   * đó lần này** — hợp lệ, NCC giao làm nhiều đợt. */
  const active = items.filter((it) => Number(lineOf(it.id).quantity) > 0);

  function validate(): string | null {
    if (active.length === 0) return "Chưa nhập số lượng nhận cho dòng nào.";
    for (const it of active) {
      const line = lineOf(it.id);
      const label = names.nameOf(it.drug_id) ?? `Mã ${it.drug_id.slice(0, 8)}`;
      if (!line.lot_no.trim()) return `${label}: thiếu số lô.`;
      if (!line.expiry_date) return `${label}: thiếu hạn dùng.`;
      if (Number(line.quantity) > remainingOf(it))
        return `${label}: nhận ${line.quantity} vượt số còn lại ${remainingOf(it)}.`;
      if (line.unit_cost !== "" && Number(line.unit_cost) < 0)
        return `${label}: giá nhập không được âm.`;
    }
    return null;
  }

  async function submit() {
    const invalid = validate();
    if (invalid) {
      setError(invalid);
      return;
    }
    setError(null);
    const payload: ReceiveLineInput[] = active.map((it) => {
      const line = lineOf(it.id);
      return {
        po_item_id: it.id,
        drug_id: it.drug_id,
        quantity_received: line.quantity,
        lot_no: line.lot_no.trim(),
        expiry_date: line.expiry_date,
        // Bỏ trống giá nhập ⇒ dùng giá đã đặt trên đơn. Người dỡ hàng thường
        // không cầm hoá đơn NCC; bắt họ gõ lại giá là mời gõ sai.
        unit_cost: line.unit_cost === "" ? it.unit_price : line.unit_cost,
      };
    });

    try {
      const grn = await receive.mutateAsync({ po_id: po.id, items: payload });
      setDone(grn.id);
    } catch (err) {
      if (err instanceof ReceiptNotConfirmedError) {
        setPendingGrn(err.grnId);
        setError(
          "Phiếu nhập ĐÃ TẠO nhưng chưa chốt — tồn kho chưa tăng. " +
            "Bấm “Chốt lại phiếu” bên dưới, ĐỪNG nhập lại từ đầu (sẽ thành hai phiếu).",
        );
      } else {
        setError(err instanceof ApiError ? err.problem.detail : "Không nhận được hàng.");
      }
    }
  }

  async function retryConfirm() {
    if (!pendingGrn) return;
    setError(null);
    try {
      const grn = await confirmAgain.mutateAsync(pendingGrn);
      setPendingGrn(null);
      setDone(grn.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.problem.detail : "Vẫn chưa chốt được phiếu.");
    }
  }

  const busy = receive.isPending || confirmAgain.isPending;

  return (
    <DetailDialog open title={`Nhận hàng · đơn ${po.code}`} onClose={onClose}>

      {done ? (
        <div className={local.notice} role="status">
          {/* 🔴 Câu này từng ghi cứng "Đã nhận hàng và CHỐT PHIẾU" cho cả hai trường hợp, rồi
              ngay sau đó nói phiếu chuyển sang "Nhận một phần" — hai vế NÓI NGƯỢC NHAU trong
              cùng một khối. Người đọc không biết phiếu xong hay chưa, mà đây đúng là câu duy
              nhất trên màn trả lời câu hỏi đó. Lộ ra khi xem lại ảnh của bản quay (kỷ luật
              #20). Nay cả hai vế cùng phân nhánh theo một điều kiện. */}
          <strong>
            {active.length === items.length
              ? "Đã nhận hàng và chốt phiếu."
              : "Đã nhận một phần, phiếu vẫn đang mở."}
          </strong>{" "}
          Tồn kho đã tăng theo từng lô vừa nhập. Đơn mua chuyển sang{" "}
          <strong>{active.length === items.length ? "“Đã nhận đủ”" : "“Nhận một phần”"}</strong>.
          <div className={local.actions}>
            <button type="button" className={styles.button} onClick={onClose}>
              Xong
            </button>
          </div>
        </div>
      ) : (
        <>
          {error && (
            <div className={styles.error} role="alert">
              <span>{error}</span>
              {pendingGrn ? (
                <button
                  type="button"
                  className={styles.retry}
                  onClick={retryConfirm}
                  disabled={busy}
                >
                  {confirmAgain.isPending ? "Đang chốt…" : "Chốt lại phiếu"}
                </button>
              ) : (
                <button type="button" className={styles.retry} onClick={() => setError(null)}>
                  Đóng
                </button>
              )}
            </div>
          )}

          {detail.isLoading ? (
            <>
              <div className={styles.skeleton} />
              <div className={styles.skeleton} />
            </>
          ) : detail.error ? (
            <div className={styles.error} role="alert">
              <span>Không tải được chi tiết đơn.</span>
              <button type="button" className={styles.retry} onClick={() => detail.refetch()}>
                Thử lại
              </button>
            </div>
          ) : items.length === 0 ? (
            <p className={styles.empty}>
              Đơn này đã nhận đủ mọi dòng hàng — không còn gì để nhận.
            </p>
          ) : (
            <>
              <p className={local.hint}>
                Bỏ trống dòng nào là <strong>chưa nhận dòng đó</strong> — nhận tiếp
                lần sau được. Bỏ trống giá nhập thì lấy theo giá đã đặt trên đơn.
              </p>

              <div className={styles.tableWrap}>
                <table className={`${styles.table} ${local.receiveTable}`}>
                  <thead>
                    <tr>
                      <th>Thuốc</th>
                      <th className={styles.num}>Còn phải nhận</th>
                      <th className={styles.num}>Nhận lần này</th>
                      <th>Số lô</th>
                      <th>Hạn dùng</th>
                      <th className={styles.num}>Giá nhập</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <ReceiveRow
                        key={it.id}
                        item={it}
                        line={lineOf(it.id)}
                        name={names.nameOf(it.drug_id)}
                        onChange={(patch) => setLine(it.id, patch)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <div className={local.actions}>
                <span className={styles.muted}>
                  {active.length === 0
                    ? "Chưa chọn dòng nào"
                    : `${active.length}/${items.length} dòng · ${formatMoney(
                        String(
                          active.reduce(
                            (sum, it) =>
                              sum +
                              Number(lineOf(it.id).quantity) *
                                Number(lineOf(it.id).unit_cost || it.unit_price),
                            0,
                          ),
                        ),
                      )} đ`}
                </span>
                <button
                  type="button"
                  className={styles.button}
                  onClick={submit}
                  disabled={busy || active.length === 0 || pendingGrn !== null}
                >
                  {receive.isPending ? "Đang nhận…" : "Nhận hàng & chốt phiếu"}
                </button>
              </div>
            </>
          )}
        </>
      )}
    </DetailDialog>
  );
}

/** Một dòng nhập. Tách ra để cảnh báo hạn dùng nằm cạnh đúng ô của nó — gom hết
 * cảnh báo lên đầu bảng thì với 8 dòng, người đọc không biết dòng nào. */
function ReceiveRow({
  item,
  line,
  name,
  onChange,
}: {
  item: PurchaseOrderItem;
  line: DraftLine;
  name: string | null;
  onChange: (patch: Partial<DraftLine>) => void;
}) {
  const remaining = remainingOf(item);
  const expiryWarning = expiryNote(line.expiry_date);

  return (
    <tr>
      <td>
        {name ?? <span className={styles.muted}>Mã {item.drug_id.slice(0, 8)}</span>}
        {Number(item.quantity_received) > 0 && (
          <span className={`${styles.chip} ${styles.chipMuted} ${local.tag}`}>
            đã nhận {formatQty(item.quantity_received)}
          </span>
        )}
      </td>
      <td className={styles.num}>{remaining}</td>
      <td className={styles.num}>
        <input
          className={`${styles.input} ${local.qty}`}
          type="number"
          inputMode="decimal"
          min={0}
          max={remaining}
          step="any"
          value={line.quantity}
          onChange={(e) => onChange({ quantity: e.target.value })}
          aria-label={`Số lượng nhận — ${name ?? item.drug_id}`}
          placeholder="0"
        />
      </td>
      <td>
        <input
          className={`${styles.input} ${local.lot}`}
          value={line.lot_no}
          onChange={(e) => onChange({ lot_no: e.target.value })}
          aria-label={`Số lô — ${name ?? item.drug_id}`}
          maxLength={64}
          placeholder="bắt buộc"
        />
      </td>
      <td>
        <input
          className={`${styles.input} ${local.date}`}
          type="date"
          value={line.expiry_date}
          onChange={(e) => onChange({ expiry_date: e.target.value })}
          aria-label={`Hạn dùng — ${name ?? item.drug_id}`}
          min={todayLocal()}
        />
        {expiryWarning && (
          <span className={expiryWarning.expired ? local.warnInline : local.hint} role="status">
            {expiryWarning.text}
          </span>
        )}
      </td>
      <td className={styles.num}>
        <input
          className={`${styles.input} ${local.qty}`}
          type="number"
          inputMode="decimal"
          min={0}
          step="any"
          value={line.unit_cost}
          onChange={(e) => onChange({ unit_cost: e.target.value })}
          aria-label={`Giá nhập — ${name ?? item.drug_id}`}
          placeholder={formatSo(item.unit_price)}
        />
      </td>
    </tr>
  );
}

/**
 * Cảnh báo hạn dùng — **cảnh báo, không chặn** (lý do ở docstring ngăn kéo).
 *
 * 🔴 So NGÀY với NGÀY, không so ngày với thời điểm hiện tại. Bản đầu lấy
 * `hạn − Date.now()`, tức là trừ nửa đêm cho 14 giờ chiều, nên một lô hết hạn
 * **đúng hôm nay** ra `−1` và bị dán nhãn *"đã quá hạn 1 ngày"*. Hạn ghi trên
 * vỉ thuốc là ngày **còn** dùng được, không phải ngày đầu tiên hỏng.
 *
 * Lệch một ngày nghe nhỏ, hậu quả thì không: nó gán "quá hạn" cho hàng còn bán
 * được, người nhận hàng học cách bỏ qua cảnh báo, và lúc đó cảnh báo **thật**
 * cũng mất tác dụng. Test bắt được, không phải mắt đọc mã.
 */
export function expiryNote(iso: string): { text: string; expired: boolean } | null {
  if (!iso) return null;
  const expiry = new Date(`${iso}T00:00:00`);
  const today = new Date(`${todayLocal()}T00:00:00`);
  const days = Math.round((expiry.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return { text: `Đã quá hạn ${-days} ngày`, expired: true };
  if (days <= 90) return { text: `Còn ${days} ngày`, expired: false };
  return null;
}
