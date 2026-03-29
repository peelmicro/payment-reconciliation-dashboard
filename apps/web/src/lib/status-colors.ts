// Status badge styles for consistent colors across all pages
// Each status gets a unique color so they're visually distinguishable

export const reconciliationStatusStyles: Record<string, string> = {
  matched: "bg-green-100 text-green-800 border-green-200",
  matched_with_fee: "bg-emerald-100 text-emerald-800 border-emerald-200",
  amount_mismatch: "bg-amber-100 text-amber-800 border-amber-200",
  missing_internal: "bg-red-100 text-red-800 border-red-200",
  missing_external: "bg-orange-100 text-orange-800 border-orange-200",
  duplicate: "bg-purple-100 text-purple-800 border-purple-200",
  disputed: "bg-rose-100 text-rose-800 border-rose-200",
};

export const paymentStatusStyles: Record<string, string> = {
  succeeded: "bg-green-100 text-green-800 border-green-200",
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  failed: "bg-red-100 text-red-800 border-red-200",
  refunded: "bg-blue-100 text-blue-800 border-blue-200",
  partially_refunded: "bg-sky-100 text-sky-800 border-sky-200",
  disputed: "bg-rose-100 text-rose-800 border-rose-200",
};
