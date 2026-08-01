"use client";

import { useState } from "react";

import { useAuthStore } from "@/features/auth/auth-store";
import { useDrugNames } from "@/features/catalog/use-drug-names";
import { type LoaiSo, useKySo, useSoKiemSoat } from "@/features/compliance/use-so-kiem-soat";
import { useCsvExport } from "@/features/reports/use-export";
import { thongDiepLoi } from "@/shared/api/errors";
import { formatDate, formatQty, formatTime } from "@/shared/format/number";
import styles from "@/shared/ui/screen.module.css";

import local from "./page.module.css";

const LOAI_SO: { ma: LoaiSo; nhan: string; moTa: string }[] = [
  {
    ma: "PL_VIII",
    nhan: "Phụ lục VIII — Gây nghiện · Hướng thần · Tiền chất",
    moTa: "TT18 Điều 12.1.a. Mẫu sổ bắt buộc cho thuốc gây nghiện, hướng thần, tiền chất.",
  },
  {
    ma: "PL_XVI",
    nhan: "Phụ lục XVI — Dạng phối hợp · Thuốc độc · Chất bị cấm",
    moTa: "TT18 Điều 12.3. Mẫu sổ cho thuốc dạng phối hợp, thuốc độc, chất thuộc danh mục cấm.",
  },
];

function homNay(): string {
  return new Date().toISOString().slice(0, 10);
}
function dauThang(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}

/**
 * Màn **Sổ thuốc kiểm soát đặc biệt** — đóng lỗi C-03 (UAT 2026-08-01), mức Critical.
 *
 * 🔴 Vì sao Critical chứ không Major: giữ sổ này là **nghĩa vụ pháp lý** của cơ sở bán lẻ
 * (TT18), không phải tiện ích. Backend có đủ từ Sprint 7 — bút toán, chốt sổ ngày, ký, xuất
 * mẫu — nhưng không màn nào, nên dược sĩ không dùng được và khi thanh tra hỏi thì phần mềm
 * không giúp được gì **dù dữ liệu nằm sẵn trong đó**.
 *
 * ⚠️ **Màn này tự nói ra là chưa được rà pháp lý.** Chain gác phần pháp lý tới sau video
 * (§7dg); điều kiện GĐ kèm theo là màn phải tuyên bố điều đó **trên chính nó**, để một ảnh
 * chụp từ video không bị đọc thành cam kết tuân thủ.
 */
export default function SoKiemSoatPage() {
  const [loaiSo, setLoaiSo] = useState<LoaiSo>("PL_VIII");
  const [tuNgay, setTuNgay] = useState(dauThang());
  const [denNgay, setDenNgay] = useState(homNay());

  const ds = useSoKiemSoat({ loaiSo, tuNgay, denNgay });
  const rows = ds.data ?? [];
  const ten = useDrugNames(rows.map((r) => r.drug_id));

  const xuat = useCsvExport();
  const ky = useKySo();

  const quyen = new Set(useAuthStore((s) => s.session)?.permissions ?? []);
  const coQuyenKy = quyen.has("compliance.ledger.sign");

  const [ngayKy, setNgayKy] = useState(homNay());
  const [matKhau, setMatKhau] = useState("");
  const [maHaiLop, setMaHaiLop] = useState("");
  const [dangKy, setDangKy] = useState(false);

  const soDuCuoi = rows.length > 0 ? rows[rows.length - 1].balance : null;
  const chon = LOAI_SO.find((l) => l.ma === loaiSo)!;

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <div>
          <h1 className={styles.title}>Sổ thuốc kiểm soát đặc biệt</h1>
          <p className={styles.subtitle}>
            Sổ theo dõi xuất, nhập, tồn kho — <strong>Thông tư 18/2025 Phụ lục VIII/XVI</strong>.
            Mỗi dòng là một bút toán, <strong>không sửa và không xoá được</strong>.
          </p>
        </div>
      </div>

      {/* ⚠️ Điều kiện GĐ kèm việc Chain gác pháp lý (§7dg quyết định 8): màn TỰ NÓI nó chưa
          được Trợ lý Pháp Lý rà. Ảnh chụp màn này sẽ đi vào video hướng dẫn, và một ảnh
          trông như phần mềm tuân thủ đủ là thứ khó rút lại nhất. */}
      <p className={local.chuaRa}>
        {/* `{" "}` tường minh sau `</strong>`: khoảng trắng viết trần ở đây bị nuốt và chữ
            dính thành "pháp lý.Bố cục". Ảnh chụp thấy trước, phép đo `innerText` xác nhận
            sau — kỷ luật #15 dặn phóng to trước khi kết luận, và lần này ảnh đúng. */}
        🔴 <strong>Chưa được rà pháp lý.</strong>{" "}
        Bố cục và cách tính cột &quot;Còn lại&quot; đã theo mẫu TT18, nhưng{" "}
        <strong>chưa có ai đối chiếu với văn bản gốc</strong> và chưa xác nhận sổ này đủ để
        trình thanh tra. Dùng để theo dõi nội bộ; bản in ra vẫn phải đối chiếu mẫu giấy trước
        khi ký.
      </p>

      <div className={styles.controls}>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Mẫu sổ</span>
          <select
            className={styles.select}
            value={loaiSo}
            onChange={(e) => setLoaiSo(e.target.value as LoaiSo)}
            aria-label="Mẫu sổ"
          >
            {LOAI_SO.map((l) => (
              <option key={l.ma} value={l.ma}>
                {l.nhan}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Từ ngày</span>
          <input
            className={styles.input}
            type="date"
            value={tuNgay}
            onChange={(e) => setTuNgay(e.target.value)}
            aria-label="Từ ngày"
          />
        </label>
        <label className={styles.field}>
          <span className={styles.fieldLabel}>Đến ngày</span>
          <input
            className={styles.input}
            type="date"
            value={denNgay}
            onChange={(e) => setDenNgay(e.target.value)}
            aria-label="Đến ngày"
          />
        </label>
      </div>

      <p className={styles.subtitle}>{chon.moTa}</p>

      <div className={local.hanhDong}>
        <button
          type="button"
          className={styles.ghost}
          disabled={xuat.busy !== null}
          onClick={() =>
            void xuat.download(
              `/compliance/controlled-ledger/books/${loaiSo}/export?date_from=${tuNgay}&date_to=${denNgay}`,
              `so-${loaiSo.toLowerCase()}-${tuNgay}_${denNgay}.csv`,
              "ky",
            )
          }
        >
          Kết xuất sổ (CSV)
        </button>
        <button
          type="button"
          className={styles.ghost}
          disabled={xuat.busy !== null}
          onClick={() =>
            void xuat.download(
              `/compliance/controlled-ledger/books/${loaiSo}/daily-closure?day=${denNgay}`,
              `so-${loaiSo.toLowerCase()}-cuoi-ngay-${denNgay}.csv`,
              "ngay",
            )
          }
        >
          Kết xuất cuối ngày {formatDate(denNgay)}
        </button>
        {coQuyenKy && (
          <button type="button" className={styles.button} onClick={() => setDangKy((v) => !v)}>
            Ký xác nhận sổ ngày
          </button>
        )}
      </div>

      {/* 🔴 Nói ra việc "in cuối mỗi ngày" là BẮT BUỘC, không phải tuỳ chọn — TT18 Điều 15.1
          ghi chú Phụ lục VIII. Người dùng không đọc thông tư; nếu màn không nói thì họ sẽ
          coi nút kết xuất là một tiện ích và bỏ qua nó hàng tháng trời. */}
      <p className={local.batBuoc}>
        Mẫu sổ điện tử chỉ hợp lệ khi được <strong>trích xuất và in vào cuối MỖI ngày</strong>{" "}
        (TT18 Điều 15.1). Chữ ký điện tử dưới đây thay cho việc ký tay từng trang; chưa ký thì
        vẫn phải in ra và ký tay.
      </p>

      {xuat.error && <p className={styles.error}>{xuat.error}</p>}

      {dangKy && coQuyenKy && (
        <div className={local.hopKy}>
          <p className={local.canhBaoKy}>
            ⚠️ Ký rồi thì <strong>không ký lại được ngày này</strong> và{" "}
            <strong>không ghi thêm bút toán nào vào ngày này</strong> nữa. Đây là hành vi pháp
            lý không đảo ngược được.
          </p>
          <div className={styles.controls}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Ngày cần ký</span>
              <input
                className={styles.input}
                type="date"
                value={ngayKy}
                onChange={(e) => setNgayKy(e.target.value)}
                aria-label="Ngày cần ký"
              />
            </label>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Mật khẩu của bạn</span>
              <input
                className={styles.input}
                type="password"
                value={matKhau}
                onChange={(e) => setMatKhau(e.target.value)}
                autoComplete="current-password"
                aria-label="Mật khẩu của bạn"
              />
            </label>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Mã 2 lớp (nếu đã bật)</span>
              <input
                className={styles.input}
                type="text"
                inputMode="numeric"
                value={maHaiLop}
                onChange={(e) => setMaHaiLop(e.target.value)}
                aria-label="Mã 2 lớp"
              />
            </label>
          </div>
          <button
            type="button"
            className={styles.button}
            disabled={!matKhau || ky.isPending}
            onClick={() =>
              ky.mutate(
                {
                  loaiSo,
                  ngay: ngayKy,
                  matKhau,
                  maHaiLop: maHaiLop || undefined,
                },
                { onSuccess: () => setMatKhau("") },
              )
            }
          >
            {ky.isPending ? "Đang ký…" : "Xác nhận ký"}
          </button>
          {ky.error && <p className={styles.error}>{thongDiepLoi(ky.error)}</p>}
          {ky.data && (
            <p className={local.daKy}>
              ✓ Đã ký sổ ngày <strong>{formatDate(ky.data.book_date)}</strong> lúc{" "}
              {formatTime(ky.data.signed_at)}. Mã toàn vẹn{" "}
              <span className={styles.mono}>{ky.data.content_sha256.slice(0, 16)}…</span>
            </p>
          )}
        </div>
      )}

      {ds.isLoading && <div className={styles.skeleton} aria-label="Đang tải" />}
      {ds.error && <p className={styles.error}>{thongDiepLoi(ds.error)}</p>}

      {/* Trạng thái rỗng nói ra HỆ QUẢ, không chỉ "chưa có gì" (bài học U-05). Ở màn này
          "sổ rỗng" là một câu có hai nghĩa rất khác nhau, nên phải nói cả hai. */}
      {!ds.isLoading && !ds.error && rows.length === 0 && (
        <p className={styles.empty}>
          Chưa có bút toán nào trong khoảng ngày này ở mẫu <strong>{chon.nhan}</strong>. Nghĩa
          là quầy <em>chưa nhập hoặc bán</em> thuốc thuộc nhóm này trong kỳ — không phải sổ
          hỏng. Nếu quầy có bán mà sổ trống, kiểm tra lại phân loại thuốc trong{" "}
          <em>Danh mục thuốc</em>: chỉ thuốc được đánh dấu kiểm soát đặc biệt mới vào sổ.
        </p>
      )}

      {rows.length > 0 && (
        <>
          <p className={styles.subtitle}>
            {rows.length} bút toán
            {soDuCuoi !== null && (
              <>
                {" "}
                · tồn cuối kỳ <strong>{formatQty(soDuCuoi)}</strong>
              </>
            )}
          </p>
          <div className={styles.tableWrap}>
            <table className={`${styles.table} ${local.bangThe}`} data-testid="ds-so-kiem-soat">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Tên thuốc</th>
                  <th>Số chứng từ</th>
                  <th>Nơi nhập / nơi nhận</th>
                  <th>Nhập</th>
                  <th>Xuất</th>
                  <th>Còn lại</th>
                  <th>Số lô · Hạn dùng</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.document_no}-${r.transaction_at}-${i}`}>
                    <td data-nhan="Thời gian" className={styles.mono}>
                      {formatTime(r.transaction_at)}
                    </td>
                    <td data-nhan="Tên thuốc">
                      {/* Tra không ra tên thì hiện mã rút gọn, KHÔNG bỏ trống: một dòng sổ
                          pháp lý không nói được nó nói về thuốc gì là một dòng vô dụng. */}
                      {ten.nameOf(r.drug_id) ?? (
                        <span className={local.ma}>Mã {r.drug_id.slice(0, 8)}</span>
                      )}
                    </td>
                    <td data-nhan="Số chứng từ" className={styles.mono}>
                      {r.document_no}
                    </td>
                    <td data-nhan="Nơi nhập / nơi nhận">{r.source_or_destination}</td>
                    <td data-nhan="Nhập" className={local.so}>
                      {r.quantity_in === null ? "" : formatQty(r.quantity_in)}
                    </td>
                    <td data-nhan="Xuất" className={local.so}>
                      {r.quantity_out === null ? "" : formatQty(r.quantity_out)}
                    </td>
                    <td data-nhan="Còn lại" className={`${local.so} ${local.conLai}`}>
                      {formatQty(r.balance)}
                    </td>
                    <td data-nhan="Số lô · Hạn dùng">
                      <span className={styles.mono}>{r.lot_no}</span>
                      <span className={local.ma}> · HSD {formatDate(r.expiry_date)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
