# payment-reconciliation-dashboard

A payment reconciliation dashboard that matches internal payment records against external provider data (Stripe, PayPal, bank transfers).

## Design Decisions

### Provider Payment Linking (`payment_id`)

Each provider table (`stripe_payments`, `paypal_payments`, `bank_transfer_payments`) has a `payment_id` column (FK to `payments.id`, nullable, unique, indexed) that links external provider records back to internal payments.

**How `payment_id` is populated in production:**

| Provider | Mechanism |
|----------|-----------|
| **Stripe** | When creating a payment intent, we pass our `payment.code` in Stripe's `metadata` field. When Stripe returns data (webhook/API), we extract the code from metadata, look up the payment, and store its ID. |
| **PayPal** | Same approach — `payment.code` is passed in PayPal's `custom_id` field when creating an order. On capture/webhook, we extract it and resolve the `payment_id`. |
| **Bank transfers** | Banks don't support custom metadata. `payment_id` is populated by matching on business fields: `value_date` (date proximity), `iban_masked` (account match), and `vat_number` (merchant identification). |

The `payment_id` index enables efficient `LEFT JOIN` queries to determine which internal payments have not yet been processed by provider simulations, avoiding expensive `NOT IN` subqueries.
