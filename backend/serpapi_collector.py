"""SerpApi collector stub for PlotTwistt.

Owned by Teammate 1 (feat/serpapi-collector).
This stub ensures backend imports cleanly and provides a typed signature.
"""

import os
from typing import Any, Dict, List
from backend.schemas import AnalyzeRequest


async def collect_location_signals(request: AnalyzeRequest) -> Dict[str, Any]:
    """Collect web, news, and maps friction signals via SerpApi.
    
    In the live branch (`feat/serpapi-collector`), this queries SerpApi Google Search,
    Google News, and Google Maps to find mentions of waterlogging, demolition notices,
    traffic congestions, and zoning disputes for the target location.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not configured.")

    # Placeholder returning empty signal dict until feat/serpapi-collector is merged
    return {
        "signals": [],
        "query_locality": request.location.locality,
        "intent": request.intent.value,
        "source": "serpapi_stub",
    }

