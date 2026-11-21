"""PlotTwistt FastAPI Main Application."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.cache import (
    PRESETS,
    get_cached_response,
    get_fallback_response,
    save_cached_response,
)
from backend.serpapi_collector import collect_location_signals
from backend.synthesizer import synthesize_friction_report

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plottwistt")

app = FastAPI(
    title="PlotTwistt API",
    description="Land & Civic Friction Radar API for Beyond 9TO5 Buildathon",
    version="1.0.0",
)

# Enable CORS for Vite frontend (http://localhost:5173) and any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Flexible Request Model matching both Frontend UI and SPEC.md
class LocationObj(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = "Bengaluru"


class FlexibleAnalyzeRequest(BaseModel):
    location: Union[str, LocationObj]
    lat: Optional[float] = None
    lng: Optional[float] = None
    intent: str = "warehouse"


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify service availability."""
    return {
        "status": "ok",
        "service": "PlotTwistt Radar API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/presets", status_code=status.HTTP_200_OK)
def get_presets():
    """Return curated reference locations with distinct friction profiles."""
    return PRESETS


@app.post("/api/analyze", status_code=status.HTTP_200_OK)
async def analyze_location(
    request: FlexibleAnalyzeRequest,
    refresh: bool = Query(default=False, description="Bypass cache and force live recalculation"),
):
    """Analyze a location and intent for land, civic, and environmental friction."""
    # Normalize locality name and coordinates
    if isinstance(request.location, str):
        locality = request.location
        lat = request.lat or 12.9716
        lng = request.lng or 77.5946
    else:
        locality = request.location.locality or request.location.address or "Bengaluru"
        lat = request.location.lat or request.lat or 12.9716
        lng = request.location.lng or request.lng or 77.5946

    intent = request.intent.lower()

    # 1. Attempt live SerpApi collection + synthesis
    try:
        logger.info("Executing live SerpApi collector for '%s' (%s)...", locality, intent)
        raw_signals = await collect_location_signals(locality, intent, lat, lng)
        logger.info("Synthesizing %d signals into cited receipt flags...", raw_signals.get("total_signals", 0))
        result = await synthesize_friction_report(locality, intent, raw_signals)
        return result
    except Exception as exc:
        logger.warning(
            "Live analysis pipeline encountered exception (%s: %s). Serving safe demo preset.",
            type(exc).__name__,
            exc,
        )
        # Fallback to rich pre-configured demo analysis matching frontend format
        from backend.cache import get_frontend_compatible_fallback
        return get_frontend_compatible_fallback(locality, intent)
