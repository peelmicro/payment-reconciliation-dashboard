#!/usr/bin/env bash
set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "=== Payment Reconciliation Dashboard — Initial Seed ==="
echo ""
echo "API URL: $API_URL"
echo ""

# 1. Health check
echo "1/8  Checking API health..."
curl -sf "$API_URL/health" > /dev/null || { echo "ERROR: API is not reachable at $API_URL. Is the server running?"; exit 1; }
echo "     OK"

# 2. Seed reference data
echo "2/8  Seeding currencies (USD, EUR, GBP)..."
curl -sf -X POST "$API_URL/seed/currencies" > /dev/null
echo "     OK"

echo "3/8  Seeding providers (Stripe, PayPal, Bankinter)..."
curl -sf -X POST "$API_URL/seed/providers" > /dev/null
echo "     OK"

echo "4/8  Seeding merchants (2 Spain, 1 UK)..."
curl -sf -X POST "$API_URL/seed/merchants" > /dev/null
echo "     OK"

# 3. Generate internal payments (15 in one call)
echo "5/8  Generating 15 fake payments..."
curl -sf -X POST "$API_URL/payments/generate?count=15" > /dev/null
echo "     OK"

# 4. Simulate provider records
echo "6/8  Simulating Stripe payments..."
curl -sf -X POST "$API_URL/stripe-payments/simulate" > /dev/null
echo "     OK"

echo "7/8  Simulating PayPal payments..."
curl -sf -X POST "$API_URL/paypal-payments/simulate" > /dev/null
echo "     OK"

echo "     Simulating bank transfer payments..."
curl -sf -X POST "$API_URL/bank-payments/simulate" > /dev/null
echo "     OK"

# 5. Simulate orphan records (to demonstrate missing_internal status)
echo "     Simulating 2 orphan Stripe records..."
curl -sf -X POST "$API_URL/stripe-payments/simulate-orphan?count=2" > /dev/null
echo "     OK"

echo "     Simulating 2 orphan PayPal records..."
curl -sf -X POST "$API_URL/paypal-payments/simulate-orphan?count=2" > /dev/null
echo "     OK"

echo "     Simulating 2 orphan bank transfer records..."
curl -sf -X POST "$API_URL/bank-payments/simulate-orphan?count=2" > /dev/null
echo "     OK"

# 6. Run reconciliation
echo "8/8  Running reconciliation engine..."
curl -sf -X POST "$API_URL/reconciliations/run" > /dev/null
echo "     OK"

echo ""
echo "=== Done! Open http://localhost:3000 to see the dashboard ==="
