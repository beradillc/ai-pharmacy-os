"use client";

import { useState } from "react";

import { ApiError } from "@/shared/api/errors";
import { getAccessToken } from "@/shared/api/token-storage";
import type { ProblemDetail } from "@/shared/api/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * Tải một tệp CSV từ endpoint báo cáo.
 *
 * Vì sao không dùng thẳng `<a href>`: mọi endpoint báo cáo đòi `Authorization:
 * Bearer`, mà thẻ `<a>` không gắn header được. Trình duyệt sẽ gọi không kèm token
 * và nhận về 401 — người dùng thấy một tệp lỗi tải xuống chứ không thấy lời giải
 * thích nào.
 *
 * Không dùng `apiFetch` vì hàm đó luôn `JSON.parse` phần thân; ở đây thân là CSV.
 * Nhưng phần **lỗi** thì vẫn là RFC 7807 JSON, nên vẫn đọc ra `ApiError` để màn
 * hình hiện đúng câu backend nói (ví dụ "khoảng thời gian không hợp lệ").
 */
export function useCsvExport() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(path: string, filename: string, key: string) {
    setBusy(key);
    setError(null);
    try {
      const token = getAccessToken();
      const res = await fetch(`${BASE_URL}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });

      if (!res.ok) {
        const text = await res.text();
        let detail = `Không tải được báo cáo (mã ${res.status}).`;
        try {
          const problem = JSON.parse(text) as ProblemDetail;
          detail = new ApiError(problem).problem.detail;
        } catch {
          // Thân lỗi không phải JSON — giữ câu mặc định, đừng ném tiếp một lỗi
          // khác che mất lỗi thật.
        }
        setError(detail);
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Không kết nối được máy chủ.");
    } finally {
      setBusy(null);
    }
  }

  return { download, busy, error, clearError: () => setError(null) };
}
