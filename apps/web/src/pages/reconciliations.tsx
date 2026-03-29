import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { reconciliationStatusStyles } from "@/lib/status-colors";
import { formatAmount } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useReconciliations } from "@/hooks/use-reconciliations";
import type { Reconciliation } from "@/types/api";



function providerType(r: Reconciliation): string {
  if (r.stripe_payment_id) return "Stripe";
  if (r.paypal_payment_id) return "PayPal";
  if (r.bank_transfer_id) return "Bank";
  return "-";
}

export function ReconciliationsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const limit = 15;

  const { data, isLoading } = useReconciliations(
    statusFilter || undefined,
    limit,
    page * limit
  );

  const reconciliations = data?.reconciliations ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Reconciliations</h2>

      {/* Filter */}
      <div className="flex gap-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="matched">Matched</option>
          <option value="matched_with_fee">Matched with Fee</option>
          <option value="amount_mismatch">Amount Mismatch</option>
          <option value="missing_internal">Missing Internal</option>
          <option value="duplicate">Duplicate</option>
          <option value="disputed">Disputed</option>
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {total} reconciliations {statusFilter && `(${statusFilter.replace(/_/g, " ")})`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-muted-foreground">Loading...</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead className="text-right">Internal</TableHead>
                    <TableHead className="text-right">External</TableHead>
                    <TableHead className="text-right">Delta</TableHead>
                    <TableHead className="text-right">Confidence</TableHead>
                    <TableHead>Reconciled</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reconciliations.map((r: Reconciliation) => (
                    <TableRow
                      key={r.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/reconciliations/${r.id}`)}
                    >
                      <TableCell className="font-mono text-xs">
                        {r.code}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={reconciliationStatusStyles[r.status] ?? ""}
                        >
                          {r.status.replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {providerType(r)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatAmount(r.internal_amount, r.currency_symbol)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatAmount(r.external_amount, r.currency_symbol)}
                      </TableCell>
                      <TableCell
                        className={`text-right font-mono ${
                          r.delta !== 0 ? "text-destructive" : ""
                        }`}
                      >
                        {r.delta !== 0 ? formatAmount(Math.abs(r.delta), r.currency_symbol) : "-"}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {r.confidence}%
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(r.reconciled_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="mt-4 flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Page {page + 1} of {totalPages || 1} ({total} total)
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page + 1 >= totalPages}
                    className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
