"""PlotTwistt FastAPI Main Application."""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware

from backend.cache import (
    PRESETS,
    get_cached_response,
    get_fallback_response,
    save_cached_response,
)
from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    PresetItem,
)
from backend.serpapi_collector import collect_location_signals
from backend.synthesizer import synthesize_friction

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plottwistt")

app = FastAPI(
    title="PlotTwistt API",
    description="Land & Civic Friction Radar API for Beyond 9TO5 Buildathon",
    version="0.1.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint to verify service availability."""
    return {
        "status": "ok",
        "service": "PlotTwistt Radar API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/presets", response_model=List[PresetItem], status_code=status.HTTP_200_OK)
def get_presets():
    """Return curated reference locations with distinct friction profiles."""
    return PRESETS


@app.post("/api/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_location(
    request: AnalyzeRequest,
    refresh: bool = Query(default=False, description="Bypass cache and force recalculation"),
):
    """Analyze a location and intent for land, civic, and environmental friction."""
    # 1. Check cache first unless refresh is forced
    if not refresh:
        cached = get_cached_response(request.location, request.intent)
        if cached:
            logger.info("Serving cached result for %s (%s)", request.location.locality, request.intent.value)
            return cached

    # 2. Attempt live collector & synthesizer pipeline with safe fallback
    try:
        logger.info("Executing collector for %s...", request.location.locality)
        raw_signals = await collect_location_signals(request)
        logger.info("Executing synthesizer...")
        result = await synthesize_friction(request, raw_signals)
        result.cached = False
        save_cached_response(result)
        return result
    except Exception as exc:
        logger.warning(
            "Live analysis pipeline encountered exception (%s: %s). Falling back to safe demo baseline.",
            type(exc).__name__,
            exc,
        )
        fallback = get_fallback_response(request)
        # Store in cache so repeat queries in demo are quick
        save_cached_response(fallback)
        return fallback

