"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useCatalogDrugs } from "@/features/catalog/use-drug-ingredients";
import { useLocations } from "@/features/location/use-locations";
import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import { TabManGop } from "@/components/layout/TabManGop";

import local from "./page.module.css";

/**
 * Nhập hàng nhanh — **không cần đơn mua hàng** (BERAS V2 Phase 6).
 *
 * 🔴 Vì sao màn này tồn tại dù `POST /inventory/receive` đã có từ lâu: cái thiếu chưa bao
 * giờ là API, mà là **chỗ để bấm**. Nhà thuốc Việt Nam nhận hàng từ trình dược viên đứng
 * ngay tại quầy — dựng một đơn mua hàng trước để rồi xác nhận nhận đúng cái vừa dựng là
 * thêm hai bước cho một việc mất ba mươi giây.
 *
 * Bố cục **một cột, ô nhập từ trên xuống theo đúng thứ tự tay người ta làm**: thuốc → số
 * lượng → lô → hạn dùng → vị trí. Không có bảng, không có gì phải kéo ngang — đây là màn
 * dùng trên điện thoại, đứng cạnh thùng hàng.
 */
const TAB_NHAP = [
  { href: "/nhap-nhanh", nhan: "Nhập hàng nhanh" },
  { href: "/khoi-tao-ton", nhan: "Khởi tạo tồn kho" },
] as const;

export default function QuickReceivePage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const coQuyen = quyen.has("inventory.receive");

  const drugs = useCatalogDrugs();
  const locs = useLocations();

  const [drugId, setDrugId] = useState("");
  const [soLuong, setSoLuong] = useState("");
  const [lo, setLo] = useState("");
  const [hsd, setHsd] = useState("");
  const [giaVon, setGiaVon] = useState("");
  const [viTri, setViTri] = useState("");
  const [dangLuu, setDangLuu] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);
  const [daNhan, setDaNhan] = useState<string[]>([]);

  if (!coQuyen) {
    return (
      <div className={styles.page}>
        <div className={styles.head}>
          <div>
            <h1 className={styles.title}>Nhập hàng nhanh</h1>
          </div>
        </div>
        <p className={styles.hint}>Bạn không có quyền nhận hàng.</p>
      </div>
    );
  }

  const cho = (locs.data ?? []).filter((l) => l.kind === "BIN" || l.kind === "SHELF");
  const tenThuoc = (drugs.data ?? []).find((d) => d.id === drugId)?.name ?? "";
  const duDe = drugId !== "" && soLuong.trim() !== "" && lo.trim() !== "" && hsd !== "";

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Nhập hàng nhanh</h1>
          <p className={styles.subtitle}>
            Không cần đơn mua hàng. Nhận xong, chọn ô là hàng có địa chỉ ngay — quầy thấy
            chỗ lấy mà không phải đợi ai xếp kệ.
          </p>
        </div>
      </div>
      <TabManGop tabs={TAB_NHAP} />

      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      <div className={local.form}>
        <label className={local.o}>
          <span className={local.nhan}>Thuốc</span>
          <select
            className={styles.select}
            value={drugId}
            onChange={(e) => setDrugId(e.target.value)}
            aria-label="Chọn thuốc"
          >
            <option value="">— chọn thuốc —</option>
            {(drugs.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Số lượng</span>
          <input
            className={styles.input}
            inputMode="numeric"
            value={soLuong}
            onChange={(e) => setSoLuong(e.target.value)}
            aria-label="Số lượng nhập"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Số lô</span>
          <input
            className={styles.input}
            value={lo}
            onChange={(e) => setLo(e.target.value)}
            placeholder="Theo vỏ hộp"
            aria-label="Số lô"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Hạn dùng</span>
          <input
            className={styles.input}
            type="date"
            value={hsd}
            onChange={(e) => setHsd(e.target.value)}
            aria-label="Hạn dùng"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Giá vốn (không bắt buộc)</span>
          <input
            className={styles.input}
            inputMode="numeric"
            value={giaVon}
            onChange={(e) => setGiaVon(e.target.value)}
            placeholder="0"
            aria-label="Giá vốn"
          />
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Sắp xếp (không bắt buộc)</span>
          <select
            className={styles.select}
            value={viTri}
            onChange={(e) => setViTri(e.target.value)}
            aria-label="Sắp xếp vào ô"
          >
            <option value="">— để xếp sau —</option>
            {cho.map((l) => (
              <option key={l.id} value={l.id}>
                {l.path}
                {l.name ? ` · ${l.name}` : ""}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className={styles.button}
          disabled={dangLuu || !duDe}
          onClick={async () => {
            setLoi(null);
            setDangLuu(true);
            try {
              await apiFetch("/inventory/receive", {
                method: "POST",
                body: {
                  drug_id: drugId,
                  lot_no: lo.trim(),
                  expiry_date: hsd,
                  quantity: soLuong.trim(),
                  cost_price: giaVon.trim() || "0",
                  location_id: viTri || null,
                },
              });
              // Giữ lại THUỐC và VỊ TRÍ, xoá số lượng/lô/HSD: nhận nhiều lô của cùng một
              // mặt hàng vào cùng một ô là ca thường gặp nhất, và bắt chọn lại từ đầu mỗi
              // lượt là bắt làm lại đúng phần không đổi.
              setDaNhan((t) => [
                `${tenThuoc} · lô ${lo.trim()} · ${soLuong.trim()}` +
                  (viTri ? ` → ${cho.find((l) => l.id === viTri)?.path ?? ""}` : " (chưa xếp ô)"),
                ...t,
              ]);
              setSoLuong("");
              setLo("");
              setHsd("");
            } catch (err) {
              setLoi(
                err instanceof ApiError
                  ? err.problem.detail
                  : `Không nhận được — ${err instanceof Error ? err.message : String(err)}`,
              );
            } finally {
              setDangLuu(false);
            }
          }}
        >
          {dangLuu ? "Đang lưu…" : "Nhận vào kho"}
        </button>
      </div>

      {daNhan.length > 0 && (
        <>
          <h2 className={local.nhan}>Đã nhận trong lượt này</h2>
          <ul className={local.daNhan} data-testid="da-nhan">
            {daNhan.map((d, i) => (
              <li key={`${d}-${i}`}>✓ {d}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
