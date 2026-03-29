from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.bank.model import BankTransferPayment
from app.common.code_generator import generate_code
from app.common.enums import ReconciliationStatus
from app.currency.model import Currency
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.paypal.model import PaypalPayment
from app.reconciliation.engine import (
    CONFIDENCE_THRESHOLD,
    InternalPayment,
    MatchCandidate,
    score_match,
)
from app.reconciliation.model import Reconciliation
from app.stripe.model import StripePayment


async def _build_candidates(session: AsyncSession) -> list[MatchCandidate]:
    """Load all provider payments that haven't been reconciled yet."""
    candidates = []

    # Stripe: LEFT JOIN reconciliations to find unreconciled
    rec_s = aliased(Reconciliation)
    stripe_result = await session.execute(
        select(StripePayment)
        .outerjoin(rec_s, StripePayment.id == rec_s.stripe_payment_id)
        .where(rec_s.id.is_(None))
    )
    for sp in stripe_result.scalars().all():
        candidates.append(MatchCandidate(
            provider_type="stripe",
            provider_record_id=str(sp.id),
            amount=sp.amount,
            currency=sp.currency,
            card_bin=sp.card_bin,
            card_last4=sp.card_last4,
            iban_country=None,
            iban_last_four=None,
            vat_number=sp.vat_number,
            provider_date=sp.stripe_created_at,
        ))

    # PayPal: LEFT JOIN reconciliations to find unreconciled
    rec_p = aliased(Reconciliation)
    paypal_result = await session.execute(
        select(PaypalPayment)
        .outerjoin(rec_p, PaypalPayment.id == rec_p.paypal_payment_id)
        .where(rec_p.id.is_(None))
    )
    for pp in paypal_result.scalars().all():
        candidates.append(MatchCandidate(
            provider_type="paypal",
            provider_record_id=str(pp.id),
            amount=pp.amount,
            currency=pp.currency,
            card_bin=pp.card_bin,
            card_last4=pp.card_last4,
            iban_country=None,
            iban_last_four=None,
            vat_number=pp.vat_number,
            provider_date=pp.paypal_created_at,
        ))

    # Bank: LEFT JOIN reconciliations to find unreconciled
    rec_b = aliased(Reconciliation)
    bank_result = await session.execute(
        select(BankTransferPayment)
        .outerjoin(rec_b, BankTransferPayment.id == rec_b.bank_transfer_id)
        .where(rec_b.id.is_(None))
    )
    for bp in bank_result.scalars().all():
        candidates.append(MatchCandidate(
            provider_type="bank",
            provider_record_id=str(bp.id),
            amount=bp.amount,
            currency=bp.currency,
            card_bin=None,
            card_last4=None,
            iban_country=bp.iban_country,
            iban_last_four=bp.iban_last_four,
            vat_number=bp.vat_number,
            provider_date=bp.bank_created_at,
        ))

    return candidates


async def _build_internal_payments(
    session: AsyncSession,
) -> list[InternalPayment]:
    """Load all internal payments with their merchant's VAT number."""
    currencies = (await session.execute(select(Currency))).scalars().all()
    currency_map = {c.id: c for c in currencies}

    merchants = (await session.execute(select(Merchant))).scalars().all()
    merchant_map = {m.id: m for m in merchants}

    payments_result = await session.execute(select(Payment))
    payments = payments_result.scalars().all()

    return [
        InternalPayment(
            payment_id=str(p.id),
            amount=p.amount,
            fee=p.fee,
            net=p.net,
            currency_id=str(p.currency_id),
            currency_code=currency_map[p.currency_id].code,
            card_bin=p.card_bin,
            card_last_four=p.card_last_four,
            iban_country=p.iban_country,
            iban_last_four=p.iban_last_four,
            vat_number=merchant_map[p.merchant_id].vat_number,
            processed_at=p.processed_at,
        )
        for p in payments
    ]


def _determine_status(
    amount_match_type: str,
) -> ReconciliationStatus:
    """Determine reconciliation status from the amount match type."""
    if amount_match_type == "exact":
        return ReconciliationStatus.matched
    elif amount_match_type == "after_fee":
        return ReconciliationStatus.matched_with_fee
    else:
        return ReconciliationStatus.amount_mismatch


async def run_reconciliation(session: AsyncSession) -> dict:
    """
    Run the full reconciliation process:
    1. Load unreconciled provider payments (candidates)
    2. Load internal payments
    3. Score each candidate against all internal payments
    4. Create reconciliation records for matches, mismatches, and missing_internal
    5. Count missing_external (informational only — no records created,
       so they can be matched in future runs when provider data arrives)
    """

    candidates = await _build_candidates(session)
    internal_payments = await _build_internal_payments(session)

    # Track which internal payments have been matched in this run
    matched_payment_ids: set[str] = set()
    # Track already reconciled payment IDs (from previous runs)
    existing_rec = await session.execute(
        select(Reconciliation.payment_id).where(
            Reconciliation.payment_id.is_not(None)
        )
    )
    already_reconciled = {str(row[0]) for row in existing_rec.all()}

    results = {
        "matched": 0,
        "matched_with_fee": 0,
        "amount_mismatch": 0,
        "missing_internal": 0,
        "missing_external": 0,
        "duplicate": 0,
        "total_processed": 0,
    }

    now = datetime.now(timezone.utc)

    # --- Match each candidate (provider payment) against internal payments ---
    for candidate in candidates:
        best_result = None
        matches_above_threshold = []

        for payment in internal_payments:
            # Skip already matched payments
            if payment.payment_id in matched_payment_ids:
                continue
            if payment.payment_id in already_reconciled:
                continue

            result = score_match(payment, candidate)
            if result.confidence >= CONFIDENCE_THRESHOLD:
                matches_above_threshold.append(result)
                if best_result is None or result.confidence > best_result.confidence:
                    best_result = result

        code = await generate_code(session, "REC")

        if len(matches_above_threshold) > 1:
            # Multiple matches — flag as duplicate
            matched_payment = _get_internal_payment(
                best_result, internal_payments
            )
            recon = Reconciliation(
                code=code,
                status=ReconciliationStatus.duplicate,
                payment_id=matched_payment.payment_id if matched_payment else None,
                internal_amount=matched_payment.amount if matched_payment else 0,
                stripe_payment_id=_provider_id(candidate, "stripe"),
                paypal_payment_id=_provider_id(candidate, "paypal"),
                bank_transfer_id=_provider_id(candidate, "bank"),
                external_amount=candidate.amount,
                delta=0,
                currency_id=_find_currency_id_by_code(
                    candidate.currency, internal_payments
                ),
                score=best_result.score if best_result else 0,
                max_score=best_result.max_score if best_result else 0,
                confidence=best_result.confidence if best_result else 0,
                reconciled_at=now,
                reconciled_by="system",
                notes=f"Multiple matches found ({len(matches_above_threshold)} candidates above threshold)",
            )
            session.add(recon)
            results["duplicate"] += 1

        elif best_result is not None:
            # Single best match
            matched_payment = _get_internal_payment(
                best_result, internal_payments
            )
            status = _determine_status(best_result.amount_match_type)
            delta = candidate.amount - matched_payment.amount

            recon = Reconciliation(
                code=code,
                status=status,
                payment_id=matched_payment.payment_id,
                internal_amount=matched_payment.amount,
                stripe_payment_id=_provider_id(candidate, "stripe"),
                paypal_payment_id=_provider_id(candidate, "paypal"),
                bank_transfer_id=_provider_id(candidate, "bank"),
                external_amount=candidate.amount,
                delta=delta,
                currency_id=matched_payment.currency_id,
                score=best_result.score,
                max_score=best_result.max_score,
                confidence=best_result.confidence,
                reconciled_at=now,
                reconciled_by="system",
                notes=f"Score: {best_result.score}/{best_result.max_score} ({best_result.confidence}%)",
            )
            session.add(recon)
            matched_payment_ids.add(matched_payment.payment_id)
            results[status.value] += 1

        else:
            # No match found — provider has a record we don't
            currency_id = _find_currency_id_by_code(
                candidate.currency, internal_payments
            )
            recon = Reconciliation(
                code=code,
                status=ReconciliationStatus.missing_internal,
                payment_id=None,
                internal_amount=0,
                stripe_payment_id=_provider_id(candidate, "stripe"),
                paypal_payment_id=_provider_id(candidate, "paypal"),
                bank_transfer_id=_provider_id(candidate, "bank"),
                external_amount=candidate.amount,
                delta=candidate.amount,
                currency_id=currency_id,
                score=0,
                max_score=0,
                confidence=0,
                reconciled_at=now,
                reconciled_by="system",
                notes="No matching internal payment found",
            )
            session.add(recon)
            results["missing_internal"] += 1

        results["total_processed"] += 1

    # --- Count missing_external (informational only, no records created) ---
    cutoff = now - timedelta(hours=1)
    for payment in internal_payments:
        if payment.payment_id in matched_payment_ids:
            continue
        if payment.payment_id in already_reconciled:
            continue
        if payment.processed_at > cutoff:
            continue
        results["missing_external"] += 1

    await session.commit()
    return results


# --- Helper functions ---

def _provider_id(candidate: MatchCandidate, provider_type: str) -> str | None:
    """Return the provider record ID only if it matches the provider type."""
    if candidate.provider_type == provider_type:
        return candidate.provider_record_id
    return None


def _get_internal_payment(
    result, internal_payments: list[InternalPayment]
) -> InternalPayment:
    """Find the internal payment that produced the best match result."""
    best_payment = None
    best_score = -1
    for payment in internal_payments:
        r = score_match(payment, result.candidate)
        if r.score > best_score:
            best_score = r.score
            best_payment = payment
    return best_payment


def _find_currency_id_by_code(
    currency_code: str,
    internal_payments: list[InternalPayment],
) -> str:
    """Find a currency_id by matching the currency code from internal payments."""
    for p in internal_payments:
        if p.currency_code == currency_code:
            return p.currency_id
    return internal_payments[0].currency_id if internal_payments else ""
