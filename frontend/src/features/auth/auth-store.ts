import { create } from "zustand";

import * as tokenStorage from "@/shared/api/token-storage";
import type { Session } from "@/shared/api/types";

interface AuthState {
  session: Session | null;
  /** False until the client has read localStorage once. Needed because the
   * server-rendered pass never has a session (no `window`), so components must
   * wait for hydration before deciding "show login" vs "show POS" — deciding
   * too early flashes the wrong screen. */
  hydrated: boolean;
  hydrate: () => void;
  login: (session: Session) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  hydrated: false,
  hydrate: () => set({ session: tokenStorage.getSession(), hydrated: true }),
  login: (session) => {
    tokenStorage.setSession(session);
    set({ session, hydrated: true });
  },
  logout: () => {
    tokenStorage.clearSession();
    set({ session: null, hydrated: true });
  },
}));
