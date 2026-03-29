import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.common.code_generator import generate_code
from app.common.enums import PaymentMethod, PaymentStatus, PaypalPaymentType
from app.currency.model import Currency
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.paypal.model import PaypalPayment
from app.provider.model import Provider

fake = Faker()

# Map PaymentStatus to PayPal's raw status strings
STATUS_MAP = {
    PaymentStatus.succeeded: "COMPLETED",
    PaymentStatus.pending: "PENDING",
    PaymentStatus.failed: "FAILED",
    PaymentStatus.refunded: "REFUNDED",
    PaymentStatus.partially_refunded: "PARTIALLY_REFUNDED",
    PaymentStatus.disputed: "DISPUTED",
}


async def simulate_paypal_payments(session: AsyncSession) -> list[dict]:
    """
    Take recent internal payments from PayPal provider and create
    corresponding paypal_payments records, simulating PayPal's data.
    Applies PayPal fee (3.49% + 49 cents) and introduces small discrepancies.
    """

    # Find the PayPal provider
    result = await session.execute(
        select(Provider).where(Provider.code == "PAYPAL")
    )
    paypal_provider = result.scalar_one_or_none()
    if paypal_provider is None:
        return []

    # LEFT JOIN to find payments not yet simulated
    pp = aliased(PaypalPayment)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    payments_result = await session.execute(
        select(Payment)
        .outerjoin(pp, Payment.id == pp.payment_id)
        .where(
            Payment.provider_id == paypal_provider.id,
            Payment.payment_method.in_([
                PaymentMethod.card,
                PaymentMethod.paypal_wallet,
            ]),
            Payment.processed_at >= since,
            pp.id.is_(None),
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

        # PayPal fee: 3.49% + 49 cents
        paypal_fee = int(payment.amount * 0.0349) + 49

        # Introduce small discrepancies in ~20% of cases
        amount = payment.amount
        if random.random() < 0.2:
            amount += random.randint(-50, 50)

        paypal_net = amount - paypal_fee

        # Map our status to PayPal's status strings
        paypal_status = STATUS_MAP.get(payment.status, "COMPLETED")

        # PayPal timestamp: slightly after our processed_at (1-120 seconds)
        paypal_created = payment.processed_at + timedelta(
            seconds=random.randint(1, 120)
        )

        code = await generate_code(session, "PPL")

        paypal_payment = PaypalPayment(
            code=code,
            payment_id=payment.id,
            provider_id=paypal_provider.id,
            order_id=f"{fake.hexify('^^^^^^^^^^^^^^^^^^')}",
            capture_id=f"{fake.hexify('^^^^^^^^^^^^^^^^^^')}",
            payer_id=f"{fake.hexify('^^^^^^^^^^^^^^')}",
            payment_type=PaypalPaymentType.capture,
            status=paypal_status,
            amount=amount,
            fee=paypal_fee,
            net=paypal_net,
            currency=currency.code,
            refunded=payment.amount if payment.status == PaymentStatus.refunded else 0,
            card_bin=payment.card_bin,
            card_last4=payment.card_last_four,
            card_masked=payment.card_masked,
            card_brand=payment.card_brand,
            country=merchant.country,
            vat_number=merchant.vat_number,
            paypal_created_at=paypal_created,
        )
        session.add(paypal_payment)
        created.append({
            "code": code,
            "order_id": paypal_payment.order_id,
            "internal_payment": payment.code,
            "amount": amount,
            "fee": paypal_fee,
            "status": paypal_status,
            "currency": currency.code,
        })

    await session.commit()
    return created
