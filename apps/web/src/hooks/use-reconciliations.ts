import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import type {
  AskResponse,
  PaginatedResponse,
  Payment,
  Reconciliation,
  ReconciliationSummary,
  TrendsResponse,
} from "@/types/api";

export function useSummary() {
  return useQuery({
    queryKey: ["reconciliations", "summary"],
    queryFn: () => fetchApi<ReconciliationSummary>("/reconciliations/summary"),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useTrends(days: number = 30) {
  return useQuery({
    queryKey: ["reconciliations", "trends", days],
    queryFn: () => fetchApi<TrendsResponse>(`/reconciliations/trends?days=${days}`),
  });
}

export function useReconciliations(status?: string, limit = 20, offset = 0) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  return useQuery({
    queryKey: ["reconciliations", status, limit, offset],
    queryFn: () =>
      fetchApi<PaginatedResponse<Reconciliation>>(
        `/reconciliations?${params.toString()}`
      ),
  });
}

export function useReconciliation(id: string) {
  return useQuery({
    queryKey: ["reconciliation", id],
    queryFn: () => fetchApi<Reconciliation>(`/reconciliations/${id}`),
    enabled: !!id,
  });
}

export function usePayments(
  params: Record<string, string> = {},
  limit = 20,
  offset = 0
) {
  const searchParams = new URLSearchParams(params);
  searchParams.set("limit", String(limit));
  searchParams.set("offset", String(offset));

  return useQuery({
    queryKey: ["payments", params, limit, offset],
    queryFn: () =>
      fetchApi<PaginatedResponse<Payment>>(
        `/payments?${searchParams.toString()}`
      ),
  });
}

export function useAsk() {
  return useMutation({
    mutationFn: (question: string) =>
      fetchApi<AskResponse>("/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
  });
}
