# Xome Campaign Platform

An AI-powered real estate campaign platform that generates personalized emails promoting recommended properties to high-intent buyers. Built with FastAPI on the backend, React + TailwindCSS on the frontend, LangGraph for pipeline orchestration, deployed as a single-process Databricks App.

![Architecture](pipeline_flow.png)

---

## How It Works

### Dashboard Mode

1. Use the **filter sidebar** to narrow down by city, state, price range, property type, buyer segment, and **top listings count** (1–30)
2. Click **Search Users** to find matching high-intent buyers (top 20)
3. Select a user from the dropdown — their profile banner and recommended properties load automatically
4. **Click properties to select/deselect** them (all selected by default, with a "Select All" checkbox). Only selected properties are included in the campaign email
5. Click **Generate Email** — the LangGraph pipeline runs with the user profile and selected properties already passed from the UI (no redundant DB queries), fetches browsing history for personalization, and Claude Sonnet 4.6 generates a personalized HTML email
6. Preview the email (HTML or plain text), click property links to see detail modals
7. Click **Save to Volume** to persist the email as a `.txt` file in Unity Catalog and record each property in the `campaign_tracking` table
8. Properties that have been sent in a campaign display a **"Campaign sent on {date}"** banner

### Chat Mode

1. Switch to the **Chat** tab via the header toggle
2. Type a natural language request, e.g. "Generate a campaign email for USER_001" or "Generate email for USER_042 in Austin"
3. The LangGraph pipeline extracts the user ID (and optional city/state), runs the full pipeline autonomously, and returns a reply with an inline email preview
4. The generated email is displayed in both the chat conversation and a sidebar preview panel

**Critical rule:** Campaign properties come exclusively from the `recommendations` table. Browsing data is used for personalization tone only.

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │         Databricks App (Port 8000)          │
                    │                                             │
 Browser ──────────►│  FastAPI serves:                            │
                    │    ├── /assets/*           (static frontend) │
                    │    ├── /*                  (SPA fallback)    │
                    │    ├── /api/campaign/*     (REST API)        │
                    │    ├── /api/chat/message   (Chat API)        │
                    │    └── /invocations        (MLflow compat)   │
                    └────────────┬────────────────────────────────┘
                                 │
                    ┌────────────▼────────────────────────────────┐
                    │        LangGraph StateGraph                  │
                    │                                              │
                    │  process_input → retrieve_candidates →       │
                    │  rank_and_select → enrich_context →          │
                    │  generate_email → END                        │
                    │       |                  |                    │
                    │       +--[error]--→ handle_error → END       │
                    └────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
    Claude Sonnet 4.6    Delta Tables          UC Volume
    (Foundation Model)   (users, properties,   (campaign_emails)
                         recommendations,
                         browsing_activity,
                         campaign_tracking)
```

The app runs as a **single process** — FastAPI on port 8000 serves both the pre-built React frontend (from `frontend/dist/`) and all API endpoints. This is required because Databricks Apps only exposes one port.

**Dashboard call chain:** `React UI → campaign_api.py → LangGraph (source=dashboard, profile+properties from UI) → email_generator.py → Claude LLM`
**Chat call chain:** `React UI → chat_api.py → LangGraph (source=chat, fetches profile+properties from DB) → email_generator.py → Claude LLM`

---

## LangGraph Pipeline

Both Dashboard and Chat modes share the same `StateGraph`:

| Node | Purpose | Dashboard | Chat |
|------|---------|-----------|------|
| `process_input` | Extract user_id, fetch profile | **Skips DB query** — uses `user_profile` from UI | Parses `raw_message` via regex/LLM fallback, fetches profile from DB |
| `retrieve_candidates` | Fetch recommended properties | **Skips DB query** — uses `properties_input` from UI | Full DB query with optional city/state filter |
| `rank_and_select` | Sort by score, pick top N | **Pass-through** (already selected by user in UI) | Full sort, pick top N |
| `enrich_context` | Fetch last 20 browsing activities | DB query (only node that reads from DB) | Same — DB query |
| `generate_email` | Call Claude LLM | Returns email result | Also builds `chat_response` summary |
| `handle_error` | Format error message | Returns error detail | Sets `chat_response` with error |

---

## Project Structure

```
xome/
├── agent_server/                 # Backend application
│   ├── agent.py                  # LLM setup (_SanitizedChatDatabricks, get_llm)
│   ├── campaign_api.py           # REST API router (/api/campaign/*)
│   ├── chat_api.py               # Chat API router (/api/chat/*)
│   ├── graph_state.py            # LangGraph CampaignState TypedDict
│   ├── graph_nodes.py            # LangGraph node functions
│   ├── graph.py                  # LangGraph StateGraph definition + compilation
│   ├── email_generator.py        # Email generation logic (prompt building, LLM call, parsing)
│   ├── tools.py                  # SQL execution helper (_execute_sql)
│   ├── prompts.py                # System prompt + email generation + extraction templates
│   ├── config.py                 # Constants (catalog, schema, warehouse, endpoints, metros)
│   ├── start_server.py           # FastAPI app + routers + /invocations + static file serving
│   └── __init__.py
├── frontend/                     # React application (Vite + TailwindCSS)
│   ├── package.json              # Dependencies: react, vite, tailwindcss, lucide-react
│   ├── vite.config.ts            # Dev proxy /api → localhost:8000
│   ├── tailwind.config.js        # Xome color palette
│   ├── index.html
│   ├── .npmrc                    # npm registry mirror config
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # Root layout (Header + view switching: AppShell / ChatPanel)
│       ├── index.css             # Tailwind directives + custom styles
│       ├── types/index.ts        # TypeScript interfaces (incl. ChatMessage)
│       ├── api/
│       │   ├── campaign.ts       # Typed fetch wrappers for campaign REST endpoints
│       │   └── chat.ts           # Typed fetch wrapper for chat endpoint
│       ├── lib/utils.ts          # formatPrice, formatDate helpers
│       └── components/
│           ├── layout/
│           │   ├── Header.tsx        # Xome branding bar + Dashboard/Chat toggle
│           │   ├── Sidebar.tsx       # Left filter panel container
│           │   └── AppShell.tsx      # Dashboard: state management + orchestration
│           ├── chat/
│           │   ├── ChatPanel.tsx     # Chat conversation + input + email preview sidebar
│           │   └── ChatMessage.tsx   # Individual message bubble (user/assistant)
│           ├── filters/
│           │   ├── FilterPanel.tsx   # City, State, Price Range, Property Type, Segment
│           │   └── metros.ts        # City-to-state mapping for filter cascade
│           ├── users/
│           │   ├── UserDropdown.tsx      # Searchable dropdown, top 20 users
│           │   └── UserProfileCard.tsx   # Selected user summary card
│           ├── properties/
│           │   ├── PropertyCard.tsx      # Zillow-style card with image, price, stats, score bar
│           │   ├── PropertyGrid.tsx      # Responsive grid layout
│           │   └── PropertyDetailModal.tsx  # Detail popup from email links
│           └── email/
│               ├── EmailPreview.tsx  # Tabbed HTML/PlainText preview with click interception
│               └── EmailActions.tsx  # Generate + Save buttons with status indicators
├── notebooks/
│   ├── 01_generate_data.py       # Synthetic data generation (4 Delta tables, PK/FK constraints)
│   └── 02_genie_setup_instructions.py  # 10 SQL queries + Genie Space setup guide
├── scripts/
│   ├── quickstart.py             # Interactive setup (auth, MLflow experiment)
│   ├── start_app.py              # Concurrent frontend dev + backend launcher
│   └── discover_tools.py         # Databricks tool/resource discovery
├── databricks.yml                # Bundle config (app + job)
├── app.yaml                      # Databricks Apps runtime config (single process)
├── pyproject.toml                # Python dependencies and entry points
├── pipeline_flow.mmd             # Architecture diagram (Mermaid source)
└── pipeline_flow.png             # Architecture diagram (rendered)
```

---

## Key Components

### LangGraph Pipeline (`graph.py`, `graph_state.py`, `graph_nodes.py`)

The `CampaignState` TypedDict flows through a `StateGraph` with nodes for input processing, candidate retrieval, ranking, context enrichment, and email generation. A `source` field (`"dashboard"` or `"chat"`) controls behavior differences at each node.

### REST API (`campaign_api.py`)

FastAPI `APIRouter` with prefix `/api/campaign`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/filters` | Distinct cities, states, property types, segments, price ranges |
| `POST` | `/users` | Top 20 users matching filters (joined with recommendation counts) |
| `GET` | `/users/{id}/profile` | Full user profile |
| `POST` | `/users/{id}/listings` | Top N recommended properties with campaign tracking status (configurable 1–30, LEFT JOIN campaign_tracking) |
| `POST` | `/generate-email` | Generate campaign email via LangGraph (source=dashboard, accepts user_profile + properties from UI) |
| `POST` | `/save-email` | Save email to UC Volume + insert tracking rows into campaign_tracking |

### Chat API (`chat_api.py`)

FastAPI `APIRouter` with prefix `/api/chat`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/message` | Natural language chat → LangGraph (source=chat) → reply + email |

### MLflow-Compatible Endpoint

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/invocations` | Accepts `{messages: [{role, content}]}`, routes to LangGraph |

### Email Generator (`email_generator.py`)

Module for prompt construction and LLM invocation:

- `build_properties_section(properties)` — Format property details for the prompt
- `build_browsing_section(browsing)` — Format browsing activity for personalization
- `format_email_prompt(profile, properties, browsing)` — Build full LLM prompt
- `generate_campaign_email(llm, profile, properties, browsing)` — Invoke Claude and return parsed result
- `parse_email_response(raw)` — Parse `SUBJECT` / `HTML` / `PLAIN TEXT` sections from LLM output

### SQL Helper (`tools.py`)

`_execute_sql(query)` — Executes SQL against the Databricks SQL Warehouse via `WorkspaceClient.statement_execution.execute_statement()` and returns results as a list of dicts.

### LLM Setup (`agent.py`)

`get_llm()` — Returns a `_SanitizedChatDatabricks` instance (a `ChatDatabricks` subclass that strips `id` fields from tool message content blocks for Claude compatibility on Databricks Foundation Model API).

### Frontend

#### UI Layout — Dashboard Mode

```
┌───────────────────────────────────────────────────────────┐
│  Header: Xome Campaign Platform    [Dashboard] [Chat]      │
├──────────────┬────────────────────────────────────────────┤
│ FILTERS      │ [User Dropdown ▼]                          │
│              │ [User Profile Banner — name, segment,      │
│ City    [▼]  │  email, location, budget, preferences]     │
│ State   [▼]  │────────────────────────────────────────────│
│ Price [═══]  │ Top Recommended Listings    [☑ Select All] │
│ Listings[══] │ ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│ Type    [▼]  │ │ ☑ Card  │ │ ☑ Card  │ │ ☐ Card  │      │
│ Segment [▼]  │ └─────────┘ └─────────┘ └─────────┘      │
│              │ ┌─────────┐ ┌─────────┐                    │
│ [Search      │ │ ☑ Card  │ │ ☑ Card  │  (click to        │
│  Users]      │ └─────────┘ └─────────┘   select/deselect) │
│              │────────────────────────────────────────────│
│              │ [Generate Email] [Save to Volume]          │
│              │ Email Preview (HTML | Plain Text tabs)     │
└──────────────┴────────────────────────────────────────────┘
```

#### UI Layout — Chat Mode

```
┌───────────────────────────────────────────────────────────┐
│  Header: Xome Campaign Platform    [Dashboard] [Chat]      │
├───────────────────────────────────┬────────────────────────┤
│  Chat Messages                    │ Latest Email Preview   │
│  ┌───────────────────────────┐   │                        │
│  │ User: Generate email for  │   │ Subject: ...           │
│  │       USER_001            │   │ [HTML] [Plain Text]    │
│  └───────────────────────────┘   │                        │
│  ┌───────────────────────────┐   │ (rendered email)       │
│  │ Assistant: I've generated │   │                        │
│  │ a campaign email...       │   │                        │
│  │ [Inline Email Preview]    │   │                        │
│  └───────────────────────────┘   │                        │
│                                   │                        │
│  ┌──────────────────────┐ [Send] │                        │
│  │ Type a message...     │       │                        │
│  └──────────────────────┘        │                        │
└───────────────────────────────────┴────────────────────────┘
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
                                 ├── image_url (picsum.photos)
        │                        └── description
        ▼                              │
browsing_activity (10,000)     recommendations (5,000)
  PK: activity_id                PK: recommendation_id
  FK: user_id -> users           FK: user_id -> users
  FK: property_id -> properties  FK: property_id -> properties
  ├── activity_type              ├── recommendation_score (0.0-1.0)
  ├── session_duration           ├── recommendation_reason
  └── device_type, referral      └── model_version, is_active

campaign_tracking
  FK: user_id -> users
  FK: property_id -> properties
  ├── recommendation_id
  ├── campaign_date (DATE)
  └── campaign_status (BOOLEAN)
```

The `campaign_tracking` table is created automatically at app startup. It records which user+property combinations have been sent in campaign emails. The listings endpoint LEFT JOINs this table to show "Campaign sent on {date}" banners in the UI.

All tables are stored as Delta tables in Unity Catalog: `serverless_stable_14ey07_catalog.xome.*`

---

## Configuration

| Setting | Value |
|---------|-------|
| Catalog | `serverless_stable_14ey07_catalog` |
| Schema | `xome` |
| Workspace | fevm (`https://fevm-serverless-stable-14ey07.cloud.databricks.com`) |
| SQL Warehouse | `1f01d0f9de5b5108` |
| LLM Endpoint | `databricks-claude-sonnet-4-6` |
| UC Volume | `campaign_emails` (for saved email files) |
| App URL | https://agent-xome-langgraph-campaign-7474645414452466.aws.databricksapps.com |

---

## How to Run

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js 20+](https://nodejs.org/) and npm
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.283.0+
- A Databricks workspace with access to Foundation Model APIs

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/birbalin25/xome_first.git
cd xome_first

# 2. Create .env from template
cp .env.example .env
# Edit .env: set DATABRICKS_CONFIG_PROFILE=fevm

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Start the app (backend on :8000, frontend dev on :3000 with API proxy)
uv run start-app
```

Open http://localhost:8000 in your browser. During local development, the Vite dev server runs on port 3000 and proxies `/api` requests to port 8000.

### Build Frontend for Production

```bash
cd frontend && npm run build && cd ..
```

This creates `frontend/dist/` which FastAPI serves as static files in production.

### Test the REST API

```bash
# Get filter options
curl http://localhost:8000/api/campaign/filters

# Search users with filters
curl -X POST http://localhost:8000/api/campaign/users \
  -H "Content-Type: application/json" \
  -d '{"city": "Austin", "state": "TX"}'

# Get user profile
curl http://localhost:8000/api/campaign/users/USER_001/profile

# Get top recommended listings
curl -X POST http://localhost:8000/api/campaign/users/USER_001/listings \
  -H "Content-Type: application/json" \
  -d '{"city": "Austin", "state": "TX"}'

# Chat interface
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate a campaign email for USER_001"}'

# MLflow-compatible invocations
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Generate email for USER_001"}]}'
```

### Deploy to Databricks

```bash
# Build frontend first
cd frontend && npm run build && cd ..

# Validate the bundle
databricks bundle validate --target prod

# Deploy resources (app + job)
databricks bundle deploy --target prod

# Deploy app source code
databricks apps deploy agent-xome-langgraph-campaign --profile fevm \
  --source-code-path /Workspace/Users/birbal.das@databricks.com/.bundle/xome_langgraph_campaign/prod/files

# Generate synthetic data (run once)
databricks bundle run xome_setup_pipeline --target prod
```

### Check App Status

```bash
# Status
databricks apps get agent-xome-langgraph-campaign --profile fevm

# Logs
databricks apps logs agent-xome-langgraph-campaign --profile fevm
```

---

## Notebooks

### `01_generate_data.py` — Synthetic Data Generation

Generates 4 Delta tables using Faker with:
- City-calibrated budgets and property prices
- Realistic browsing patterns (70% in preferred city)
- ML-scored recommendations with template explanations
- Valid image URLs via picsum.photos
- Primary keys and foreign key constraints

### `02_genie_setup_instructions.py` — Genie Space Queries

10 SQL analytics queries: most active users, price analysis by city/type, upcoming auctions, lapsed users for targeting, recommendation performance, browsing-to-bid conversion, property interest rankings, segment behavior comparison, device/channel engagement, auction vs standard performance.

---

## Dependencies

**Backend (Python):** `fastapi`, `uvicorn`, `databricks-langchain`, `databricks-sdk`, `python-dotenv`, `langgraph`, `faker` (data gen only)

**Frontend (Node.js):** `react`, `vite`, `tailwindcss`, `lucide-react`, `typescript`

---

## GitHub

Repositories:
- https://github.com/birbalin25/xome_first
- https://github.com/birbalin25/xome_langgraph
