from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.currency.model import Currency
from app.merchant.model import Merchant
from app.provider.model import Provider


CURRENCIES_DATA = [
    {"code": "USD", "iso_number": "840", "symbol": "$", "decimal_points": 2},
    {"code": "EUR", "iso_number": "978", "symbol": "€", "decimal_points": 2},
    {"code": "GBP", "iso_number": "826", "symbol": "£", "decimal_points": 2},
]


async def seed_currencies(session: AsyncSession) -> list[dict]:
    """Insert currencies if they don't already exist. Returns what was created."""
    created = []
    for data in CURRENCIES_DATA:
        # Check if currency already exists
        result = await session.execute(
            select(Currency).where(Currency.code == data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            currency = Currency(**data)
            session.add(currency)
            created.append(data)
    await session.commit()
    return created


PROVIDERS_DATA = [
    {"code": "STRIPE", "name": "Stripe"},
    {"code": "PAYPAL", "name": "PayPal"},
    {"code": "BANKINTER", "name": "Bankinter"},
]


async def seed_providers(session: AsyncSession) -> list[dict]:
    """Insert providers if they don't already exist. Returns what was created."""
    created = []
    for data in PROVIDERS_DATA:
        result = await session.execute(
            select(Provider).where(Provider.code == data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            provider = Provider(**data)
            session.add(provider)
            created.append(data)
    await session.commit()
    return created


# currency_code is used to look up the currency_id at seed time
MERCHANTS_DATA = [
    {
        "code": "TIENDA_SOL",
        "name": "Tienda Sol S.L.",
        "email": "admin@tiendasol.es",
        "phone": "+34 912 345 678",
        "country": "ES",
        "currency_code": "EUR",
        "vat_number": "B12345678",
    },
    {
        "code": "MODA_IBERIA",
        "name": "Moda Iberia S.A.",
        "email": "finance@modaiberia.es",
        "phone": "+34 933 456 789",
        "country": "ES",
        "currency_code": "EUR",
        "vat_number": "A87654321",
    },
    {
        "code": "LONDON_GOODS",
        "name": "London Goods Ltd.",
        "email": "billing@londongoods.co.uk",
        "phone": "+44 20 7946 0958",
        "country": "GB",
        "currency_code": "GBP",
        "vat_number": "GB123456789",
    },
]


async def seed_merchants(session: AsyncSession) -> list[dict]:
    """Insert merchants if they don't already exist. Returns what was created."""
    created = []
    for data in MERCHANTS_DATA:
        result = await session.execute(
            select(Merchant).where(Merchant.code == data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            # Separate currency_code from the rest (it's not a Merchant column)
            merchant_data = {k: v for k, v in data.items() if k != "currency_code"}
            # Look up the currency by code to get its UUID
            currency_result = await session.execute(
                select(Currency).where(Currency.code == data["currency_code"])
            )
            currency = currency_result.scalar_one()
            merchant = Merchant(**merchant_data, currency_id=currency.id)
            session.add(merchant)
            created.append(data)
    await session.commit()
    return created
