"""SerpApi collector for PlotTwistt.

Collects real-world search, news, and civic signals using SerpApi.
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
    """Extract neighborhood, ward, or main road name from a full door-number address.
    
    Example: 'No. 200 4th Main Cross Anjanagar Magadi Road' -> 'Anjanagar Magadi Road'
    """
    # Remove door, plot, flat, and house numbers
    cleaned = re.sub(
        r"^(?:no\.?|plot|door|flat|survey|sy\.?)\s*[\d\w\-\/]+[,\s]*",
        "",
        address,
        flags=re.IGNORECASE,
    ).strip()

    # Remove leading numeric main/cross sequences (e.g. '4th Main Cross', '1st Cross')
    cleaned = re.sub(
        r"^(\d+(?:st|nd|rd|th)?\s*(?:main|cross|stage|phase|block)?\s*(?:road|rd)?\s*(?:cross|main)?\s*)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    # If something sensible was extracted, use it; otherwise fall back to original
    if cleaned and len(cleaned) >= 3:
        # Keep neighborhood + corridor (e.g., 'Anjanagar Magadi Road')
        return cleaned.split(",")[0].strip()
    return address.split(",")[0].strip()


async def collect_location_signals(
    locality: str, intent: str, lat: float | None = None, lng: float | None = None
) -> Dict[str, Any]:
    """Query SerpApi for news, civic discussions, road conditions, and neighborhood issues."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not configured.")

    clean_locality = extract_searchable_locality(locality)

    # Neighborhood-focused search queries targeting realistic surrounding headaches
    intent_queries = {
        "warehouse": [
            f'"{clean_locality}" Bangalore traffic waterlogging OR road',
            f'"{clean_locality}" Bangalore heavy vehicle entry ban OR truck',
            f'"{clean_locality}" Bangalore civic issues BBMP',
        ],
        "retail": [
            f'"{clean_locality}" Bangalore commercial parking traffic towing',
            f'"{clean_locality}" Bangalore civic issues BBMP road',
            f'"{clean_locality}" Bangalore market footfall retail',
        ],
        "plot": [
            f'"{clean_locality}" Bangalore BDA layout development land',
            f'"{clean_locality}" Bangalore water supply tanker groundwater',
            f'"{clean_locality}" Bangalore road widening demolition',
        ],
    }

    queries = intent_queries.get(intent.lower(), intent_queries["warehouse"])
    collected_news: List[Dict[str, Any]] = []
    collected_web: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch Google News for the locality
        try:
            news_params = {
                "engine": "google_news",
                "q": f"{clean_locality} Bangalore",
                "api_key": api_key,
                "gl": "in",
                "hl": "en",
            }
            res = await client.get(SERPAPI_URL, params=news_params)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("news_results", [])[:6]:
                    source_name = (
                        item.get("source", {}).get("name", "News Outlet")
                        if isinstance(item.get("source"), dict)
                        else str(item.get("source", "News"))
                    )
                    # Filter out generic directory portals
                    collected_news.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "source": source_name,
                        "date": item.get("date", ""),
                        "snippet": item.get("snippet", item.get("title", "")),
                    })
        except Exception as e:
            logger.warning("SerpApi news collection error: %s", e)

        # 2. Fetch Google Web search for civic / road / municipal conditions
        try:
            web_params = {
                "engine": "google",
                "q": queries[0],
                "api_key": api_key,
                "gl": "in",
                "hl": "en",
                "num": 6,
            }
            res = await client.get(SERPAPI_URL, params=web_params)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("organic_results", [])[:6]:
                    link = item.get("link", "")
                    # Don't capture the generic rajakaluve directory search result
                    if "rajakaluve.org" in link:
                        continue
                    collected_web.append({
                        "title": item.get("title", ""),
                        "url": link,
                        "source": item.get("displayed_link", "Civic Source"),
                        "snippet": item.get("snippet", ""),
                    })
        except Exception as e:
            logger.warning("SerpApi web search error: %s", e)

    return {
        "locality": clean_locality,
        "original_query": locality,
        "intent": intent,
        "news": collected_news,
        "web": collected_web,
        "total_signals": len(collected_news) + len(collected_web),
    }
