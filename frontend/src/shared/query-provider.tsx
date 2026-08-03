"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "@/shared/api/errors";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  // Created inside useState, not at module scope: a client created at module
  // scope would be shared across requests on the server. This app is
  // effectively client-only (auth-gated POS), but the safe pattern costs
  // nothing and avoids a footgun if a server-rendered route is added later.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 🔴 KHÔNG thử lại lỗi 4xx (V3-10). `retry: 1` cũ thử lại MỌI lỗi, kể cả 401 —
            // tức là mỗi lần phiên hết, ứng dụng gửi thêm một yêu cầu chắc chắn hỏng nữa
            // rồi mới chịu báo, làm chậm đúng lúc cần đưa người dùng về màn đăng nhập nhanh
            // nhất. Yêu cầu sai ở phía người gọi thì gửi lại y hệt sẽ hỏng y hệt.
            retry: (soLan, loi) =>
              soLan < 1 && !(loi instanceof ApiError && loi.status < 500),
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
