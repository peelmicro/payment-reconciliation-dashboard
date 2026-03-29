import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useReconciliation } from "@/hooks/use-reconciliations";
import { reconciliationStatusStyles } from "@/lib/status-colors";
import { formatAmount } from "@/lib/format";

export function ReconciliationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: r, isLoading } = useReconciliation(id ?? "");

  if (isLoading) {
    return <div className="text-muted-foreground">Loading...</div>;
  }

  if (!r) {
    return <div className="text-muted-foreground">Reconciliation not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate("/reconciliations")}
          className="rounded-md border px-3 py-1 text-sm"
        >
          Back
        </button>
        <h2 className="text-2xl font-bold">{r.code}</h2>
        <Badge
          variant="outline"
          className={reconciliationStatusStyles[r.status] ?? ""}
        >
          {r.status.replace(/_/g, " ")}
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Amounts */}
        <Card>
          <CardHeader>
            <CardTitle>Amounts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Internal Amount</span>
              <span className="font-mono">{formatAmount(r.internal_amount, r.currency_symbol)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">External Amount</span>
              <span className="font-mono">{formatAmount(r.external_amount, r.currency_symbol)}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="font-medium">Delta</span>
              <span
                className={`font-mono font-medium ${
                  r.delta !== 0 ? "text-destructive" : "text-green-600"
                }`}
              >
                {r.delta === 0
                  ? "No difference"
                  : formatAmount(Math.abs(r.delta), r.currency_symbol)}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Scoring */}
        <Card>
          <CardHeader>
            <CardTitle>Match Scoring</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Score</span>
              <span className="font-mono">
                {r.score} / {r.max_score}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-mono font-medium">{r.confidence}%</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-muted-foreground">Notes</span>
              <span className="text-sm">{r.notes ?? "-"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Links */}
        <Card>
          <CardHeader>
            <CardTitle>Linked Records</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Payment ID</span>
              <span className="font-mono text-xs">{r.payment_id ?? "None"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Provider</span>
              <span className="font-mono text-xs">
                {r.stripe_payment_id
                  ? `Stripe: ${r.stripe_payment_id.slice(0, 8)}...`
                  : r.paypal_payment_id
                    ? `PayPal: ${r.paypal_payment_id.slice(0, 8)}...`
                    : r.bank_transfer_id
                      ? `Bank: ${r.bank_transfer_id.slice(0, 8)}...`
                      : "None"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle>Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Reconciled At</span>
              <span className="text-sm">
                {new Date(r.reconciled_at).toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Reconciled By</span>
              <span className="text-sm">{r.reconciled_by}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(r.created_at).toLocaleString()}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
