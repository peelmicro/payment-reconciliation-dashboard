"""
Unit tests for the reconciliation scoring engine.

score_match() is pure Python with no database dependency — ideal for unit tests.
Each test covers a specific scoring rule in isolation.
"""
from datetime import datetime, timedelta, timezone

from app.reconciliation.engine import (
    CONFIDENCE_THRESHOLD,
    InternalPayment,
    MatchCandidate,
    score_match,
)

# ---------------------------------------------------------------------------
# Helpers — build default objects and override only the fields under test
# ---------------------------------------------------------------------------

def make_payment(**overrides) -> InternalPayment:
    defaults = {
        "payment_id": "pay-001",
        "amount": 10_000,       # €100.00 in cents
        "fee": 250,             # €2.50 fee
        "net": 9_750,           # amount - fee
        "currency_id": "curr-001",
        "currency_code": "EUR",
        "card_bin": "411111",
        "card_last_four": "4242",
        "iban_country": None,
        "iban_last_four": None,
        "vat_number": "ES12345678",
        "processed_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
    }
    return InternalPayment(**{**defaults, **overrides})


def make_candidate(**overrides) -> MatchCandidate:
    defaults = {
        "provider_type": "stripe",
        "provider_record_id": "str-001",
        "amount": 10_000,
        "currency": "EUR",
        "card_bin": "411111",
        "card_last4": "4242",
        "iban_country": None,
        "iban_last_four": None,
        "vat_number": "ES12345678",
        "provider_date": datetime(2026, 3, 1, 12, 1, 0, tzinfo=timezone.utc),  # 1 min later
    }
    return MatchCandidate(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Amount scoring
# ---------------------------------------------------------------------------

class TestAmountScoring:
    def test_exact_amount_match_type_is_exact(self):
        result = score_match(make_payment(amount=10_000), make_candidate(amount=10_000))
        assert result.amount_match_type == "exact"

    def test_exact_amount_contributes_100_points(self):
        result = score_match(make_payment(amount=10_000), make_candidate(amount=10_000))
        # At minimum: 100 (amount) must be in the score
        assert result.score >= 100

    def test_amount_match_after_fee_type_is_after_fee(self):
        # net = 10000 - 250 = 9750 — provider charged net amount
        result = score_match(
            make_payment(amount=10_000, fee=250, net=9_750),
            make_candidate(amount=9_750),
        )
        assert result.amount_match_type == "after_fee"

    def test_amount_match_after_fee_contributes_80_points(self):
        result = score_match(
            make_payment(amount=10_000, fee=250, net=9_750),
            make_candidate(amount=9_750),
        )
        assert result.score >= 80

    def test_large_amount_difference_is_mismatch(self):
        # diff = 2000 > 50 cent tolerance → mismatch
        result = score_match(make_payment(amount=10_000), make_candidate(amount=8_000))
        assert result.amount_match_type == "mismatch"


# ---------------------------------------------------------------------------
# Currency filter (hard gate — not scored)
# ---------------------------------------------------------------------------

class TestCurrencyFilter:
    def test_currency_mismatch_returns_zero_confidence(self):
        result = score_match(
            make_payment(currency_code="EUR"),
            make_candidate(currency="USD"),
        )
        assert result.confidence == 0
        assert result.score == 0

    def test_currency_mismatch_returns_zero_even_when_amounts_match(self):
        result = score_match(
            make_payment(amount=10_000, currency_code="EUR"),
            make_candidate(amount=10_000, currency="GBP"),
        )
        assert result.score == 0


# ---------------------------------------------------------------------------
# Card field scoring
# ---------------------------------------------------------------------------

class TestCardScoring:
    def test_matching_bin_and_last4_adds_50_points(self):
        payment = make_payment(card_bin="411111", card_last_four="4242", vat_number=None)
        candidate = make_candidate(card_bin="411111", card_last4="4242", vat_number=None)
        result = score_match(payment, candidate)
        # max = 100 (amount) + 50 (card) + 30 (date) = 180
        assert result.score == 180

    def test_mismatched_last4_scores_lower_than_match(self):
        payment = make_payment(card_bin="411111", card_last_four="4242", vat_number=None)
        match = score_match(payment, make_candidate(card_bin="411111", card_last4="4242", vat_number=None))
        mismatch = score_match(payment, make_candidate(card_bin="411111", card_last4="9999", vat_number=None))
        assert match.score > mismatch.score

    def test_card_not_in_max_score_when_candidate_has_no_card(self):
        payment = make_payment(card_bin="411111", card_last_four="4242", vat_number=None)
        candidate = make_candidate(card_bin=None, card_last4=None, vat_number=None)
        result = score_match(payment, candidate)
        # Card not counted — max = 100 + 30 = 130
        assert result.max_score == 130


# ---------------------------------------------------------------------------
# IBAN field scoring
# ---------------------------------------------------------------------------

class TestIBANScoring:
    def test_matching_iban_adds_50_points(self):
        payment = make_payment(card_bin=None, card_last_four=None, iban_country="ES", iban_last_four="1234", vat_number=None)
        candidate = make_candidate(card_bin=None, card_last4=None, iban_country="ES", iban_last_four="1234", vat_number=None)
        result = score_match(payment, candidate)
        # max = 100 + 50 (IBAN) + 30 (date) = 180
        assert result.score == 180

    def test_iban_not_in_max_score_when_only_one_side_has_it(self):
        payment = make_payment(card_bin=None, card_last_four=None, iban_country="ES", iban_last_four="1234", vat_number=None)
        candidate = make_candidate(card_bin=None, card_last4=None, iban_country=None, iban_last_four=None, vat_number=None)
        result = score_match(payment, candidate)
        assert result.max_score == 130  # 100 (amount) + 30 (date)


# ---------------------------------------------------------------------------
# VAT number scoring
# ---------------------------------------------------------------------------

class TestVATScoring:
    def test_matching_vat_adds_50_points(self):
        payment = make_payment(card_bin=None, card_last_four=None, vat_number="ES12345678")
        candidate = make_candidate(card_bin=None, card_last4=None, vat_number="ES12345678")
        result = score_match(payment, candidate)
        # max = 100 + 50 (VAT) + 30 (date) = 180
        assert result.score == 180

    def test_vat_mismatch_does_not_add_points(self):
        payment = make_payment(card_bin=None, card_last_four=None, vat_number="ES12345678")
        candidate = make_candidate(card_bin=None, card_last4=None, vat_number="FR99999999")
        result = score_match(payment, candidate)
        # max = 180 (VAT counted), but score = 100 + 0 (VAT mismatch) + 30 = 130
        assert result.score == 130


# ---------------------------------------------------------------------------
# Date proximity scoring
# ---------------------------------------------------------------------------

class TestDateProximityScoring:
    def _payment_and_candidate(self, delta: timedelta) -> tuple:
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        payment = make_payment(processed_at=now, card_bin=None, card_last_four=None, vat_number=None)
        candidate = make_candidate(provider_date=now + delta, card_bin=None, card_last4=None, vat_number=None)
        return payment, candidate

    def test_within_5_minutes_adds_30_points(self):
        payment, candidate = self._payment_and_candidate(timedelta(minutes=4))
        result = score_match(payment, candidate)
        assert result.score == 130  # 100 (exact amount) + 30 (date ≤5min)

    def test_within_1_hour_adds_20_points(self):
        payment, candidate = self._payment_and_candidate(timedelta(minutes=30))
        result = score_match(payment, candidate)
        assert result.score == 120  # 100 + 20

    def test_within_1_day_adds_10_points(self):
        payment, candidate = self._payment_and_candidate(timedelta(hours=12))
        result = score_match(payment, candidate)
        assert result.score == 110  # 100 + 10

    def test_beyond_1_day_adds_zero_date_points(self):
        payment, candidate = self._payment_and_candidate(timedelta(days=2))
        result = score_match(payment, candidate)
        assert result.score == 100  # 100 only — no date bonus


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

class TestConfidenceCalculation:
    def test_confidence_equals_score_over_max_score_as_percentage(self):
        payment = make_payment(card_bin=None, card_last_four=None, vat_number=None)
        candidate = make_candidate(card_bin=None, card_last4=None, vat_number=None)
        result = score_match(payment, candidate)
        expected = int((result.score / result.max_score) * 100)
        assert result.confidence == expected

    def test_perfect_match_gives_100_percent_confidence(self):
        # All fields match and date is very close
        payment = make_payment(card_bin=None, card_last_four=None, vat_number=None)
        candidate = make_candidate(card_bin=None, card_last4=None, vat_number=None)
        result = score_match(payment, candidate)
        assert result.confidence == 100

    def test_confidence_threshold_is_65(self):
        assert CONFIDENCE_THRESHOLD == 65
