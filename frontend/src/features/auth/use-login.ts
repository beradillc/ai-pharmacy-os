import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/shared/api/client";
import type { LoginRequest, Session } from "@/shared/api/types";

import { useAuthStore } from "./auth-store";

/** POST /auth/login — real JWT auth, no dev-header fallback (yêu cầu của
 * sếp). `branch_id` is optional on the request; omitting it when the account
 * reaches several branches gets a 400 (`ApiError.isBranchSelectionRequired`)
 * carrying the picker list, handled by the caller. */
export function useLogin() {
  const login = useAuthStore((s) => s.login);

  return useMutation({
    mutationFn: (body: LoginRequest) =>
      apiFetch<Session>("/auth/login", { method: "POST", body, skipAuth: true }),
    onSuccess: login,
  });
}
