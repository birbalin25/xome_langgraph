# CLAUDE.md

## Project Overview

Xome Campaign Platform — an AI-powered real estate campaign tool that generates personalized emails promoting recommended properties to high-intent buyers. Built with FastAPI backend, React + TailwindCSS frontend, LangGraph orchestration, deployed as a single-process Databricks App.

## Key Paths

- Backend: `agent_server/`
- REST API router: `agent_server/campaign_api.py`
- Chat API router: `agent_server/chat_api.py`
- LangGraph state: `agent_server/graph_state.py`
- LangGraph nodes: `agent_server/graph_nodes.py`
- LangGraph graph: `agent_server/graph.py`
- Email generation logic: `agent_server/email_generator.py`
- LLM setup: `agent_server/agent.py`
- SQL helper: `agent_server/tools.py`
- Prompts: `agent_server/prompts.py`
- Server entry point: `agent_server/start_server.py`
- Frontend (React): `frontend/`
- Frontend components: `frontend/src/components/`
- Dashboard API client: `frontend/src/api/campaign.ts`
- Chat API client: `frontend/src/api/chat.ts`
- Data generation: `notebooks/01_generate_data.py`
- Deployment: `databricks.yml`, `app.yaml`

## Architecture

```
Browser → FastAPI (port 8000) → serves frontend/dist/ (static) + REST API (/api/campaign/*, /api/chat/*)
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                   LangGraph     Delta Tables  UC Volume
                   StateGraph
                      │
                      ▼
                  Claude LLM
```

**Two UI paths, one pipeline:**
- Dashboard: `React UI → campaign_api.py → LangGraph (source=dashboard) → email_generator.py → Claude LLM`
- Chat: `React UI → chat_api.py → LangGraph (source=chat) → email_generator.py → Claude LLM`

**LangGraph StateGraph:**
```
process_input → retrieve_candidates → rank_and_select → enrich_context → generate_email → END
     |                                      |
     +--[error]--> handle_error --> END     +--[error]--> handle_error --> END
```

**Single-process deployment:** FastAPI on port 8000 serves both the pre-built React frontend (from `frontend/dist/`) and all API endpoints. Databricks Apps only exposes port 8000.

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
- UC Volume: `campaign_emails`
- App URL: `https://agent-xome-langgraph-campaign-7474645414452466.aws.databricksapps.com`

## REST API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/campaign/filters` | Distinct cities, states, types, segments, price ranges |
| `POST` | `/api/campaign/users` | Top 20 users matching filters |
| `GET` | `/api/campaign/users/{id}/profile` | Full user profile |
| `POST` | `/api/campaign/users/{id}/listings` | Top 5 recommended properties |
| `POST` | `/api/campaign/generate-email` | Generate email via LangGraph (source=dashboard) |
| `POST` | `/api/campaign/save-email` | Save email to UC Volume |
| `POST` | `/api/chat/message` | Chat interface — natural language → LangGraph (source=chat) |
| `POST` | `/invocations` | MLflow-compatible endpoint → LangGraph (source=chat) |

## Common Commands

```bash
# Local dev (runs backend + frontend dev server concurrently)
uv run start-app

# Build frontend for production
cd frontend && npm run build && cd ..

# Deploy
databricks bundle deploy --target prod
databricks apps deploy agent-xome-langgraph-campaign --profile fevm --source-code-path /Workspace/Users/birbal.das@databricks.com/.bundle/xome_langgraph_campaign/prod/files

# Run data pipeline
databricks bundle run xome_setup_pipeline --target prod

# Check app status / logs
databricks apps get agent-xome-langgraph-campaign --profile fevm
databricks apps logs agent-xome-langgraph-campaign --profile fevm
```

## Data Tables

| Table | Rows | PK | FKs |
|-------|------|----|-----|
| `users` | 500 | `user_id` | — |
| `properties` | 1,000 | `property_id` | — |
| `browsing_activity` | 10,000 | `activity_id` | `user_id` → users, `property_id` → properties |
| `recommendations` | 5,000 | `recommendation_id` | `user_id` → users, `property_id` → properties |

## Dependencies

**Backend:** `fastapi`, `uvicorn`, `databricks-langchain`, `databricks-sdk`, `python-dotenv`, `langgraph`. Data gen uses `faker`.

**Frontend:** `react`, `vite`, `tailwindcss`, `lucide-react`, `typescript`.

## Known Deployment Notes

- Frontend must be built before deploy — `frontend/dist/` is served as static files by FastAPI.
- `frontend/dist/` must be included in bundle deploy — the `!frontend/dist/` exception in `.gitignore` overrides the global `dist/` exclusion pattern.
- npm registry: `.npmrc` in `frontend/` points to `https://registry.npmmirror.com` for corporate network compatibility.
