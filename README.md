# Labhya Compute

A marketplace where people can rent out idle GPUs by the hour. Hosts run a small desktop app that starts a Docker container on their machine and opens a reverse SSH tunnel to a relay server; renters then connect to that container over SSH through the relay.

Labhya Compute started as our 7th-semester college project at Tribhuvan University, built by a team of three: **Sudip Niroula, Sugam Dahal and Saurab Prasai** (August 2025). It won Most Innovative Project at Ambition Hackathon 2025. The first version used Django REST Framework; in July 2026 Sudip rewrote the backend in FastAPI and SQLModel, and the Django code was removed.

## How it works

```mermaid
sequenceDiagram
    participant R as Renter (web app)
    participant API as API (FastAPI)
    participant A as Host agent (Windows)
    participant Relay as Relay server
    R->>API: Rent a GPU (wallet balance checked)
    API->>API: Create session, lease a relay port
    A->>API: Poll for pending sessions
    A->>A: Start Docker container with SSH, set session password
    A->>Relay: ssh -R relay_port -> container port 22
    A->>API: Mark session started, report GPU metrics
    R->>Relay: ssh -p relay_port ... (reaches the container)
    R->>API: End session (cost charged, port released)
```

| Part | Stack | Where |
|---|---|---|
| Web app | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui | `frontend/` |
| API | FastAPI, SQLModel, PostgreSQL, JWT auth | `backend/app/` |
| Host agent | Python, Tkinter, Docker, OpenSSH; packaged as a Windows `.exe` with PyInstaller | `backend/agent/`, `build_agent.py` |
| Session image | Ubuntu 22.04 with OpenSSH | `backend/agent/docker/session/` |

A GitHub Actions workflow (`.github/workflows/build-agent.yml`) builds the Windows agent on every push to `main` and commits it to `frontend/public/downloads/`, where the web app offers it for download.

## Running it locally

**With Docker Compose** (PostgreSQL, API and web app):

```bash
docker compose up --build
```

The web app is then at http://localhost:3001 and the API at http://localhost:8080 (interactive docs at `/docs`).

**Without Docker:**

```bash
# API
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:password@localhost:5432/labhya_compute
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn app.main:app --reload --port 8000

# Web app (in another terminal)
cd frontend
pnpm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api pnpm dev
```

**Host agent:** needs Windows 10 or 11 with WSL2 and Docker. Either download the agent from the web app or run `python backend/agent/agent_gui.py`.

**Tests:**

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The tests use a temporary SQLite database and cover the rental flow, session access rules and token refresh.

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | API | PostgreSQL connection string (or set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_HOST`, `DB_PORT`) |
| `SECRET_KEY` | API | Signs login tokens. Required in any deployment; if it is missing, a temporary random key is used and logins stop working after a restart |
| `CORS_ALLOWED_ORIGINS` | API | Comma-separated web app origins |
| `RELAY_HOST`, `RELAY_PORT_RANGE_START`, `RELAY_PORT_RANGE_END` | API | Relay server address and the ports it can lease to sessions |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | API | Access token lifetime (default 24 hours) |
| `NEXT_PUBLIC_API_URL` | Web app | Base URL of the API, ending in `/api` |

## Known limitations

- **No real payments.** The wallet is simulated: adding funds does not take money from anywhere.
- **Windows-only hosts.** The agent depends on WSL2 and Docker Desktop.
- **SSH passwords are stored in plain text** in the database so the renter can see them, and the agent turns off SSH host-key checking when it connects to the relay. A real deployment would use per-session keys and a pinned relay host key.
- **No database migrations yet.** Tables are created at startup with `SQLModel.metadata.create_all`, so schema changes to an existing database have to be applied by hand. Alembic is listed as a dependency but not set up.
- **End-to-end SSH path not re-tested since the FastAPI rewrite.** The API tests cover the backend, but the full agent → relay → container connection still needs checking; for example, the connection string shows the relay account name, while the container's user is `labuser`.
- **Frontend type errors.** `next.config.mjs` skips type checking during builds, and `tsc` currently reports type errors in a few pages.
- **Built agent binaries live in the repository.** Publishing them as GitHub Release assets would keep the repository small.

## Repository layout

```
backend/
  app/            FastAPI app: models, schemas, routers (auth, gpus, sessions, wallets, dashboard)
  agent/          Host agent (Tkinter GUI) and the session container image
  tests/          API tests
frontend/         Next.js web app
build_agent.py    Packages the agent with PyInstaller
docker-compose.yml
```
