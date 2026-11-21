"""Shared Pydantic models and schemas for PlotTwistt."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    WAREHOUSE = "warehouse"
    RETAIL = "retail"
    PLOT = "plot"


class FrictionCategory(str, Enum):
    FLOODING_DRAINAGE = "flooding_drainage"
    ZONING_LEGAL = "zoning_legal"
    CIVIC_FRICTION = "civic_friction"
    ACCESS_INFRASTRUCTURE = "access_infrastructure"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Location(BaseModel):
    lat: float = Field(..., description="Latitude coordinates")
    lng: float = Field(..., description="Longitude coordinates")
    address: str = Field(..., description="Readable address or landmark")
    locality: str = Field(..., description="Locality or neighborhood name")
    city: str = Field(default="Bengaluru", description="City name")


class Receipt(BaseModel):
    title: str = Field(..., description="News or publication title")
    source: str = Field(..., description="Publisher or domain name")
    url: str = Field(..., description="Direct clickable URL link")
    exact_quote: str = Field(..., description="Verifiable cited excerpt from the source")
    published_date: Optional[str] = Field(None, description="Publication date or estimated period")


class FrictionPoint(BaseModel):
    category: FrictionCategory = Field(..., description="Category of friction identified")
    title: str = Field(..., description="Short headline of the friction")
    summary: str = Field(..., description="Detailed description of the issue for this intent")
    severity: SeverityLevel = Field(..., description="Severity level: low, medium, or high")
    receipts: List[Receipt] = Field(default_factory=list, description="Citations and evidence trails")


class AnalyzeRequest(BaseModel):
    location: Location
    intent: IntentType


class PresetItem(BaseModel):
    id: str
    name: str
    location: Location
    intent: IntentType
    description: str


class AnalyzeResponse(BaseModel):
    query: AnalyzeRequest
    friction_score: int = Field(..., ge=0, le=100, description="Overall friction score from 0 (clean) to 100 (high risk)")
    verdict: str = Field(..., description="High-level assessment summary")
    summary: str = Field(..., description="Contextual friction briefing")
    friction_points: List[FrictionPoint] = Field(default_factory=list)
    positive_signals: List[str] = Field(default_factory=list, description="Positive advantages identified")
    cached: bool = Field(default=False, description="Whether this response was served from cache")
    analyzed_at: str = Field(..., description="ISO 8601 timestamp of analysis")

