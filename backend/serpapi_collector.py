"""SerpApi multi-angle collector for PlotTwistt.

Collects real-world search, news, and civic signals across 4 key dimensions:
1. Local News & Crime / Law & Order incidents
2. Land, BDA/BBMP Encroachments, & Illegal Layout / Property disputes
3. Road conditions, Traffic bottlenecks, & Transit connectivity
4. Waterlogging, Drainage & Civic infrastructure (BESCOM power cuts, water supply)
"""

from __future__ import annotations
import os
import re
import logging
from typing import Any, Dict, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("plottwistt.collector")

SERPAPI_URL = "https://serpapi.com/search.json"


def extract_searchable_locality(address: str) -> str:
    """Extract neighborhood and corridor from a raw address string.
    
    Example: 'No. 200 4th Main Cross Anjanagar Magadi Road' -> 'Anjanagar Magadi Road'
    """
    cleaned = re.sub(
        r"^(?:no\.?|plot|door|flat|survey|sy\.?)\s*[\d\w\-\/]+[,\s]*",
        "",
        address,
        flags=re.IGNORECASE,
    ).strip()

    cleaned = re.sub(
        r"^(\d+(?:st|nd|rd|th)?\s*(?:main|cross|stage|phase|block)?\s*(?:road|rd)?\s*(?:cross|main)?\s*)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    if cleaned and len(cleaned) >= 3:
        return cleaned.split(",")[0].strip()
    return address.split(",")[0].strip()


async def collect_location_signals(
    locality: str, intent: str, lat: float | None = None, lng: float | None = None
) -> Dict[str, Any]:
    """Query SerpApi across multiple lenses: news, crime/civic, land disputes, and road/traffic."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not configured.")

    clean_loc = extract_searchable_locality(locality)
    # Also extract the broader corridor if there's both a neighborhood and road (e.g. 'Magadi Road')
    corridor = clean_loc
    if " " in clean_loc:
        parts = clean_loc.split()
        if len(parts) >= 2 and parts[-1].lower() in ["road", "rd", "layout", "nagar"]:
            corridor = " ".join(parts[-2:])

    collected_news: List[Dict[str, Any]] = []
    collected_web: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=18.0) as client:
        # Lens 1: Google News for recent local incidents and corridor activities
        try:
            news_res = await client.get(
                SERPAPI_URL,
                params={
                    "engine": "google_news",
                    "q": f'"{corridor}" Bangalore',
                    "api_key": api_key,
                    "gl": "in",
                    "hl": "en",
                },
            )
            if news_res.status_code == 200:
                for item in news_res.json().get("news_results", [])[:8]:
                    source_name = (
                        item.get("source", {}).get("name", "News")
                        if isinstance(item.get("source"), dict)
                        else str(item.get("source", "News"))
                    )
                    collected_news.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "source": source_name,
                        "date": item.get("date", ""),
                        "snippet": item.get("snippet", item.get("title", "")),
                        "type": "news",
                    })
        except Exception as e:
            logger.warning("News search failed: %s", e)

        # Lens 2: Land disputes, illegal layouts, and property acquisition/demolition
        try:
            land_res = await client.get(
                SERPAPI_URL,
                params={
                    "engine": "google",
                    "q": f'"{corridor}" Bangalore (land dispute OR illegal layout OR demolition OR acquisition OR BDA)',
                    "api_key": api_key,
                    "gl": "in",
                    "hl": "en",
                    "num": 5,
                },
            )
            if land_res.status_code == 200:
                for item in land_res.json().get("organic_results", [])[:5]:
                    link = item.get("link", "")
                    if "rajakaluve.org" in link or "youtube.com" in link:
                        continue
                    collected_web.append({
                        "title": item.get("title", ""),
                        "url": link,
                        "source": item.get("displayed_link", "Legal / Land Record"),
                        "snippet": item.get("snippet", ""),
                        "lens": "zoning_legal",
                    })
        except Exception as e:
            logger.warning("Land query failed: %s", e)

        # Lens 3: Local crime, police action, civic protests, and neighbor friction
        try:
            civic_res = await client.get(
                SERPAPI_URL,
                params={
                    "engine": "google",
                    "q": f'"{corridor}" Bangalore (police OR crime OR protest OR accident OR traffic jam)',
                    "api_key": api_key,
                    "gl": "in",
                    "hl": "en",
                    "num": 5,
                },
            )
            if civic_res.status_code == 200:
                for item in civic_res.json().get("organic_results", [])[:5]:
                    link = item.get("link", "")
                    if "youtube.com" in link or "rajakaluve.org" in link:
                        continue
                    collected_web.append({
                        "title": item.get("title", ""),
                        "url": link,
                        "source": item.get("displayed_link", "Civic / Police Record"),
                        "snippet": item.get("snippet", ""),
                        "lens": "civic_incident",
                    })
        except Exception as e:
            logger.warning("Civic query failed: %s", e)

    return {
        "locality": clean_loc,
        "corridor": corridor,
        "original_query": locality,
        "intent": intent,
        "news": collected_news,
        "web": collected_web,
        "total_signals": len(collected_news) + len(collected_web),
    }
