"""
Tests for the reconciliation service.

Two levels of testing:
1. Pure Python helpers (_determine_status, _provider_id, _find_currency_id_by_code)
   — no database, no mocking needed.
2. run_reconciliation() with an empty mocked database
   — verifies the orchestration contract: zero results, commit always called.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.common.enums import ReconciliationStatus
from app.reconciliation.engine import InternalPayment, MatchCandidate
from app.reconciliation.service import (
    _determine_status,
    _find_currency_id_by_code,
    _provider_id,
    run_reconciliation,
)


# ---------------------------------------------------------------------------
# _determine_status — maps scoring result to ReconciliationStatus
# ---------------------------------------------------------------------------

class TestDetermineStatus:
    def test_exact_amount_maps_to_matched(self):
        assert _determine_status("exact") == ReconciliationStatus.matched

    def test_after_fee_maps_to_matched_with_fee(self):
        assert _determine_status("after_fee") == ReconciliationStatus.matched_with_fee

    def test_mismatch_maps_to_amount_mismatch(self):
        assert _determine_status("mismatch") == ReconciliationStatus.amount_mismatch

    def test_unknown_type_maps_to_amount_mismatch(self):
        # Any unrecognised value falls through to the else branch
        assert _determine_status("unknown") == ReconciliationStatus.amount_mismatch


# ---------------------------------------------------------------------------
# _provider_id — returns the record ID only when provider type matches
# ---------------------------------------------------------------------------

class TestProviderId:
    def _stripe_candidate(self) -> MatchCandidate:
        return MatchCandidate(
            provider_type="stripe",
            provider_record_id="stripe-abc-123",
            amount=10_000,
            currency="EUR",
            card_bin="411111",
            card_last4="4242",
            iban_country=None,
            iban_last_four=None,
            vat_number=None,
            provider_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )

    def test_returns_id_when_provider_type_matches(self):
        assert _provider_id(self._stripe_candidate(), "stripe") == "stripe-abc-123"

    def test_returns_none_when_provider_type_differs(self):
        assert _provider_id(self._stripe_candidate(), "paypal") is None
        assert _provider_id(self._stripe_candidate(), "bank") is None


# ---------------------------------------------------------------------------
# _find_currency_id_by_code — looks up currency_id from internal payments
# ---------------------------------------------------------------------------

class TestFindCurrencyIdByCode:
    def _payments(self) -> list[InternalPayment]:
        now = datetime(2026, 3, 1, tzinfo=timezone.utc)
        return [
            InternalPayment(
                payment_id="p1", amount=10_000, fee=0, net=10_000,
                currency_id="curr-eur", currency_code="EUR",
                card_bin=None, card_last_four=None,
                iban_country=None, iban_last_four=None,
                vat_number=None, processed_at=now,
            ),
            InternalPayment(
                payment_id="p2", amount=10_000, fee=0, net=10_000,
                currency_id="curr-gbp", currency_code="GBP",
                card_bin=None, card_last_four=None,
                iban_country=None, iban_last_four=None,
                vat_number=None, processed_at=now,
            ),
        ]

    def test_returns_matching_currency_id(self):
        assert _find_currency_id_by_code("EUR", self._payments()) == "curr-eur"
        assert _find_currency_id_by_code("GBP", self._payments()) == "curr-gbp"

    def test_falls_back_to_first_currency_when_code_not_found(self):
        # USD is not in the list — returns the first payment's currency_id
        assert _find_currency_id_by_code("USD", self._payments()) == "curr-eur"


# ---------------------------------------------------------------------------
# run_reconciliation — orchestration with empty mocked database
# ---------------------------------------------------------------------------

class TestRunReconciliation:
    def _make_empty_session(self) -> AsyncMock:
        """
        Session mock where every query returns empty results.
        Simulates a database with no provider payments and no internal payments.
        """
        session = AsyncMock()

        def empty_result(*args, **kwargs):
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            result.all.return_value = []
            result.scalar.return_value = 0
            return result

        session.execute = AsyncMock(side_effect=empty_result)
        session.add = MagicMock()
        session.commit = AsyncMock()
        return session

    async def test_empty_database_returns_all_zero_counts(self):
        results = await run_reconciliation(self._make_empty_session())
        assert results["total_processed"] == 0
        assert results["matched"] == 0
        assert results["matched_with_fee"] == 0
        assert results["amount_mismatch"] == 0
        assert results["missing_internal"] == 0
        assert results["missing_external"] == 0
        assert results["duplicate"] == 0

    async def test_commit_is_always_called(self):
        """Commit must run even when there is nothing to reconcile."""
        session = self._make_empty_session()
        await run_reconciliation(session)
        session.commit.assert_called_once()

    async def test_no_records_added_when_database_is_empty(self):
        """session.add() must not be called if there are no candidates."""
        session = self._make_empty_session()
        await run_reconciliation(session)
        session.add.assert_not_called()
