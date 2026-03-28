from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.seed.service import seed_currencies, seed_merchants, seed_providers

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/currencies")
async def seed_currencies_endpoint(session: AsyncSession = Depends(get_session)):
    created = await seed_currencies(session)
    return {
        "message": f"Seeded {len(created)} currencies",
        "created": created,
    }


@router.post("/providers")
async def seed_providers_endpoint(session: AsyncSession = Depends(get_session)):
    created = await seed_providers(session)
    return {
        "message": f"Seeded {len(created)} providers",
        "created": created,
    }


@router.post("/merchants")
async def seed_merchants_endpoint(session: AsyncSession = Depends(get_session)):
    created = await seed_merchants(session)
    return {
        "message": f"Seeded {len(created)} merchants",
        "created": created,
    }
