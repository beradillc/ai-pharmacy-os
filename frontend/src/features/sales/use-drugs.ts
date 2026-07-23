import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { apiFetch } from "@/shared/api/client";
import type { Drug } from "@/shared/api/types";

/**
 * `GET /drugs` has no server-side search — only `limit`/`offset` (the
 * `?query=&cursor=` in docs/11_API_DESIGN.md does not exist in
 * `catalog/interface/router.py`). Fetches a page and filters client-side by
 * name/barcode. Fine for a single branch's catalog at "minimal POS" scope;
 * revisit if a tenant's drug count makes 200 unpaginated rows too coarse.
 */
export function useDrugs(search: string) {
  const query = useQuery({
    queryKey: ["drugs"],
    queryFn: () => apiFetch<Drug[]>("/drugs?limit=200"),
    staleTime: 60_000,
  });

  const filtered = useMemo(() => {
    const drugs = query.data ?? [];
    const term = search.trim().toLowerCase();
    if (!term) return drugs;
    return drugs.filter(
      (d) => d.name.toLowerCase().includes(term) || d.barcode?.toLowerCase() === term,
    );
  }, [query.data, search]);

  return { ...query, drugs: filtered };
}
