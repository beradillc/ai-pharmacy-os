"use client";

import { useEffect, useRef } from "react";

import styles from "./ConfirmDialog.module.css";

/**
 * Hộp xác nhận / nhập một giá trị.
 *
 * Thay cho `window.confirm` và `window.prompt`. Ba lý do, xếp theo mức nghiêm
 * trọng:
 *
 * ① **Một số webview không hiện `window.prompt` gì cả** — nó trả `null` lặng lẽ.
 *    Trên máy tính để bàn thì không sao; trên máy tính bảng đặt ở quầy thì thu
 *    ngân bấm "Thêm" và **không có gì xảy ra**, không thông báo lỗi nào.
 * ② Không style được, nên nó phá vỡ mọi thứ còn lại của giao diện.
 * ③ Nó **khoá luồng JavaScript** — mọi thứ khác đứng hình cho tới khi người dùng
 *    bấm.
 *
 * Dùng `<dialog>` thật để trình duyệt lo bẫy tiêu điểm bàn phím, phím Esc và lớp
 * phủ. Tự làm ba thứ đó bằng tay là ba chỗ để sai mà không ai kiểm.
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Xác nhận",
  cancelLabel = "Huỷ",
  tone = "normal",
  /** Có mặt ⇒ hộp thoại có ô nhập, `onConfirm` nhận giá trị đã gõ. */
  input,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "normal" | "danger";
  input?: { label: string; defaultValue?: string; type?: "text" | "number"; suffix?: string };
  onConfirm: (value: string) => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      // Đưa con trỏ vào ô nhập và bôi đen sẵn: người dùng gõ đè được ngay,
      // không phải xoá tay giá trị cũ.
      inputRef.current?.select();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onConfirm(inputRef.current?.value ?? "");
  }

  return (
    <dialog
      ref={ref}
      className={styles.dialog}
      // `onCancel` bắt phím Esc — không có nó thì Esc đóng hộp mà trạng thái
      // React vẫn tưởng nó đang mở, và lần sau mở lại sẽ không lên.
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onCancel();
      }}
      aria-labelledby="confirm-title"
    >
      <form method="dialog" className={styles.body} onSubmit={submit}>
        <h2 id="confirm-title" className={styles.title}>
          {title}
        </h2>
        {description && <p className={styles.text}>{description}</p>}

        {input && (
          <label className={styles.field}>
            <span className={styles.fieldLabel}>{input.label}</span>
            <span className={styles.inputWrap}>
              <input
                ref={inputRef}
                className={styles.input}
                type={input.type ?? "text"}
                defaultValue={input.defaultValue}
                inputMode={input.type === "number" ? "numeric" : undefined}
              />
              {input.suffix && <span className={styles.suffix}>{input.suffix}</span>}
            </span>
          </label>
        )}

        <div className={styles.actions}>
          <button type="button" className={styles.cancel} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="submit"
            className={tone === "danger" ? styles.confirmDanger : styles.confirm}
          >
            {confirmLabel}
          </button>
        </div>
      </form>
    </dialog>
  );
}
