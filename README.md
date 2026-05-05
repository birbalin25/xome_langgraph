# Xome Agentic Email & Personalized Communication Platform

An AI-powered campaign platform that sends personalized emails promoting recommended properties to high-intent real estate buyers. Built with LangGraph, deployed as a Databricks App with a Next.js chat interface.

![Pipeline Flow](pipeline_flow.png)

## How It Works

1. You open the chat UI and ask: _"Generate a campaign email for user `<user_id>`"_
2. The agent extracts the user ID, fetches their profile from the `users` table
3. It pulls recommended properties from the `recommendations` table (the **only** source for campaign properties)
4. It ranks them by recommendation score and picks the top 5
5. It fetches recent browsing activity for personalization context
6. Claude Sonnet 4.6 generates a personalized HTML email with subject line, property showcase, and segment-appropriate messaging

**Critical rule:** Campaign properties come exclusively from the recommendation engine. Browsing data is used for personalization tone only.

---

## Project Structure

```
xome/
├── agent_server/              # Core agent application
│   ├── agent.py               # LangGraph StateGraph (5 nodes, conditional edges)
│   ├── tools.py               # SQL-backed tools (get_user_profile, get_recommendations, get_browsing_context)
│   ├── prompts.py             # System prompt + email generation template
│   ├── config.py              # Constants (catalog, schema, warehouse, endpoints)
│   ├── utils.py               # Auth helpers, stream processing, _SanitizedChatDatabricks
│   ├── start_server.py        # FastAPI + MLflow AgentServer entry point
│   └── __init__.py
├── notebooks/
│   ├── 01_generate_data.py    # Synthetic data generation (4 Delta tables, PK/FK constraints)
│   └── 02_genie_setup_instructions.py  # 10 SQL queries + Genie Space setup guide
├── scripts/
│   ├── quickstart.py          # Interactive setup (auth, MLflow experiment)
│   ├── start_app.py           # Concurrent frontend + backend launcher
│   └── discover_tools.py      # Databricks tool/resource discovery
├── databricks.yml             # Bundle config (app + experiment + job + Genie Space)
├── app.yaml                   # Databricks Apps runtime config
├── pyproject.toml             # Python dependencies and entry points
├── requirements.txt           # Contains "uv" (actual deps in pyproject.toml)
├── .env.example               # Environment variable template
├── pipeline_flow.png          # Architecture diagram
└── pipeline_flow.mmd          # Mermaid source for the diagram
```

---

## Key Components

### `agent_server/agent.py` — LangGraph Pipeline

The core of the application. Implements a custom `StateGraph` with 5 nodes and conditional error routing:

| Node | Purpose | Tools/APIs Used |
|------|---------|-----------------|
| `process_input` | Parses user message with LLM to extract `user_id`, fetches user profile | Claude Sonnet 4.6 (extraction), `get_user_profile` |
| `retrieve_candidates` | Fetches recommended properties from the recommendations table | `get_recommendations` |
| `rank_and_select` | Sorts candidates by `recommendation_score`, picks top 5 | Pure logic (no external calls) |
| `enrich_context` | Fetches recent browsing activity for personalization | `get_browsing_context` |
| `generate_email` | Generates HTML + plain text campaign email | Claude Sonnet 4.6 (generation) |

Error handling routes to `handle_error` if: no valid user ID found, user not found in DB, or no recommendations exist.

The state flows through `CampaignState` (a `TypedDict`) carrying: `messages`, `user_profile`, `candidate_properties`, `top_5_properties`, `browsing_context`, `campaign_email`, and `error`.

Also includes `_SanitizedChatDatabricks` — a `ChatDatabricks` subclass that strips `id` fields from tool message content blocks, required for Claude compatibility on Databricks Foundation Model API.

The `@invoke()` and `@stream()` decorators register handlers with MLflow's Responses API for both synchronous and streaming access.

### `agent_server/tools.py` — SQL-Backed Tools

Three `@tool`-decorated functions that query Delta tables via the Databricks SQL Statement Execution API:

- **`get_user_profile(user_id)`** — Single-row lookup from `users` table. Returns profile with preferences, budget, segment.
- **`get_recommendations(user_id, city, state, limit)`** — JOINs `recommendations` with `properties`. Filters by active recommendations and optional city/state. Sorted by `recommendation_score DESC`. This is the **only** source for campaign properties.
- **`get_browsing_context(user_id)`** — JOINs `browsing_activity` with `properties`. Returns recent activity with a summary of activity types, cities browsed, and property types viewed. For personalization context only.

All tools use a shared `_execute_sql()` helper that calls `WorkspaceClient.statement_execution.execute_statement()` against the configured SQL warehouse.

### `agent_server/prompts.py` — LLM Prompts

Two templates:

- **`SYSTEM_PROMPT`** — Defines the agent's identity as the "Xome Campaign Agent", the 6-step workflow, and critical rules about recommendation-only property sourcing.
- **`EMAIL_GENERATION_PROMPT`** — A structured template with placeholders for user profile, top 5 properties (with all details including auction info), and browsing context. Instructs Claude to generate segment-appropriate messaging (first-time buyer = encouraging, investor = ROI-focused, upgrader = aspirational, downsizer = practical).

### `agent_server/config.py` — Configuration

All constants in one place: catalog name, schema, SQL warehouse ID, LLM endpoint, Genie Space ID, and a `METROS` dictionary defining 10 US cities with base property prices.

### `agent_server/utils.py` — Utilities

- **`process_agent_astream_events()`** — Converts LangGraph stream events to MLflow `ResponsesAgentStreamEvent` format. Filters out `ToolMessage` and intermediate `AIMessage` with tool calls, only yielding final text responses to the UI.
- **`get_user_workspace_client()`** — Creates a `WorkspaceClient` using the forwarded access token for on-behalf-of (OBO) authentication when deployed.
- **`get_databricks_host_from_env()`** — Extracts workspace URL from SDK config.

### `agent_server/start_server.py` — Server Entry Point

Loads `.env`, imports the agent module (which registers `@invoke`/`@stream` handlers), creates an MLflow `AgentServer` with chat proxy enabled, and exposes the FastAPI `app` for uvicorn.

### `notebooks/01_generate_data.py` — Synthetic Data Generation

Databricks notebook that generates 4 Delta tables using Faker:

| Table | Rows | Description |
|-------|------|-------------|
| `users` | 500 | Buyers with city-calibrated budgets, property type preferences, segments (first_time_buyer/investor/upgrader/downsizer) |
| `properties` | 1,000 | Listings with realistic pricing by city and type, neighborhoods, school ratings, auction data, valid image URLs via picsum.photos |
| `browsing_activity` | 10,000 | User interactions (view/save/search/share/bid) with realistic city affinity (70% in preferred city) |
| `recommendations` | 5,000 | Computed scores based on budget/city/type/beds match with template explanations |

After data generation, the notebook sets:
- **Primary keys** on all ID columns (with `NOT NULL` constraints)
- **Foreign keys** linking `browsing_activity` and `recommendations` back to `users` and `properties`

### `notebooks/02_genie_setup_instructions.py` — Genie Space Setup

Contains 10 SQL analytics queries for the Genie Space:

1. Most active users in the last 30 days
2. Average property prices by city and type
3. Upcoming auctions in the next 14 days
4. Lapsed high-intent users (campaign targeting)
5. Recommendation performance by city
6. Browsing-to-bid conversion funnel
7. Properties with most user interest
8. User segment behavior comparison
9. Device and channel engagement analysis
10. Auction vs standard listing performance

### `databricks.yml` — Bundle Configuration

Defines:
- **App resource** (`agent-xome-campaign`) with permissions for the MLflow experiment, SQL warehouse, and Genie Space
- **MLflow experiment** for tracing
- **Job** (`xome_setup_pipeline`) for running the data generation notebook on serverless compute
- **Targets**: `dev` (local development) and `prod` (fevm workspace)

### `scripts/` — Helper Scripts

- **`quickstart.py`** — Interactive first-time setup: validates prerequisites (uv, node, databricks CLI), authenticates with Databricks OAuth, creates MLflow experiment, writes `.env` config.
- **`start_app.py`** — Runs backend (FastAPI agent server) and frontend (Next.js chat app) concurrently. Clones the `e2e-chatbot-app-next` template if needed, monitors both processes, reports when both are ready.
- **`discover_tools.py`** — Scans the workspace for available UC functions, tables, vector search indexes, Genie spaces, and MCP servers. Useful for finding resources to connect to the agent.

---

## Configuration

| Setting | Value |
|---------|-------|
| Catalog | `serverless_stable_14ey07_catalog` |
| Schema | `xome` |
| Workspace | fevm (`https://fevm-serverless-stable-14ey07.cloud.databricks.com`) |
| SQL Warehouse | `1f01d0f9de5b5108` |
| LLM Endpoint | `databricks-claude-sonnet-4-6` |
| Genie Space | `01f1484fd22e1d558c5ed706de7b522d` |
| App URL | https://agent-xome-campaign-7474645414452466.aws.databricksapps.com |

---

## How to Run

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js 20+](https://nodejs.org/) and npm
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.283.0+
- A Databricks workspace with access to Foundation Model APIs

### Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/birbalin25/xome_first.git
cd xome_first

# 2. Create .env from template
cp .env.example .env
# Edit .env: set DATABRICKS_CONFIG_PROFILE=fevm

# 3. Run quickstart (sets up auth + MLflow experiment)
uv run quickstart --profile fevm

# 4. Start the app (backend on :8000, frontend on :3000)
uv run start-app
```

Open http://localhost:3000 in your browser.

### Test the Backend Directly

```bash
# Get a sample user_id
databricks api post /api/2.0/sql/statements --profile fevm --json '{
  "warehouse_id": "1f01d0f9de5b5108",
  "statement": "SELECT user_id, first_name, preferred_city FROM serverless_stable_14ey07_catalog.xome.users LIMIT 3",
  "wait_timeout": "30s"
}'

# Call the agent
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"input": [{"role": "user", "content": "Generate a campaign email for user <USER_ID>"}]}'
```

### Deploy to Databricks

```bash
# Validate the bundle
databricks bundle validate --target prod

# Deploy resources (app, experiment, job)
databricks bundle deploy --target prod

# Deploy app source code
databricks apps deploy agent-xome-campaign --profile fevm \
  --source-code-path /Workspace/Users/birbal.das@databricks.com/.bundle/xome_campaign/prod/files

# Generate synthetic data (run once)
databricks bundle run xome_setup_pipeline --target prod
```

### Check App Status

```bash
# Status
databricks apps get agent-xome-campaign --profile fevm

# Logs
databricks apps logs agent-xome-campaign --profile fevm
```

---

## Data Model

```
users (500)                    properties (1,000)
  PK: user_id                    PK: property_id
  ├── preferred_city             ├── city, state, neighborhood
  ├── budget_min/max             ├── price, beds, baths, sqft
  ├── preferred_property_type    ├── listing_status (active/pending/auction/sold)
  └── user_segment               ├── auction_date, auction_start_price
                                 └── image_url (picsum.photos)
        │                              │
        ▼                              ▼
browsing_activity (10,000)     recommendations (5,000)
  PK: activity_id                PK: recommendation_id
  FK: user_id -> users           FK: user_id -> users
  FK: property_id -> properties  FK: property_id -> properties
  ├── activity_type              ├── recommendation_score (0.0-1.0)
  ├── session_duration           ├── recommendation_reason
  └── device_type, referral      └── model_version, is_active
```

---

## GitHub

Repository: https://github.com/birbalin25/xome_first
