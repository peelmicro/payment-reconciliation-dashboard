# Payment Reconciliation Dashboard

A full-stack payment reconciliation system that matches internal payment records against external provider data (Stripe, PayPal, bank transfers) using a confidence-based scoring engine.

Built as a portfolio project demonstrating real-world fintech patterns: async Python, React dashboards, workflow automation, and natural language querying.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Database** | PostgreSQL 16, asyncpg driver |
| **Data processing** | Pandas (trend aggregation) |
| **NL queries** | LangChain, Anthropic Claude (claude-sonnet-4) |
| **Frontend** | React 19, TypeScript 5, Vite 8 |
| **UI** | shadcn/ui, Tailwind CSS v4 |
| **Data fetching** | TanStack Query v5 |
| **Data grids** | TanStack Table v8 |
| **Charts** | Recharts |
| **Workflow automation** | n8n |
| **Infrastructure** | Docker Compose |
| **API testing** | pytest, pytest-asyncio, httpx |
| **Frontend testing** | Vitest, Testing Library |
| **Linting (Python)** | ruff |
| **Linting (TS)** | ESLint |

---

## How to Run

### Option 1 — Docker Compose (full stack)

```bash
docker compose up -d
```

This starts:
- PostgreSQL on port **5432**
- n8n on port **5678** (http://localhost:5678)
- API on port **8000** (http://localhost:8000)
- Web on port **3000** (http://localhost:3000)

### Option 2 — Local development

**Prerequisites:** Python 3.12+, Node.js 20+, PostgreSQL 16 running locally.

```bash
# 1. Start PostgreSQL (Docker only)
docker compose up -d postgres n8n

# 2. Backend
cd apps/api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Edit DATABASE_URL and ANTHROPIC_API_KEY
fastapi dev app/main.py          # http://localhost:8000

# 3. Frontend (new terminal)
cd apps/web
npm install
npm run dev                      # http://localhost:5173
```

### Convenience scripts (from repo root)

| Command | What it does |
|---------|-------------|
| `npm run api` | Start FastAPI dev server |
| `npm run web` | Start Vite dev server |
| `npm run api:test` | Run pytest |
| `npm run web:test` | Run Vitest |
| `npm run api:lint` | Run ruff linter |
| `npm run api:lint:fix` | Run ruff with auto-fix |
| `npm run web:lint` | Run ESLint |
| `npm run dc:up` | `docker compose up -d` |
| `npm run dc:down` | `docker compose down` |
| `npm run dc:ps` | Show running containers |
| `npm run dc:clean` | Stop and remove volumes |
| `npm run dc:logs` | Follow all container logs |

---

## Reconciliation Algorithm

The engine scores each provider payment (candidate) against all unreconciled internal payments and selects the best match above a **65% confidence threshold**.

### Scoring criteria

| Criteria | Points | When scored |
|----------|--------|-------------|
| Amount — exact match | +100 | Always |
| Amount — after fee (net ≈ external) | +80 | Always |
| Amount — within 5% tolerance | +50 | Always |
| Card BIN + last4 | +50 | Both records have card data |
| IBAN country + last4 | +50 | Both records have IBAN data |
| VAT number | +50 | Both records have VAT |
| Date — same day | +30 | Always |
| Date — within 1 day | +20 | Always |
| Date — within 7 days | +10 | Always |

**Confidence** = `(score / max_possible_score) × 100`

The `max_possible_score` is calculated **dynamically** — a criterion is only added to the maximum if both the internal payment and the provider record have data for that field. This ensures fair comparison across provider types:

- A PayPal wallet payment (no card/IBAN) has max 180 pts (100 + 50 VAT + 30 date). Score 180/180 = **100%**.
- A Stripe card payment has max 230 pts (100 + 50 card + 50 VAT + 30 date). Score 230/230 = **100%**.

Both are equally strong matches despite having different field sets.

### Reconciliation statuses

| Status | Meaning |
|--------|---------|
| `matched` | Exact amount match above threshold |
| `matched_with_fee` | Net amount (after fee) matches external |
| `amount_mismatch` | Fields match but amount differs |
| `missing_internal` | Provider has a record; we don't |
| `missing_external` | We have a record; provider doesn't (yet) |
| `duplicate` | Multiple internal records above threshold |
| `disputed` | Manually flagged for review |

---

## n8n Workflows

All workflows are exported as JSON files in `n8n/workflows/` and can be imported into any n8n instance.

| Workflow | File | Trigger | What it does |
|----------|------|---------|-------------|
| WF1 | `WF1_seed_base_data.json` | Manual | Seeds currencies, providers, merchants (in sequence) |
| WF2 | `WF2_generate_fake_payments.json` | Every 5 min | Generates 5 fake internal payments |
| WF3 | `WF3_simulate_stripe.json` | Every 10 min | Simulates Stripe records from recent card payments |
| WF4 | `WF4_simulate_paypal.json` | Every 30 min | Simulates PayPal records from recent card/wallet payments |
| WF5 | `WF5_simulate_bank.json` | Every 1 hour | Simulates bank transfer records from recent bank payments |
| WF6 | `WF6_run_reconciliation.json` | Every 15 min | Runs the reconciliation engine |

### How to import workflows

1. Start the stack: `docker compose up -d` (or `npm run dc:up`)
2. Open n8n at http://localhost:5678
3. Click **"+"** → **"Workflow"** to create a new workflow
4. Click the **three dots menu (...)** at the top right → **"Import from file"**
5. Select a JSON file from `n8n/workflows/`
6. Click **"Execute workflow"** to test manually
7. Toggle **"Publish"** to activate the cron schedule

> **Note:** The API server must be running for workflows to work. Workflows call `http://host.docker.internal:8000` to reach the API from inside Docker.

---

## Ask AI (Natural Language Queries)

The `/ask` endpoint accepts plain-text questions in English or Spanish and returns answers from the database.

```bash
# Example
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the match rate for this week?"}'
```

Requires `ANTHROPIC_API_KEY` in `apps/api/.env`.

The endpoint uses a two-step LangChain chain:
1. Generate SQL from the question (Claude reads the schema)
2. Execute the SQL, then generate a natural language answer from the results

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/reconciliations` | List reconciliations (paginated, filterable by status) |
| GET | `/reconciliations/summary` | Dashboard KPIs: match rate, totals, confidence stats |
| GET | `/reconciliations/trends` | Daily trends over N days (Pandas aggregation) |
| GET | `/reconciliations/missing-external` | Internal payments with no provider match |
| GET | `/reconciliations/{id}` | Single reconciliation detail |
| POST | `/reconciliations/run` | Trigger reconciliation engine manually |
| POST | `/ask` | Natural language query |
| POST | `/seed` | Seed base reference data |
| GET | `/docs` | Swagger UI |

`.http` files for VS Code REST Client are in `apps/api/http/`.

---

## Testing

### Run all tests

```bash
npm run api:test    # pytest
npm run web:test    # vitest
```

### Test breakdown

| File | Tests | What it covers |
|------|-------|---------------|
| `tests/test_engine.py` | 21 | Scoring engine: amount, currency, card, IBAN, VAT, date proximity, confidence |
| `tests/test_endpoints.py` | 15 | FastAPI endpoints: health, list, summary, detail (mocked session) |
| `tests/test_service.py` | 11 | Service helpers: status mapping, provider ID, currency lookup, reconciliation flow |
| `src/lib/format.test.ts` | 5 | Currency formatting utilities |
| `src/lib/status-colors.test.ts` | 6 | Status badge color mapping |
| `src/components/layout.test.tsx` | 3 | Navigation layout render and links |

**Total: 61 tests**

### Testing approach

- **API**: `pytest-asyncio` with `asyncio_mode = auto`, `httpx.AsyncClient` with `ASGITransport` for in-process endpoint testing, `AsyncMock` dependency overrides to avoid real database connections.
- **Frontend**: Vitest with `jsdom` environment, `@testing-library/react` for component rendering, `MemoryRouter` wrapping for route-dependent components.

---

## Project Structure

```
payment-reconciliation-dashboard/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── app/
│   │   │   ├── bank/               # Bank transfer payment model + router
│   │   │   ├── common/             # Code generator, enums
│   │   │   ├── currency/           # Currency reference data
│   │   │   ├── merchant/           # Merchant model + router
│   │   │   ├── payment/            # Internal payments (source of truth)
│   │   │   ├── paypal/             # PayPal payment model + router
│   │   │   ├── provider/           # Provider reference data
│   │   │   ├── reconciliation/     # Engine, service, router
│   │   │   │   ├── engine.py       # Scoring + confidence algorithm
│   │   │   │   ├── service.py      # Orchestration + DB persistence
│   │   │   │   └── router.py       # REST endpoints
│   │   │   ├── ask/                # LangChain NL query endpoint
│   │   │   ├── seed/               # Seed data service
│   │   │   ├── stripe/             # Stripe payment model + router
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   ├── database.py         # Async engine + session
│   │   │   └── main.py             # FastAPI app + router mounting
│   │   ├── http/                   # VS Code REST Client .http files
│   │   ├── tests/                  # pytest test suite
│   │   ├── Dockerfile
│   │   ├── pytest.ini
│   │   ├── requirements.txt
│   │   └── ruff.toml
│   └── web/                        # React frontend
│       ├── src/
│       │   ├── api/                # TanStack Query hooks
│       │   ├── components/         # shadcn/ui + custom components
│       │   ├── lib/                # Utilities (format, status-colors)
│       │   ├── pages/              # Route-level page components
│       │   ├── test/               # Vitest setup
│       │   └── types/              # TypeScript API types
│       ├── Dockerfile
│       ├── nginx.conf
│       └── vite.config.ts
├── n8n/
│   └── workflows/                  # Exported n8n workflow JSON files
├── docker-compose.yml
├── package.json                    # Root convenience scripts
└── README.md
```

---

## Assumptions

1. **Amounts in cents** — all monetary values are stored as integers in minor currency units (e.g., 4999 = €49.99). Never floats.
2. **Separate provider tables** — `stripe_payments`, `paypal_payments`, and `bank_transfer_payments` each have provider-specific fields, rather than a polymorphic single table.
3. **Scoring over exact key matching** — real-world provider data rarely has a clean foreign key back to internal records. Confidence scoring handles partial information gracefully.
4. **VAT number as linking field** — in European payments, the merchant VAT number is a reliable cross-system identifier available in both internal and external records.
5. **65% confidence threshold** — chosen to be permissive enough to handle real-world data skew while strict enough to avoid false positives.
6. **n8n for data simulation** — provider workflows (Stripe, PayPal, bank) simulate what real webhooks would provide, demonstrating the full reconciliation lifecycle without live provider credentials.
7. **Single-currency dashboard** — the summary KPIs aggregate all currencies together. Multi-currency breakdown is a natural extension (see below).
8. **Human-readable codes** — format `PREFIX-YYYY-MM-SEQUENCE` (e.g., `PAY-2026-03-000012`) using a `code_sequences` table with a per-prefix counter to guarantee uniqueness without gaps.

---

## Decisions Postponed

These were considered but intentionally deferred to keep scope appropriate for the assessment:

| Decision | Why deferred |
|----------|-------------|
| Mixed-currency dashboard totals | Requires exchange rate data; adds significant complexity for limited demo value |
| Real provider webhooks (Stripe, PayPal) | Needs live credentials and a public endpoint; n8n simulation is equivalent for the demo |
| Alembic database migrations | `create_all` is acceptable for a seed-based demo; Alembic would be required in production |
| Per-merchant reconciliation rules | Different merchants may need different scoring thresholds; not required for the demo dataset |
| n8n workflow pagination | Provider simulation workflows fetch all records; real workflows would need cursor-based pagination |
| Real BIN database lookup | Card BIN matching uses stored values; a production system would validate against a live BIN database |

---

## What I Would Do Differently

1. **Alembic for migrations** — `create_all` on startup is convenient for demos but unsafe in production where existing data must be preserved across schema changes.
2. **Event-driven reconciliation** — instead of polling every 15 minutes (WF6), trigger reconciliation when a new provider record arrives via webhook.
3. **Idempotent provider ingestion** — the simulation workflows insert new records on every run; a real system would use provider transaction IDs as unique constraints to prevent duplicates.
4. **Per-merchant scoring rules** — some merchants have higher fee variance or longer settlement windows; the scoring thresholds should be configurable per merchant.
5. **Async LangChain** — the `/ask` endpoint uses a synchronous LangChain chain in an async FastAPI endpoint; this blocks the event loop. A production implementation would use `langchain_anthropic.astream` or run in a thread pool.
6. **Structured logging** — replace `print` statements with structured JSON logs (using `structlog`) for easier aggregation in a log management system.
7. **Caching for reference data** — currencies, merchants, and providers are loaded from the database on every request; an in-memory cache with a short TTL would reduce database load significantly.

---

## How to Extend for Production

| Concern | Approach |
|---------|---------|
| **Container orchestration** | Deploy the `api` and `web` Docker images to any container platform — Kubernetes, AWS ECS, Google Cloud Run, or Azure Container Apps |
| **Database** | Replace the Docker PostgreSQL with a managed service (RDS, Cloud SQL, Azure Database for PostgreSQL) with automated backups and read replicas |
| **Migrations** | Add Alembic for schema version control — run `alembic upgrade head` as an init container before the API starts |
| **Secrets** | Store `DATABASE_URL`, `ANTHROPIC_API_KEY`, and other secrets in a secrets manager (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault) |
| **Observability** | Add structured logging, metrics (Prometheus/OpenTelemetry), and distributed tracing |
| **CI/CD** | Build and push Docker images on merge to main; deploy with a rolling update strategy |
| **Real provider webhooks** | Replace n8n simulation workflows with real Stripe/PayPal webhook endpoints that ingest provider data in real time |
| **Multi-tenancy** | Add `tenant_id` to all tables and row-level security policies in PostgreSQL for SaaS deployment |

---

## Trade-offs

| Decision | Trade-off |
|----------|----------|
| Scoring-based matching | More flexible than exact key matching, but requires tuning thresholds per business context |
| Separate provider tables | Cleaner schema and type safety, but adding a new provider requires a new table + migration |
| n8n for workflows | No-code visual orchestration is easy to monitor, but adds an extra service and couples the demo to n8n's data model |
| Dynamic max_score | Fair confidence % across provider types, but harder to explain to non-technical stakeholders than a fixed scale |
| Pandas for trends | Clean aggregation code, but pulls all reconciliation rows into memory — would need chunking for large datasets |
| LangChain two-step chain | Reliable SQL generation + NL answer, but makes 2 LLM calls per question; a single call with tool use would be more efficient |

---

## AI Tools Used

This project was developed with **Claude Code** (Anthropic's CLI tool). Per the assessment instructions, all AI assistance is documented here:

- **Architecture decisions** — discussed scoring engine design, provider table separation, and n8n workflow structure with Claude Code.
- **Code generation** — FastAPI routers, SQLAlchemy models, React components, TanStack Query hooks, and Dockerfile configurations were written with Claude Code assistance.
- **Test suite** — pytest fixtures, mock session strategies, and Vitest component tests were developed iteratively with Claude Code.
- **Debugging** — resolved issues including nested `.git` repository (Vite init), Docker `npm ci` lock file mismatch, and ruff `# noqa` inside triple-quoted strings.
- **Documentation** — this README and the n8n workflow export instructions were written with Claude Code.

All generated code was reviewed, understood, and validated before being committed.
