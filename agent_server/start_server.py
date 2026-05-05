from pathlib import Path

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from mlflow.genai.agent_server import AgentServer, setup_mlflow_git_based_version_tracking

# Load env vars from .env before importing the agent for proper auth
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

# Need to import the agent to register the functions with the server
import agent_server.agent  # noqa: E402

agent_server = AgentServer("ResponsesAgent", enable_chat_proxy=False)

# Define the app as a module level variable to enable multiple workers
app = agent_server.app  # noqa: F841

from agent_server.campaign_api import router as campaign_router  # noqa: E402
app.include_router(campaign_router)

# Serve the built frontend static files from frontend/dist/
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # Mount static assets (JS, CSS, images) under /assets
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

    # SPA fallback: serve index.html for any non-API, non-file route
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Try to serve the exact file from dist/ first (e.g. favicon.ico)
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise serve index.html for SPA client-side routing
        index_file = FRONTEND_DIST / "index.html"
        if index_file.is_file():
            return HTMLResponse(index_file.read_text())
        return HTMLResponse("<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>", status_code=500)

setup_mlflow_git_based_version_tracking()


def main():
    agent_server.run(app_import_string="agent_server.start_server:app")
