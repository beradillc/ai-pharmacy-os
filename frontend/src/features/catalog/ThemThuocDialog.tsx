"use client";

import { useState } from "react";

import { useCreateDrug } from "@/features/catalog/use-create-drug";
import { DetailDialog } from "@/components/overlay/DetailDialog";
import { ApiError } from "@/shared/api/errors";
import type { Drug, RxClass } from "@/shared/api/types";

import styles from "@/shared/ui/screen.module.css";

import local from "./them-thuoc.module.css";

/**
 * Thêm một mã thuốc mới — **gọi được GIỮA LÚC ĐANG NHẬP HÀNG** (V3-1, Chain duyệt 04/08).
 *
 * 🔴 **Đây là điều kiện thiết kế, không phải tiện nghi.** Chain hỏi đúng câu *"làm giữa quy
 * trình để nhập nhanh được không"*. Nếu tạo thuốc bắt người ta rời màn nhập hàng thì mọi thứ
 * đã gõ dở — số lượng, lô, hạn dùng — **mất sạch**, và người đứng cạnh thùng hàng sẽ chọn đại
 * một mã gần giống thay vì tạo mã đúng. Cửa sổ nổi lên trên, đóng lại là quay về đúng chỗ cũ
 * với mã mới **đã được chọn sẵn**.
 *
 * **Chỉ hỏi 4 thứ bắt buộc** (tên · loại kê đơn · đơn vị · giá bán). Phần còn lại — hoạt chất,
 * số đăng ký, mã ATC, quy cách — sửa sau ở màn Danh mục thuốc. Bắt điền đủ ở đây là bắt người
 * đang bận dỡ hàng làm việc của người ngồi bàn giấy, và kết quả sẽ là những dòng điền bừa.
 *
 * 🔴 **Hoạt chất để trống là hợp lệ nhưng KHÔNG vô hại** — nó làm cảnh báo dị ứng im lặng cho
 * mã hàng đó. Cửa sổ nói thẳng điều này thay vì giấu đi: người tạo mã cần biết mình vừa để lại
 * việc gì, chứ không phải phát hiện ra lúc bán nhầm cho người dị ứng.
 */
const LOAI: { ma: RxClass; nhan: string; moTa: string }[] = [
  { ma: "OTC", nhan: "Không kê đơn", moTa: "Bán tự do tại quầy" },
  { ma: "ETC", nhan: "Kê đơn", moTa: "Phải có đơn thuốc" },
  {
    ma: "CONTROLLED",
    nhan: "Kiểm soát đặc biệt",
    moTa: "Gây nghiện / hướng thần — vào sổ TT20",
  },
];

export function ThemThuocDialog({
  open,
  onClose,
  onCreated,
  tenGoiY = "",
}: {
  open: boolean;
  onClose: () => void;
  /** Gọi khi tạo xong — nơi gọi dùng để **chọn sẵn** mã mới ở ô đang đứng. */
  onCreated?: (thuoc: Drug) => void;
  /** Điền sẵn tên nếu nơi gọi đã biết (ví dụ người dùng vừa gõ vào ô tìm). */
  tenGoiY?: string;
}) {
  const tao = useCreateDrug();
  const [ten, setTen] = useState(tenGoiY);
  const [loai, setLoai] = useState<RxClass>("OTC");
  const [donVi, setDonVi] = useState("viên");
  const [gia, setGia] = useState("");
  const [loi, setLoi] = useState<string | null>(null);

  // Mở lại cửa sổ thì bắt đầu sạch. Giữ lại nội dung lần trước là cách chắc chắn nhất để
  // tạo nhầm một mã trùng với mã vừa tạo xong.
  //
  // Đặt trong RENDER, không phải `useEffect` — đây là khuôn "chỉnh state khi prop đổi" của
  // React, và nó khác `useEffect` ở một điểm quan trọng: React xử lý ngay trong cùng lượt
  // render, nên người dùng KHÔNG kịp thấy một khung hình mang dữ liệu cũ. Với `useEffect`
  // thì cửa sổ hiện ra còn nguyên tên lần trước rồi mới chớp sang rỗng.
  const [moTruocDo, setMoTruocDo] = useState(open);
  if (open !== moTruocDo) {
    setMoTruocDo(open);
    if (open) {
      setTen(tenGoiY);
      setLoai("OTC");
      setDonVi("viên");
      setGia("");
      setLoi(null);
    }
  }

  const duDe = ten.trim() !== "" && donVi.trim() !== "";

  async function luu() {
    setLoi(null);
    try {
      const thuoc = await tao.mutateAsync({
        name: ten.trim(),
        rx_class: loai,
        base_unit: donVi.trim(),
        // Chuỗi rỗng ⇒ `null` (chưa định giá), KHÔNG phải 0. Một mã giá 0 sẽ lặng lẽ bán
        // không thu tiền; một mã chưa định giá thì màn bán hàng hỏi giá tay.
        sale_price: gia.trim() === "" ? null : gia.trim(),
      });
      onCreated?.(thuoc);
      onClose();
    } catch (e) {
      setLoi(
        e instanceof ApiError
          ? e.message
          : "Không lưu được mã thuốc. Kiểm tra kết nối rồi thử lại.",
      );
    }
  }

  return (
    <DetailDialog
      open={open}
      title="Thêm thuốc mới"
      subtitle="Chỉ 4 mục bắt buộc — phần còn lại sửa sau ở Danh mục thuốc"
      onClose={onClose}
    >
      {loi && (
        <div className={styles.error} role="alert">
          <span>{loi}</span>
        </div>
      )}

      <div className={local.form}>
        <label className={local.o}>
          <span className={local.nhan}>Tên thuốc</span>
          <input
            className={styles.input}
            value={ten}
            onChange={(e) => setTen(e.target.value)}
            placeholder="VD: Paracetamol 500mg"
            aria-label="Tên thuốc"
            autoFocus
          />
        </label>

        <fieldset className={local.nhom}>
          <legend className={local.nhan}>Loại kê đơn</legend>
          {LOAI.map((l) => (
            <label key={l.ma} className={local.chon}>
              <input
                type="radio"
                name="rx_class"
                checked={loai === l.ma}
                onChange={() => setLoai(l.ma)}
              />
              <span>
                <strong>{l.nhan}</strong> <span className={local.mo}>— {l.moTa}</span>
              </span>
            </label>
          ))}
        </fieldset>

        <label className={local.o}>
          <span className={local.nhan}>Đơn vị lẻ</span>
          <input
            className={styles.input}
            value={donVi}
            onChange={(e) => setDonVi(e.target.value)}
            placeholder="viên, gói, ống, chai…"
            aria-label="Đơn vị lẻ"
          />
          <span className={local.mo}>Đơn vị nhỏ nhất khi bán lẻ cho khách.</span>
        </label>

        <label className={local.o}>
          <span className={local.nhan}>Giá bán lẻ (đ)</span>
          <input
            className={styles.input}
            inputMode="numeric"
            value={gia}
            onChange={(e) => setGia(e.target.value)}
            placeholder="Bỏ trống nếu chưa biết"
            aria-label="Giá bán lẻ"
          />
          <span className={local.mo}>
            Bỏ trống = chưa định giá, màn bán hàng sẽ hỏi giá khi bán.
          </span>
        </label>

        <p className={local.luuY} role="note">
          Mã mới <strong>chưa có hoạt chất</strong>, nên cảnh báo dị ứng sẽ{" "}
          <strong>không kêu</strong> cho mã này. Bổ sung hoạt chất ở màn Danh mục thuốc khi
          rảnh tay.
        </p>
      </div>

      <div className={local.day}>
        <button type="button" className={styles.ghost} onClick={onClose}>
          Huỷ
        </button>
        <button
          type="button"
          className={styles.button}
          disabled={!duDe || tao.isPending}
          onClick={() => void luu()}
        >
          {tao.isPending ? "Đang lưu…" : "Lưu mã thuốc"}
        </button>
      </div>
    </DetailDialog>
  );
}
