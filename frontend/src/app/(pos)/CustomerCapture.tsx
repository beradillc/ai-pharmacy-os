"use client";

import { useEffect, useState } from "react";

import {
  ConsentNotRecordedError,
  looksLikePhone,
  useCustomerByPhone,
  useQuickCreateAtCounter,
} from "@/features/crm/use-customers";
import { ApiError } from "@/shared/api/errors";
import type { Customer } from "@/shared/api/types";

import styles from "./page.module.css";

/**
 * Ô hỏi số điện thoại khách, ngay trên giỏ hàng.
 *
 * Chain chốt 2026-07-29 (quyết định Đ-4): *"chỉ cần hỏi xin được số điện thoại
 * lúc lên đơn, thanh toán, là xác nhận cung cấp thông tin"*. Khách tự đọc số khi
 * được hỏi là **hành vi khẳng định**, không phải im lặng — nên thoả Luật 91/2025
 * Điều 9 mà không cần thêm một hộp thoại nữa để bấm.
 *
 * Bốn điều kiện để chỗ này không trượt khỏi ranh giới đó:
 *
 * ① **Bỏ trống là bán bình thường.** Bán hàng không cần khách hàng. Không có ô
 *    nào bắt buộc, không có cảnh báo nào khi để trống — nếu để trống mà bị cằn
 *    nhằn thì thu ngân sẽ gõ số bừa cho qua, và ta có một hồ sơ khách hàng sai.
 *
 * ② **Chỉ xin đồng ý CƠ BẢN.** Backend ném lỗi nếu ai đó gửi `basis=COUNTER` kèm
 *    `LOYALTY`/`HEALTH`, nên chỗ này không thể tiện tay nới ra. Muốn tích điểm
 *    thì vẫn phải hỏi riêng ở màn Khách hàng.
 *
 * ③ **Nói ra là đang ghi lại gì.** Một dòng chữ nhỏ dưới ô, không phải điều
 *    khoản 400 chữ mà không ai đọc. Thu ngân phải đọc được nó cho khách nghe
 *    trong hai giây.
 *
 * ④ **Số đã có khách thì KHÔNG tạo lại.** Gõ số → tra trước → thấy thì gắn luôn.
 *    Tạo trùng hồ sơ là cách làm hỏng cả lịch sử mua lẫn điểm sau này.
 */
export function CustomerCapture({
  value,
  onChange,
}: {
  value: Customer | null;
  onChange: (customer: Customer | null) => void;
}) {
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [orphanId, setOrphanId] = useState<string | null>(null);

  const lookup = useCustomerByPhone(phone);
  const quickCreate = useQuickCreateAtCounter();

  const searching = looksLikePhone(phone) && lookup.isLoading;
  const found = lookup.data?.[0] ?? null;
  const notFound = looksLikePhone(phone) && !lookup.isLoading && (lookup.data?.length ?? 0) === 0;

  // Gắn ngay khi tra ra — không bắt bấm thêm một nút "Chọn". Thu ngân đang giữ
  // hàng trên tay; mỗi cú bấm thừa ở đây là một cú bấm bị bỏ qua lúc đông khách.
  //
  // 🔴 Phải nằm trong `useEffect`, KHÔNG gọi thẳng trong thân render. Bản đầu
  // tôi viết `if (found && …) onChange(found)` ngay giữa render — đo thật thì
  // bán xong khách **vẫn còn gắn**: cha gọi `setCustomer(null)`, component vẽ
  // lại, ô số điện thoại vẫn giữ nguyên giá trị nên `found` vẫn có, và nó **gắn
  // lại ngay lập tức**. Bỏ gắn thành ra không bỏ được.
  //
  // Cha còn đổi `key` sau mỗi lần bán để component dựng lại từ đầu — hai cơ chế
  // bù nhau: `useEffect` sửa vòng lặp gắn-lại, `key` xoá luôn số của khách trước.
  useEffect(() => {
    if (found && value?.id !== found.id) onChange(found);
  }, [found, value, onChange]);

  async function createAndAttach() {
    setError(null);
    try {
      const made = await quickCreate.mutateAsync({ full_name: name.trim(), phone: phone.trim() });
      onChange(made);
      setName("");
    } catch (err) {
      if (err instanceof ConsentNotRecordedError) {
        setOrphanId(err.customerId);
        setError(
          "Đã tạo hồ sơ khách nhưng CHƯA ghi được đồng ý. Vào màn Khách hàng bấm đồng ý cho " +
            "người này, ĐỪNG tạo lại — sẽ thành hai hồ sơ.",
        );
      } else {
        setError(err instanceof ApiError ? err.problem.detail : "Không tạo được hồ sơ khách.");
      }
    }
  }

  if (value) {
    return (
      <div className={styles.customerBox}>
        <div>
          <strong>{value.full_name}</strong>
          <span className={styles.customerPhone}>{value.phone}</span>
        </div>
        <button
          type="button"
          className={styles.customerClear}
          onClick={() => {
            onChange(null);
            setPhone("");
          }}
        >
          Bỏ gắn
        </button>
      </div>
    );
  }

  return (
    <div className={styles.customerBox}>
      <label className={styles.customerField}>
        <span className={styles.customerLabel}>Số điện thoại khách (không bắt buộc)</span>
        <input
          className={styles.customerInput}
          type="tel"
          inputMode="tel"
          value={phone}
          onChange={(e) => {
            setPhone(e.target.value);
            setError(null);
          }}
          placeholder="Hỏi khách rồi gõ vào đây"
          aria-label="Số điện thoại khách hàng"
        />
      </label>

      {searching && <span className={styles.customerHint}>Đang tra…</span>}

      {notFound && (
        <div className={styles.customerNew}>
          <span className={styles.customerHint}>
            Số này chưa có hồ sơ. Nhập tên để tạo nhanh, hoặc bỏ qua và bán như khách vãng lai.
          </span>
          <div className={styles.customerNewRow}>
            <input
              className={styles.customerInput}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Tên khách"
              aria-label="Tên khách hàng mới"
              maxLength={255}
            />
            <button
              type="button"
              className={styles.customerCreate}
              onClick={createAndAttach}
              disabled={!name.trim() || quickCreate.isPending || orphanId !== null}
            >
              {quickCreate.isPending ? "Đang lưu…" : "Tạo & gắn"}
            </button>
          </div>
          <span className={styles.customerHint}>
            Khách đọc số cho mình là đã đồng ý cho lưu tên và số để ghi lên hoá đơn. Muốn{" "}
            <strong>tích điểm</strong> thì phải hỏi riêng ở màn Khách hàng.
          </span>
        </div>
      )}

      {error && (
        <p className={styles.customerError} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
