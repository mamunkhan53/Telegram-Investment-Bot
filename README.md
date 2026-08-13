# Telegram Investment Platform

A production-oriented Telegram investment platform in Python. Telegram is the client interface; application services, persistence, scheduling, administration, and blockchain integrations are designed to run on the backend.

> **Current milestone:** Core implementation baseline complete. The repository now includes configuration validation, centralized logging, async SQLAlchemy models and repositories, transaction-safe wallet and investment services, referral and withdrawal workflows, BNB Smart Chain deposit monitoring, Telegram handlers, a Bootstrap admin panel, FastAPI health and admin endpoints, APScheduler jobs, an initial Alembic migration, and deployment scripts. Review [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for installation and live-launch instructions.

## Technology Baseline

| Layer | Technology | Responsibility |
|---|---|---|
| Telegram client | Aiogram 3.x | Commands, callbacks, authentication flow, and user-facing interactions |
| HTTP server | FastAPI, Jinja2, Bootstrap 5 | Admin panel and future API endpoints |
| Persistence | PostgreSQL, SQLAlchemy 2.x, Alembic | Durable data storage, ORM mapping, and schema migrations |
| Background work | APScheduler, asyncio | Deposit checks, investment cycles, notifications, and withdrawal processing |
| Blockchain | Web3.py | BNB Smart Chain integration with an abstraction path for other networks |
| Configuration | Pydantic Settings, python-dotenv | Environment-based configuration and validation |
| Cache | Redis | Optional caching and coordination support |
| Operations | Docker, Docker Compose, Linux | Repeatable local and production execution |

## Project Structure

```text
telegram-investment-bot/
├── app/
│   ├── bot/
│   │   ├── handlers/       # Telegram event handlers; orchestration only
│   │   ├── keyboards/      # Inline keyboard builders
│   │   ├── callbacks/      # Callback payload definitions and routing
│   │   ├── commands/       # Bot command registration and command modules
│   │   ├── middlewares/    # Authentication, logging, throttling, and context
│   │   ├── filters/        # Reusable Telegram filters
│   │   ├── states/          # Finite-state machine definitions
│   │   └── bot.py          # Bot and dispatcher composition
│   ├── admin/
│   │   ├── routes/         # Admin dashboard routes
│   │   ├── auth/           # Admin login and authorization
│   │   ├── templates/      # Jinja2 templates
│   │   ├── static/         # Bootstrap overrides and static assets
│   │   └── admin.py        # Admin application composition
│   ├── api/
│   │   ├── routes/         # Versioned HTTP API routes
│   │   └── api.py          # FastAPI application composition
│   ├── database/
│   │   ├── models/         # SQLAlchemy ORM models only
│   │   ├── repositories/   # Database access abstractions only
│   │   ├── migrations/     # Alembic migration files
│   │   ├── session.py      # Async engine and session factory
│   │   └── base.py         # Declarative base and model metadata
│   ├── services/           # Business use cases and domain orchestration
│   ├── scheduler/          # APScheduler jobs and job registration
│   ├── blockchain/         # Network clients, wallets, and monitoring adapters
│   ├── config/             # Settings and immutable application constants
│   ├── utils/              # Shared validation, formatting, logging, and helpers
│   └── main.py             # Application entry point
├── tests/                  # Unit, integration, and end-to-end tests
├── docs/                   # Architecture and operational documentation
├── scripts/                # Safe operational and maintenance scripts
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template; no secrets
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Local PostgreSQL and Redis services
└── README.md
```

## Architecture Rules

The implementation follows a layered flow:

```text
Telegram / HTTP request
        ↓
Handlers / Routes
        ↓
Services
        ↓
Repositories
        ↓
SQLAlchemy models and PostgreSQL
```

Handlers and routes must remain thin and must not contain business rules. Services own business decisions and transaction boundaries. Repositories own database access. ORM models remain inside the database layer, while scheduled jobs only coordinate service calls. Blockchain adapters are isolated behind interfaces so additional networks can be added without rewriting business services.

## Installation

The complete installation, staging, and live-deployment procedure is documented in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). The short local workflow is:

```bash
git clone <your-repository-url> telegram-investment-bot
cd telegram-investment-bot
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set all required values in `.env` before starting the application. Private keys, bot tokens, passwords, and API keys must never be committed to version control.

## Environment Variables

The `.env.example` file documents the initial configuration surface. Important groups include application secrets, Telegram credentials, PostgreSQL connection strings, optional Redis settings, administrator authentication, BNB Smart Chain RPC and contract configuration, platform wallet settings, scheduler intervals, and public URLs.

## Database Migration

Alembic is the migration tool. The repository includes the initial schema migration and the normal workflow is:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

Migrations must be reviewed before applying them to production. Production balance changes must be performed through service-level transactions, not ad hoc database edits.

## Running the Bot and Admin Panel

The application entry points are available through the process selector. Use separate processes for the API, bot, and scheduler worker:

```bash
python -m app.main
uvicorn app.api.api:app --host 0.0.0.0 --port 8000 --reload
```

The bot process and the admin/API process may be run separately in production so that each can be supervised and restarted independently.

## Docker Usage

The repository includes Docker entry points for local and production-oriented execution. The expected local workflow is:

```bash
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d api bot worker
```

The API, bot, and scheduler worker are separate services so background jobs are not duplicated when the HTTP process is scaled.

## Deployment

The platform is intended to support three deployment styles:

| Target | Intended use |
|---|---|
| Docker Compose on a Linux VPS | Full control, persistent bot process, PostgreSQL, Redis, reverse proxy, and backups |
| Railway or comparable container platform | Managed deployment with environment variables and managed PostgreSQL |
| Local Linux development | Module development, tests, and sandbox validation |

Before going live, configure HTTPS for the admin panel, restrict administrative access, use a managed or backed-up PostgreSQL instance, protect the hot wallet, validate blockchain confirmations, configure process restart policies, and test deposit, withdrawal, and accounting invariants on a test network.

## Development Workflow

The implementation is organized module by module. Before enabling real funds, complete the staging verification, compliance review, security testing, custody review, and independent financial-code audit described in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). The outbound hot-wallet signer remains intentionally disabled in this release; withdrawal requests stay available for controlled admin processing.
