"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuthStore } from "@/features/auth/auth-store";

/** Auth guard for every screen under the POS route group. Reads localStorage
 * only after mount (`hydrate()`) — the server-rendered pass has no
 * `window`, so redirecting before hydration would bounce a logged-in cashier
 * to /login on every hard refresh. */
export default function PosLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const session = useAuthStore((s) => s.session);
  const hydrated = useAuthStore((s) => s.hydrated);
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !session) {
      router.replace("/login");
    }
  }, [hydrated, session, router]);

  if (!hydrated || !session) {
    return null;
  }

  return <>{children}</>;
}
