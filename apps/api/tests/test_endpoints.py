"""
Endpoint tests for the FastAPI application.

Uses httpx AsyncClient wired directly to the app (no real server).
The database session is replaced by a mock (see conftest.py), so these
tests run without PostgreSQL and verify routing, response structure, and
status codes — not database logic.
"""


class TestHealthEndpoint:
    async def test_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_returns_ok_status(self, client):
        response = await client.get("/health")
        assert response.json() == {"status": "ok"}


class TestReconciliationsListEndpoint:
    async def test_returns_200(self, client):
        response = await client.get("/reconciliations")
        assert response.status_code == 200

    async def test_response_has_expected_keys(self, client):
        data = (await client.get("/reconciliations")).json()
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "reconciliations" in data

    async def test_reconciliations_is_a_list(self, client):
        data = (await client.get("/reconciliations")).json()
        assert isinstance(data["reconciliations"], list)

    async def test_empty_database_returns_zero_total(self, client):
        data = (await client.get("/reconciliations")).json()
        assert data["total"] == 0

    async def test_status_filter_is_accepted(self, client):
        response = await client.get("/reconciliations?status=matched")
        assert response.status_code == 200

    async def test_pagination_params_are_reflected(self, client):
        data = (await client.get("/reconciliations?limit=5&offset=10")).json()
        assert data["limit"] == 5
        assert data["offset"] == 10


class TestSummaryEndpoint:
    async def test_returns_200(self, summary_client):
        response = await summary_client.get("/reconciliations/summary")
        assert response.status_code == 200

    async def test_response_has_all_expected_top_level_keys(self, summary_client):
        data = (await summary_client.get("/reconciliations/summary")).json()
        assert "total_reconciled" in data
        assert "match_rate" in data
        assert "status_counts" in data
        assert "amounts" in data
        assert "confidence" in data
        assert "by_provider" in data

    async def test_match_rate_is_calculated_correctly(self, summary_client):
        data = (await summary_client.get("/reconciliations/summary")).json()
        # Mock: 8 matched + 2 amount_mismatch = 10 total → 80.0 %
        assert data["total_reconciled"] == 10
        assert data["match_rate"] == 80.0

    async def test_provider_breakdown_values(self, summary_client):
        data = (await summary_client.get("/reconciliations/summary")).json()
        assert data["by_provider"]["stripe"] == 5
        assert data["by_provider"]["paypal"] == 3
        assert data["by_provider"]["bank"] == 2

    async def test_confidence_values(self, summary_client):
        data = (await summary_client.get("/reconciliations/summary")).json()
        assert data["confidence"]["average"] == 92.5
        assert data["confidence"]["min"] == 75
        assert data["confidence"]["max"] == 100


class TestReconciliationDetailEndpoint:
    async def test_nonexistent_id_returns_error_dict(self, client):
        response = await client.get("/reconciliations/nonexistent-id")
        assert response.status_code == 200
        assert "error" in response.json()

    async def test_error_message_mentions_not_found(self, client):
        data = (await client.get("/reconciliations/no-such-id")).json()
        assert "not found" in data["error"].lower()
