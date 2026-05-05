"""REST API router for the campaign dashboard UI."""

import io
import logging
from datetime import datetime
from typing import Optional

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_server.config import CATALOG, SCHEMA, VOLUME_NAME
from agent_server.email_generator import generate_campaign_email, parse_email_response
from agent_server.tools import _execute_sql

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/campaign", tags=["campaign"])

_ws = WorkspaceClient()


# ── Pydantic request/response models ──────────────────────────────────────────


class UserFilterRequest(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    property_type: Optional[str] = None
    segment: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None


class ListingsRequest(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None


class GenerateEmailRequest(BaseModel):
    user_id: str
    properties: list[dict]


class SaveEmailRequest(BaseModel):
    user_id: str
    subject: str
    html: str
    plain_text: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/filters")
async def get_filters():
    """Return distinct filter values from the database."""
    try:
        cities = _execute_sql(f"SELECT DISTINCT city FROM {CATALOG}.{SCHEMA}.properties ORDER BY city")
        states = _execute_sql(f"SELECT DISTINCT state FROM {CATALOG}.{SCHEMA}.properties ORDER BY state")
        property_types = _execute_sql(
            f"SELECT DISTINCT property_type FROM {CATALOG}.{SCHEMA}.properties ORDER BY property_type"
        )
        segments = _execute_sql(
            f"SELECT DISTINCT user_segment FROM {CATALOG}.{SCHEMA}.users ORDER BY user_segment"
        )
        prices = _execute_sql(
            f"SELECT MIN(price) as min_price, MAX(price) as max_price FROM {CATALOG}.{SCHEMA}.properties"
        )

        return {
            "cities": [r["city"] for r in cities if r.get("city")],
            "states": [r["state"] for r in states if r.get("state")],
            "property_types": [r["property_type"] for r in property_types if r.get("property_type")],
            "segments": [r["user_segment"] for r in segments if r.get("user_segment")],
            "price_range": {
                "min": float(prices[0]["min_price"]) if prices else 0,
                "max": float(prices[0]["max_price"]) if prices else 5000000,
            },
        }
    except Exception as e:
        logger.exception("Failed to fetch filters")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def search_users(req: UserFilterRequest):
    """Return top 20 active users matching the given filters."""
    where = ["u.is_active = true"]

    if req.city:
        where.append(f"u.preferred_city = '{req.city}'")
    if req.state:
        where.append(f"u.preferred_state = '{req.state}'")
    if req.property_type:
        where.append(f"u.preferred_property_type = '{req.property_type}'")
    if req.segment:
        where.append(f"u.user_segment = '{req.segment}'")
    if req.price_min is not None:
        where.append(f"u.budget_max >= {req.price_min}")
    if req.price_max is not None:
        where.append(f"u.budget_min <= {req.price_max}")

    where_str = " AND ".join(where)

    query = f"""
    SELECT u.user_id, u.first_name, u.last_name, u.email,
           u.preferred_city, u.preferred_state, u.user_segment,
           u.budget_min, u.budget_max, u.preferred_property_type,
           COUNT(r.recommendation_id) AS rec_count
    FROM {CATALOG}.{SCHEMA}.users u
    LEFT JOIN {CATALOG}.{SCHEMA}.recommendations r
        ON u.user_id = r.user_id AND r.is_active = true
    WHERE {where_str}
    GROUP BY u.user_id, u.first_name, u.last_name, u.email,
             u.preferred_city, u.preferred_state, u.user_segment,
             u.budget_min, u.budget_max, u.preferred_property_type
    ORDER BY rec_count DESC
    LIMIT 20
    """
    try:
        rows = _execute_sql(query)
        return {"users": rows}
    except Exception as e:
        logger.exception("Failed to search users")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Return full profile for a single user."""
    query = f"""
    SELECT user_id, first_name, last_name, email, phone,
           preferred_city, preferred_state, budget_min, budget_max,
           preferred_property_type, preferred_beds_min,
           signup_date, is_active, user_segment
    FROM {CATALOG}.{SCHEMA}.users
    WHERE user_id = '{user_id}'
    LIMIT 1
    """
    try:
        rows = _execute_sql(query)
        if not rows:
            raise HTTPException(status_code=404, detail="User not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch user profile")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/listings")
async def get_user_listings(user_id: str, req: ListingsRequest):
    """Return top 5 recommended properties for a user."""
    where = [f"r.user_id = '{user_id}'", "r.is_active = true"]
    if req.city:
        where.append(f"p.city = '{req.city}'")
    if req.state:
        where.append(f"p.state = '{req.state}'")
    where_str = " AND ".join(where)

    query = f"""
    SELECT r.recommendation_id, r.recommendation_score, r.recommendation_reason,
           r.generated_at,
           p.property_id, p.address, p.city, p.state, p.zip_code,
           p.price, p.beds, p.baths, p.sqft, p.property_type,
           p.year_built, p.school_rating, p.neighborhood,
           p.listing_status, p.days_on_market,
           p.auction_date, p.auction_start_price,
           p.hoa_fee, p.description, p.image_url
    FROM {CATALOG}.{SCHEMA}.recommendations r
    JOIN {CATALOG}.{SCHEMA}.properties p ON r.property_id = p.property_id
    WHERE {where_str}
    ORDER BY r.recommendation_score DESC
    LIMIT 5
    """
    try:
        rows = _execute_sql(query)
        return {"properties": rows}
    except Exception as e:
        logger.exception("Failed to fetch listings")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-email")
async def generate_email(req: GenerateEmailRequest):
    """Generate a campaign email for the given user + properties."""
    from agent_server.agent import get_llm

    # Fetch full profile
    profile_rows = _execute_sql(f"""
        SELECT user_id, first_name, last_name, email, phone,
               preferred_city, preferred_state, budget_min, budget_max,
               preferred_property_type, preferred_beds_min,
               signup_date, is_active, user_segment
        FROM {CATALOG}.{SCHEMA}.users
        WHERE user_id = '{req.user_id}'
        LIMIT 1
    """)
    if not profile_rows:
        raise HTTPException(status_code=404, detail="User not found")

    profile = profile_rows[0]

    # Fetch browsing context
    browsing_rows = _execute_sql(f"""
        SELECT b.activity_type, b.activity_timestamp, b.session_duration_seconds,
               b.search_query, b.device_type, b.referral_source,
               p.address, p.city, p.state, p.price, p.property_type,
               p.beds, p.neighborhood
        FROM {CATALOG}.{SCHEMA}.browsing_activity b
        JOIN {CATALOG}.{SCHEMA}.properties p ON b.property_id = p.property_id
        WHERE b.user_id = '{req.user_id}'
        ORDER BY b.activity_timestamp DESC
        LIMIT 20
    """)

    try:
        llm = get_llm()
        result = await generate_campaign_email(llm, profile, req.properties, browsing_rows)
        return result
    except Exception as e:
        logger.exception("Failed to generate email")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-email")
async def save_email(req: SaveEmailRequest):
    """Save the generated email as a .txt file to a Unity Catalog Volume."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"campaign_{req.user_id}_{timestamp}.txt"
    volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}/{filename}"

    content = f"SUBJECT: {req.subject}\n\nHTML:\n{req.html}\n\nPLAIN TEXT:\n{req.plain_text}"

    try:
        _ws.files.upload(
            file_path=volume_path,
            contents=io.BytesIO(content.encode("utf-8")),
            overwrite=True,
        )
        return {"path": volume_path, "filename": filename}
    except Exception as e:
        logger.exception("Failed to save email to Volume")
        raise HTTPException(status_code=500, detail=str(e))
