from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import PaymentMethod, PaymentStatus
from app.currency.model import Currency
from app.database import get_session
from app.merchant.model import Merchant
from app.payment.model import Payment
from app.payment.service import generate_fake_payments
from app.provider.model import Provider

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("")
async def list_payments(
    status: PaymentStatus | None = None,
    payment_method: PaymentMethod | None = None,
    merchant_code: str | None = None,
    provider_code: str | None = None,
    currency_code: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    # Start building the query
    query = select(Payment)

    # Apply filters if provided
    if status is not None:
        query = query.where(Payment.status == status)
    if payment_method is not None:
        query = query.where(Payment.payment_method == payment_method)
    if merchant_code is not None:
        query = query.join(Merchant).where(Merchant.code == merchant_code)
    if provider_code is not None:
        query = query.join(Provider).where(Provider.code == provider_code)
    if currency_code is not None:
        query = query.join(Currency).where(Currency.code == currency_code)

    # Get total count (before pagination)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Apply pagination and ordering
    query = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    payments = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "payments": [
            {
                "id": str(p.id),
                "code": p.code,
                "merchant_id": str(p.merchant_id),
                "provider_id": str(p.provider_id),
                "status": p.status.value,
                "payment_method": p.payment_method.value,
                "amount": p.amount,
                "fee": p.fee,
                "net": p.net,
                "currency_id": str(p.currency_id),
                "customer_id": p.customer_id,
                "customer_name": p.customer_name,
                "customer_email": p.customer_email,
                "description": p.description,
                "card_bin": p.card_bin,
                "card_last_four": p.card_last_four,
                "card_masked": p.card_masked,
                "card_brand": p.card_brand,
                "iban_country": p.iban_country,
                "iban_bank": p.iban_bank,
                "iban_branch": p.iban_branch,
                "iban_last_four": p.iban_last_four,
                "iban_masked": p.iban_masked,
                "processed_at": p.processed_at.isoformat(),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in payments
        ],
    }


@router.post("/generate")
async def generate_payments(
    count: int = Query(default=5, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    created = await generate_fake_payments(session, count)
    return {
        "message": f"Generated {len(created)} fake payments",
        "payments": created,
    }
