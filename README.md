# AI-Assisted Smart Disaster Response & Emergency Coordination Platform

Full-stack platform where citizens report incidents, an **AI triage engine** scores severity and suggests
actions, and responders verify, dispatch resources and monitor analytics on a live dashboard.

## Tech stack
Python 3.10+ · FastAPI · SQLAlchemy · PostgreSQL (SQLite for local dev) · JWT auth · Pandas analytics ·
React 18 + Chart.js dashboard · Pytest · Docker · Swagger/OpenAPI (`/docs`) · GitHub Copilot / Claude for AI-assisted development

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- Dashboard: http://localhost:8000  ·  Swagger UI: http://localhost:8000/docs
- Seeded admin: `admin` / `Admin@12345` (override with `ADMIN_PASSWORD`). New registrations are *citizens*; admin promotes users to *responder* via `PUT /admin/users/{username}/role`.

## Run with PostgreSQL + Docker
```bash
docker compose up --build
```

## Tests
```bash
pytest -q
```

## REST API
| Method | Endpoint | Role | Purpose |
|---|---|---|---|
| POST | /auth/register | public | Create citizen account |
| POST | /auth/login | public | Get JWT |
| PUT | /admin/users/{u}/role | admin | Promote/demote user |
| POST | /incidents | any user | Report incident (AI triage applied) |
| GET | /incidents | any user | List/filter (`status`, `category`, `min_severity`) |
| GET | /incidents/{id} | any user | Incident detail |
| PATCH | /incidents/{id}/status | responder/admin | Update status |
| DELETE | /incidents/{id} | admin | Remove incident |
| POST/GET | /resources | responder+/any | Manage & view resources |
| POST | /incidents/{id}/dispatch | responder/admin | Allocate resource (stock-checked) |
| GET | /analytics/summary | any user | Pandas-based analytics |
| GET | /health | public | Liveness check |

## Architecture
```
React dashboard ──HTTP/JSON+JWT──► FastAPI (routers, RBAC) ──► SQLAlchemy ──► PostgreSQL
                                        │
                                        └─► ai.py (triage: rules now, LLM-pluggable)
```
Modules: `database.py` (engine/session) · `models.py` (ORM) · `schemas.py` (validation) · `security.py` (hashing, JWT, RBAC) · `ai.py` (triage) · `main.py` (routes).

**ER summary:** User 1─* Incident · Incident 1─* Dispatch *─1 Resource.

## Security measures
PBKDF2-SHA256 salted password hashing · JWT with expiry · role-based access control · Pydantic input validation
(length/range/enum limits) · SQLAlchemy parameterised queries (no SQL injection) · secrets via environment variables ·
configurable CORS · public registration cannot create privileged roles.
*Before real deployment:* set `SECRET_KEY`, `ADMIN_PASSWORD`, restrict `CORS_ORIGINS`, use HTTPS, add rate-limiting.

## AI-assisted development workflow (document your own evidence here)
| Phase | AI tool used | Example prompt | Human review |
|---|---|---|---|
| Requirements | Claude | "Turn this problem statement into user stories and roles" | Edited roles to citizen/responder/admin |
| Architecture | Claude/Copilot | "Design ER model + REST endpoints for incident/dispatch" | Verified relations |
| Backend | Copilot | Inline completion of routes & schemas | Manual RBAC review |
| Testing | Claude | "Write pytest covering auth, RBAC, dispatch stock limits" | Ran and fixed tests |
| Documentation | Claude | "Generate README + API table" | Checked against code |
| Security review | Claude | "Review this FastAPI app for OWASP Top 10 issues" | Applied fixes |

> Add your own screenshots of Copilot/Claude sessions and prompt logs to `docs/` as proof of AI-assisted workflow.

## Responsible / ethical AI
- AI output is **advisory** — every incident is shown with "human must verify"; only responders can change status or dispatch.
- Triage is rule-based and explainable (matched signals are shown), avoiding opaque decisions on life-critical matters.
- Known limitations: keyword rules can miss context, English-only, no verified geolocation. False negatives are mitigated by responder review.
- No personal data beyond username is stored.

## Cloud deployment
Render/Railway/Replit/AWS: build from `Dockerfile`, attach managed PostgreSQL, set `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`.
Health-check path: `/health`.

## Future work
LLM-based triage with human-in-the-loop, map view (Leaflet), SMS alerts, WebSocket live updates, Alembic migrations.
