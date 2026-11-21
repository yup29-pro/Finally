"""SerpApi multi-angle collector and geocoding helper for PlotTwistt.

Provides:
- Strict local geographic extraction (ignores broad state/country keywords like 'Karnataka')
- Hierarchical location categorization (Locality -> Neighborhood -> Corridor -> City)
- Strict negative filtering against distant, unrelated Bangalore hubs (e.g., BTM, Whitefield, Silk Board)
- Proximity-based signal queries tailored strictly to the targeted sector
"""

from __future__ import annotations
import math
import os
import re
import logging
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("plottwistt.collector")

SERPAPI_URL = "https://serpapi.com/search.json"

# Unrelated distant localities to reject when searching a specific corridor
DISTANT_LOCALITIES_FILTER = [
    "btm", "btm layout", "silk board", "varthur", "panathur", "whitefield",
    "electronic city", "sarjapur", "bellandur", "marathahalli", "hebbal",
    "yelahanka", "banashankari", "koramangala", "indiranagar"
]


def clean_locality_tokens(address: str) -> List[str]:
    """Extract clean, meaningful sub-locality and corridor names from user address."""
    # Common typo normalization (e.g. 'Madagi Road' -> 'Magadi Road')
    normalized = re.sub(r"\bmadagi\b", "Magadi", address, flags=re.I)
    normalized = re.sub(r"\bbydrahalli\b", "Byadarahalli", normalized, flags=re.I)

    # Split by comma or semicolon
    raw_parts = [p.strip() for p in re.split(r"[,;]+", normalized) if p.strip()]

    clean_parts: List[str] = []
    for part in raw_parts:
        # Strip door/plot/survey numbers
        p_clean = re.sub(
            r"^(?:no\.?|plot|door|flat|survey|sy\.?)\s*[\d\w\-\/]+[,\s]*",
            "",
            part,
            flags=re.IGNORECASE,
        ).strip()
        # Strip leading numerical crosses/mains
        p_clean = re.sub(
            r"^(\d+(?:st|nd|rd|th)?\s*(?:main|cross|stage|phase|block)?\s*(?:road|rd)?\s*(?:cross|main)?\s*)+",
            "",
            p_clean,
            flags=re.IGNORECASE,
        ).strip()

        # Ignore broad administrative words that pollute queries
        if p_clean.lower() in ["karnataka", "india", "bengaluru", "bangalore"]:
            continue

        if len(p_clean) >= 3 and p_clean not in clean_parts:
            clean_parts.append(p_clean)

    return clean_parts if clean_parts else [normalized.strip()]


async def resolve_hierarchical_location(query: str, lat: float | None = None, lng: float | None = None) -> Dict[str, Any]:
    """Resolve hierarchical location breakdown avoiding state/country dilution."""
    api_key = os.getenv("SERPAPI_API_KEY")
    tokens = clean_locality_tokens(query)

    hyperlocal = tokens[0] if tokens else "Bengaluru"
    locality = tokens[1] if len(tokens) >= 2 else hyperlocal
    corridor = tokens[-1] if len(tokens) >= 3 else (tokens[1] if len(tokens) == 2 else hyperlocal)

    hierarchy = {
        "raw_query": query,
        "hyperlocal": hyperlocal,
        "locality": locality,
        "corridor": corridor,
        "city": "Bengaluru",
        "resolved_lat": lat or 12.9716,
        "resolved_lng": lng or 77.5946,
        "display_hierarchy": " ❯ ".join([p for p in [hyperlocal, locality, corridor, "Bengaluru"] if p]),
    }

    if not api_key:
        return hierarchy

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                SERPAPI_URL,
                params={
                    "engine": "google_maps",
                    "q": f"{hyperlocal} {corridor} Bangalore",
                    "api_key": api_key,
                },
            )
            if res.status_code == 200:
                data = res.json()
                place = data.get("place_results", {})
                if not place and data.get("local_results"):
                    place = data.get("local_results")[0]

                if place:
                    gps = place.get("gps_coordinates") or {}
                    if gps.get("latitude") and gps.get("longitude"):
                        hierarchy["resolved_lat"] = gps["latitude"]
                        hierarchy["resolved_lng"] = gps["longitude"]

                    addr_parts = [
                        p.strip() for p in place.get("address", "").split(",")
                        if p.strip() and p.strip().lower() not in ["karnataka", "india", "bengaluru", "bangalore"]
                    ]
                    if addr_parts:
                        hierarchy["display_hierarchy"] = " ❯ ".join(
                            [hyperlocal] + addr_parts[:2] + ["Bengaluru"]
                        )
    except Exception as e:
        logger.debug("Hierarchy resolution error: %s", e)

    return hierarchy


async def collect_location_signals(
    locality: str, intent: str, lat: float | None = None, lng: float | None = None
) -> Dict[str, Any]:
    """Harvest strictly localized news and civic friction signals."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not configured.")

    tokens = clean_locality_tokens(locality)
    hierarchy = await resolve_hierarchical_location(locality, lat, lng)

    hyperlocal = hierarchy["hyperlocal"]
    corridor = hierarchy["corridor"]

    # Target queries strictly anchoring to the local neighborhood & corridor
    anchor = f"{hyperlocal} {corridor}".strip() if hyperlocal != corridor else corridor

    collected_signals: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=18.0) as client:
        search_targets = [
            # 1. Hyper-local news
            {
                "engine": "google_news",
                "q": f"{anchor} Bangalore",
                "category": "civic_incident",
            },
            # 2. Local crime, police, and law & order in the corridor
            {
                "engine": "google_news",
                "q": f"{corridor} Bangalore police crime OR accident OR protest",
                "category": "civic_incident",
            },
            # 3. Local land disputes, illegal layouts, and BDA/BBMP demolitions along corridor
            {
                "engine": "google",
                "q": f"{corridor} Bangalore (land dispute OR illegal layout OR demolition OR acquisition OR BDA)",
                "category": "zoning_buffer_row",
            },
            # 4. Traffic congestion, road widening, and potholes on corridor
            {
                "engine": "google",
                "q": f"{corridor} Bangalore (traffic jam OR road condition OR bottleneck OR pothole OR widening)",
                "category": "civic_neighbor_friction",
            },
            # 5. Local waterlogging, drainage, and BESCOM power outages
            {
                "engine": "google",
                "q": f"{corridor} Bangalore (waterlogging OR flood OR drain overflow OR BESCOM power shutdown)",
                "category": "flooding_drainage",
            },
        ]

        for st in search_targets:
            try:
                params = {
                    "engine": st["engine"],
                    "q": st["q"],
                    "api_key": api_key,
                    "gl": "in",
                    "hl": "en",
                }
                if st["engine"] == "google":
                    params["num"] = 6

                res = await client.get(SERPAPI_URL, params=params)
                if res.status_code != 200:
                    continue

                data = res.json()
                items = data.get("news_results", []) if st["engine"] == "google_news" else data.get("organic_results", [])

                for it in items[:5]:
                    link = it.get("link", "")
                    title = it.get("title", "")
                    snippet = it.get("snippet", title)

                    if not title or "rajakaluve.org" in link or "youtube.com" in link:
                        continue

                    # STRICT DISTANT SECTOR FILTER:
                    # If this search is about Magadi Road / Byadarahalli, reject stories explicitly about BTM, Whitefield, Silk Board, etc.
                    text_lower = f"{title} {snippet}".lower()
                    target_lower = f"{hyperlocal} {corridor}".lower()
                    
                    is_distant = False
                    for distant_loc in DISTANT_LOCALITIES_FILTER:
                        # If the story explicitly focuses on a distant locality not in the user query
                        if distant_loc in text_lower and distant_loc not in target_lower:
                            # Verify if target corridor is absent from this story
                            if not any(token.lower() in text_lower for token in [hyperlocal, corridor] if len(token) > 3):
                                is_distant = True
                                break

                    if is_distant:
                        continue

                    src_name = (
                        it.get("source", {}).get("name", "Local News")
                        if isinstance(it.get("source"), dict)
                        else it.get("source", it.get("displayed_link", "Civic Report"))
                    )

                    collected_signals.append({
                        "title": title,
                        "url": link,
                        "source": src_name,
                        "snippet": snippet,
                        "category": st["category"],
                        "target_anchor": anchor,
                    })
            except Exception as e:
                logger.debug("Signal error for query '%s': %s", st["q"], e)

    return {
        "locality": hyperlocal,
        "corridor": corridor,
        "hierarchy": hierarchy,
        "intent": intent,
        "signals": collected_signals,
        "total_signals": len(collected_signals),
    }
