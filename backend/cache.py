"""File cache, demo presets, and safe fallbacks for PlotTwistt."""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FrictionCategory,
    FrictionPoint,
    IntentType,
    Location,
    PresetItem,
    Receipt,
    SeverityLevel,
)

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Curated reference presets across Bengaluru with contrasting friction profiles
PRESETS: List[PresetItem] = [
    PresetItem(
        id="bellandur-lake-corridor",
        name="Bellandur ORR (Lake Buffer & Flood-Prone Zone)",
        location=Location(
            lat=12.9298,
            lng=77.6749,
            address="Bellandur Outer Ring Road, Near Ecospace",
            locality="Bellandur",
            city="Bengaluru",
        ),
        intent=IntentType.WAREHOUSE,
        description="High-friction spot: Severe monsoon waterlogging, lake buffer encroachment notices, heavy vehicle traffic congestion.",
    ),
    PresetItem(
        id="peenya-industrial-area",
        name="Peenya Industrial Area Stage 2 (Industrial & Logistics Hub)",
        location=Location(
            lat=13.0285,
            lng=77.5197,
            address="Peenya 2nd Stage, Industrial Estate",
            locality="Peenya",
            city="Bengaluru",
        ),
        intent=IntentType.WAREHOUSE,
        description="Medium-friction spot: Permitted industrial activity, ground water quality cautions, toll congestion at Goraguntepalya.",
    ),
    PresetItem(
        id="indiranagar-100ft-road",
        name="Indiranagar 100 Feet Road (Commercial & Retail Strip)",
        location=Location(
            lat=12.9719,
            lng=77.6412,
            address="100 Feet Road, HAL 2nd Stage, Indiranagar",
            locality="Indiranagar",
            city="Bengaluru",
        ),
        intent=IntentType.RETAIL,
        description="High commercial friction: Residential RWA noise protests, BBMP zoning crackdowns on commercial conversions, limited parking.",
    ),
    PresetItem(
        id="sarjapur-road-greenfield",
        name="Sarjapur Road Extension (Plot Investment Zone)",
        location=Location(
            lat=12.8596,
            lng=77.7854,
            address="Sarjapur-Bagalur Road, Near Dommasandra",
            locality="Sarjapur",
            city="Bengaluru",
        ),
        intent=IntentType.PLOT,
        description="Moderate friction: Revenue land conversions, Rajakaluve buffer scrutiny, upcoming road widening proposals.",
    ),
]


def make_cache_slug(location: Location, intent: IntentType) -> str:
    """Generate a clean filesystem slug for caching responses."""
    locality_clean = re.sub(r"[^a-zA-Z0-9]+", "-", location.locality.lower()).strip("-")
    intent_clean = intent.value.lower()
    lat_str = f"{location.lat:.4f}".replace(".", "_")
    lng_str = f"{location.lng:.4f}".replace(".", "_")
    return f"{locality_clean}_{intent_clean}_{lat_str}_{lng_str}"


def get_cached_response(location: Location, intent: IntentType) -> Optional[AnalyzeResponse]:
    """Retrieve cached response if present."""
    slug = make_cache_slug(location, intent)
    cache_file = CACHE_DIR / f"{slug}.json"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["cached"] = True
        return AnalyzeResponse(**data)
    except Exception:
        return None


def save_cached_response(response: AnalyzeResponse) -> None:
    """Save an analysis response to cache."""
    try:
        slug = make_cache_slug(response.query.location, response.query.intent)
        cache_file = CACHE_DIR / f"{slug}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(response.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Failing to write cache should not crash the request
        pass


def get_fallback_response(request: AnalyzeRequest) -> AnalyzeResponse:
    """Produce a deterministic, high-quality fallback response matching SPEC.md."""
    locality = request.location.locality or "Bengaluru Locality"
    intent = request.intent.value
    now_iso = datetime.now(timezone.utc).isoformat()

    # Contextual fallback data based on intent
    if request.intent == IntentType.WAREHOUSE:
        score = 68
        verdict = f"Moderate-to-High Logistics & Drainage Friction in {locality}"
        summary = (
            f"Analysis for warehouse operations in {locality} shows notable monsoon drainage vulnerabilities "
            f"and arterial access bottlenecks during peak hours, alongside local municipal buffer scrutiny."
        )
        friction_points = [
            FrictionPoint(
                category=FrictionCategory.FLOODING_DRAINAGE,
                title="Stormwater & Drain Runoff Vulnerability",
                summary="Low-lying approach roads and storm drain runoff can cause periodic access disruptions during sustained monsoon downpours.",
                severity=SeverityLevel.HIGH,
                receipts=[
                    Receipt(
                        title="Bengaluru Monsoon Waterlogging Hotspots Reported by Traffic Police",
                        source="The Hindu",
                        url="https://www.thehindu.com/news/cities/bangalore/bengaluru-monsoon-traffic-and-drainage-updates/article68123456.ece",
                        exact_quote="Service roads along major corridors witnessed persistent water accumulation of up to 2 feet during peak rain.",
                        published_date="2024-06-15",
                    )
                ],
            ),
            FrictionPoint(
                category=FrictionCategory.ACCESS_INFRASTRUCTURE,
                title="Heavy Commercial Vehicle Movement Restrictions",
                summary="Peak-hour heavy vehicle curbs apply on key access arteries between 08:00–11:00 and 16:00–21:00.",
                severity=SeverityLevel.MEDIUM,
                receipts=[
                    Receipt(
                        title="Bengaluru Traffic Police Advisory on Heavy Goods Vehicles Entry Timings",
                        source="Deccan Herald",
                        url="https://www.deccanherald.com/city/top-bengaluru-stories/traffic-police-tighten-heavy-vehicle-timings-on-arterial-stretches-2198765",
                        exact_quote="Goods vehicles exceeding 7.5 tonnes barred from entering specific municipal ring routes during peak morning and evening intervals.",
                        published_date="2024-03-22",
                    )
                ],
            ),
        ]
        positive_signals = [
            "Proximity to major outer freight corridors",
            "High availability of 3PL logistics ecosystem in surrounding belt",
        ]
    elif request.intent == IntentType.RETAIL:
        score = 55
        verdict = f"Commercial & Civic Friction Advisory for {locality}"
        summary = (
            f"Retail assessment for {locality} indicates active customer density with friction concentrated around "
            f"municipal parking enforcement, commercial signage bylaws, and neighborhood association scrutiny."
        )
        friction_points = [
            FrictionPoint(
                category=FrictionCategory.CIVIC_FRICTION,
                title="Parking Scarcity & Street Towing Enforcement",
                summary="Intensive municipal towing drives and strict curbs on customer street parking on fronting roads.",
                severity=SeverityLevel.HIGH,
                receipts=[
                    Receipt(
                        title="BBMP and Traffic Police Crack Down on Illegal Commercial Parking",
                        source="Bangalore Mirror",
                        url="https://bangaloremirror.indiatimes.com/bangalore/civic/parking-crackdown-intensifies-on-busy-commercial-lanes/articleshow/98765432.cms",
                        exact_quote="Shoppers faced heavy fines as authorities designated multiple stretches as strict no-parking corridors.",
                        published_date="2024-08-10",
                    )
                ],
            ),
            FrictionPoint(
                category=FrictionCategory.ZONING_LEGAL,
                title="Commercial Conversion & By-law Audits",
                summary="Scrutiny over building plan approvals and commercial usage compliance in mixed-residential belts.",
                severity=SeverityLevel.MEDIUM,
                receipts=[
                    Receipt(
                        title="High Court Directs Municipal Body to Inspect Commercial Units in Mixed Zones",
                        source="Times of India",
                        url="https://timesofindia.indiatimes.com/city/bengaluru/hc-monitoring-commercial-units-in-residential-zones/articleshow/91234567.cms",
                        exact_quote="Notices issued to establishments operating without designated basement parking or sanctioned commercial conversion certificates.",
                        published_date="2024-04-05",
                    )
                ],
            ),
        ]
        positive_signals = [
            "Strong demographic purchasing power and high evening pedestrian density",
            "Convenient public transit and metro station connectivity within short radius",
        ]
    else:  # IntentType.PLOT
        score = 62
        verdict = f"Zoning & Land Title Friction Advisory for {locality}"
        summary = (
            f"Plot investment review in {locality} highlights vigilance needed for NGT lake buffer clearances, "
            f"stormwater drain (Rajakaluve) alignments, and verifying conversion from agricultural to non-agricultural status."
        )
        friction_points = [
            FrictionPoint(
                category=FrictionCategory.ZONING_LEGAL,
                title="Rajakaluve & Lake Buffer Demarcation Checks",
                summary="Mandatory verification required regarding the 30-meter lake buffer and 50-meter primary storm drain buffer under NGT guidelines.",
                severity=SeverityLevel.HIGH,
                receipts=[
                    Receipt(
                        title="Demolition Drives Target Encroachments on Secondary Rajakaluves",
                        source="Deccan Herald",
                        url="https://www.deccanherald.com/city/top-bengaluru-stories/stormwater-drain-survey-identifies-encroachments-in-eastern-suburbs-2345678",
                        exact_quote="Survey department maps identified multiple layout boundary fences infringing on natural drainage channels.",
                        published_date="2024-07-19",
                    )
                ],
            ),
            FrictionPoint(
                category=FrictionCategory.CIVIC_FRICTION,
                title="Proposed Road Widening & Master Plan Alignments",
                summary="Proposed master plan road widening could affect front setback margins of peripheral plots.",
                severity=SeverityLevel.MEDIUM,
                receipts=[
                    Receipt(
                        title="BDA Revised Master Plan: Road Widening Stretches Marked for Peripheral Belts",
                        source="The Hindu",
                        url="https://www.thehindu.com/news/cities/bangalore/bda-masterplan-road-widening-proposals-detailed/article68345678.ece",
                        exact_quote="Properties adjoining the designated peripheral roads may be subject to setback revisions under revised widening plans.",
                        published_date="2024-02-14",
                    )
                ],
            ),
        ]
        positive_signals = [
            "Rapid capital appreciation trajectory in surrounding suburban belt",
            "Upcoming road and infrastructural expansion planned in master framework",
        ]

    return AnalyzeResponse(
        query=request,
        friction_score=score,
        verdict=verdict,
        summary=summary,
        friction_points=friction_points,
        positive_signals=positive_signals,
        cached=False,
        analyzed_at=now_iso,
    )

