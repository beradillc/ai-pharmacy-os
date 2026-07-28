"use client";

import { useState } from "react";

import {
  useDismiss,
  useMaterialize,
  useRunReorder,
  useSuggestions,
  useUndoMaterialize,
} from "@/features/analytics/use-suggestions";
import { useAuthStore } from "@/features/auth/auth-store";
import { ApiError } from "@/shared/api/errors";
import type { ReorderSuggestion, SuggestionStatus } from "@/shared/api/types";
import { daysOfStockLeft, formatQty, formatTime } from "@/shared/format/number";

import styles from "./page.module.css";

/** Bao nhiêu giây còn hiện nút hoàn tác. Thuần THỊ GIÁC — máy chủ không đếm
 * giờ; giới hạn thật là đơn còn ở trạng thái nháp (docs/19 §10.1). Hết 10 giây
 * chỉ là thông báo tự ẩn, không phải cửa đóng lại. */
const UNDO_SECONDS = 10;

interface Toast {
  suggestionId: string;
  poCode: string;
}

function drugLabel(s: ReorderSuggestion): string {
  return s.drug_name ?? `Mã ${s.drug_id.slice(0, 8)}`;
}

function supplierLabel(s: ReorderSuggestion): string {
  if (s.supplier_id === null) return "chưa có";
  return s.supplier_name ?? `Mã ${s.supplier_id.slice(0, 8)}`;
}

export default function ReorderPage() {
  const session = useAuthStore((s) => s.session);
  const canAct = new Set(session?.permissions ?? []).has("analytics.reorder.run");

  const [tab, setTab] = useState<SuggestionStatus>("PENDING");
  const { data, isLoading, error, refetch } = useSuggestions(tab);

  const run = useRunReorder();
  const materialize = useMaterialize();
  const undo = useUndoMaterialize();
  const dismiss = useDismiss();

  const [toast, setToast] = useState<Toast | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function report(err: unknown, fallback: string) {
    setActionError(err instanceof ApiError ? err.problem.detail : fallback);
  }

  async function handleMaterialize(s: ReorderSuggestion) {
    setActionError(null);
    try {
      const out = await materialize.mutateAsync(s.id);
      setToast({ suggestionId: s.id, poCode: out.po_code });
      window.setTimeout(
        () => setToast((t) => (t?.suggestionId === s.id ? null : t)),
        UNDO_SECONDS * 1000,
      );
    } catch (err) {
      report(err, "Không tạo được đơn mua nháp.");
    }
  }

  async function handleUndo(suggestionId: string) {
    setActionError(null);
    try {
      await undo.mutateAsync(suggestionId);
      setToast(null);
    } catch (err) {
      // 422 = đơn đã gửi NCC. Phải hiện ra, KHÔNG được nuốt (docs/19 §10.1).
      report(err, "Không hoàn tác được.");
      setToast(null);
    }
  }

  async function handleDismiss(s: ReorderSuggestion) {
    // Bỏ qua là che một cảnh báo tồn kho, không phải đóng một thông báo ⇒ hỏi
    // một lần (docs/19 §5).
    if (!window.confirm(`Bỏ qua đề xuất "${drugLabel(s)}"?`)) return;
    setActionError(null);
    try {
      await dismiss.mutateAsync(s.id);
    } catch (err) {
      report(err, "Không bỏ qua được.");
    }
  }

  const rows = data ?? [];
  const calculatedAt = rows[0]?.calculated_at;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <h1 className={styles.title}>Đề xuất đặt hàng</h1>
        <div className={styles.controls}>
          {calculatedAt && (
            <span className={styles.meta}>Tính lúc {formatTime(calculatedAt)}</span>
          )}
          {canAct && (
            <button
              type="button"
              className={styles.primary}
              onClick={() => run.mutate()}
              disabled={run.isPending}
            >
              {run.isPending ? "Đang tính…" : "Tính lại"}
            </button>
          )}
        </div>
      </div>

      {run.isSuccess && !run.isPending && (
        <p className={styles.summary}>
          Đã xét {run.data.drugs_evaluated} · đề xuất {run.data.suggested} · thiếu dữ liệu{" "}
          {run.data.insufficient_data}
        </p>
      )}

      <div className={styles.tabs} role="tablist">
        {(["PENDING", "DISMISSED"] as const).map((s) => (
          <button
            key={s}
            type="button"
            role="tab"
            aria-selected={tab === s}
            className={tab === s ? styles.tabActive : styles.tab}
            onClick={() => setTab(s)}
          >
            {s === "PENDING" ? "Đang mở" : "Đã bỏ qua"}
          </button>
        ))}
      </div>

      {actionError && (
        <div className={styles.error} role="alert">
          <span>{actionError}</span>
          <button type="button" className={styles.ghost} onClick={() => setActionError(null)}>
            Đóng
          </button>
        </div>
      )}

      {toast && (
        <div className={styles.toast} role="status">
          <span>
            Đã tạo đơn mua nháp <strong className={styles.code}>#{toast.poCode}</strong>
          </span>
          <button
            type="button"
            className={styles.ghost}
            onClick={() => handleUndo(toast.suggestionId)}
            disabled={undo.isPending}
          >
            Hoàn tác
          </button>
        </div>
      )}

      {error && (
        <div className={styles.error} role="alert">
          <span>
            {error instanceof ApiError ? error.problem.detail : "Không tải được đề xuất."}
          </span>
          <button type="button" className={styles.ghost} onClick={() => refetch()}>
            Thử lại
          </button>
        </div>
      )}

      {isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}

      {!isLoading && !error && rows.length === 0 && (
        <p className={styles.empty}>
          {tab === "PENDING"
            ? "Không mặt hàng nào cần đặt thêm."
            : "Chưa bỏ qua đề xuất nào."}
        </p>
      )}

      {rows.length > 0 && (
        <div className={styles.table}>
          <div className={styles.headRow}>
            <span>Thuốc</span>
            <span className={styles.num}>Tồn</span>
            <span className={styles.num}>Điểm đặt</span>
            <span className={styles.num}>Bán/ngày</span>
            <span className={styles.num}>Đề xuất</span>
            <span>Nhà cung cấp</span>
          </div>

          {rows.map((s) => {
            const daysLeft = daysOfStockLeft(s.on_hand_at_calc, s.avg_daily_velocity);
            const thin = s.status === "INSUFFICIENT_DATA" || daysLeft === null;
            return (
              <div key={s.id} className={styles.item}>
                <div className={styles.dataRow}>
                  <span className={styles.name}>{drugLabel(s)}</span>
                  <span className={styles.num}>{formatQty(s.on_hand_at_calc)}</span>
                  <span className={styles.num}>{thin ? "—" : formatQty(s.reorder_point)}</span>
                  <span className={styles.num}>
                    {thin ? "—" : formatQty(s.avg_daily_velocity)}
                  </span>
                  <span className={styles.num}>{thin ? "—" : formatQty(s.suggested_qty)}</span>
                  <span className={styles.supplier}>{supplierLabel(s)}</span>
                </div>

                <div className={styles.actionRow}>
                  <span className={thin ? styles.chipNeutral : styles.chipUrgent}>
                    {thin ? "Chưa đủ dữ liệu bán" : `Hết trong ~${daysLeft} ngày`}
                  </span>
                  {canAct && tab === "PENDING" && (
                    <span className={styles.actions}>
                      <button
                        type="button"
                        className={styles.primarySmall}
                        onClick={() => handleMaterialize(s)}
                        disabled={!s.can_materialize || materialize.isPending}
                        title={
                          s.can_materialize
                            ? undefined
                            : "Chưa gán nhà cung cấp — không tạo được đơn nháp"
                        }
                      >
                        Tạo đơn nháp
                      </button>
                      <button
                        type="button"
                        className={styles.ghost}
                        onClick={() => handleDismiss(s)}
                        disabled={dismiss.isPending}
                      >
                        Bỏ qua
                      </button>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
