# Installation and Live Deployment Guide

This guide covers local installation, Docker deployment, a Linux VPS launch, and a managed container alternative. The platform is designed to run as three separate processes in production: the **FastAPI admin/API service**, the **Telegram bot service**, and the **APScheduler worker**.

> **Important financial-safety status:** The implementation is suitable for continued development and staging validation. The outbound hot-wallet signer is intentionally not enabled in this release; withdrawal requests remain visible for controlled admin processing. Before accepting real funds, complete legal and compliance review, KYC/AML controls, custody and key-management review, testnet verification, security testing, and an independent financial-code audit.

## 1. Prerequisites

For local development, use Linux, macOS, or Windows with Python 3.12 or newer, Git, PostgreSQL, and Redis. Docker Compose is the recommended path because it supplies PostgreSQL and Redis consistently.

For a Linux VPS, use a current Ubuntu or Debian server with a public DNS name, an attached persistent disk or managed database backup, and a firewall that exposes only SSH and HTTPS. Do not expose PostgreSQL or Redis directly to the public internet.

| Component | Development | Production recommendation |
|---|---|---|
| Python | 3.12+ virtual environment | Container image from the repository |
| PostgreSQL | Docker Compose PostgreSQL | Managed PostgreSQL or private VPS container with tested backups |
| Redis | Optional local container | Private Redis, only if enabled |
| Telegram | BotFather token | Dedicated production bot token |
| Blockchain | BSC testnet or controlled RPC | BSC mainnet RPC with rate limits and monitoring |
| Reverse proxy | Optional | Nginx, Caddy, or a managed HTTPS proxy |

## 2. Obtain the Source and Create Configuration

```bash
git clone <your-repository-url> telegram-investment-bot
cd telegram-investment-bot
cp .env.example .env
```

Generate strong secrets locally. The commands below print values to the terminal; copy them into `.env` without committing the file.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

PYTHONPATH=. python scripts/generate_secret.py 48
PYTHONPATH=. python scripts/generate_secret.py 48
PYTHONPATH=. python scripts/generate_admin_hash.py
```

Use the first random value for `SECRET_KEY`, the second for `ADMIN_SESSION_SECRET`, and the password hash output for `ADMIN_PASSWORD_HASH`. The administrator password should be unique to this platform and stored in a password manager.

## 3. Required Environment Values

Edit `.env` and set the following values. Never commit `.env`, a private key, a seed phrase, or an RPC credential to Git.

```dotenv
APP_ENV=staging
APP_PROCESS=all
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=<random-value-at-least-32-characters>
ADMIN_SESSION_SECRET=<different-random-value-at-least-32-characters>

TELEGRAM_BOT_TOKEN=<BotFather-token>
ADMIN_USERNAME=<admin-username>
ADMIN_PASSWORD_HASH=<bcrypt-hash>

DATABASE_URL=postgresql+asyncpg://investment:change-this-db-password@postgres:5432/investment
DATABASE_SYNC_URL=postgresql+psycopg://investment:change-this-db-password@postgres:5432/investment
REDIS_URL=redis://redis:6379/0
REDIS_ENABLED=true

BSC_RPC_URL=<private-or-rate-limited-BSC-RPC-endpoint>
BSC_CHAIN_ID=56
BSC_USDT_CONTRACT_ADDRESS=<verified-USDT-contract-address>
BSC_CONFIRMATIONS_REQUIRED=12
PLATFORM_DEPOSIT_ADDRESS=<controlled-deposit-address>

ADMIN_BASE_URL=https://admin.example.com
PUBLIC_BASE_URL=https://admin.example.com
```

For Docker Compose, the database host is `postgres` and the Redis host is `redis`. For a managed database, replace both URLs with the provider's private connection strings. Use a separate staging bot, database, wallet, RPC credential, and contract configuration from production.

## 4. Local Installation with Docker Compose

Start the supporting services first:

```bash
docker compose up -d postgres redis
```

Apply the initial schema migration:

```bash
docker compose run --rm api alembic upgrade head
```

Start the API, Telegram bot, and worker:

```bash
docker compose up -d api bot worker
```

Check the containers and API health endpoint:

```bash
docker compose ps
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

Open the admin login page at `http://127.0.0.1:8000/admin/login`. The bot should respond to `/start` after its Telegram token and database configuration are valid.

View logs with:

```bash
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f worker
```

Use lowercase `docker` in the second command if your shell is case-sensitive:

```bash
docker compose logs -f bot
```

## 5. Local Installation Without a Containerized Application

Keep PostgreSQL and Redis running through Compose, then use three terminals from the repository root.

```bash
source .venv/bin/activate
export PYTHONPATH=.
```

Run the migration:

```bash
alembic upgrade head
```

Run the API:

```bash
APP_PROCESS=api python -m app.main
```

Run the Telegram bot in a second terminal:

```bash
APP_PROCESS=bot python -m app.main
```

Run the scheduler worker in a third terminal:

```bash
APP_PROCESS=worker python -m app.main
```

The `all` mode is convenient for a single development process, but separate services are preferred for production because the scheduler must have exactly one active worker unless a distributed job-lock strategy is added.

## 6. Live Deployment on a Linux VPS

Create a deployment directory and install Docker Engine and the Docker Compose plugin using the operating system's supported package instructions. Clone the repository into a non-root application directory and restrict `.env` permissions:

```bash
sudo mkdir -p /opt/telegram-investment-bot
sudo chown "$USER":"$USER" /opt/telegram-investment-bot
git clone <your-repository-url> /opt/telegram-investment-bot
cd /opt/telegram-investment-bot
cp .env.example .env
chmod 600 .env
```

Set `APP_ENV=staging` during the first launch. Complete the staging validation below before switching to production. After configuring the database password, Telegram token, RPC endpoint, verified contract, deposit address, administrator hash, and random secrets, build and migrate:

```bash
docker compose build
docker compose up -d postgres redis
until docker compose exec -T postgres pg_isready -U investment -d investment; do sleep 2; done
docker compose run --rm api alembic upgrade head
docker compose up -d api bot worker
docker compose ps
```

Put the API behind HTTPS. A minimal Nginx location should proxy only the API service and should not proxy PostgreSQL, Redis, or the bot process. Enable TLS through your chosen certificate manager, then set `ADMIN_BASE_URL` and `PUBLIC_BASE_URL` to the HTTPS URL and restart the API:

```bash
docker compose up -d --force-recreate api
curl https://admin.example.com/healthz
```

Use a firewall to allow SSH and HTTPS only. Restrict SSH to trusted source addresses where possible, disable password-based SSH login, and use a non-root deployment user. Store database and RPC credentials outside source control, rotate them after any suspected exposure, and keep wallet signing keys outside the application container until the signer design has been independently reviewed.

## 7. Managed Container Deployment

The repository can also be deployed to a managed container platform that supports a Dockerfile, PostgreSQL, Redis, environment variables, and separate services or workers. Create one application service for the API, one long-running bot service, and one worker service. Use the same image with these process values:

| Service | `APP_PROCESS` | Port |
|---|---|---:|
| API | `api` | `8000` |
| Bot | `bot` | none |
| Scheduler | `worker` | none |

Attach PostgreSQL and Redis services, copy the required environment variables into the platform secret manager, deploy the image, and run `alembic upgrade head` as a one-off release command before enabling the API, bot, and worker services. Configure an HTTPS health check against `/healthz` or `/readyz` and configure automatic restarts.

## 8. Staging Verification Before Mainnet

Use a separate staging bot and database. Verify the following behaviors using test funds:

| Area | Verification |
|---|---|
| Registration | `/start` creates one user and one wallet; repeated `/start` does not duplicate either record. |
| Referral | A valid Telegram deep-link referral attributes the new user once and does not allow self-referral. |
| Deposit monitoring | The same blockchain event cannot create two deposits, and crediting the same deposit twice cannot create two ledger entries. |
| Wallet accounting | Credits, debits, reservations, releases, and failed withdrawals preserve non-negative balances. |
| Investment engine | A plan range is enforced, principal is debited once, maturity is processed once, and profit is credited once. |
| Withdrawals | Requests are idempotent, destination addresses are validated, and failed requests release reserved funds. |
| Admin security | Invalid credentials are rejected, sessions are signed and time-limited, and privileged actions are audited. |
| Operations | API, bot, and worker restart independently; PostgreSQL backups restore successfully; logs contain no secrets. |

Do not switch `APP_ENV` to `production` until these checks pass and all required production variables are present. The production settings validator intentionally fails startup when required bot, admin, contract, deposit-address, or secret values are missing.

## 9. Backups, Monitoring, and Recovery

Back up PostgreSQL before every schema change and retain encrypted copies outside the server. A simple Compose backup command is:

```bash
mkdir -p backups
docker compose exec -T postgres pg_dump -U investment -d investment | gzip > "backups/investment-$(date +%Y%m%d-%H%M%S).sql.gz"
```

A restore should be performed only after stopping application writers and confirming the target database. Test restoration periodically on a separate database; a backup that has never been restored is not a verified recovery plan.

Monitor `/healthz`, `/readyz`, container restart counts, PostgreSQL storage, RPC error rates, scheduler logs, pending withdrawals, and failed Telegram notifications. Alert on repeated worker failures, database connectivity failures, blockchain scan lag, unexpected balance adjustments, and any withdrawal state that remains processing beyond its operational threshold.

## 10. Updating the Live Version

Pull the reviewed release, build the new image, run migrations, and restart services in that order:

```bash
cd /opt/telegram-investment-bot
git fetch --all
git checkout <reviewed-release-tag>
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d api bot worker
docker compose ps
```

Keep the previous image or release tag available for rollback. Never run an unreviewed schema migration against the production database, and never deploy a new withdrawal or signer implementation without a staged transaction test and independent review.
