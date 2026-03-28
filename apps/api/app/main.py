from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: test database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    print("Database connection OK")
    yield
    # Shutdown: close all connections
    await engine.dispose()


app = FastAPI(
    title="Payment Reconciliation API",
    description="Reconciliation dashboard for matching internal payments with provider records",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}
