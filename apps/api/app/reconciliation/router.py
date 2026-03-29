from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ReconciliationStatus
from app.database import get_session
from app.reconciliation.model import Reconciliation
from app.reconciliation.service import run_reconciliation

router = APIRouter(prefix="/reconciliations", tags=["reconciliation"])


@router.get("")
async def list_reconciliations(
    status: ReconciliationStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    query = select(Reconciliation)

    if status is not None:
        query = query.where(Reconciliation.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    query = query.order_by(Reconciliation.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    reconciliations = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "reconciliations": [
            {
                "id": str(r.id),
                "code": r.code,
                "status": r.status.value,
                "payment_id": str(r.payment_id) if r.payment_id else None,
                "internal_amount": r.internal_amount,
                "stripe_payment_id": str(r.stripe_payment_id) if r.stripe_payment_id else None,
                "paypal_payment_id": str(r.paypal_payment_id) if r.paypal_payment_id else None,
                "bank_transfer_id": str(r.bank_transfer_id) if r.bank_transfer_id else None,
                "external_amount": r.external_amount,
                "delta": r.delta,
                "currency_id": str(r.currency_id),
                "score": r.score,
                "max_score": r.max_score,
                "confidence": r.confidence,
                "reconciled_at": r.reconciled_at.isoformat(),
                "reconciled_by": r.reconciled_by,
                "notes": r.notes,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in reconciliations
        ],
    }


@router.post("/run")
async def run_reconciliation_endpoint(
    session: AsyncSession = Depends(get_session),
):
    results = await run_reconciliation(session)
    return {
        "message": "Reconciliation completed",
        "results": results,
    }
