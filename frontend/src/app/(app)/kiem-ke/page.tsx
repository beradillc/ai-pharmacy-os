"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useDrugNames } from "@/features/catalog/use-drug-names";
import {
  NHAN_TRANG_THAI,
  useApproveCount,
  useCountLine,
  useOpenCount,
  useRejectCount,
  useStockCount,
  useStockCounts,
  useSubmitCount,
} from "@/features/inventory/use-stock-count";
import { useLocations, useStockAtLocation } from "@/features/location/use-locations";
import { ApiError } from "@/shared/api/errors";
import type { StockCount } from "@/shared/api/types";
import styles from "@/shared/ui/screen.module.css";

import { TabManGop } from "@/components/layout/TabManGop";

import local from "./page.module.css";

/**
 * **Kiểm kê theo ô** (BERAS V2 Phase 11).
 *
 * Đếm tay, so với sổ, chênh thì **chờ duyệt** — không tự áp vào tồn kho. Con số đếm được
 * là một *lời khai*, không phải một *sự thật*: đếm sót một hộp khuất sau lô khác thì hệ
 * thống sẽ ghi nhận mất hàng, và một khi đã thành chuyển động thì nó nằm trong sổ vĩnh viễn.
 *
 * 🔴 Ba chỗ màn này cố ý làm khác thói quen:
 *
 * 1. **Danh sách lô của ô được nạp sẵn** — người đếm không phải nhớ ô có lô nào. Họ chỉ
 *    điền số vào từng dòng có sẵn, và thêm dòng khi tìm thấy lô hệ thống không biết.
 * 2. **Chưa nộp thì cột "sổ ghi" để trống**, không hiện 0. Xem `StockCountLine.system_qty`.
 * 3. **Nút Duyệt chỉ hiện với người có `inventory.reconcile`** — nhưng KHÔNG chặn người
 *    đếm tự duyệt phiếu mình. Nhà thuốc nhỏ chỉ có một người; chặn thì tính năng vô dụng
 *    với nhóm khách hàng đông nhất. Thay vào đó hiện **cả hai tên** để trùng nhau thì
 *    nhìn ra được.
 */
const TAB_KHO = [
  { href: "/so-do-kho", nhan: "Sơ đồ kho" },
  { href: "/kiem-ke", nhan: "Kiểm kê" },
] as const;

export default function StockCountPage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const demDuoc = quyen.has("inventory.receive");
  const duyetDuoc = quyen.has("inventory.reconcile");

  const [dangMo, setDangMo] = useState<string | null>(null);
  const ds = useStockCounts();

  if (!quyen.has("inventory.read")) {
    return (
      <div className={styles.page}>
        <div className={styles.head}>
          <div>
            <h1 className={styles.title}>Kiểm kê</h1>
          </div>
        </div>
        <p className={styles.hint}>Bạn không có quyền xem tồn kho.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Kiểm kê</h1>
          <p className={styles.subtitle}>
            Đếm từng ô, so với sổ. Chênh lệch <strong>chờ duyệt</strong> — tồn kho chỉ đổi
            sau khi có người ký, không đổi lúc nộp.
          </p>
        </div>
      </div>
      <TabManGop tabs={TAB_KHO} />

      {demDuoc && <MoPhien onMo={setDangMo} />}

      {ds.isLoading ? (
        <p className={styles.hint}>Đang tải…</p>
      ) : (ds.data ?? []).length === 0 ? (
        <p className={styles.hint}>
          Chưa có phiên kiểm kê nào. Chọn một ô ở trên để bắt đầu đếm.
        </p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={`${styles.table} ${local.bangThe}`}>
            <thead>
              <tr>
                <th>Mở lúc</th>
                <th>Ô</th>
                <th>Trạng thái</th>
                <th className={styles.num}>Số dòng</th>
                <th />
              </tr>
            </thead>
            <tbody data-testid="ds-phien">
              {(ds.data ?? []).map((p) => (
                <DongPhien key={p.id} p={p} onMo={() => setDangMo(p.id === dangMo ? null : p.id)} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dangMo !== null && (
        <ChiTietPhien
          id={dangMo}
          demDuoc={demDuoc}
          duyetDuoc={duyetDuoc}
          onClose={() => setDangMo(null)}
        />
      )}
    </div>
  );
}

function DongPhien({ p, onMo }: { p: StockCount; onMo: () => void }) {
  const locs = useLocations();
  const o = (locs.data ?? []).find((l) => l.id === p.location_id);
  return (
    <tr>
      <td data-nhan="Mở lúc">{new Date(p.created_at).toLocaleString("vi-VN")}</td>
      <td data-nhan="Ô" className={styles.mono}>{o?.path ?? p.location_id.slice(0, 8)}</td>
      <td data-nhan="Trạng thái">
        <span className={local[`tt_${p.status}`] ?? ""}>{NHAN_TRANG_THAI[p.status]}</span>
      </td>
      <td data-nhan="Số dòng" className={styles.num}>{p.lines.length}</td>
      <td className={`${styles.num} ${local.oNut}`}>
        <button type="button" className={styles.ghost} onClick={onMo}>
          Mở
        </button>
      </td>
    </tr>
  );
}

function MoPhien({ onMo }: { onMo: (id: string) => void }) {
  const locs = useLocations();
  const [o, setO] = useState("");
  const [loi, setLoi] = useState<string | null>(null);
  const mo = useOpenCount();
  const cho = (locs.data ?? []).filter((l) => l.kind === "BIN" || l.kind === "SHELF");

  return (
    <div className={styles.controls}>
      <select
        className={styles.select}
        value={o}
        onChange={(e) => setO(e.target.value)}
        aria-label="Chọn ô để kiểm kê"
      >
        <option value="">— chọn ô để kiểm —</option>
        {cho.map((l) => (
          <option key={l.id} value={l.id}>
            {l.path}
            {l.name ? ` · ${l.name}` : ""}
          </option>
        ))}
      </select>
      <button
        type="button"
        className={styles.button}
        disabled={o === "" || mo.isPending}
        onClick={async () => {
          setLoi(null);
          try {
            onMo((await mo.mutateAsync(o)).id);
          } catch (err) {
            setLoi(err instanceof ApiError ? err.problem.detail : String(err));
          }
        }}
      >
        {mo.isPending ? "Đang mở…" : "Bắt đầu kiểm ô này"}
      </button>
      {loi && (
        <span className={styles.error} role="alert">
          {loi}
        </span>
      )}
    </div>
  );
}

function ChiTietPhien({
  id,
  demDuoc,
  duyetDuoc,
  onClose,
}: {
  id: string;
  demDuoc: boolean;
  duyetDuoc: boolean;
  onClose: () => void;
}) {
  const phien = useStockCount(id);
  const locs = useLocations();
  const [loi, setLoi] = useState<string | null>(null);

  const ghi = useCountLine();
  const nop = useSubmitCount();
  const duyet = useApproveCount();
  const tuChoi = useRejectCount();

  const p = phien.data;
  const o = (locs.data ?? []).find((l) => l.id === p?.location_id);
  // Nạp sẵn lô đang nằm trong ô — người đếm không phải nhớ ô có gì.
  const trongO = useStockAtLocation(p?.location_id ?? null);
  // `inventory` không được import `catalog`, nên dòng tồn chỉ có `drug_id`. Tên thuốc gắn
  // ở tầng màn hình bằng hook đã có sẵn (màn Hoá đơn dùng từ Sprint 10) — không dựng hook
  // thứ hai cho cùng một việc.
  const tenThuoc = useDrugNames((trongO.data ?? []).map((r) => r.drug_id));

  if (!p) {
    return (
      <section className={styles.drawer} aria-label="Phiên kiểm kê">
        <p className={styles.hint}>Đang tải…</p>
      </section>
    );
  }

  const dangDem = p.status === "DANG_DEM";
  const choDuyet = p.status === "CHO_DUYET";
  const daDem = new Map(p.lines.map((d) => [d.batch_id, d]));

  const chay = async (fn: () => Promise<unknown>) => {
    setLoi(null);
    try {
      await fn();
    } catch (err) {
      setLoi(err instanceof ApiError ? err.problem.detail : String(err));
    }
  };

  return (
    <section className={styles.drawer} aria-label="Phiên kiểm kê">
      <div className={styles.drawerHead}>
        <h2 className={styles.drawerTitle}>
          Kiểm {o?.path ?? "ô"} · {NHAN_TRANG_THAI[p.status]}
        </h2>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Đóng
        </button>
      </div>

      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={`${styles.table} ${local.bangThe}`} data-testid="bang-dem">
          <thead>
            <tr>
              {/* 🔴 Chain giao 01/08: xem hàng phải là TÊN THUỐC, không phải số lô. Người
                  đếm cầm hộp thuốc trên tay và đối chiếu bằng tên — số lô chỉ để phân biệt
                  hai hộp cùng tên, nên nó là thông tin PHỤ, đặt dưới tên. */}
              <th>Thuốc</th>
              <th>Hạn dùng</th>
              <th className={styles.num}>Đếm được</th>
              <th className={styles.num}>Sổ ghi</th>
              <th className={styles.num}>Chênh</th>
            </tr>
          </thead>
          <tbody>
            {(trongO.data ?? []).map((r) => (
              <DongDem
                key={r.batch_id}
                ten={tenThuoc.nameOf(r.drug_id)}
                lot={r.lot_no}
                hsd={r.expiry_date}
                dong={daDem.get(r.batch_id) ?? null}
                doiDuoc={dangDem && demDuoc}
                onGhi={(sl) => chay(() => ghi.mutateAsync({ countId: id, batch_id: r.batch_id, counted_qty: sl }))}
              />
            ))}
          </tbody>
        </table>
      </div>

      {(trongO.data ?? []).length === 0 && (
        <p className={styles.hint}>Ô này chưa có hàng trong sổ — không có gì để đối chiếu.</p>
      )}

      <p className={local.aiLam}>
        Người đếm <strong>{p.counted_by.slice(0, 8)}</strong>
        {p.decided_by !== null && (
          <>
            {" · "}người duyệt <strong>{p.decided_by.slice(0, 8)}</strong>
            {p.decided_by === p.counted_by && (
              <span className={local.trungTen}> (cùng một người)</span>
            )}
          </>
        )}
      </p>

      <div className={local.cuoi}>
        {dangDem && demDuoc && (
          <button
            type="button"
            className={styles.button}
            disabled={nop.isPending || p.lines.length === 0}
            onClick={() => chay(() => nop.mutateAsync(id))}
          >
            {nop.isPending ? "Đang nộp…" : "Nộp phiên"}
          </button>
        )}
        {choDuyet && duyetDuoc && (
          <>
            <button
              type="button"
              className={styles.button}
              disabled={duyet.isPending}
              onClick={() => chay(() => duyet.mutateAsync(id))}
            >
              {duyet.isPending ? "Đang duyệt…" : "Duyệt — áp vào tồn kho"}
            </button>
            <button
              type="button"
              className={styles.ghost}
              disabled={tuChoi.isPending}
              onClick={() => chay(() => tuChoi.mutateAsync(id))}
            >
              Từ chối
            </button>
          </>
        )}
        {choDuyet && !duyetDuoc && (
          <p className={styles.hint}>
            Phiên đã nộp, đang chờ người có quyền duyệt. Tồn kho <strong>chưa</strong> đổi.
          </p>
        )}
      </div>
    </section>
  );
}

function DongDem({
  ten,
  lot,
  hsd,
  dong,
  doiDuoc,
  onGhi,
}: {
  /** `null` khi danh mục chưa tải xong hoặc mặt hàng đã bị xoá — hiện mã rút gọn thay vì
   *  một ô trống, để người đếm còn biết mình đang đối chiếu cái gì. */
  ten: string | null;
  lot: string;
  hsd: string;
  dong: { counted_qty: string; system_qty: string | null; lech: string | null } | null;
  doiDuoc: boolean;
  onGhi: (soLuong: string) => void;
}) {
  const [nhap, setNhap] = useState(dong?.counted_qty ?? "");
  const lech = dong?.lech === null || dong?.lech === undefined ? null : Number(dong.lech);

  return (
    <tr>
      <td data-nhan="Thuốc">
        <div>{ten ?? "—"}</div>
        <div className={`${styles.mono} ${local.soLo}`}>Lô {lot}</div>
      </td>
      <td data-nhan="Hạn dùng">{new Date(hsd).toLocaleDateString("vi-VN")}</td>
      <td data-nhan="Đếm được" className={styles.num}>
        {doiDuoc ? (
          <input
            className={local.oSo}
            inputMode="numeric"
            value={nhap}
            onChange={(e) => setNhap(e.target.value)}
            onBlur={() => nhap.trim() !== "" && onGhi(nhap.trim())}
            aria-label={`Đếm được lô ${lot}`}
          />
        ) : (
          (dong?.counted_qty ?? "—")
        )}
      </td>
      {/* 🔴 Chưa nộp thì để TRỐNG, không hiện 0 — 0 đọc y hệt "đã chốt và khớp". */}
      <td data-nhan="Sổ ghi" className={styles.num}>{dong?.system_qty ?? "—"}</td>
      <td
        data-nhan="Chênh"
        className={`${styles.num} ${lech === null ? "" : lech === 0 ? local.khop : local.lech}`}
      >
        {lech === null ? "—" : lech > 0 ? `+${lech}` : lech}
      </td>
    </tr>
  );
}
