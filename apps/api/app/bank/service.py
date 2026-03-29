import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.bank.model import BankTransferPayment
from app.common.code_generator import generate_code
from app.common.enums import BankTransferType, PaymentMethod, PaymentStatus
from app.currency.model import Currency
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.provider.model import Provider

# Map PaymentStatus to bank's raw status strings
STATUS_MAP = {
    PaymentStatus.succeeded: "EXECUTED",
    PaymentStatus.pending: "PENDING",
    PaymentStatus.failed: "REJECTED",
    PaymentStatus.refunded: "RETURNED",
    PaymentStatus.partially_refunded: "PARTIALLY_RETURNED",
    PaymentStatus.disputed: "UNDER_REVIEW",
}

# Map payment method to bank transfer type
TRANSFER_TYPE_MAP = {
    PaymentMethod.bank_transfer: [
        BankTransferType.sepa_credit,
        BankTransferType.swift,
        BankTransferType.domestic,
    ],
    PaymentMethod.direct_debit: [
        BankTransferType.sepa_direct_debit,
    ],
}


async def simulate_bank_payments(session: AsyncSession) -> list[dict]:
    """
    Take recent internal payments from Bankinter provider and create
    corresponding bank_transfer_payments records, simulating bank data.
    Banks have no processing fees but introduce inconsistent formats
    and delayed settlement dates.
    """

    # Find the Bankinter provider
    result = await session.execute(
        select(Provider).where(Provider.code == "BANKINTER")
    )
    bank_provider = result.scalar_one_or_none()
    if bank_provider is None:
        return []

    # LEFT JOIN to find payments not yet simulated
    bp = aliased(BankTransferPayment)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    payments_result = await session.execute(
        select(Payment)
        .outerjoin(bp, Payment.id == bp.payment_id)
        .where(
            Payment.provider_id == bank_provider.id,
            Payment.payment_method.in_([
                PaymentMethod.bank_transfer,
                PaymentMethod.direct_debit,
            ]),
            Payment.processed_at >= since,
            bp.id.is_(None),
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

        # Banks don't charge processing fees, but introduce
        # small discrepancies in ~15% of cases (rounding, currency conversion)
        amount = payment.amount
        if random.random() < 0.15:
            amount += random.randint(-30, 30)

        # Map our status to bank's status strings
        bank_status = STATUS_MAP.get(payment.status, "EXECUTED")

        # Pick a transfer type based on payment method
        transfer_types = TRANSFER_TYPE_MAP.get(
            payment.payment_method, [BankTransferType.sepa_credit]
        )
        transfer_type = random.choice(transfer_types)

        # Value date: settlement date, typically 1-3 business days after processing
        value_date = (
            payment.processed_at + timedelta(days=random.randint(1, 3))
        ).date()

        # Bank timestamp: slightly after our processed_at (1-300 seconds)
        bank_created = payment.processed_at + timedelta(
            seconds=random.randint(1, 300)
        )

        code = await generate_code(session, "BNK")

        bank_payment = BankTransferPayment(
            code=code,
            payment_id=payment.id,
            provider_id=bank_provider.id,
            payment_type=transfer_type,
            status=bank_status,
            vat_number=merchant.vat_number,
            amount=amount,
            currency=currency.code,
            iban_country=payment.iban_country,
            iban_bank=payment.iban_bank,
            iban_branch=payment.iban_branch,
            iban_last_four=payment.iban_last_four,
            iban_masked=payment.iban_masked,
            value_date=value_date,
            bank_created_at=bank_created,
        )
        session.add(bank_payment)
        created.append({
            "code": code,
            "internal_payment": payment.code,
            "amount": amount,
            "status": bank_status,
            "transfer_type": transfer_type.value,
            "value_date": value_date.isoformat(),
            "currency": currency.code,
        })

    await session.commit()
    return created
