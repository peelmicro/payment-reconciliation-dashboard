// Enums matching the backend
export type PaymentStatus =
  | "pending"
  | "succeeded"
  | "failed"
  | "refunded"
  | "partially_refunded"
  | "disputed";

export type PaymentMethod =
  | "card"
  | "paypal_wallet"
  | "bank_transfer"
  | "direct_debit";

export type ReconciliationStatus =
  | "matched"
  | "matched_with_fee"
  | "amount_mismatch"
  | "missing_internal"
  | "missing_external"
  | "duplicate"
  | "disputed";

// API response types
export interface Payment {
  id: string;
  code: string;
  merchant_id: string;
  provider_id: string;
  status: PaymentStatus;
  payment_method: PaymentMethod;
  amount: number;
  fee: number;
  net: number;
  currency_id: string;
  currency_code: string;
  currency_symbol: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  description: string;
  card_bin: string | null;
  card_last_four: string | null;
  card_masked: string | null;
  card_brand: string | null;
  iban_country: string | null;
  iban_bank: string | null;
  iban_branch: string | null;
  iban_last_four: string | null;
  iban_masked: string | null;
  processed_at: string;
  created_at: string;
  updated_at: string;
}

export interface Reconciliation {
  id: string;
  code: string;
  status: ReconciliationStatus;
  payment_id: string | null;
  internal_amount: number;
  stripe_payment_id: string | null;
  paypal_payment_id: string | null;
  bank_transfer_id: string | null;
  external_amount: number;
  delta: number;
  currency_id: string;
  currency_code: string;
  currency_symbol: string;
  score: number;
  max_score: number;
  confidence: number;
  reconciled_at: string;
  reconciled_by: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  total: number;
  limit: number;
  offset: number;
  payments?: T[];
  reconciliations?: T[];
}

export interface ReconciliationSummary {
  total_reconciled: number;
  match_rate: number;
  status_counts: {
    matched: number;
    matched_with_fee: number;
    amount_mismatch: number;
    missing_internal: number;
    missing_external: number;
    duplicate: number;
    disputed: number;
  };
  amounts: {
    total_internal: number;
    total_external: number;
    total_discrepancy: number;
  };
  confidence: {
    average: number;
    min: number;
    max: number;
  };
  by_provider: {
    stripe: number;
    paypal: number;
    bank: number;
  };
}

export interface TrendDay {
  date: string;
  total: number;
  matched: number;
  amount_mismatch: number;
  missing_internal: number;
  match_rate: number;
  total_internal: number;
  total_external: number;
  total_discrepancy: number;
  avg_confidence: number;
  by_provider: {
    stripe: number;
    paypal: number;
    bank: number;
  };
}

export interface TrendsResponse {
  days: number;
  trends: TrendDay[];
}

export interface AskResponse {
  question: string;
  sql?: string;
  answer?: string;
  error?: string;
}
