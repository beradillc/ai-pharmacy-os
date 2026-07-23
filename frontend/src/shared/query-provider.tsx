"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
