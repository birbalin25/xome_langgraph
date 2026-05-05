# Xome Campaign Platform

An AI-powered real estate campaign platform that generates personalized emails promoting recommended properties to high-intent buyers. Built with FastAPI on the backend, React + TailwindCSS on the frontend, deployed as a single-process Databricks App.

![Architecture](pipeline_flow.png)

---

## How It Works

1. Use the **filter sidebar** to narrow down by city, state, price range, property type, or buyer segment
2. Click **Search Users** to find matching high-intent buyers (top 20)
3. Select a user from the dropdown — their profile and top 5 recommended properties load automatically
4. Click **Generate Email** — Claude Sonnet 4.6 generates a personalized HTML email with subject line, property showcase, and segment-appropriate messaging
5. Preview the email (HTML or plain text), click property links to see detail modals
6. Click **Save to Volume** to persist the email as a `.txt` file in Unity Catalog

**Critical rule:** Campaign properties come exclusively from the `recommendations` table. Browsing data is used for personalization tone only.

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │         Databricks App (Port 8000)          │
                    │                                             │
 Browser ──────────►│  FastAPI serves:                            │
                    │    ├── /assets/*        (static frontend)   │
                    │    ├── /*               (SPA fallback)      │
                    │    └── /api/campaign/*  (REST API)          │
                    └────────────┬────────────────────────────────┘
                                 │
                    ┌────────────▼────────────────────────────────┐
                    │           Backend Components                │
                    │  campaign_api.py  ←── REST endpoints        │
                    │  email_generator.py ←── prompt + LLM call   │
                    │  tools.py         ←── _execute_sql()        │
                    │  config.py        ←── constants              │
                    └────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
    Claude Sonnet 4.6    Delta Tables          UC Volume
    (Foundation Model)   (users, properties,   (campaign_emails)
                         recommendations,
                         browsing_activity)
```

The app runs as a **single process** — FastAPI on port 8000 serves both the pre-built React frontend (from `frontend/dist/`) and all API endpoints. This is required because Databricks Apps only exposes one port.

**Call chain:** `React UI → campaign_api.py (REST) → email_generator.py → Claude LLM`

---

## Project Structure

```
xome/
├── agent_server/                 # Backend application
│   ├── agent.py                  # LLM setup (_SanitizedChatDatabricks, get_llm)
│   ├── campaign_api.py           # REST API router (/api/campaign/*)
│   ├── email_generator.py        # Email generation logic (prompt building, LLM call, parsing)
│   ├── tools.py                  # SQL execution helper (_execute_sql)
│   ├── prompts.py                # System prompt + email generation template
│   ├── config.py                 # Constants (catalog, schema, warehouse, endpoints, metros)
│   ├── start_server.py           # FastAPI app + static file serving
│   └── __init__.py
├── frontend/                     # React application (Vite + TailwindCSS)
│   ├── package.json              # Dependencies: react, vite, tailwindcss, lucide-react
│   ├── vite.config.ts            # Dev proxy /api → localhost:8000
│   ├── tailwind.config.js        # Xome color palette
│   ├── index.html
│   ├── .npmrc                    # npm registry mirror config
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # Root layout (Header + AppShell)
│       ├── index.css             # Tailwind directives + custom styles
│       ├── types/index.ts        # TypeScript interfaces
│       ├── api/campaign.ts       # Typed fetch wrappers for all REST endpoints
│       ├── lib/utils.ts          # formatPrice, formatDate helpers
│       └── components/
│           ├── layout/
│           │   ├── Header.tsx        # Xome branding bar
│           │   ├── Sidebar.tsx       # Left filter panel container
│           │   └── AppShell.tsx      # Top-level state management + orchestration
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

### REST API (`campaign_api.py`)

FastAPI `APIRouter` with prefix `/api/campaign`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/filters` | Distinct cities, states, property types, segments, price ranges |
| `POST` | `/users` | Top 20 users matching filters (joined with recommendation counts) |
| `GET` | `/users/{id}/profile` | Full user profile |
| `POST` | `/users/{id}/listings` | Top 5 recommended properties (optional city/state filter) |
| `POST` | `/generate-email` | Generate campaign email via Claude LLM |
| `POST` | `/save-email` | Save email to UC Volume |

### Email Generator (`email_generator.py`)

Shared module for prompt construction and LLM invocation:

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

#### UI Layout

```
┌───────────────────────────────────────────────────────────┐
│  Header: Xome Campaign Platform                           │
├──────────────┬────────────────────────────────────────────┤
│ FILTERS      │ [User Dropdown ▼]     [User Profile Card] │
│              │────────────────────────────────────────────│
│ City    [▼]  │ Top Recommended Listings                   │
│ State   [▼]  │ ┌────────┐ ┌────────┐ ┌────────┐         │
│ Price [═══]  │ │  Card  │ │  Card  │ │  Card  │         │
│ Type    [▼]  │ └────────┘ └────────┘ └────────┘         │
│ Segment [▼]  │ ┌────────┐ ┌────────┐                     │
│              │ │  Card  │ │  Card  │                     │
│ [Search      │ └────────┘ └────────┘                     │
│  Users]      │────────────────────────────────────────────│
│              │ [Generate Email] [Save to Volume]          │
│              │ Email Preview (HTML | Plain Text tabs)     │
└──────────────┴────────────────────────────────────────────┘
```

#### Property Cards (Zillow-style)

- Full-width image (from `image_url` column or picsum.photos fallback)
- Status badge: green (Active), yellow (Pending), red pulsing (Auction)
- Price, beds/baths/sqft, address, neighborhood
- Recommendation score progress bar
- Auction banner with date and starting price (for auction listings)

#### Email Preview

- Tabbed view: HTML rendered in sandboxed iframe, plain text in `<pre>` block
- Click interception: injected script intercepts link clicks in the iframe, sends `postMessage` to parent, matches to a property by address, and opens a **PropertyDetailModal** popup instead of navigating away

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
```

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
| App URL | https://agent-xome-campaign-7474645414452466.aws.databricksapps.com |

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

**Backend (Python):** `fastapi`, `uvicorn`, `databricks-langchain`, `databricks-sdk`, `python-dotenv`, `faker` (data gen only)

**Frontend (Node.js):** `react`, `vite`, `tailwindcss`, `lucide-react`, `typescript`

---

## GitHub

Repository: https://github.com/birbalin25/xome_first
