# CLAUDE.md

## Project Overview

Xome Campaign Platform — an AI-powered real estate campaign tool that generates personalized emails promoting recommended properties to high-intent buyers. Built with LangGraph + FastAPI backend, React + TailwindCSS frontend, deployed as a single-process Databricks App.

## Key Paths

- Backend API + agent: `agent_server/`
- Shared email logic: `agent_server/email_generator.py`
- REST API router: `agent_server/campaign_api.py`
- LangGraph agent: `agent_server/agent.py`
- Server entry point: `agent_server/start_server.py`
- Frontend (React): `frontend/`
- Frontend components: `frontend/src/components/`
- API client: `frontend/src/api/campaign.ts`
- Data generation: `notebooks/01_generate_data.py`
- Genie queries: `notebooks/02_genie_setup_instructions.py`
- Deployment: `databricks.yml`, `app.yaml`

## Architecture

```
Browser → FastAPI (port 8000) → serves frontend/dist/ (static) + REST API + LangGraph agent
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                    Claude LLM   Delta Tables  UC Volume
```

**Two paths to generate emails, both using shared `email_generator.py`:**

1. **Dashboard UI** → `campaign_api.py` (REST endpoints) → `email_generator.py` → Claude LLM
2. **Chat agent** → `agent.py` (LangGraph 5-node pipeline) → `email_generator.py` → Claude LLM

LangGraph pipeline: `process_input → retrieve_candidates → rank_and_select → enrich_context → generate_email`

**Single-process deployment:** FastAPI on port 8000 serves both the pre-built React frontend (from `frontend/dist/`) and all API endpoints. `enable_chat_proxy=False` in AgentServer. Databricks Apps only exposes port 8000.

## Critical Rules

- Campaign email properties come ONLY from the `recommendations` table. Browsing data is for personalization context only.
- Frontend must be built (`cd frontend && npm run build`) before deploying — `frontend/dist/` is served as static files.
- `.gitignore` has `!frontend/dist/` exception to include the built frontend in bundle deploy.

## Configuration

- Catalog: `serverless_stable_14ey07_catalog`
- Schema: `xome`
- Workspace: fevm (`https://fevm-serverless-stable-14ey07.cloud.databricks.com`)
- SQL Warehouse: `1f01d0f9de5b5108`
- LLM: `databricks-claude-sonnet-4-6`
- Genie Space: `01f1484fd22e1d558c5ed706de7b522d`
- UC Volume: `campaign_emails`
- App URL: `https://agent-xome-campaign-7474645414452466.aws.databricksapps.com`

## REST API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/campaign/filters` | Distinct cities, states, types, segments, price ranges |
| `POST` | `/api/campaign/users` | Top 20 users matching filters |
| `GET` | `/api/campaign/users/{id}/profile` | Full user profile |
| `POST` | `/api/campaign/users/{id}/listings` | Top 5 recommended properties |
| `POST` | `/api/campaign/generate-email` | Generate email via Claude LLM |
| `POST` | `/api/campaign/save-email` | Save email to UC Volume |

## Common Commands

```bash
# Local dev (runs backend + frontend dev server concurrently)
uv run start-app

# Build frontend for production
cd frontend && npm run build && cd ..

# Deploy
databricks bundle deploy --target prod
databricks apps deploy agent-xome-campaign --profile fevm --source-code-path /Workspace/Users/birbal.das@databricks.com/.bundle/xome_campaign/prod/files

# Run data pipeline
databricks bundle run xome_setup_pipeline --target prod

# Check app status / logs
databricks apps get agent-xome-campaign --profile fevm
databricks apps logs agent-xome-campaign --profile fevm
```

## Data Tables

| Table | Rows | PK | FKs |
|-------|------|----|-----|
| `users` | 500 | `user_id` | — |
| `properties` | 1,000 | `property_id` | — |
| `browsing_activity` | 10,000 | `activity_id` | `user_id` → users, `property_id` → properties |
| `recommendations` | 5,000 | `recommendation_id` | `user_id` → users, `property_id` → properties |

## Dependencies

**Backend:** `fastapi`, `databricks-langchain`, `mlflow>=3.10.0`, `langgraph`, `langchain-mcp-adapters`, `python-dotenv`. Data gen uses `faker`.

**Frontend:** `react`, `vite`, `tailwindcss`, `lucide-react`, `typescript`.

## Known Deployment Notes

- `enable_chat_proxy` must be `False` in `start_server.py` — when `True`, it intercepts all GET requests and proxies to a non-existent port 3000, causing 503 errors.
- `frontend/dist/` must be included in bundle deploy — the `!frontend/dist/` exception in `.gitignore` overrides the global `dist/` exclusion pattern.
- npm registry: `.npmrc` in `frontend/` points to `https://registry.npmmirror.com` for corporate network compatibility.
