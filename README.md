# payment-reconciliation-dashboard

A payment reconciliation dashboard that matches internal payment records against external provider data (Stripe, PayPal, bank transfers).

## Design Decisions

### Provider Payment Linking (`payment_id`)

Each provider table (`stripe_payments`, `paypal_payments`, `bank_transfer_payments`) has a `payment_id` column (FK to `payments.id`, nullable, unique, indexed) that links external provider records back to internal payments.

**How `payment_id` is populated in production:**

| Provider | Mechanism |
|----------|-----------|
| **Stripe** | When creating a payment intent, we pass our `payment.code` and `vat_number` in Stripe's `metadata` field. When Stripe returns data (webhook/API), we extract them from metadata, look up the payment, and store its ID. |
| **PayPal** | Same approach — `payment.code` and `vat_number` are passed in PayPal's `custom_id` and `metadata` fields when creating an order. On capture/webhook, we extract them and resolve the `payment_id`. |
| **Bank transfers** | Banks don't support custom metadata. `payment_id` is populated by matching on business fields: `value_date` (date proximity), `iban_masked` (account match), and `vat_number` (merchant identification). |

The `payment_id` index enables efficient `LEFT JOIN` queries to determine which internal payments have not yet been processed by provider simulations, avoiding expensive `NOT IN` subqueries.

### VAT Number in Provider Payments

The `vat_number` field exists in all three provider tables (`stripe_payments`, `paypal_payments`, `bank_transfer_payments`). It serves as a strong business identifier for reconciliation matching.

| Provider | How `vat_number` is obtained |
|----------|------------------------------|
| **Stripe** | Passed in payment intent `metadata` when creating the payment. Returned in Stripe's webhook/API response. |
| **PayPal** | Passed in order `metadata` when creating the order. Returned in PayPal's capture/webhook response. |
| **Bank transfers** | Included natively in bank transaction data — banks use the tax identification number as part of the transfer details. |

### Reconciliation Scoring

The reconciliation engine uses a **confidence percentage** scoring system to match provider payments against internal records. This ensures fair comparison across all provider types, regardless of which matching fields are available.

| Criteria | Points | When scored |
|----------|--------|-------------|
| Amount match (exact) | +100 | Always |
| Card BIN + last4 | +50 | Both records have card data |
| IBAN country + last4 | +50 | Both records have IBAN data |
| VAT number | +50 | Both records have VAT |
| Date proximity | +10 to +30 | Always |

**Confidence** = `(score / max_possible_score) * 100`. The `max_possible_score` is calculated dynamically based on which fields are non-null in both records. Threshold: **65%**.

Example: A PayPal wallet payment (no card/IBAN data) has max 180 points (100 + 50 + 30). A score of 180/180 = 100% confidence — just as strong as a Stripe card match at 230/230 = 100%.
