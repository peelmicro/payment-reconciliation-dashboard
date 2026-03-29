import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useSummary, useTrends } from "@/hooks/use-reconciliations";
import { reconciliationStatusStyles } from "@/lib/status-colors";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

function formatCents(cents: number): string {
  return (cents / 100).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDiscrepancy(cents: number): string {
  return `${formatCents(cents)} (mixed currencies)`;
}

export function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useSummary();
  const { data: trends, isLoading: trendsLoading } = useTrends(30);

  if (summaryLoading) {
    return <div className="text-muted-foreground">Loading dashboard...</div>;
  }

  if (!summary) {
    return <div className="text-muted-foreground">No data available</div>;
  }

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Match Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.match_rate}%</div>
            <p className="text-xs text-muted-foreground">
              {summary.status_counts.matched + summary.status_counts.matched_with_fee} of{" "}
              {summary.total_reconciled} reconciled
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Reconciled
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.total_reconciled}</div>
            <p className="text-xs text-muted-foreground">
              Avg confidence: {summary.confidence.average}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Discrepancy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatDiscrepancy(summary.amounts.total_discrepancy)}
            </div>
            <p className="text-xs text-muted-foreground">
              Absolute difference across all records
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Mismatches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {summary.status_counts.amount_mismatch}
            </div>
            <p className="text-xs text-muted-foreground">
              {summary.status_counts.missing_internal} missing internal
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdown */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(summary.status_counts).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={reconciliationStatusStyles[status] ?? ""}
                    >
                      {status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <span className="font-mono text-sm">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>By Provider</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(summary.by_provider).map(([provider, count]) => (
                <div key={provider} className="flex items-center justify-between">
                  <span className="text-sm font-medium capitalize">{provider}</span>
                  <span className="font-mono text-sm">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trends Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Reconciliation Trends</CardTitle>
        </CardHeader>
        <CardContent>
          {trendsLoading ? (
            <div className="text-muted-foreground">Loading trends...</div>
          ) : trends && trends.trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trends.trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="matched" fill="#22c55e" name="Matched" />
                <Bar
                  dataKey="amount_mismatch"
                  fill="#f59e0b"
                  name="Amount Mismatch"
                />
                <Bar
                  dataKey="missing_internal"
                  fill="#ef4444"
                  name="Missing Internal"
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-muted-foreground">
              No trend data available yet
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
