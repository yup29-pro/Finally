# PlotTwistt API Contract & Specification

**PlotTwistt** is a Land & Civic Friction Radar that inspects site headaches for prospective land buyers, tenants, and builders based on intent (`warehouse`, `retail`, or `plot`).

---

## 1. Intent Definitions
- `warehouse`: Sensitive to heavy vehicle access restrictions, waterlogging/submersion, low bridges, narrow approach roads, industrial zoning buffers, neighbor noise complaints.
- `retail`: Sensitive to customer footfall visibility, civic road widening/demolition, parking/traffic police towing zones, stormwater drains overflowing into basements, local commercial tax disputes.
- `plot`: Sensitive to lake buffer zones (NGT rulings), revenue land vs gramathana classification, Rajakaluve (storm drain) encroachment notices, builder legal disputes, high-tension power line clearance.

---

## 2. Shared Data Models

### Location
```json
{
  "lat": 12.9716,
  "lng": 77.5946,
  "address": "Bellandur Outer Ring Road, Bengaluru",
  "locality": "Bellandur",
  "city": "Bengaluru"
}
```

### Risk Category
One of:
- `flooding_drainage` (Waterlogging, rajakaluve, low elevation)
- `zoning_legal` (Lake buffer, demolition notices, road widening, land dispute)
- `civic_friction` (Garbage dump, traffic bottleneck, industrial noise, neighbor protest)
- `access_infrastructure` (Power line clearance, narrow approach, heavy vehicle ban)

### Severity Level
- `low`: Informational or minor historic occurrence.
- `medium`: Notable constraint requiring verification or operational adjustments.
- `high`: Major barrier, legal block, or severe recurring disruption.

### Receipt (Source Citation)
Every friction point MUST link to a verifiable receipt trail:
```json
{
  "title": "Outer Ring Road flooded after heavy rain, tech corridor blocked",
  "source": "Deccan Herald",
  "url": "https://www.deccanherald.com/example-flood-news",
  "exact_quote": "Water entered basement parking lots along the Bellandur lake basin...",
  "published_date": "2023-09-05"
}
```

### Friction Point
```json
{
  "category": "flooding_drainage",
  "title": "Severe Lake Basin Waterlogging & Overflow",
  "summary": "Basement and access road inundation recorded during monsoon seasons due to proximity to lake overflow channels.",
  "severity": "high",
  "receipts": [ ...Receipt... ]
}
```

### Overall Friction Score
- `0 - 30`: Low Friction (Green / relatively clean site record)
- `31 - 70`: Moderate Friction (Yellow / caution advised, site checks required)
- `71 - 100`: High Friction (Red / major historical and civic roadblocks)

---

## 3. Endpoints

### 1. `GET /health`
Returns service status.
**Response `200 OK`**:
```json
{
  "status": "ok",
  "service": "PlotTwistt Radar API",
  "timestamp": "2026-11-21T11:15:00Z"
}
```

### 2. `GET /api/presets`
Returns curated reference locations for immediate demo and testing without consuming live API tokens.
**Response `200 OK`**:
```json
[
  {
    "id": "bellandur-tech-corridor",
    "name": "Bellandur ORR (Lake Buffer & Flood Prone)",
    "location": {
      "lat": 12.9298,
      "lng": 77.6749,
      "address": "Bellandur ORR, Bengaluru, Karnataka",
      "locality": "Bellandur",
      "city": "Bengaluru"
    },
    "intent": "warehouse",
    "description": "High friction zone: Lake buffer encroachments, recurring monsoon waterlogging, tech corridor traffic."
  },
  ...
]
```

### 3. `POST /api/analyze?refresh=false`
Submits a location and intent to run friction radar analysis.

**Query Parameters**:
- `refresh` (boolean, optional, default `false`): If `true`, bypasses cache and forces live retrieval from SerpApi + You.com.

**Request Body**:
```json
{
  "location": {
    "lat": 12.9298,
    "lng": 77.6749,
    "address": "Bellandur ORR, Bengaluru",
    "locality": "Bellandur",
    "city": "Bengaluru"
  },
  "intent": "warehouse"
}
```

**Response `200 OK`**:
```json
{
  "query": {
    "location": { ... },
    "intent": "warehouse"
  },
  "friction_score": 82,
  "verdict": "High Civic & Waterlogging Friction",
  "summary": "Site exhibits critical flood vulnerabilities during heavy monsoon downpours and sits adjacent to NGT-designated lake buffer zones.",
  "friction_points": [
    {
      "category": "flooding_drainage",
      "title": "Severe Monsoon Waterlogging",
      "summary": "Access road submersion and basement flooding reported repeatedly.",
      "severity": "high",
      "receipts": [
        {
          "title": "Bengaluru rain: Bellandur tech corridor flooded again",
          "source": "The Hindu",
          "url": "https://www.thehindu.com/news/cities/bangalore/bellandur-floods",
          "exact_quote": "Service roads remained inundated for over 48 hours after heavy rains.",
          "published_date": "2024-05-18"
        }
      ]
    }
  ],
  "positive_signals": [
    "Well-connected arterial corridor with multi-lane Outer Ring Road frontage",
    "Heavy commercial density and robust telecom infrastructure"
  ],
  "cached": true,
  "analyzed_at": "2026-11-21T11:15:00Z"
}
```

