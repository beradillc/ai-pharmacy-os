"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";

/**
 * Sổ theo dõi xuất, nhập, tồn kho thuốc kiểm soát đặc biệt — TT18 Phụ lục VIII / XVI.
 *
 * 🔴 Vì sao đây là lỗi **Critical**, không phải Major (báo cáo UAT §1 mục 22): giữ sổ này
 * là **nghĩa vụ pháp lý** của cơ sở bán lẻ, không phải một tính năng tiện ích. Backend đã
 * có đủ từ Sprint 7 — bút toán, chốt sổ ngày, ký, xuất báo cáo, 122 hoạt chất kiểm soát nạp
 * sẵn — nhưng **không màn nào**, nên dược sĩ không dùng được và khi thanh tra hỏi thì phần
 * mềm không giúp được gì dù dữ liệu nằm sẵn trong đó.
 */

/** Hai mẫu sổ pháp lý. Mã khớp `LedgerBookType` bên Python — có cổng bắt chéo. */
export type LoaiSo = "PL_VIII" | "PL_XVI";

/** Một dòng sổ, khớp `LedgerBookRowResponse` của backend. */
export interface DongSo {
  drug_id: string;
  transaction_at: string;
  source_or_destination: string;
  document_no: string;
  quantity_in: string | null;
  quantity_out: string | null;
  balance: string;
  lot_no: string;
  expiry_date: string;
  note: string | null;
}

export function useSoKiemSoat(params: { loaiSo: LoaiSo; tuNgay: string; denNgay: string }) {
  const { loaiSo, tuNgay, denNgay } = params;
  return useQuery({
    queryKey: ["compliance", "so-kiem-soat", loaiSo, tuNgay, denNgay],
    queryFn: () => {
      const q = new URLSearchParams({ date_from: tuNgay, date_to: denNgay });
      return apiFetch<DongSo[]>(
        `/compliance/controlled-ledger/books/${loaiSo}?${q.toString()}`,
      );
    },
    staleTime: 15_000,
  });
}

/** Kết quả một lượt ký sổ — khớp `LedgerBookSignatureResponse`. */
export interface ChuKySo {
  id: string;
  book_type: string;
  book_date: string;
  content_sha256: string;
  prev_hash: string | null;
  signed_by_user_id: string;
  signed_at: string;
}

/**
 * Ký xác nhận điện tử **1 sổ / 1 ngày** — TT18 Điều 15.1.d, hướng A.
 *
 * 🔴 Bắt buộc nhập lại mật khẩu ngay tại đây (re-auth), **không** chấp nhận chỉ dựa vào
 * phiên đang mở: đây là một hành vi pháp lý **không đảo ngược được** — ký rồi thì không ký
 * lại được ngày đó và không ghi thêm dòng nào vào ngày đó nữa (backend trả 409 cả hai ca).
 * Một cú bấm nhầm trên máy để quên đăng nhập là đủ để khoá vĩnh viễn một ngày trong sổ.
 */
export function useKySo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: {
      loaiSo: LoaiSo;
      ngay: string;
      matKhau: string;
      maHaiLop?: string;
    }) =>
      apiFetch<ChuKySo>(`/compliance/controlled-ledger/books/${v.loaiSo}/sign`, {
        method: "POST",
        body: {
          book_date: v.ngay,
          current_password: v.matKhau,
          ...(v.maHaiLop ? { totp_code: v.maHaiLop } : {}),
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["compliance", "so-kiem-soat"] });
    },
  });
}
