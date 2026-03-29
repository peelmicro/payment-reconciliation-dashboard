from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import StripePaymentType
from app.database import get_session
from app.stripe.model import StripePayment
from app.stripe.service import simulate_stripe_payments

router = APIRouter(prefix="/stripe-payments", tags=["stripe"])


@router.get("")
async def list_stripe_payments(
    status: str | None = None,
    payment_type: StripePaymentType | None = None,
    currency: str | None = None,
    card_brand: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(StripePayment)

    if status is not None:
        query = query.where(StripePayment.status == status)
    if payment_type is not None:
        query = query.where(StripePayment.payment_type == payment_type)
    if currency is not None:
        query = query.where(StripePayment.currency == currency)
    if card_brand is not None:
        query = query.where(StripePayment.card_brand == card_brand)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    query = query.order_by(StripePayment.created_at.desc()).offset(offset).limit(limit)
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
                "payment_id": str(p.payment_id) if p.payment_id else None,
                "provider_id": str(p.provider_id),
                "payment_intent_id": p.payment_intent_id,
                "charge_id": p.charge_id,
                "customer_id": p.customer_id,
                "payment_type": p.payment_type.value,
                "status": p.status,
                "amount": p.amount,
                "fee": p.fee,
                "net": p.net,
                "currency": p.currency,
                "refunded": p.refunded,
                "card_bin": p.card_bin,
                "card_last4": p.card_last4,
                "card_masked": p.card_masked,
                "card_brand": p.card_brand,
                "card_funding": p.card_funding,
                "country": p.country,
                "vat_number": p.vat_number,
                "stripe_created_at": p.stripe_created_at.isoformat(),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in payments
        ],
    }


@router.post("/simulate")
async def simulate_stripe(session: AsyncSession = Depends(get_session)):
    created = await simulate_stripe_payments(session)
    return {
        "message": f"Simulated {len(created)} Stripe payments",
        "payments": created,
    }
