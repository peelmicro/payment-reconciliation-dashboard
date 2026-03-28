# CLAUDE.md — Payment Reconciliation Dashboard

## Project Overview

A payment reconciliation dashboard that matches internal payment records against external provider data (Stripe, PayPal, bank transfers). Built as a portfolio project demonstrating full-stack development with real-world fintech patterns.

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy (async), Pydantic v2, PostgreSQL 16
- **Frontend:** React 19, TypeScript 5, Vite 8, TanStack Query + Table, shadcn/ui, Tailwind CSS v4
- **Infrastructure:** Docker Compose (PostgreSQL, n8n, API, Web)
- **Testing:** pytest (API), Vitest (Web)
- **Bonus:** LangChain for natural language queries

## Project Structure

```
apps/api/          # FastAPI backend
apps/web/          # React frontend
n8n/workflows/     # Exported n8n workflow JSON files
docker-compose.yml # Full stack orchestration
```

### Backend Layout (`apps/api/app/`)

Each domain entity follows the pattern: `entity/` with model, service, router modules.

- `common/` — Shared utilities (code generation, etc.)
- `currency/`, `provider/`, `merchant/` — Reference data entities
- `payment/` — Internal payment records (source of truth)
- `stripe/`, `paypal/`, `bank/` — External provider payment records
- `reconciliation/` — Reconciliation engine and results
- `ask/` — LangChain NL query endpoint (bonus)
- `seed/` — Seed data service
- `database.py` — SQLAlchemy async engine and session
- `main.py` — FastAPI app entry point

## Conventions

### General

- All monetary amounts are stored in **minor units (cents)** — never floats
- UUIDs for all primary keys
- Human-readable codes with format `PREFIX-YYYY-MM-SEQUENCE` (e.g., `PAY-2026-03-000012`)
- Soft deletes via `disabledAt` nullable datetime (not hard deletes)
- All tables include `createdAt` and `updatedAt` timestamps

### Python / Backend

- Use **async** SQLAlchemy sessions and FastAPI async endpoints
- Pydantic v2 for all request/response validation
- One router per entity domain, mounted in `main.py`
- `.http` files in `apps/api/http/` for VS Code REST Client testing
- Snake_case for Python code, camelCase for JSON API responses (Pydantic alias)

### TypeScript / Frontend

- Strict TypeScript — no `any` types
- TanStack Query for all server state (no local state for API data)
- TanStack Table for data grids with sorting, filtering, pagination
- shadcn/ui components — do not build custom UI primitives
- API types in `src/types/`

### Database

- PostgreSQL 16 with async driver (asyncpg)
- Tables created on app startup via SQLAlchemy `create_all`
- Enums defined as PostgreSQL enums: `paymentStatus`, `paymentMethod`, `reconciliationStatus`, `stripePaymentType`, `paypalPaymentType`, `bankTransferType`
- Foreign keys reference UUIDs; card/IBAN fields are mutually exclusive per payment method

### Testing

- `pytest` with async support for API tests
- `vitest` for frontend component and hook tests
- Tests live in `apps/api/tests/` and alongside frontend source files

### Docker

- `docker compose up` must start the full stack (PostgreSQL, n8n, API, Web)
- PostgreSQL on port 5432, n8n on port 5678
- n8n workflows exported as JSON in `n8n/workflows/`

## Key Design Decisions

- **Scoring-based reconciliation** over exact key matching — real-world payments rarely have perfect matching keys
- **Separate provider tables** (stripe_payments, paypal_payments, bank_transfer_payments) over polymorphic single table — each provider has unique fields
- **n8n for workflow automation** over coded cron jobs — visual workflows are easier to monitor and modify
- **code_sequences table** for human-readable code generation with uniqueness guarantees

## Commands

```bash
# Backend
cd apps/api && pip install -r requirements.txt
cd apps/api && python -m pytest

# Frontend
cd apps/web && npm install
cd apps/web && npm run dev
cd apps/web && npx vitest

# Full stack
docker compose up
```
