# Banking Enterprise Data Lakehouse Simulator

> **Synthetic demo data only — not for production banking data.**
> Personal portfolio project. Not an official BNI system, not connected to any bank infrastructure.

A locally runnable banking data lakehouse simulator that demonstrates governed multi-unit data onboarding, Medallion Architecture processing (Landing → Bronze → Silver → Gold), metadata management, data quality, lineage, and time-bound access to curated data products.

## Docs

- [Product Requirements (PRD)](docs/PRD.md)
- [Tech stack architecture](docs/architecture.mmd) (Mermaid)
- [Metadata ERD](docs/erd.mmd) (Mermaid)

## Stack

Streamlit · FastAPI · PostgreSQL · DuckDB + PyArrow + Pandas · Parquet · Docker Compose · Pytest · Plotly

## Status

Work in progress. Being built milestone by milestone (see PRD section 19).
Milestone 1 (Foundation) is in place: Docker Compose stack, PostgreSQL with migrations,
FastAPI, a Streamlit shell, and seeded demo users.

## Run it locally

### Prerequisites

- Docker Desktop (on Windows, with the WSL2 backend) and Docker Compose v2
- Git
- For running tests on the host: Python 3.11 (and optionally [uv](https://docs.astral.sh/uv/))

### Start the stack

```bash
cp .env.example .env            # placeholder local credentials; edit if you like
docker compose up -d --build    # db, api (runs migrations on start), frontend
docker compose exec api python -m scripts.seed_demo_data   # safe to re-run
```

Then open <http://localhost:8501> and pick a demo user in the sidebar.

| Service | URL |
|---|---|
| Streamlit UI | <http://localhost:8501> |
| API | <http://localhost:8000> (OpenAPI docs at `/docs`) |
| API health | <http://localhost:8000/health> |
| PostgreSQL | `localhost:5433` |

The API uses mock authentication: send `X-Demo-User: <username>` (for example
`sari.submitter`) and the API acts as that seeded user.

```bash
curl http://localhost:8000/api/v1/demo-users
curl -H "X-Demo-User: sari.submitter" http://localhost:8000/api/v1/me
```

Stop with `docker compose down`; add `-v` to also delete the database volume.

### Connect with DBeaver (or any SQL client)

New PostgreSQL connection:

- Host `localhost`, port **5433**
- Database, user and password: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` from your `.env`

### Run the tests

Tests run on the host against the Compose PostgreSQL on `localhost:5433`. Integration tests
create a throwaway database (`lakehouse_test_<random>`) and drop it afterwards; they never
touch the dev database.

```bash
docker compose up -d db
uv venv --python 3.11 .venv          # or: python -m venv .venv, then pip install -r requirements.txt
uv pip install -r requirements.txt   # installs into ./.venv
.venv/Scripts/python -m pytest       # Windows; on macOS/Linux: .venv/bin/python -m pytest
```

Run pytest from the repository root so it picks up `.env`.

### Updating dependencies

`requirements.in` lists the direct dependencies. `requirements.txt` is the lock compiled from
it: every package, transitive ones included, pinned with hashes, and the Docker image installs
it with `pip install --require-hashes`. To change a dependency, edit `requirements.in` and
re-compile the lock (never edit `requirements.txt` by hand):

```bash
uv pip compile requirements.in --universal --python-version 3.11 --generate-hashes -o requirements.txt
```

Add `--upgrade` to also move unpinned transitive dependencies to their latest versions.

### Troubleshooting: port 5432 vs 5433

The Compose database is published on host port **5433**, not the PostgreSQL default 5432,
because a natively installed PostgreSQL often already owns 5432. If DBeaver or the tests
connect to 5432 you are talking to that other server (wrong database, wrong credentials).
Use `localhost:5433` from the host. Inside Compose, the api reaches the database at `db:5432`.
