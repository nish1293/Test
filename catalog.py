"""
UCF Project Catalog — Urban Sustainability Project Definitions
Organized by theme. Each project entry contains metadata used for
financial structuring, KPI generation, and reform checklist selection.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Project:
    code: str                          # e.g. "A1"
    name: str
    theme: str                         # e.g. "GREEN & BLUE INFRASTRUCTURE"
    theme_code: str                    # e.g. "A"
    description: List[str]             # bullet points
    kpis: List[str]
    # Cost bands in ₹ crore (small_city, medium_city, large_city)
    cost_band_low: float               # crore, for a small ULB
    cost_band_high: float              # crore, for a large ULB
    finance_instruments: List[str]     # preferred instruments
    green_eligible: bool = True        # qualifies for Green / Climate Bond
    revenue_generating: bool = False   # has user-fee revenue stream
    requires_env_clearance: bool = False
    reform_prerequisites: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Project catalog — one entry per sub-project
# ---------------------------------------------------------------------------

CATALOG: List[Project] = [
    # ────────────────────────────────────────────────────────────────────
    # A. GREEN & BLUE INFRASTRUCTURE
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="A1", name="Footpaths & Non-Motorized Transport (NMT)",
        theme="GREEN & BLUE INFRASTRUCTURE", theme_code="A",
        description=[
            "Accessible footpaths (disability-compliant, CPWD norms)",
            "Dedicated cycling lanes & cycle-sharing stations",
            "Pedestrian plazas and street greening",
            "Shade structures, tree-lined corridors",
        ],
        kpis=[
            "km of footpath built",
            "% compliant with disability norms",
            "modal shift %",
            "pedestrian injury rate reduction",
        ],
        cost_band_low=10, cost_band_high=150,
        finance_instruments=["General obligation bond", "UCF grant"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Master Plan / GIS-based property mapping complete",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="A2", name="Public Parks & Urban Green Spaces",
        theme="GREEN & BLUE INFRASTRUCTURE", theme_code="A",
        description=[
            "Neighbourhood parks (under 2 ha) and city parks (2–20 ha)",
            "Biodiversity parks and urban forests",
            "Pocket parks in high-density areas",
            "Sports and recreation grounds",
        ],
        kpis=[
            "m² of green space per capita (target ≥9 m²/person, WHO standard)",
            "tree canopy cover %",
            "park accessibility radius (% population within 400 m)",
        ],
        cost_band_low=5, cost_band_high=100,
        finance_instruments=["General obligation bond", "Green bond", "UCF grant"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
            "Master Plan / GIS-based property mapping complete",
        ],
    ),
    Project(
        code="A3", name="Urban Wetland & Waterbody Restoration",
        theme="GREEN & BLUE INFRASTRUCTURE", theme_code="A",
        description=[
            "Lake desilting and bund restoration",
            "Wetland biodiversity corridors",
            "Rejuvenation of rivers passing through urban areas",
            "Encroachment removal and riparian buffer zones",
        ],
        kpis=[
            "ha of wetland restored",
            "water storage capacity added (ML)",
            "species count improvement",
        ],
        cost_band_low=15, cost_band_high=200,
        finance_instruments=["Green bond", "Climate bond", "UCF grant"],
        green_eligible=True, revenue_generating=False,
        requires_env_clearance=True,
        reform_prerequisites=[
            "Environmental clearances initiated",
            "Master Plan / GIS-based property mapping complete",
        ],
    ),
    Project(
        code="A4", name="Urban Forestry & Tree Planting",
        theme="GREEN & BLUE INFRASTRUCTURE", theme_code="A",
        description=[
            "Avenue tree planting programs",
            "Rooftop gardens and vertical green walls on public buildings",
            "Miyawaki forests on vacant municipal land",
        ],
        kpis=[
            "trees planted",
            "survival rate at 3 years",
            "CO₂ sequestered (MT/year)",
            "urban heat island mitigation (°C reduction)",
        ],
        cost_band_low=2, cost_band_high=40,
        finance_instruments=["UCF grant", "Green bond", "General obligation bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="A5", name="Riverfront Development",
        theme="GREEN & BLUE INFRASTRUCTURE", theme_code="A",
        description=[
            "Ghats and promenades",
            "Flood control embankments with green design",
            "Integrated riverfront with NMT, parks, and cultural spaces",
        ],
        kpis=[
            "km of riverfront developed",
            "flood risk reduction (HH protected)",
            "footfall / usage",
        ],
        cost_band_low=30, cost_band_high=500,
        finance_instruments=["Green bond", "PPP – BOT", "Term loan (HUDCO/NaBFID)", "UCF grant"],
        green_eligible=True, revenue_generating=True,
        requires_env_clearance=True,
        reform_prerequisites=[
            "Environmental clearances initiated",
            "Master Plan / GIS-based property mapping complete",
            "SEBI-registered credit rating obtained",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # B. WATER & SANITATION
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="B1", name="Piped Water Supply (24×7)",
        theme="WATER & SANITATION", theme_code="B",
        description=[
            "Distribution network upgrades",
            "Water treatment plants (WTPs)",
            "Last-mile connections for underserved areas",
            "Non-revenue water (NRW) reduction — leakage detection, metering",
        ],
        kpis=[
            "% HH with 24×7 supply",
            "NRW % (target <20%)",
            "liters per capita per day (lpcd)",
            "% metered connections",
        ],
        cost_band_low=50, cost_band_high=1000,
        finance_instruments=["Revenue bond", "Term loan (HUDCO/NaBFID)", "Hybrid: grant + bond"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "User charge policy adopted (especially for water/SWM)",
            "Property tax coverage & collection efficiency target",
            "Own Source Revenue (OSR) improvement plan filed",
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="B2", name="Sewerage & Wastewater Treatment",
        theme="WATER & SANITATION", theme_code="B",
        description=[
            "Underground drainage (UGD) networks",
            "Sewage treatment plants (STPs) — conventional and nature-based",
            "Septage management for peri-urban areas",
            "Fecal sludge management (FSM)",
        ],
        kpis=[
            "% HH connected to sewer",
            "ML/day treated",
            "% treated to tertiary standard",
            "recycled water reuse %",
        ],
        cost_band_low=60, cost_band_high=1200,
        finance_instruments=["Term loan (HUDCO/NaBFID)", "Revenue bond", "Hybrid: grant + bond + PPP"],
        green_eligible=True, revenue_generating=True,
        requires_env_clearance=True,
        reform_prerequisites=[
            "User charge policy adopted (especially for water/SWM)",
            "Environmental clearances initiated",
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="B3", name="Stormwater Drainage & Flood Management",
        theme="WATER & SANITATION", theme_code="B",
        description=[
            "Primary/secondary/tertiary drain upgrades",
            "Retention ponds and detention basins",
            "Nature-based flood management (wetlands, permeable surfaces)",
            "Early warning systems",
        ],
        kpis=[
            "flood-prone area reduced (ha)",
            "drain coverage km",
            "properties de-risked",
            "flood event frequency reduction",
        ],
        cost_band_low=20, cost_band_high=400,
        finance_instruments=["General obligation bond", "Green bond", "UCF grant"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Master Plan / GIS-based property mapping complete",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="B4", name="Rainwater Harvesting & Groundwater Recharge",
        theme="WATER & SANITATION", theme_code="B",
        description=[
            "Recharge wells and percolation pits in parks/roads",
            "Mandatory rooftop RWH for public buildings",
            "Aquifer mapping and recharge zone protection",
        ],
        kpis=[
            "ML/year recharged",
            "groundwater table improvement (m)",
            "number of structures built",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["UCF grant", "General obligation bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="B5", name="Solid Waste Management",
        theme="WATER & SANITATION", theme_code="B",
        description=[
            "Door-to-door collection fleet (EV vehicles preferred)",
            "Wet waste: composting, biogas plants",
            "Dry waste: MRF (Material Recovery Facilities), recycling",
            "Construction & Demolition (C&D) waste processing",
            "Legacy landfill bioremediation",
            "Sanitary landfill development",
        ],
        kpis=[
            "% waste scientifically processed",
            "% source segregation",
            "MT landfill diverted/year",
            "biogas generated (m³/day)",
        ],
        cost_band_low=20, cost_band_high=300,
        finance_instruments=["Revenue bond", "PPP – DBFOT", "Hybrid: grant + bond + PPP"],
        green_eligible=True, revenue_generating=True,
        requires_env_clearance=True,
        reform_prerequisites=[
            "User charge policy adopted (especially for water/SWM)",
            "Environmental clearances initiated",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # C. CLEAN ENERGY & ENERGY EFFICIENCY
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="C1", name="Rooftop Solar on Municipal Buildings",
        theme="CLEAN ENERGY & ENERGY EFFICIENCY", theme_code="C",
        description=[
            "Municipal offices, schools, health centres, markets, pumping stations",
            "Group net metering / virtual net metering",
        ],
        kpis=[
            "MW installed",
            "kWh/year generated",
            "% municipal energy demand met by solar",
            "CO₂ avoided (MT/year)",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["Green bond", "Climate bond", "UCF grant"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="C2", name="Solar-Powered Street Lighting",
        theme="CLEAN ENERGY & ENERGY EFFICIENCY", theme_code="C",
        description=[
            "LED + solar hybrid streetlights",
            "Smart lighting with dimming and sensors",
            "Replacement of conventional high-energy streetlights",
        ],
        kpis=[
            "number of lights replaced",
            "% energy saving",
            "kWh/year saved",
            "payback period",
        ],
        cost_band_low=3, cost_band_high=50,
        finance_instruments=["Green bond", "UCF grant", "General obligation bond"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="C3", name="Energy Efficiency in Water & Sewage Pumping",
        theme="CLEAN ENERGY & ENERGY EFFICIENCY", theme_code="C",
        description=[
            "High-efficiency pumps and motors",
            "Variable frequency drives (VFDs)",
            "SCADA-based monitoring",
        ],
        kpis=[
            "% energy reduction in water operations",
            "kWh/ML pumped",
        ],
        cost_band_low=3, cost_band_high=60,
        finance_instruments=["Green bond", "UCF grant"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="C4", name="Waste-to-Energy",
        theme="CLEAN ENERGY & ENERGY EFFICIENCY", theme_code="C",
        description=[
            "Biogas from wet waste / STPs",
            "Power from landfill gas",
        ],
        kpis=[
            "MW capacity",
            "units generated/day",
            "waste diverted from landfill (MT/day)",
        ],
        cost_band_low=20, cost_band_high=300,
        finance_instruments=["PPP – BOT", "Revenue bond", "Green bond"],
        green_eligible=True, revenue_generating=True,
        requires_env_clearance=True,
        reform_prerequisites=[
            "Environmental clearances initiated",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="C5", name="EV Charging Infrastructure (Public)",
        theme="CLEAN ENERGY & ENERGY EFFICIENCY", theme_code="C",
        description=[
            "Public EV charging stations at parks, markets, transit hubs",
            "E-bus charging depots",
        ],
        kpis=[
            "number of charging points",
            "kWh dispensed/month",
            "% public fleet electrified",
        ],
        cost_band_low=5, cost_band_high=60,
        finance_instruments=["PPP – BOT", "Green bond", "UCF grant"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # D. CLIMATE ADAPTATION & RESILIENCE
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="D1", name="Urban Heat Island Mitigation",
        theme="CLIMATE ADAPTATION & RESILIENCE", theme_code="D",
        description=[
            "Cool roofs on public and low-income housing",
            "Reflective pavements and permeable surfaces",
            "Shade infrastructure: canopies, pergolas, green corridors",
        ],
        kpis=[
            "temperature reduction (°C) in target zones",
            "cool roof area (m²)",
            "heat-related illness reduction",
        ],
        cost_band_low=5, cost_band_high=100,
        finance_instruments=["Climate bond", "UCF grant", "General obligation bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="D2", name="Climate-Resilient Infrastructure Design",
        theme="CLIMATE ADAPTATION & RESILIENCE", theme_code="D",
        description=[
            "Retrofitting existing infrastructure to climate standards",
            "Vulnerability mapping and risk assessments",
            "Climate-proofing of roads, drains, public buildings",
        ],
        kpis=[
            "% infrastructure assessed",
            "% retrofitted",
            "risk score improvement",
        ],
        cost_band_low=10, cost_band_high=200,
        finance_instruments=["Climate bond", "General obligation bond", "UCF grant"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Master Plan / GIS-based property mapping complete",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="D3", name="Disaster Risk Reduction (DRR)",
        theme="CLIMATE ADAPTATION & RESILIENCE", theme_code="D",
        description=[
            "Early warning systems (flood, heatwave, cyclone)",
            "Emergency operation centres",
            "Community resilience programs",
        ],
        kpis=[
            "% population covered by early warning",
            "response time (hours)",
            "damage reduction (₹ crore)",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["UCF grant", "General obligation bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="D4", name="Air Quality Improvement",
        theme="CLIMATE ADAPTATION & RESILIENCE", theme_code="D",
        description=[
            "Dust suppression systems",
            "Green buffer zones near industrial/traffic corridors",
            "Clean fuel transitions for street vendors, small industry",
            "Real-time air quality monitoring network (AQMS)",
        ],
        kpis=[
            "PM2.5 / PM10 reduction (μg/m³)",
            "AQI improvement",
            "number of monitoring stations",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["UCF grant", "Green bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="D5", name="Urban Agriculture & Food Systems",
        theme="CLIMATE ADAPTATION & RESILIENCE", theme_code="D",
        description=[
            "Community gardens on municipal land",
            "Rooftop food gardens on public buildings",
            "Farmer markets and local food hubs",
        ],
        kpis=[
            "ha under urban agriculture",
            "kg/year produced",
            "HH food-secure",
            "₹ saved on food procurement",
        ],
        cost_band_low=2, cost_band_high=30,
        finance_instruments=["UCF grant", "General obligation bond"],
        green_eligible=True, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # E. SUSTAINABLE MOBILITY
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="E1", name="Bus Rapid Transit (BRT) & Public Transport",
        theme="SUSTAINABLE MOBILITY", theme_code="E",
        description=[
            "Dedicated bus lanes",
            "Bus shelters with real-time displays",
            "Integrated ticketing systems",
        ],
        kpis=[
            "daily ridership",
            "average speed (kmph)",
            "modal share of public transport %",
            "CO₂ avoided",
        ],
        cost_band_low=50, cost_band_high=800,
        finance_instruments=["Revenue bond", "PPP – DBFOT", "Green bond", "Term loan (HUDCO/NaBFID)"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
            "Own Source Revenue (OSR) improvement plan filed",
        ],
    ),
    Project(
        code="E2", name="Transit-Oriented Development (TOD)",
        theme="SUSTAINABLE MOBILITY", theme_code="E",
        description=[
            "Mixed-use development around transit nodes",
            "Densification of transit corridors",
            "Affordable housing near transit",
        ],
        kpis=[
            "FSI uplift monetized",
            "affordable units created",
            "car trips reduced/day",
        ],
        cost_band_low=30, cost_band_high=600,
        finance_instruments=["PPP – BOT", "Revenue bond", "Hybrid: grant + bond + PPP"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Master Plan / GIS-based property mapping complete",
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="E3", name="Parking Management & Demand Reduction",
        theme="SUSTAINABLE MOBILITY", theme_code="E",
        description=[
            "Smart parking systems",
            "Paid parking revenue recycling to public transport",
            "Park-and-ride facilities",
        ],
        kpis=[
            "parking revenue (₹/year)",
            "average search time reduction",
            "car trips to CBD reduced %",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["Revenue bond", "PPP – BOT"],
        green_eligible=False, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="E4", name="Waterways & Non-Motorized Freight",
        theme="SUSTAINABLE MOBILITY", theme_code="E",
        description=[
            "Inland waterway use for freight (where applicable)",
            "Cargo cycles and electric cargo vehicles for last-mile delivery",
        ],
        kpis=[
            "MT freight shifted",
            "diesel consumption avoided",
            "CO₂ avoided",
        ],
        cost_band_low=10, cost_band_high=150,
        finance_instruments=["Green bond", "PPP – BOT", "UCF grant"],
        green_eligible=True, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # F. HERITAGE & PLACE-MAKING
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="F1", name="Heritage Core Restoration",
        theme="HERITAGE & PLACE-MAKING", theme_code="F",
        description=[
            "Restoration of historic buildings, havelis, ghats",
            "Heritage walks and cultural tourism infrastructure",
        ],
        kpis=[
            "structures restored",
            "tourist footfall",
            "local artisan jobs created",
        ],
        cost_band_low=10, cost_band_high=200,
        finance_instruments=["UCF grant", "General obligation bond", "PPP – BOT"],
        green_eligible=False, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="F2", name="Public Plazas & People-First Streets",
        theme="HERITAGE & PLACE-MAKING", theme_code="F",
        description=[
            "Open plazas, stepped squares, seating areas",
            "Street redesign (car-free zones, pedestrianization)",
            "Markets and street vendor zones formalized",
        ],
        kpis=[
            "m² of public space created",
            "street vendor livelihoods",
            "pedestrian footfall",
        ],
        cost_band_low=5, cost_band_high=80,
        finance_instruments=["General obligation bond", "UCF grant"],
        green_eligible=False, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
            "Master Plan / GIS-based property mapping complete",
        ],
    ),
    Project(
        code="F3", name="Creative Districts & Mixed-Use Redevelopment",
        theme="HERITAGE & PLACE-MAKING", theme_code="F",
        description=[
            "Brownfield conversion to creative/innovation hubs",
            "Adaptive reuse of old government buildings",
        ],
        kpis=[
            "floor space redeveloped (m²)",
            "jobs created",
            "private investment catalyzed (₹ crore)",
        ],
        cost_band_low=20, cost_band_high=400,
        finance_instruments=["PPP – BOT", "Revenue bond", "Hybrid: grant + bond + PPP"],
        green_eligible=False, revenue_generating=True,
        reform_prerequisites=[
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),

    # ────────────────────────────────────────────────────────────────────
    # G. INCLUSIVE & SOCIAL INFRASTRUCTURE
    # ────────────────────────────────────────────────────────────────────
    Project(
        code="G1", name="Affordable Housing near Transit & Jobs",
        theme="INCLUSIVE & SOCIAL INFRASTRUCTURE", theme_code="G",
        description=[
            "In-situ slum redevelopment",
            "Rental housing for urban workers",
        ],
        kpis=[
            "units created",
            "% below market rate",
            "proximity to transit (metres)",
        ],
        cost_band_low=30, cost_band_high=600,
        finance_instruments=["PPP – DBFOT", "Term loan (HUDCO/NaBFID)", "Hybrid: grant + bond + PPP"],
        green_eligible=False, revenue_generating=True,
        reform_prerequisites=[
            "Master Plan / GIS-based property mapping complete",
            "SEBI-registered credit rating obtained",
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="G2", name="Public Toilets & Sanitation Facilities",
        theme="INCLUSIVE & SOCIAL INFRASTRUCTURE", theme_code="G",
        description=[
            "Gender-segregated, disability-accessible toilets in public spaces",
            "Pink toilets and women's safety facilities",
        ],
        kpis=[
            "seats per 1,000 population",
            "% functional",
            "female usage rate",
        ],
        cost_band_low=5, cost_band_high=40,
        finance_instruments=["UCF grant", "General obligation bond"],
        green_eligible=False, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="G3", name="Urban Health Centres & Public Wellness",
        theme="INCLUSIVE & SOCIAL INFRASTRUCTURE", theme_code="G",
        description=[
            "Primary Urban Health Centres (PUHC)",
            "Open fitness equipment in parks",
        ],
        kpis=[
            "OPD visits/month",
            "distance to nearest health facility (km)",
        ],
        cost_band_low=5, cost_band_high=60,
        finance_instruments=["UCF grant", "General obligation bond"],
        green_eligible=False, revenue_generating=False,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
        ],
    ),
    Project(
        code="G4", name="Digital & Smart City Infrastructure",
        theme="INCLUSIVE & SOCIAL INFRASTRUCTURE", theme_code="G",
        description=[
            "City-wide fiber optic backbone",
            "Open data portals and dashboards",
            "Integrated Command and Control Centres (ICCC)",
        ],
        kpis=[
            "% city covered by broadband",
            "datasets published",
            "response time to citizen grievances",
        ],
        cost_band_low=15, cost_band_high=300,
        finance_instruments=["PPP – BOT", "General obligation bond", "Term loan (HUDCO/NaBFID)"],
        green_eligible=False, revenue_generating=True,
        reform_prerequisites=[
            "Annual audited accounts up to date (last 3 years)",
            "SEBI-registered credit rating obtained",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

CATALOG_BY_CODE: dict[str, Project] = {p.code: p for p in CATALOG}
THEMES = sorted({p.theme for p in CATALOG})


def get_projects_by_theme(theme_code: str) -> List[Project]:
    return [p for p in CATALOG if p.theme_code == theme_code.upper()]


def get_project(code: str) -> Optional[Project]:
    return CATALOG_BY_CODE.get(code.upper())
