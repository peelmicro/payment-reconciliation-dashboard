from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ReconciliationStatus
from app.database import get_session
from app.payment.model import Payment
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


@router.get("/summary")
async def reconciliation_summary(
    session: AsyncSession = Depends(get_session),
):
    """Dashboard KPIs: match rates, totals, discrepancies, confidence stats."""

    # Count by status
    status_counts = await session.execute(
        select(
            Reconciliation.status,
            func.count().label("count"),
        ).group_by(Reconciliation.status)
    )
    counts = {row.status.value: row.count for row in status_counts.all()}

    total_reconciled = sum(counts.values())

    # Total amounts
    amount_stats = await session.execute(
        select(
            func.sum(Reconciliation.internal_amount).label("total_internal"),
            func.sum(Reconciliation.external_amount).label("total_external"),
            func.sum(func.abs(Reconciliation.delta)).label("total_discrepancy"),
        )
    )
    amounts = amount_stats.one()

    # Confidence stats (only for matched records)
    confidence_stats = await session.execute(
        select(
            func.avg(Reconciliation.confidence).label("avg_confidence"),
            func.min(Reconciliation.confidence).label("min_confidence"),
            func.max(Reconciliation.confidence).label("max_confidence"),
        ).where(Reconciliation.status.in_([
            ReconciliationStatus.matched,
            ReconciliationStatus.matched_with_fee,
            ReconciliationStatus.amount_mismatch,
        ]))
    )
    confidence = confidence_stats.one()

    # Count by provider type
    provider_counts = await session.execute(
        select(
            func.count(Reconciliation.stripe_payment_id).label("stripe"),
            func.count(Reconciliation.paypal_payment_id).label("paypal"),
            func.count(Reconciliation.bank_transfer_id).label("bank"),
        )
    )
    providers = provider_counts.one()

    # Missing external count (payments older than 1 hour with no reconciliation)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    missing_external_result = await session.execute(
        select(func.count())
        .select_from(Payment)
        .outerjoin(Reconciliation, Payment.id == Reconciliation.payment_id)
        .where(
            Reconciliation.id.is_(None),
            Payment.processed_at <= cutoff,
        )
    )
    missing_external = missing_external_result.scalar()

    # Match rate
    matched_count = counts.get("matched", 0) + counts.get("matched_with_fee", 0)
    match_rate = round((matched_count / total_reconciled) * 100, 1) if total_reconciled > 0 else 0

    return {
        "total_reconciled": total_reconciled,
        "match_rate": match_rate,
        "status_counts": {
            "matched": counts.get("matched", 0),
            "matched_with_fee": counts.get("matched_with_fee", 0),
            "amount_mismatch": counts.get("amount_mismatch", 0),
            "missing_internal": counts.get("missing_internal", 0),
            "missing_external": missing_external,
            "duplicate": counts.get("duplicate", 0),
            "disputed": counts.get("disputed", 0),
        },
        "amounts": {
            "total_internal": amounts.total_internal or 0,
            "total_external": amounts.total_external or 0,
            "total_discrepancy": amounts.total_discrepancy or 0,
        },
        "confidence": {
            "average": round(float(confidence.avg_confidence), 1) if confidence.avg_confidence else 0,
            "min": confidence.min_confidence or 0,
            "max": confidence.max_confidence or 0,
        },
        "by_provider": {
            "stripe": providers.stripe,
            "paypal": providers.paypal,
            "bank": providers.bank,
        },
    }


@router.get("/missing-external")
async def list_missing_external(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Internal payments older than 1 hour with no provider match."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    # Count
    count_query = (
        select(func.count())
        .select_from(Payment)
        .outerjoin(Reconciliation, Payment.id == Reconciliation.payment_id)
        .where(
            Reconciliation.id.is_(None),
            Payment.processed_at <= cutoff,
        )
    )
    total = (await session.execute(count_query)).scalar()

    # Fetch
    query = (
        select(Payment)
        .outerjoin(Reconciliation, Payment.id == Reconciliation.payment_id)
        .where(
            Reconciliation.id.is_(None),
            Payment.processed_at <= cutoff,
        )
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
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
                "status": p.status.value,
                "payment_method": p.payment_method.value,
                "amount": p.amount,
                "fee": p.fee,
                "net": p.net,
                "customer_name": p.customer_name,
                "processed_at": p.processed_at.isoformat(),
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
    }


@router.get("/{reconciliation_id}")
async def get_reconciliation(
    reconciliation_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single reconciliation with full details."""
    result = await session.execute(
        select(Reconciliation).where(Reconciliation.id == reconciliation_id)
    )
    r = result.scalar_one_or_none()
    if r is None:
        return {"error": "Reconciliation not found"}

    return {
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


@router.post("/run")
async def run_reconciliation_endpoint(
    session: AsyncSession = Depends(get_session),
):
    results = await run_reconciliation(session)
    return {
        "message": "Reconciliation completed",
        "results": results,
    }
