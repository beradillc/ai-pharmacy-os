import type { ProblemDetail } from "./types";

/** Thrown by {@link apiFetch} for any non-2xx response. Carries the parsed
 * problem+json body so callers can branch on `type` (see error_type constants
 * in `core/errors.py` / `modules/iam/application/errors.py`) without re-parsing. */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(problem: ProblemDetail) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }

  /** `https://errors.pharmacy-os/branch-required` — login succeeded but the
   * account reaches several branches; `problem.branches` holds the picker list. */
  get isBranchSelectionRequired(): boolean {
    return this.problem.type === "https://errors.pharmacy-os/branch-required";
  }

  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}
