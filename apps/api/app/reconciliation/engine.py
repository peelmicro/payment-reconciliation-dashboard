from dataclasses import dataclass
from datetime import datetime


@dataclass
class MatchCandidate:
    """Represents an external provider payment to match against."""
    provider_type: str          # "stripe", "paypal", "bank"
    provider_record_id: str     # UUID of the provider record
    amount: int                 # Amount in cents
    currency: str               # ISO 4217 code
    card_bin: str | None
    card_last4: str | None
    iban_country: str | None
    iban_last_four: str | None
    vat_number: str | None
    provider_date: datetime     # stripe_created_at / paypal_created_at / bank_created_at


@dataclass
class InternalPayment:
    """Represents an internal payment to reconcile."""
    payment_id: str             # UUID
    amount: int                 # Amount in cents
    fee: int                    # Fee in cents
    net: int                    # Net in cents
    currency_id: str            # UUID of currency
    currency_code: str          # ISO 4217 code
    card_bin: str | None
    card_last_four: str | None
    iban_country: str | None
    iban_last_four: str | None
    vat_number: str | None      # From the merchant
    processed_at: datetime


@dataclass
class MatchResult:
    """Result of scoring a candidate against an internal payment."""
    score: int
    max_score: int
    confidence: int             # Percentage: score / max_score * 100
    candidate: MatchCandidate
    amount_match_type: str      # "exact", "after_fee", "mismatch"


# Minimum confidence percentage to consider a match valid
CONFIDENCE_THRESHOLD = 65


def score_match(
    payment: InternalPayment,
    candidate: MatchCandidate,
) -> MatchResult:
    """
    Score how well a provider payment matches an internal payment.
    Returns both raw score and confidence percentage.

    Scoring:
      - Exact amount match:            +100 points (max 100)
      - Amount match after fee:         +80 points (max 100)
      - Card match (BIN + last4):       +50 points (only if both have card data)
      - IBAN match (country + last4):   +50 points (only if both have IBAN data)
      - VAT number match:              +50 points (only if both have VAT)
      - Date proximity:                +10 to +30 points (max 30)

    Max score is calculated dynamically based on which fields are
    available in both records, so confidence % is comparable across
    all provider types.
    """
    score = 0
    max_score = 0
    amount_match_type = "mismatch"

    # 1. Currency must match (hard filter, not scored)
    if candidate.currency != payment.currency_code:
        return MatchResult(
            score=0, max_score=1, confidence=0,
            candidate=candidate, amount_match_type="mismatch",
        )

    # 2. Amount matching (always applicable: +100 max)
    max_score += 100
    if candidate.amount == payment.amount:
        score += 100
        amount_match_type = "exact"
    elif candidate.amount == payment.net:
        score += 80
        amount_match_type = "after_fee"
    elif abs(candidate.amount - payment.amount) <= 50:
        score += 60
        amount_match_type = "mismatch"

    # 3. Card matching (only if both have card data)
    if candidate.card_bin and payment.card_bin:
        max_score += 50
        if (
            candidate.card_bin == payment.card_bin
            and candidate.card_last4
            and payment.card_last_four
            and candidate.card_last4 == payment.card_last_four
        ):
            score += 50

    # 4. IBAN matching (only if both have IBAN data)
    if candidate.iban_country and payment.iban_country:
        max_score += 50
        if (
            candidate.iban_country == payment.iban_country
            and candidate.iban_last_four
            and payment.iban_last_four
            and candidate.iban_last_four == payment.iban_last_four
        ):
            score += 50

    # 5. VAT number matching (only if both have VAT)
    if candidate.vat_number and payment.vat_number:
        max_score += 50
        if candidate.vat_number == payment.vat_number:
            score += 50

    # 6. Date proximity (always applicable: +30 max)
    max_score += 30
    time_diff = abs(
        (candidate.provider_date - payment.processed_at).total_seconds()
    )
    if time_diff <= 300:          # Within 5 minutes
        score += 30
    elif time_diff <= 3600:       # Within 1 hour
        score += 20
    elif time_diff <= 86400:      # Within 1 day
        score += 10

    # Calculate confidence percentage
    confidence = int((score / max_score) * 100) if max_score > 0 else 0

    return MatchResult(
        score=score,
        max_score=max_score,
        confidence=confidence,
        candidate=candidate,
        amount_match_type=amount_match_type,
    )
