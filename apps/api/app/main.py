from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ask.router import router as ask_router
from app.bank.model import BankTransferPayment  # noqa: F401
from app.bank.router import router as bank_router
from app.common.base import Base
from app.common.code_sequence import CodeSequence  # noqa: F401
from app.currency.model import Currency  # noqa: F401
from app.database import engine
from app.merchant.model import Merchant  # noqa: F401
from app.payment.model import Payment  # noqa: F401
from app.payment.router import router as payment_router
from app.paypal.model import PaypalPayment  # noqa: F401
from app.paypal.router import router as paypal_router
from app.provider.model import Provider  # noqa: F401
from app.reconciliation.model import Reconciliation  # noqa: F401
from app.reconciliation.router import router as reconciliation_router
from app.seed.router import router as seed_router
from app.stripe.model import StripePayment  # noqa: F401
from app.stripe.router import router as stripe_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and test connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")
    yield
    # Shutdown: close all connections
    await engine.dispose()


app = FastAPI(
    title="Payment Reconciliation API",
    description="Reconciliation dashboard for matching internal payments with provider records",
    version="0.1.0",
    lifespan=lifespan,
)

from app.config import settings as app_settings  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(seed_router)
app.include_router(payment_router)
app.include_router(stripe_router)
app.include_router(paypal_router)
app.include_router(bank_router)
app.include_router(reconciliation_router)
app.include_router(ask_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
