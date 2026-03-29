import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.code_generator import generate_code
from app.common.enums import PaymentMethod, PaymentStatus
from app.currency.model import Currency
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.provider.model import Provider

# Map country codes to Faker locales for realistic local data
COUNTRY_LOCALES = {
    "ES": "es_ES",
    "GB": "en_GB",
    "US": "en_US",
}


def get_faker(country: str) -> Faker:
    """Get a Faker instance for the merchant's country."""
    locale = COUNTRY_LOCALES.get(country, "en_US")
    return Faker(locale)


async def generate_fake_payments(
    session: AsyncSession, count: int = 5
) -> list[dict]:
    """Generate fake payment records using Faker."""

    # Load all merchants, providers, and currencies from DB
    merchants = (await session.execute(select(Merchant))).scalars().all()
    providers = (await session.execute(select(Provider))).scalars().all()
    currencies = (await session.execute(select(Currency))).scalars().all()

    if not merchants or not providers or not currencies:
        return []

    # Build a lookup: currency_id → currency object
    currency_map = {c.id: c for c in currencies}

    created = []
    for _ in range(count):
        # Pick random merchant, provider, and use the merchant's currency
        merchant = random.choice(merchants)
        provider = random.choice(providers)
        currency = currency_map[merchant.currency_id]

        # Pick payment method based on provider
        if provider.code == "STRIPE":
            payment_method = PaymentMethod.card
        elif provider.code == "PAYPAL":
            payment_method = random.choice(
                [PaymentMethod.card, PaymentMethod.paypal_wallet]
            )
        else:
            payment_method = random.choice(
                [PaymentMethod.bank_transfer, PaymentMethod.direct_debit]
            )

        # Generate amount in cents (between 5.00 and 5000.00)
        amount = random.randint(500, 500000)
        # Fee is 1-4% of amount
        fee = int(amount * random.uniform(0.01, 0.04))
        net = amount - fee

        # Pick a random status (weighted: most are succeeded)
        status = random.choices(
            [
                PaymentStatus.succeeded,
                PaymentStatus.pending,
                PaymentStatus.failed,
                PaymentStatus.refunded,
                PaymentStatus.disputed,
            ],
            weights=[70, 10, 10, 5, 5],
            k=1,
        )[0]

        # Get a locale-specific Faker for the merchant's country
        fake = get_faker(merchant.country)

        # Generate card or IBAN fields based on payment method
        card_bin = card_last_four = card_masked = card_brand = None
        iban_country = iban_bank = iban_branch = iban_last_four = iban_masked = None

        if payment_method in (PaymentMethod.card, PaymentMethod.paypal_wallet):
            # 1. Pick a random card brand
            card_brand = random.choice(["visa", "mastercard", "amex"])
            # 2. Generate a card number of that brand (consistent BIN + brand)
            card_number = fake.credit_card_number(card_type=card_brand)
            card_bin = card_number[:6]
            card_last_four = card_number[-4:]
            card_masked = f"{card_bin}******{card_last_four}"
        else:
            # Generate a realistic IBAN for the merchant's country
            iban = fake.iban()
            iban_country = iban[:2]
            iban_bank = iban[4:8]
            iban_branch = iban[8:12]
            iban_last_four = iban[-4:]
            hidden_len = len(iban) - 12 - 4
            iban_masked = f"{iban[:12]}{'*' * hidden_len}{iban_last_four}"

        # Processed at: current time (when the payment is created)
        processed_at = datetime.now(timezone.utc)

        code = await generate_code(session, "PAY")

        payment = Payment(
            code=code,
            merchant_id=merchant.id,
            provider_id=provider.id,
            status=status,
            payment_method=payment_method,
            amount=amount,
            fee=fee,
            net=net,
            currency_id=currency.id,
            customer_id=fake.uuid4(),
            customer_name=fake.name(),
            customer_email=fake.email(),
            description=fake.sentence(nb_words=6),
            card_bin=card_bin,
            card_last_four=card_last_four,
            card_masked=card_masked,
            card_brand=card_brand,
            iban_country=iban_country,
            iban_bank=iban_bank,
            iban_branch=iban_branch,
            iban_last_four=iban_last_four,
            iban_masked=iban_masked,
            processed_at=processed_at,
        )
        session.add(payment)
        created.append({
            "code": code,
            "merchant": merchant.code,
            "provider": provider.code,
            "status": status.value,
            "payment_method": payment_method.value,
            "amount": amount,
            "currency": currency.code,
        })

    await session.commit()
    return created
