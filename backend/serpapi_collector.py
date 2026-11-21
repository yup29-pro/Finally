"""SerpApi collector for PlotTwistt.

Collects real-world search, news, and civic signals using SerpApi.
"""

from __future__ import annotations
import os
import logging
from typing import Any, Dict, List
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("plottwistt.collector")

SERPAPI_URL = "https://serpapi.com/search.json"


async def collect_location_signals(locality: str, intent: str, lat: float | None = None, lng: float | None = None) -> Dict[str, Any]:
    """Query SerpApi for news, civic discussions, and zoning/drainage issues for a given location and intent."""
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not configured.")

    clean_locality = locality.split(",")[0].strip()

    # Specialized search query terms based on intent
    intent_queries = {
        "warehouse": [
            f"{clean_locality} Bangalore waterlogging flood rain",
            f"{clean_locality} Bangalore lake buffer storm drain rajakaluve",
            f"{clean_locality} Bangalore heavy truck traffic restriction",
        ],
        "retail": [
            f"{clean_locality} Bangalore commercial parking BBMP penalty",
            f"{clean_locality} Bangalore noise complaint residential protest",
            f"{clean_locality} Bangalore road widening demolition",
        ],
        "plot": [
            f"{clean_locality} Bangalore NGT lake buffer demolition order",
            f"{clean_locality} Bangalore revenue layout gramathana conversion dispute",
            f"{clean_locality} Bangalore rajakaluve storm water encroachment",
        ],
    }

    queries = intent_queries.get(intent.lower(), intent_queries["warehouse"])
    collected_news: List[Dict[str, Any]] = []
    collected_web: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Fetch Google News for primary query
        try:
            news_params = {
                "engine": "google_news",
                "q": queries[0],
                "api_key": api_key,
                "gl": "in",
                "hl": "en",
            }
            res = await client.get(SERPAPI_URL, params=news_params)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("news_results", [])[:6]:
                    source_name = item.get("source", {}).get("name", "News Outlet") if isinstance(item.get("source"), dict) else str(item.get("source", "News"))
                    collected_news.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "source": source_name,
                        "date": item.get("date", ""),
                        "snippet": item.get("snippet", item.get("title", "")),
                    })
        except Exception as e:
            logger.warning("SerpApi news collection failed: %s", e)

        # 2. Fetch Google Web search for secondary query (buffer / zoning / disputes)
        try:
            web_params = {
                "engine": "google",
                "q": queries[1],
                "api_key": api_key,
                "gl": "in",
                "hl": "en",
                "num": 5,
            }
            res = await client.get(SERPAPI_URL, params=web_params)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("organic_results", [])[:5]:
                    collected_web.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "source": item.get("displayed_link", "Web Document"),
                        "snippet": item.get("snippet", ""),
                    })
        except Exception as e:
            logger.warning("SerpApi organic search failed: %s", e)

    return {
        "locality": clean_locality,
        "intent": intent,
        "news": collected_news,
        "web": collected_web,
        "total_signals": len(collected_news) + len(collected_web),
    }
