# 🚀 SentinelGraph AI: Deployment & Operations Guide

## 1. Deployment Topology & Container Strategy

SentinelGraph AI is containerized for consistent execution across local developer workstations, staging clusters, and production cloud environments (e.g. Docker Engine, Kubernetes, Render, AWS ECS, or DigitalOcean Droplets).

```
┌────────────────────────────────────────────────────────────────────────┐
│                   DOCKER ORCHESTRATION ARCHITECTURE                    │
├──────────────────┬─────────────────┬───────────┬───────────────────────┤
│ Service Name     │ Image / Context │ Host Port │ Responsibility        │
├──────────────────┼─────────────────┼───────────┼───────────────────────┤
│ `frontend`       │ `./frontend`    │ `80:80`   │ Nginx SPA & API proxy │
│ `api`            │ `./backend`     │ `8000`    │ FastAPI backend core  │
│ `postgres`       │ `postgres:16`   │ `5432`    │ Transactional database│
│ `neo4j`          │ `neo4j:5.26.0`  │ `7687`    │ Graph database        │
│ `prometheus`     │ `prom/prometheus`│ `9090`   │ Metrics collection    │
│ `grafana`        │ `grafana/grafana`│ `3000`   │ Telemetry dashboards  │
└──────────────────┴─────────────────┴───────────┴───────────────────────┘
```

---

## 2. Option A: Full-Stack Docker Compose (Recommended)

The root [`docker-compose.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/docker-compose.yml) deploys the complete unified platform with a single command:

### 2.1 Step-by-Step Launch Instructions
```bash
# 1. Clone repository
git clone https://github.com/DeveshChauhan-afk/SentinelGraph-AI.git
cd SentinelGraph-AI

# 2. Configure environment credentials
cp backend/.env.example backend/.env
# Edit backend/.env to provide your Google Gemini API key:
# GEMINI_API_KEY=AIzaSy...

# 3. Build and launch all 6 containers
docker compose up -d --build
```

### 2.2 Verifying Service Health
All services in the root Docker Compose define automated health probes:
```bash
docker compose ps
```
Expected output:
```text
NAME                     IMAGE                      STATUS                  PORTS
sentinelgraph-frontend   sentinelgraph-frontend     Up (healthy)            0.0.0.0:80->80/tcp
sentinelgraph-api        sentinelgraph-api          Up (healthy)            0.0.0.0:8000->8000/tcp
sentinelgraph-postgres   postgres:16                Up (healthy)            5432/tcp
sentinelgraph-neo4j      neo4j:5.26.0-community     Up (healthy)            7474/tcp, 7687/tcp
sentinelgraph-prometheus prom/prometheus:v2.53.0    Up (healthy)            9090/tcp
sentinelgraph-grafana    grafana/grafana:11.1.0     Up (healthy)            0.0.0.0:3000->3000/tcp
```

### 2.3 Accessing Endpoints
* **Analyst Web Console**: `http://localhost` (Port 80)
* **Investigation Workspace**: `http://localhost/#investigate`
* **AI Governance Console**: `http://localhost/#evaluation`
* **FastAPI Backend Swagger**: `http://localhost:8000/docs`
* **Prometheus Metrics**: `http://localhost:8000/metrics` (or `http://localhost:9090` direct)
* **Grafana Operational Dashboards**: `http://localhost:3000` (Default: `admin` / `admin`)

---

## 3. Option B: Backend-Only Development Compose

For backend engineers who do not need the frontend container and wish to run Vite locally:

```bash
cd backend
cp .env.example .env

# Launch Postgres, Prometheus, Grafana, and API
docker compose up -d --build
```
* Uses [`backend/docker-compose.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/docker-compose.yml).
* Exposes PostgreSQL directly on port `5432` for GUI access (e.g. pgAdmin, DBeaver).

---

## 4. Option C: Local Bare-Metal Development

### 4.1 Backend Setup
```bash
cd backend

# Create & activate Python 3.13 virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Install development & testing dependencies
pip install -r requirements-dev.txt

# Run migrations to latest schema head
alembic upgrade head

# Start development server with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4.2 Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
* Frontend runs at `http://localhost:5173`.
* Vite proxies `/api` calls to `http://localhost:8000`.

---

## 5. Environment Configuration Reference

Configuration is managed via Pydantic Settings reading environment variables:

| Variable | Default Value | Required | Description |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | &mdash; | **Yes** | Cryptographic key for session security & signing. |
| `DATABASE_HOST` | `localhost` | **Yes** | PostgreSQL hostname (`postgres` in Compose). |
| `DATABASE_PORT` | `5432` | No | PostgreSQL TCP port. |
| `DATABASE_NAME` | `sentinel_db` | No | Database name. |
| `DATABASE_USER` | `sentinel_user`| No | Database username. |
| `DATABASE_PASSWORD` | &mdash; | **Yes** | Database password (`SecretStr`). |
| `NEO4J_URI` | `bolt://localhost:7687` | **Yes** | Neo4j Bolt connection URI. |
| `NEO4J_USERNAME` | `neo4j` | No | Neo4j username. |
| `NEO4J_PASSWORD` | &mdash; | **Yes** | Neo4j password (`SecretStr`). |
| `NEO4J_DATABASE` | `neo4j` | No | Target graph database name. |
| `GEMINI_API_KEY` | &mdash; | **Yes** | Google Gemini API key (`SecretStr`). |
| `GEMINI_MODEL` | `gemini-2.5-flash` | No | Active Gemini model for extraction & reports. |
| `GEMINI_TIMEOUT_SECONDS` | `30` | No | Per-attempt timeout for LLM generation. |
| `GEMINI_MAX_RETRIES` | `3` | No | Maximum retry attempts for transient errors. |
| `RUN_MIGRATIONS` | `true` | No | When `true`, container runs `alembic upgrade head`. |
| `CORS_ORIGINS` | `["*"]` | No | Allowed CORS origin whitelist JSON list. |

---

## 6. Automated Database Migrations

The backend container entrypoint script ([`backend/entrypoint.sh`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/entrypoint.sh)) automates database migrations on startup:

```sh
#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Database migrations applied successfully."
fi

# Honor dynamic PORT environment variable (e.g. Render Web Services)
if [ "$1" = "uvicorn" ] && [ "$2" = "app.main:app" ]; then
    PORT="${PORT:-8000}"
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi

exec "$@"
```

* Eliminates manual migration steps during production rollouts.
* Can be disabled by setting `RUN_MIGRATIONS=false` if migrations are managed by an external CI/CD runner.

---

## 7. Cloud Deployment (Render, Cloud VMs & Kubernetes)

The application includes specific adaptations for zero-downtime cloud hosting:

### 7.1 Dynamic `$PORT` Support
Platforms like Render or Heroku assign a dynamic HTTP port at runtime via the `$PORT` environment variable. `entrypoint.sh` intercepts this and binds Uvicorn dynamically to `$PORT`.

### 7.2 Non-Root Container Execution
The backend `Dockerfile` enforces non-root execution for container security compliance:
```dockerfile
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup --create-home appuser
USER appuser
```

### 7.3 Persistent Volume Mounts
Ensure the following Docker volumes are backed by durable block storage in production:
* `postgres_data`: Backs `/var/lib/postgresql/data`.
* `neo4j_data`: Backs `/data` in Neo4j.
* `prometheus_data`: Backs `/prometheus` time-series database.
* `grafana_data`: Backs `/var/lib/grafana` dashboards and preferences.

---

## 8. Operational Runbooks

### 8.1 Viewing Logs with Request Correlation
```bash
# View all backend logs
docker compose logs -f api

# Filter logs for a specific request correlation ID
docker compose logs api | grep "7b89f022-44ef-4b45-9831-50e5eb54199c"
```

### 8.2 Database Backup Runbook
```bash
# Dump PostgreSQL database
docker compose exec postgres pg_dump -U sentinel_user sentinel_db > backup_postgres_$(date +%Y%m%d).sql

# Dump Neo4j database using cypher-shell or apoc
docker compose exec neo4j cypher-shell -u neo4j -p sentinel_neo4j_password "CALL apoc.export.cypher.all('backup.cypher', {})"
```
