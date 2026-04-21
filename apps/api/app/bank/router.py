from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bank.model import BankTransferPayment
from app.bank.service import (
    simulate_bank_payments,
    simulate_orphan_bank_payments,
)
from app.common.enums import BankTransferType
from app.database import get_session

router = APIRouter(prefix="/bank-payments", tags=["bank"])


@router.get("")
async def list_bank_payments(
    status: str | None = None,
    payment_type: BankTransferType | None = None,
    currency: str | None = None,
    iban_country: str | None = None,
    vat_number: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(BankTransferPayment)

    if status is not None:
        query = query.where(BankTransferPayment.status == status)
    if payment_type is not None:
        query = query.where(BankTransferPayment.payment_type == payment_type)
    if currency is not None:
        query = query.where(BankTransferPayment.currency == currency)
    if iban_country is not None:
        query = query.where(BankTransferPayment.iban_country == iban_country)
    if vat_number is not None:
        query = query.where(BankTransferPayment.vat_number == vat_number)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    query = query.order_by(BankTransferPayment.created_at.desc()).offset(offset).limit(limit)
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
                "payment_type": p.payment_type.value,
                "status": p.status,
                "vat_number": p.vat_number,
                "amount": p.amount,
                "currency": p.currency,
                "iban_country": p.iban_country,
                "iban_bank": p.iban_bank,
                "iban_branch": p.iban_branch,
                "iban_last_four": p.iban_last_four,
                "iban_masked": p.iban_masked,
                "value_date": p.value_date.isoformat(),
                "bank_created_at": p.bank_created_at.isoformat(),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in payments
        ],
    }


@router.post("/simulate")
async def simulate_bank(session: AsyncSession = Depends(get_session)):
    created = await simulate_bank_payments(session)
    return {
        "message": f"Simulated {len(created)} bank transfer payments",
        "payments": created,
    }


@router.post("/simulate-orphan")
async def simulate_bank_orphan(
    count: int = Query(default=3, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    created = await simulate_orphan_bank_payments(session, count)
    return {
        "message": f"Simulated {len(created)} orphan bank transfer payments",
        "payments": created,
    }
