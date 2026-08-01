"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./DetailDialog.module.css";

/**
 * Cửa sổ **xem / nhập / sửa chi tiết** — Chain giao 2026-08-01:
 * *"Tất cả các phím chức năng xem/nhập/sửa chi tiết trên giao diện mobile cần dạng cửa sổ
 * và thêm dấu ✕ để thoát khi cần"*.
 *
 * Khác `ConfirmDialog` ở chỗ nào, và vì sao không gộp làm một: `ConfirmDialog` hỏi **một
 * câu** và trả **một giá trị** — nó sở hữu nút Xác nhận/Huỷ và luồng bấm. `DetailDialog`
 * chỉ là **cái khung**: nội dung bên trong là một màn con đầy đủ (bảng, biểu mẫu, nhiều
 * nút), và khung không được biết gì về nội dung đó. Gộp hai thứ này lại sẽ đẻ ra một
 * component nhận mười tham số mà chỉ dùng ba.
 *
 * Dùng `<dialog>` thật, không dựng lớp phủ bằng `div`. Trình duyệt lo hộ **ba** thứ mà tự
 * làm là ba chỗ sai không ai kiểm: bẫy tiêu điểm bàn phím · phím `Esc` · lớp phủ `::backdrop`
 * chặn bấm ra ngoài. Đây cũng là lý do `ConfirmDialog` đã chọn `<dialog>` từ trước — cùng
 * một quyết định, không phát minh lại.
 *
 * 🔴 Khoá cuộn nền khi mở. `showModal()` **không** tự khoá cuộn trang trên iOS Safari: người
 * dùng vuốt trên cửa sổ mà TRANG PHÍA SAU trôi, đóng cửa sổ ra thì lạc mất chỗ mình đang
 * đứng. Đây là lỗi chỉ thấy trên máy thật, không cổng tự động nào bắt được.
 */
export function DetailDialog({
  open,
  title,
  onClose,
  children,
  /** Chú thích một dòng dưới tiêu đề — mã đơn, tên ô, ngày... Bỏ trống thì không hiện. */
  subtitle,
  /** Nút phụ ở đầu cửa sổ (ví dụ "In"). Nút ✕ luôn có, không tắt được. */
  actions,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  subtitle?: string;
  actions?: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  /**
   * Độ dời của cửa sổ so với vị trí GIỮA màn (Chain giao 2026-08-01: *"cửa sổ ưu tiên ban
   * đầu ở giữa, và có thể kéo di chuyển"*).
   *
   * `null` = chưa kéo lần nào ⇒ để CSS căn giữa. Chỉ khi người dùng thực sự kéo mới chuyển
   * sang `transform` — nếu đặt `transform` sẵn từ đầu thì cửa sổ mất khả năng tự căn lại
   * khi đổi kích thước cửa sổ trình duyệt, và nó sẽ lệch dần sau mỗi lần xoay máy.
   */
  const [doi, setDoi] = useState<{ x: number; y: number } | null>(null);
  const keo = useRef<{ x0: number; y0: number; dx: number; dy: number } | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      // Mở lại thì về GIỮA. Giữ chỗ người dùng kéo tới ở lần trước là bẫy: cửa sổ sau hiện
      // ra ở một góc màn vì thao tác của một cửa sổ khác, và không ai nhớ vì sao.
      setDoi(null);
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const truoc = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = truoc;
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      className={styles.hop}
      aria-label={title}
      style={doi === null ? undefined : { transform: `translate(${doi.x}px, ${doi.y}px)` }}
      // `Esc` phát `cancel` chứ không phát `close` với trạng thái của ta — bắt cả hai để
      // trạng thái React không lệch với trạng thái thật của `<dialog>`. Lệch một nhịp ở
      // đây nghĩa là cửa sổ đã đóng mà `open` vẫn `true`, và lần mở sau không có gì xảy ra.
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClose={onClose}
    >
      <div
        className={styles.dau}
        // 🔴 CHỈ trên máy tính. Trên điện thoại cửa sổ là tấm phủ bám đáy — kéo nó đi là
        // lấy mất cử chỉ vuốt-để-cuộn của chính nội dung bên trong, và người dùng không có
        // chuột để đưa nó về chỗ cũ. `pointerdown` với `pointerType` chuột/bút mới bắt đầu.
        onPointerDown={(e) => {
          if (e.pointerType === "touch") return;
          // Bấm vào nút (✕, In…) thì KHÔNG phải kéo — nếu không thì mỗi lần bấm ✕ mà tay
          // rung một pixel là một lần cửa sổ nhích đi thay vì đóng.
          if ((e.target as HTMLElement).closest("button")) return;
          keo.current = { x0: e.clientX, y0: e.clientY, dx: doi?.x ?? 0, dy: doi?.y ?? 0 };
          (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          const k = keo.current;
          if (k === null) return;
          setDoi({ x: k.dx + e.clientX - k.x0, y: k.dy + e.clientY - k.y0 });
        }}
        onPointerUp={() => {
          keo.current = null;
        }}
        style={{ cursor: doi === null ? undefined : "grabbing" }}
      >
        <div className={styles.tieuDe}>
          <h2 className={styles.ten}>{title}</h2>
          {subtitle && <p className={styles.phu}>{subtitle}</p>}
        </div>
        <div className={styles.nut}>
          {actions}
          <button type="button" className={styles.dong} onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </div>
      </div>
      <div className={styles.than}>{children}</div>
    </dialog>
  );
}
