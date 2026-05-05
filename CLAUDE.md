# CLAUDE.md

## Project Overview

Xome Agentic Email & Personalized Communication Platform. A LangGraph-based agent deployed as a Databricks App that generates personalized campaign emails promoting recommended properties to high-intent real estate buyers.

## Key Paths

- Agent code: `agent_server/`
- Data generation: `notebooks/01_generate_data.py`
- Genie queries: `notebooks/02_genie_setup_instructions.py`
- Deployment: `databricks.yml`, `app.yaml`

## Architecture

```
Chat UI (Next.js) -> FastAPI/MLflow -> LangGraph StateGraph -> Databricks SQL + Claude Sonnet 4.6
```

5-node pipeline: `process_input -> retrieve_candidates -> rank_and_select -> enrich_context -> generate_email`

## Critical Rule

Campaign email properties come ONLY from the `recommendations` table. Browsing data is for personalization context only.

## Configuration

- Catalog: `serverless_stable_14ey07_catalog`
- Schema: `xome`
- Workspace: fevm (`https://fevm-serverless-stable-14ey07.cloud.databricks.com`)
- SQL Warehouse: `1f01d0f9de5b5108`
- LLM: `databricks-claude-sonnet-4-6`
- Genie Space: `01f1484fd22e1d558c5ed706de7b522d`
- App URL: `https://agent-xome-campaign-7474645414452466.aws.databricksapps.com`

## Common Commands

```bash
# Local dev
uv run start-app

# Deploy
databricks bundle deploy --target prod
databricks apps deploy agent-xome-campaign --profile fevm --source-code-path /Workspace/Users/birbal.das@databricks.com/.bundle/xome_campaign/prod/files

# Run data pipeline
databricks bundle run xome_setup_pipeline --target prod

# Check app status
databricks apps get agent-xome-campaign --profile fevm

# Check logs
databricks apps logs agent-xome-campaign --profile fevm
```

## Data Tables

| Table | Rows | PK | FKs |
|-------|------|----|-----|
| `users` | 500 | `user_id` | - |
| `properties` | 1,000 | `property_id` | - |
| `browsing_activity` | 10,000 | `activity_id` | `user_id` -> users, `property_id` -> properties |
| `recommendations` | 5,000 | `recommendation_id` | `user_id` -> users, `property_id` -> properties |

## Dependencies

Key runtime deps: `fastapi`, `databricks-langchain`, `mlflow>=3.10.0`, `langgraph`, `langchain-mcp-adapters`, `python-dotenv`. Data gen also uses `faker`.
