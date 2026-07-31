"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useCatalogDrugs } from "@/features/catalog/use-drug-ingredients";
import { useLocations } from "@/features/location/use-locations";
import { apiFetch } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

/**
 * **Khởi tạo tồn kho, nhập theo kệ** (BERAS V2 Phase 9-10).
 *
 * Dùng đúng một lần trong đời mỗi nhà thuốc: ngày chuyển từ sổ giấy / phần mềm cũ sang
 * đây. Người ta cầm điện thoại đi dọc kệ, đếm từng ô.
 *
 * 🔴 Vì sao KHÔNG dùng lại `/nhap-nhanh` mà dựng màn riêng — khác nhau ở thứ tự, và thứ
 * tự là toàn bộ vấn đề:
 *
 * | | Nhập hàng nhanh | Khởi tạo tồn |
 * |---|---|---|
 * | Đứng đâu | cạnh thùng hàng vừa dỡ | **đi dọc kệ** |
 * | Cái gì cố định | mặt hàng đang nhận | **cái ô đang đứng trước mặt** |
 * | Ô nhập vị trí | dưới cùng, không bắt buộc | **trên cùng, chọn một lần, khoá lại** |
 *
 * Đếm một ô có mười hai mặt hàng mà mỗi lượt phải chọn lại ô là mười hai lần chọn lại một
 * thứ không đổi — và mỗi lần chọn lại là một cơ hội chọn nhầm ô bên cạnh.
 *
 * 🔴 Và nó gọi `POST /inventory/initialize`, KHÔNG phải `/receive`: xem
 * `ReceiveStockInput.is_initial` về việc vì sao trộn hai thứ làm hỏng giá vốn bình quân.
 */
export default function StockInitPage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const coQuyen = quyen.has("inventory.receive");

  const drugs = useCatalogDrugs();
  const locs = useLocations();

  const [o, setO] = useState("");
  const [daKhoa, setDaKhoa] = useState(false);
  const [drugId, setDrugId] = useState("");
  const [soLuong, setSoLuong] = useState("");
  const [lo, setLo] = useState("");
  const [hsd, setHsd] = useState("");
  const [dangLuu, setDangLuu] = useState(false);
  const [loi, setLoi] = useState<string | null>(null);
  const [daDem, setDaDem] = useState<string[]>([]);

  if (!coQuyen) {
    return (
      <div className={styles.page}>
        <div className={styles.head}>
          <div>
            <h1 className={styles.title}>Khởi tạo tồn kho</h1>
          </div>
        </div>
        <p className={styles.hint}>Bạn không có quyền nhận hàng.</p>
      </div>
    );
  }

  const cho = (locs.data ?? []).filter((l) => l.kind === "BIN" || l.kind === "SHELF");
  const oDangDung = cho.find((l) => l.id === o);
  const tenThuoc = (drugs.data ?? []).find((d) => d.id === drugId)?.name ?? "";
  const duDe = drugId !== "" && soLuong.trim() !== "" && lo.trim() !== "" && hsd !== "";

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Khởi tạo tồn kho</h1>
          <p className={styles.subtitle}>
            Ngày chuyển sang phần mềm: đi dọc kệ, chọn ô một lần rồi đếm hết ô đó. Đây{" "}
            <strong>không phải nhập mua</strong> — không vào báo cáo mua hàng, không đụng
            giá vốn.
          </p>
        </div>
      </div>

      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      {/* ─── Bước 1: chọn ô, MỘT LẦN ─────────────────────────────────────────────── */}
      <section className={local.oDang} data-testid="o-dang-dem">
        {daKhoa && oDangDung ? (
          <>
            <span className={local.nhanO}>Đang đếm ô</span>
            <strong className={local.duongDan}>{oDangDung.path}</strong>
            {oDangDung.name && <span className={local.tenO}>{oDangDung.name}</span>}
            {/* Đổi ô là hành động CÓ CHỦ Ý, không phải một ô select luôn mở. Người đi kiểm
                kê cầm điện thoại một tay — một select mở sẵn ngay trên đầu màn là thứ dễ
                quẹt trúng nhất, và quẹt trúng nó thì mọi dòng sau đó vào nhầm ô. */}
            <button
              type="button"
              className={styles.ghost}
              onClick={() => {
                setDaKhoa(false);
                setDaDem([]);
              }}
            >
              Đổi ô khác
            </button>
          </>
        ) : (
          <>
            <label className={local.o}>
              <span className={local.nhan}>Đang đứng trước ô nào?</span>
              <select
                className={styles.select}
                value={o}
                onChange={(e) => setO(e.target.value)}
                aria-label="Chọn ô đang đếm"
              >
                <option value="">— chọn ô —</option>
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
              disabled={o === ""}
              onClick={() => setDaKhoa(true)}
            >
              Bắt đầu đếm ô này
            </button>
          </>
        )}
      </section>

      {/* ─── Bước 2: đếm từng mặt hàng trong ô đó ────────────────────────────────── */}
      {daKhoa && (
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
            <span className={local.nhan}>Đếm được bao nhiêu</span>
            <input
              className={styles.input}
              inputMode="numeric"
              value={soLuong}
              onChange={(e) => setSoLuong(e.target.value)}
              aria-label="Số lượng đếm được"
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

          <p className={local.ghiChu}>
            Không hỏi giá vốn. Hàng đã nằm trên kệ từ trước, giá nhập thật nằm ở hoá đơn cũ
            — điền một con số đoán vào đây sẽ thành giá vốn trong mọi báo cáo lãi gộp sau
            này.
          </p>

          <button
            type="button"
            className={styles.button}
            disabled={dangLuu || !duDe}
            onClick={async () => {
              setLoi(null);
              setDangLuu(true);
              try {
                await apiFetch("/inventory/initialize", {
                  method: "POST",
                  body: {
                    drug_id: drugId,
                    lot_no: lo.trim(),
                    expiry_date: hsd,
                    quantity: soLuong.trim(),
                    cost_price: "0",
                    location_id: o,
                  },
                });
                setDaDem((t) => [
                  `${tenThuoc} · lô ${lo.trim()} · ${soLuong.trim()}`,
                  ...t,
                ]);
                // Xoá HẾT phần mặt hàng, giữ nguyên ô: mặt hàng kế tiếp trong cùng ô là
                // một mặt hàng KHÁC. Giữ lại thuốc cũ như `/nhap-nhanh` sẽ sai ở đây —
                // ở đó cái lặp là mặt hàng, ở đây cái lặp là ô.
                setDrugId("");
                setSoLuong("");
                setLo("");
                setHsd("");
              } catch (err) {
                setLoi(
                  err instanceof ApiError
                    ? err.problem.detail
                    : `Không lưu được — ${err instanceof Error ? err.message : String(err)}`,
                );
              } finally {
                setDangLuu(false);
              }
            }}
          >
            {dangLuu ? "Đang lưu…" : "Ghi vào ô này"}
          </button>

          {daDem.length > 0 && (
            <>
              <p className={local.nhan}>
                Đã đếm trong {oDangDung?.path} ({daDem.length} mặt hàng)
              </p>
              <ul className={local.daDem} data-testid="da-dem">
                {daDem.map((d, i) => (
                  <li key={i}>✓ {d}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
