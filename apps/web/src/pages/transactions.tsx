import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { paymentStatusStyles } from "@/lib/status-colors";
import { formatAmount } from "@/lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePayments } from "@/hooks/use-reconciliations";
import type { Payment } from "@/types/api";



export function TransactionsPage() {
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [methodFilter, setMethodFilter] = useState("");
  const limit = 15;

  const params: Record<string, string> = {};
  if (statusFilter) params.status = statusFilter;
  if (methodFilter) params.payment_method = methodFilter;

  const { data, isLoading } = usePayments(params, limit, page * limit);

  const payments = data?.payments ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Transactions</h2>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="succeeded">Succeeded</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="refunded">Refunded</option>
          <option value="disputed">Disputed</option>
        </select>

        <select
          value={methodFilter}
          onChange={(e) => { setMethodFilter(e.target.value); setPage(0); }}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">All Methods</option>
          <option value="card">Card</option>
          <option value="paypal_wallet">PayPal Wallet</option>
          <option value="bank_transfer">Bank Transfer</option>
          <option value="direct_debit">Direct Debit</option>
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            {total} transactions {statusFilter && `(${statusFilter})`}
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
                    <TableHead>Method</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="text-right">Fee</TableHead>
                    <TableHead className="text-right">Net</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Card/IBAN</TableHead>
                    <TableHead>Processed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payments.map((p: Payment) => (
                    <TableRow key={p.id}>
                      <TableCell className="font-mono text-xs">
                        {p.code}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={paymentStatusStyles[p.status] ?? ""}
                        >
                          {p.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        {p.payment_method.replace(/_/g, " ")}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatAmount(p.amount, p.currency_symbol)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-muted-foreground">
                        {formatAmount(p.fee, p.currency_symbol)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatAmount(p.net, p.currency_symbol)}
                      </TableCell>
                      <TableCell className="max-w-[150px] truncate text-xs">
                        {p.customer_name}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {p.card_masked ?? p.iban_masked ?? "-"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(p.processed_at).toLocaleString()}
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
