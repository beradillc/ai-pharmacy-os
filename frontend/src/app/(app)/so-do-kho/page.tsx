"use client";

import { useMemo, useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useDrugNames } from "@/features/catalog/use-drug-names";
import {
  NHAN_TANG,
  TANG_DUOI,
  useCreateLocation,
  useLocations,
  useTomTatO,
  useStockAtLocation,
  useUpdateLocation,
} from "@/features/location/use-locations";
import { ApiError } from "@/shared/api/errors";
import { formatQty } from "@/shared/format/number";
import type { TomTatO } from "@/features/location/use-locations";
import type { StorageLocation } from "@/shared/api/types";
import { DetailDialog } from "@/components/overlay/DetailDialog";

import styles from "@/shared/ui/screen.module.css";

import { TabManGop } from "@/components/layout/TabManGop";

import local from "./page.module.css";

/**
 * Sơ đồ kho — Kho → Khu → Kệ → Ô (BERAS V2 Phase 1).
 *
 * 🔴 Ba điều màn này cố ý làm khác thói quen, mỗi điều một lý do:
 *
 * 1. **Không có ô sửa MÃ.** Mã bất biến sau khi tạo — đổi mã buộc viết lại đường dẫn cả cây
 *    con, đúng loại thao tác hay hỏng nửa chừng. Hiện một ô rồi từ chối lưu còn tệ hơn không
 *    hiện.
 * 2. **Ô "thứ tự lấy hàng" đứng ngang hàng với mã**, không giấu trong trang con: quãng đường
 *    trong kho không suy ra được từ mã, và nếu ô này khó tìm thì không ai điền — Pick List
 *    sau đó chỉ còn cách sắp theo bảng chữ cái.
 * 3. **Danh sách tầng con lọc theo tầng cha.** Bỏ tầng thì được (Kho → Kệ), đảo tầng thì
 *    không. Chặn ở đây chỉ để đỡ một lượt đi mạng chắc chắn bị từ chối — cưỡng chế thật
 *    nằm ở máy chủ.
 */
const TAB_KHO = [
  { href: "/so-do-kho", nhan: "Sơ đồ kho" },
  { href: "/kiem-ke", nhan: "Kiểm kê" },
] as const;

export default function WarehouseMapPage() {
  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const coQuyenSua = quyen.has("location.write");

  const [hienCaNgung, setHienCaNgung] = useState(false);
  const [dangThem, setDangThem] = useState<StorageLocation | "ROOT" | null>(null);
  const [dangMo, setDangMo] = useState<StorageLocation | null>(null);
  const ds = useLocations(hienCaNgung);
  const tomTat = useTomTatO();
  /** Chỉ tầng Ô mới lên lưới: Kho/Khu/Kệ là cấu trúc, không phải chỗ đặt hàng. */
  const dsO = useMemo(
    () => (ds.data ?? []).filter((l) => l.kind === "BIN").sort((a, b) => a.pick_order - b.pick_order),
    [ds.data],
  );

  /** Cây dựng từ danh sách phẳng — máy chủ đã sắp sẵn theo thứ tự đi lấy hàng. */
  const theoCha = useMemo(() => {
    const m = new Map<string | null, StorageLocation[]>();
    for (const l of ds.data ?? []) {
      const k = l.parent_id;
      m.set(k, [...(m.get(k) ?? []), l]);
    }
    return m;
  }, [ds.data]);

  const soVitri = (ds.data ?? []).length;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Sơ đồ kho</h1>
          <p className={styles.subtitle}>
            Kho → Khu → Kệ → Ô. Mã do nhà thuốc tự đặt; thứ tự đi lấy hàng do người xếp kho
            đặt — hệ thống không đoán được từ mã.
          </p>
        </div>
      </div>
      <TabManGop tabs={TAB_KHO} />

      <div className={styles.controls}>
        {coQuyenSua && (
          <button type="button" className={styles.button} onClick={() => setDangThem("ROOT")}>
            + Thêm kho
          </button>
        )}
        <label className={local.hopChon}>
          <input
            type="checkbox"
            checked={hienCaNgung}
            onChange={(e) => setHienCaNgung(e.target.checked)}
            aria-label="Hiện cả vị trí đã ngừng"
          />
          <span>Hiện cả chỗ đã ngừng</span>
        </label>
      </div>

      {/* 🔴 Sơ đồ trực quan MỨC 1 (BERAS V2 Phase 12). Lưới các Ô, xếp theo THỨ TỰ ĐI LẤY —
          trái sang phải đúng đường chân đi trong kho.

          Cố ý KHÔNG có "phần trăm đầy" và KHÔNG có toạ độ mặt bằng: kho chưa khai sức chứa
          của ô nào và chưa ai đo toạ độ. Một bản đồ dựng từ con số không có thật thì **tệ
          hơn không có bản đồ** — người ta tin vào nó. Mức 2 (mặt bằng thật) chờ có người
          đo, xem `docs/inventory/LOCATION_MAP.md`. */}
      {soVitri > 0 && (
        <LuoiO
          o={dsO}
          tomTat={tomTat.data ?? []}
          dangTai={tomTat.isLoading}
          onMo={setDangMo}
        />
      )}

      {ds.isLoading ? (
        <p className={styles.hint}>Đang tải…</p>
      ) : soVitri === 0 ? (
        <p className={styles.hint}>
          Chưa có vị trí nào. Bắt đầu bằng một <strong>Kho</strong>, rồi thêm Khu/Kệ/Ô bên
          dưới. Nhà thuốc nhỏ có thể bỏ qua Khu — đi thẳng Kho → Kệ.
        </p>
      ) : (
        <ul className={local.cay} data-testid="cay-so-do">
          {(theoCha.get(null) ?? []).map((goc) => (
            <Nhanh
              key={goc.id}
              nut={goc}
              theoCha={theoCha}
              coQuyenSua={coQuyenSua}
              onThem={setDangThem}
              onMo={setDangMo}
            />
          ))}
        </ul>
      )}

      {dangMo !== null && <TrongO o={dangMo} onClose={() => setDangMo(null)} />}

      {dangThem !== null && (
        <ThemViTri cha={dangThem === "ROOT" ? null : dangThem} onClose={() => setDangThem(null)} />
      )}
    </div>
  );
}

function Nhanh({
  nut,
  theoCha,
  coQuyenSua,
  onThem,
  onMo,
}: {
  nut: StorageLocation;
  theoCha: Map<string | null, StorageLocation[]>;
  coQuyenSua: boolean;
  onThem: (l: StorageLocation) => void;
  onMo: (l: StorageLocation) => void;
}) {
  const con = theoCha.get(nut.id) ?? [];
  const doi = useUpdateLocation();
  const themDuoc = coQuyenSua && (TANG_DUOI[nut.kind] ?? []).length > 0;

  return (
    <li className={local.nhanh}>
      <div className={`${local.nut} ${nut.is_active ? "" : local.daNgung}`}>
        <span className={local.tang}>{NHAN_TANG[nut.kind] ?? nut.kind}</span>
        <strong className={local.ma}>{nut.code}</strong>
        {nut.name && <span className={local.ten}>{nut.name}</span>}
        <span className={local.thuTu}>đi thứ {nut.pick_order}</span>
        {!nut.is_active && <span className={local.nhanNgung}>đã ngừng</span>}

        {/* Xem được ở MỌI tầng, không riêng Ô: hỏi "cả kệ A01 có gì" cũng chính đáng như
            hỏi "ô A01/03 có gì" — nhưng máy chủ chỉ trả hàng nằm ĐÚNG nút đó, không gộp
            cây con. Gộp cây con sẽ đếm trùng khi một lô nằm ở cả kệ lẫn ô bên dưới. */}
        <button type="button" className={styles.ghost} onClick={() => onMo(nut)}>
          Xem hàng
        </button>
        {themDuoc && (
          <button type="button" className={styles.ghost} onClick={() => onThem(nut)}>
            + Thêm {NHAN_TANG[TANG_DUOI[nut.kind][0].value]}
          </button>
        )}
        {coQuyenSua && nut.is_active && (
          <button
            type="button"
            className={styles.ghost}
            disabled={doi.isPending}
            onClick={() => doi.mutate({ id: nut.id, is_active: false })}
          >
            Ngừng
          </button>
        )}
      </div>
      {con.length > 0 && (
        <ul className={local.cay}>
          {con.map((c) => (
            <Nhanh
              key={c.id}
              nut={c}
              theoCha={theoCha}
              coQuyenSua={coQuyenSua}
              onThem={onThem}
              onMo={onMo}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function ThemViTri({ cha, onClose }: { cha: StorageLocation | null; onClose: () => void }) {
  const luaChon = cha === null ? [{ value: "WAREHOUSE", label: "Kho" }] : TANG_DUOI[cha.kind];
  const [kind, setKind] = useState(luaChon[0]?.value ?? "WAREHOUSE");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [thuTu, setThuTu] = useState("0");
  const [loi, setLoi] = useState<string | null>(null);
  const tao = useCreateLocation();

  return (
    <DetailDialog
      open
      title={cha === null ? "Thêm kho mới" : `Thêm chỗ dưới ${cha.path}`}
      onClose={onClose}
    >

      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      <label className={local.oNhap}>
        <span className={local.nhan}>Tầng</span>
        <select
          className={styles.select}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          aria-label="Tầng vị trí"
        >
          {luaChon.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>

      <label className={local.oNhap}>
        <span className={local.nhan}>Mã (theo nhãn dán trên kệ)</span>
        <input
          className={styles.input}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="A01"
          aria-label="Mã vị trí"
        />
      </label>

      <label className={local.oNhap}>
        <span className={local.nhan}>Tên gợi nhớ (không bắt buộc)</span>
        <input
          className={styles.input}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Kệ kháng sinh"
          aria-label="Tên vị trí"
        />
      </label>

      <label className={local.oNhap}>
        <span className={local.nhan}>Thứ tự đi lấy hàng</span>
        <input
          className={styles.input}
          inputMode="numeric"
          value={thuTu}
          onChange={(e) => setThuTu(e.target.value)}
          aria-label="Thứ tự đi lấy hàng"
        />
      </label>
      <p className={local.ghiChu}>
        Số nhỏ hơn = đi tới trước. Đặt theo <strong>đường chân đi thật trong kho</strong>,
        không theo bảng chữ cái — kệ A01 và A02 có thể đối lưng nhau qua một lối đi.
      </p>

      <div className={local.cuoi}>
        <button
          type="button"
          className={styles.button}
          disabled={tao.isPending || !code.trim()}
          onClick={async () => {
            setLoi(null);
            try {
              await tao.mutateAsync({
                kind,
                code: code.trim(),
                name: name.trim() || null,
                parent_id: cha?.id ?? null,
                pick_order: Number(thuTu) || 0,
              });
              onClose();
            } catch (err) {
              setLoi(
                err instanceof ApiError
                  ? err.problem.detail
                  : `Không lưu được — ${err instanceof Error ? err.message : String(err)}`,
              );
            }
          }}
        >
          {tao.isPending ? "Đang lưu…" : "Lưu vị trí"}
        </button>
      </div>
    </DetailDialog>
  );
}


/** Hàng đang nằm trong MỘT vị trí — trả lời đúng câu *"ô này có thuốc gì"*. */
function TrongO({ o, onClose }: { o: StorageLocation; onClose: () => void }) {
  const ds = useStockAtLocation(o.id);
  const rows = ds.data ?? [];
  // Chain giao 01/08: xem trong ô phải thấy TÊN THUỐC. `location` không import `catalog`,
  // nên tên gắn ở tầng màn hình — cùng hook màn Hoá đơn và màn Kiểm kê đang dùng.
  const tenThuoc = useDrugNames(rows.map((r) => r.drug_id));

  return (
    <DetailDialog open title={`Hàng trong ${o.path}`} onClose={onClose}>

      {ds.isLoading ? (
        <p className={styles.hint}>Đang tải…</p>
      ) : rows.length === 0 ? (
        <p className={styles.hint}>
          Chỗ này chưa có hàng. Cất hàng vào từ màn <strong>Kho</strong> — mỗi lô có nút
          &ldquo;Sắp xếp&rdquo;.
        </p>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Thuốc</th>
                <th>Hạn dùng</th>
                <th className={styles.num}>Số lượng</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.batch_id}>
                  <td>
                    <div>{tenThuoc.nameOf(r.drug_id) ?? "—"}</div>
                    <div className={`${styles.mono} ${local.soLo}`}>Lô {r.lot_no}</div>
                  </td>
                  <td>{new Date(r.expiry_date).toLocaleDateString("vi-VN")}</td>
                  <td className={styles.num}>{formatQty(r.quantity)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DetailDialog>
  );
}


/** Ngưỡng "cận hạn" trên lưới: 90 ngày. Cùng con số màn Tồn kho đang dùng — hai màn hai
 *  ngưỡng nghĩa là hai câu trả lời cho một câu hỏi. */
const NGAY_CAN_HAN = 90;

/**
 * Lưới ô — **sơ đồ trực quan mức 1** (BERAS V2 Phase 12).
 *
 * Trả lời đúng câu hay hỏi nhất khi đứng trước kệ: **chỗ nào đang trống để xếp hàng mới**.
 * Cây danh sách phía dưới trả lời *"ô A01 nằm đâu trong cấu trúc"* — hai câu khác nhau, nên
 * hai cách hiện, không thay thế nhau. Cây vẫn là chỗ **duy nhất sửa** cấu trúc.
 */
function LuoiO({
  o,
  tomTat,
  dangTai,
  onMo,
}: {
  o: StorageLocation[];
  tomTat: TomTatO[];
  dangTai: boolean;
  onMo: (o: StorageLocation) => void;
}) {
  const theoO = new Map(tomTat.map((t) => [t.location_id, t]));
  // 🔴 `useState` với khởi tạo lười, KHÔNG gọi `Date.now()` thẳng trong render — eslint bắt
  // đúng: một hàm không thuần trong render cho kết quả đổi mỗi lần vẽ lại, và ở đây nó
  // nghĩa là một ô có thể nhảy giữa "cận hạn" và "không" chỉ vì component vẽ lại. Chốt
  // mốc thời gian MỘT lần khi mở màn; ai để màn mở qua đêm thì tải lại trang.
  const [homNay] = useState(() => Date.now());

  return (
    <section className={local.luoiKhoi} aria-label="Sơ đồ ô theo thứ tự đi lấy">
      <div className={styles.head}>
        <div>
          <h2 className={styles.subtitle}>
            {o.length} ô · xếp theo thứ tự đi lấy
            {dangTai ? " · đang đọc tồn…" : ""}
          </h2>
        </div>
      </div>
      <ul className={local.luoi} data-testid="luoi-o">
        {o.map((l) => {
          const t = theoO.get(l.id);
          const conNgay = t
            ? Math.floor((new Date(t.hsd_gan_nhat).getTime() - homNay) / 86400000)
            : null;
          const trang =
            !l.is_active
              ? local.oNgung
              : t === undefined
                ? local.oTrong
                : conNgay !== null && conNgay <= NGAY_CAN_HAN
                  ? local.oCanHan
                  : local.oDay;
          return (
            <li key={l.id}>
              <button
                type="button"
                className={`${local.oNut} ${trang}`}
                onClick={() => onMo(l)}
                // Nhãn đọc được cho trình đọc màn hình: màu là thứ họ không nghe được.
                aria-label={
                  `${l.path} — ` +
                  (!l.is_active
                    ? "đã ngừng"
                    : t === undefined
                      ? "trống"
                      : `${t.so_lo} lô, còn ${formatQty(t.tong_so_luong)}` +
                        (conNgay !== null && conNgay <= NGAY_CAN_HAN ? `, cận hạn ${conNgay} ngày` : ""))
                }
              >
                <span className={local.oMa}>{l.code}</span>
                <span className={local.oSo}>
                  {!l.is_active ? "ngừng" : t === undefined ? "trống" : formatQty(t.tong_so_luong)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {/* Mỗi cặp (ô màu + chữ) bọc trong MỘT `span` không xuống dòng: bản đầu để chúng
          trôi tự do và "đã ngừng" rơi xuống dòng dưới, tách khỏi ô màu của nó — chú thích
          mà chỉ sai màu thì tệ hơn không có chú thích. Thấy trên ảnh chụp, không cổng nào
          bắt được. */}
      <p className={local.chuThich}>
        <span className={local.cap}>
          <span className={`${local.cham} ${local.oTrong}`} /> trống
        </span>
        <span className={local.cap}>
          <span className={`${local.cham} ${local.oDay}`} /> có hàng
        </span>
        <span className={local.cap}>
          <span className={`${local.cham} ${local.oCanHan}`} /> cận hạn ≤{NGAY_CAN_HAN} ngày
        </span>
        <span className={local.cap}>
          <span className={`${local.cham} ${local.oNgung}`} /> đã ngừng
        </span>
      </p>
    </section>
  );
}
