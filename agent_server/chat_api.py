"""REST API router for the chat interface."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    email: dict | None = None


@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    """Process a chat message through the LangGraph campaign pipeline."""
    from agent_server.graph import campaign_graph

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        result = await campaign_graph.ainvoke({
            "raw_message": req.message,
            "source": "chat",
        })

        reply = result.get("chat_response") or result.get("error") or "Something went wrong."
        email = result.get("generated_email")

        return ChatResponse(reply=reply, email=email)
    except Exception as e:
        logger.exception("Chat pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
