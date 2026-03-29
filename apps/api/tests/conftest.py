import os

# Must be set before any app imports — config.py reads these at module load time
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@asynccontextmanager
async def _no_op_lifespan(app):
    """
    Replaces the real lifespan so tests never connect to a real database.
    The real lifespan runs create_all on startup; we skip that entirely.
    """
    yield


def _make_mock_session():
    """
    Returns an AsyncMock that behaves like an empty AsyncSession.
    Every execute() call returns a result that yields zero counts and empty lists,
    which lets all endpoints handle the data gracefully without errors.
    """
    session = AsyncMock()

    def generic_result(*args, **kwargs):
        result = MagicMock()
        result.scalar.return_value = 0
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        result.all.return_value = []

        # .one() is used by the summary endpoint for aggregate queries
        one = MagicMock()
        one.total_internal = 0
        one.total_external = 0
        one.total_discrepancy = 0
        one.avg_confidence = None
        one.min_confidence = 0
        one.max_confidence = 0
        one.stripe = 0
        one.paypal = 0
        one.bank = 0
        result.one.return_value = one

        return result

    session.execute = AsyncMock(side_effect=generic_result)
    return session


@pytest.fixture
async def client():
    """
    Provides an httpx AsyncClient wired directly to the FastAPI app.
    - Lifespan replaced with a no-op (no real DB startup/shutdown).
    - get_session dependency overridden with a mock session returning empty data.
    """
    from app.database import get_session
    from app.main import app

    app.router.lifespan_context = _no_op_lifespan

    mock_session = _make_mock_session()
    app.dependency_overrides[get_session] = lambda: mock_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def summary_client():
    """
    Client with a tailored mock session for the /reconciliations/summary endpoint.

    The summary endpoint makes 5 sequential execute() calls, each returning a
    different result shape. side_effect with a list returns a different value
    for each call in order.

    Seeded data: 8 matched + 2 amount_mismatch = 10 total → 80% match rate.
    """
    from app.database import get_session
    from app.main import app

    app.router.lifespan_context = _no_op_lifespan

    session = AsyncMock()

    # Call 1 — status counts: GROUP BY status
    status_result = MagicMock()
    matched_row = MagicMock()
    matched_row.status.value = "matched"
    matched_row.count = 8
    mismatch_row = MagicMock()
    mismatch_row.status.value = "amount_mismatch"
    mismatch_row.count = 2
    status_result.all.return_value = [matched_row, mismatch_row]

    # Call 2 — amount aggregates
    amounts_result = MagicMock()
    amounts_one = MagicMock()
    amounts_one.total_internal = 100_000
    amounts_one.total_external = 100_500
    amounts_one.total_discrepancy = 500
    amounts_result.one.return_value = amounts_one

    # Call 3 — confidence aggregates (matched records only)
    confidence_result = MagicMock()
    conf_one = MagicMock()
    conf_one.avg_confidence = 92.5
    conf_one.min_confidence = 75
    conf_one.max_confidence = 100
    confidence_result.one.return_value = conf_one

    # Call 4 — provider counts (stripe / paypal / bank)
    provider_result = MagicMock()
    prov_one = MagicMock()
    prov_one.stripe = 5
    prov_one.paypal = 3
    prov_one.bank = 2
    provider_result.one.return_value = prov_one

    # Call 5 — missing external count (scalar)
    missing_result = MagicMock()
    missing_result.scalar.return_value = 1

    session.execute = AsyncMock(side_effect=[
        status_result,
        amounts_result,
        confidence_result,
        provider_result,
        missing_result,
    ])

    app.dependency_overrides[get_session] = lambda: session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
