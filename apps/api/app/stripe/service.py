import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.common.code_generator import generate_code
from app.common.enums import PaymentMethod, PaymentStatus, StripePaymentType
from app.currency.model import Currency
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.provider.model import Provider
from app.stripe.model import StripePayment

fake = Faker()

# Map PaymentStatus to Stripe's raw status strings
STATUS_MAP = {
    PaymentStatus.succeeded: "succeeded",
    PaymentStatus.pending: "requires_payment_method",
    PaymentStatus.failed: "failed",
    PaymentStatus.refunded: "refunded",
    PaymentStatus.partially_refunded: "partially_refunded",
    PaymentStatus.disputed: "disputed",
}


async def simulate_stripe_payments(session: AsyncSession) -> list[dict]:
    """
    Take recent internal payments from Stripe provider and create
    corresponding stripe_payments records, simulating Stripe's data.
    Applies Stripe fee (2.9% + 30 cents) and introduces small discrepancies.
    """

    # Find the Stripe provider
    result = await session.execute(
        select(Provider).where(Provider.code == "STRIPE")
    )
    stripe_provider = result.scalar_one_or_none()
    if stripe_provider is None:
        return []

    # Find Stripe card payments from the last 24 hours
    # LEFT JOIN stripe_payments to exclude those already simulated
    sp = aliased(StripePayment)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    payments_result = await session.execute(
        select(Payment)
        .outerjoin(sp, Payment.id == sp.payment_id)
        .where(
            Payment.provider_id == stripe_provider.id,
            Payment.payment_method == PaymentMethod.card,
            Payment.processed_at >= since,
            sp.id.is_(None),  # No matching stripe_payment exists
        )
    )
    payments = payments_result.scalars().all()

    # Build lookups
    currencies = (await session.execute(select(Currency))).scalars().all()
    currency_map = {c.id: c for c in currencies}
    merchants = (await session.execute(select(Merchant))).scalars().all()
    merchant_map = {m.id: m for m in merchants}

    created = []
    for payment in payments:
        currency = currency_map[payment.currency_id]
        merchant = merchant_map[payment.merchant_id]

        # Apply Stripe fee: 2.9% + 30 cents
        stripe_fee = int(payment.amount * 0.029) + 30

        # Introduce small discrepancies in ~20% of cases
        amount = payment.amount
        if random.random() < 0.2:
            # Small amount difference (1-50 cents)
            amount += random.randint(-50, 50)

        stripe_net = amount - stripe_fee

        # Map our status to Stripe's status strings
        stripe_status = STATUS_MAP.get(payment.status, "succeeded")

        # Stripe timestamp: slightly after our processed_at (1-60 seconds)
        stripe_created = payment.processed_at + timedelta(
            seconds=random.randint(1, 60)
        )

        code = await generate_code(session, "STR")

        stripe_payment = StripePayment(
            code=code,
            payment_id=payment.id,
            provider_id=stripe_provider.id,
            payment_intent_id=f"pi_{fake.hexify('^^^^^^^^^^^^^^^^^^^^^^^^')}",
            charge_id=f"ch_{fake.hexify('^^^^^^^^^^^^^^^^^^^^^^^^')}",
            customer_id=payment.customer_id,
            payment_type=StripePaymentType.payment_intent,
            status=stripe_status,
            amount=amount,
            fee=stripe_fee,
            net=stripe_net,
            currency=currency.code,
            refunded=payment.amount if payment.status == PaymentStatus.refunded else 0,
            card_bin=payment.card_bin,
            card_last4=payment.card_last_four,
            card_masked=payment.card_masked,
            card_brand=payment.card_brand or "visa",
            card_funding=random.choice(["credit", "debit", "prepaid"]),
            country=currency.code[:2] if len(currency.code) >= 2 else None,
            vat_number=merchant.vat_number,
            stripe_created_at=stripe_created,
        )
        session.add(stripe_payment)
        created.append({
            "code": code,
            "payment_intent_id": stripe_payment.payment_intent_id,
            "internal_payment": payment.code,
            "amount": amount,
            "fee": stripe_fee,
            "status": stripe_status,
            "currency": currency.code,
        })

    await session.commit()
    return created


async def simulate_orphan_stripe_payments(
    session: AsyncSession, count: int = 3
) -> list[dict]:
    """
    Generate Stripe records with NO matching internal payment (payment_id=None).
    Simulates the real-world case where the provider has a record we never
    received (e.g., a lost webhook, or a fraud). These will appear as
    'missing_internal' after reconciliation runs.
    """

    result = await session.execute(
        select(Provider).where(Provider.code == "STRIPE")
    )
    stripe_provider = result.scalar_one_or_none()
    if stripe_provider is None:
        return []

    currencies = (await session.execute(select(Currency))).scalars().all()
    merchants = (await session.execute(select(Merchant))).scalars().all()
    if not currencies or not merchants:
        return []

    created = []
    for _ in range(count):
        currency = random.choice(currencies)
        merchant = random.choice(merchants)

        amount = random.randint(1000, 20000)
        stripe_fee = int(amount * 0.029) + 30
        stripe_net = amount - stripe_fee

        stripe_created = datetime.now(timezone.utc) - timedelta(
            minutes=random.randint(1, 600)
        )

        code = await generate_code(session, "STR")

        stripe_payment = StripePayment(
            code=code,
            payment_id=None,
            provider_id=stripe_provider.id,
            payment_intent_id=f"pi_{fake.hexify('^^^^^^^^^^^^^^^^^^^^^^^^')}",
            charge_id=f"ch_{fake.hexify('^^^^^^^^^^^^^^^^^^^^^^^^')}",
            customer_id=f"cus_{fake.hexify('^^^^^^^^^^^^^^')}",
            payment_type=StripePaymentType.payment_intent,
            status="succeeded",
            amount=amount,
            fee=stripe_fee,
            net=stripe_net,
            currency=currency.code,
            refunded=0,
            card_bin=fake.numerify("######"),
            card_last4=fake.numerify("####"),
            card_masked=f"{fake.numerify('######')}******{fake.numerify('####')}",
            card_brand=random.choice(["visa", "mastercard", "amex"]),
            card_funding=random.choice(["credit", "debit", "prepaid"]),
            country=merchant.country,
            vat_number=fake.numerify("ES#########"),
            stripe_created_at=stripe_created,
        )
        session.add(stripe_payment)
        created.append({
            "code": code,
            "payment_intent_id": stripe_payment.payment_intent_id,
            "amount": amount,
            "fee": stripe_fee,
            "currency": currency.code,
            "note": "orphan (no internal payment)",
        })

    await session.commit()
    return created
