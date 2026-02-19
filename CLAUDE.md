# CLAUDE.md — UCF Advisor: Urban Climate Finance Project Structuring

This file is the primary guide for AI assistants (Claude and others) working
on this codebase. Read it fully before making any change.

---

## 1. What this project does

**UCF Advisor** is a Python tool that helps Indian Urban Local Bodies (ULBs)
structure their sustainability projects for the Urban Climate Finance (UCF)
framework. Given a city profile and a selection of project types, it produces:

- Estimated cost bands and UCF / market / state funding splits
- Recommended finance instruments (bonds, PPP, term loans)
- A reform prerequisites checklist the city must complete before funds release
- Investor-facing KPIs for bond prospectuses and challenge applications
- Risk flag analysis based on the city's financial profile

The tool is intended to be run:
1. **Interactively** by city planners (`python ucf_advisor.py`)
2. **Non-interactively** from a JSON input file (`python ucf_advisor.py --json input.json`)
3. **Embedded** in a larger AI assistant system where the functions in
   `finance.py` are called programmatically

---

## 2. Codebase structure

```
.
├── catalog.py        # Project catalog — all data lives here
├── finance.py        # Financial structuring engine
├── ucf_advisor.py    # CLI entry point and rendering layer
├── requirements.txt  # No third-party dependencies (stdlib only)
├── README.md         # Quick-start for humans
└── CLAUDE.md         # This file
```

### 2.1 `catalog.py`

Single source of truth for all project data. Contains:

| Symbol | Type | Description |
|---|---|---|
| `Project` | `@dataclass` | One sustainability project type |
| `CATALOG` | `List[Project]` | All 31 projects ordered by theme code |
| `CATALOG_BY_CODE` | `dict[str, Project]` | Fast lookup by code (e.g. `"B1"`) |
| `THEMES` | `List[str]` | Alphabetically sorted theme names |
| `get_projects_by_theme(theme_code)` | function | Filter by `"A"`, `"B"`, … `"G"` |
| `get_project(code)` | function | Returns `Project` or `None` |

**Key `Project` fields:**

| Field | Meaning |
|---|---|
| `code` | Unique id, format `<ThemeCode><Number>` e.g. `A1`, `G4` |
| `theme_code` | Single uppercase letter `A`–`G` |
| `cost_band_low / high` | ₹ crore range for smallest / largest applicable city |
| `finance_instruments` | Ordered list, most preferred first |
| `green_eligible` | Whether project qualifies for Green/Climate bond label |
| `revenue_generating` | Whether project has user-fee income stream |
| `requires_env_clearance` | Needs Environmental Clearance (triggers risk flag) |
| `reform_prerequisites` | Preconditions tied to this project |

**When adding a new project:** append a `Project(...)` entry to `CATALOG`.
Do not change the ordering of existing entries — `CATALOG_BY_CODE` is built
from `CATALOG` at import time.

### 2.2 `finance.py`

Pure computation — no I/O, no side effects. Contains:

| Symbol | Description |
|---|---|
| `UCF_GRANT_RATIO` | 0.25 (25%) — never change without policy update |
| `MARKET_FINANCE_RATIO` | 0.50 (50%) |
| `STATE_ULB_RATIO` | 0.25 (25%) |
| `CostEstimate` | Per-project cost and split amounts |
| `FinanceStack` | Per-project recommended instruments |
| `RiskFlag` | severity + description + mitigation text |
| `StructuredOutput` | Aggregate result (dataclass with computed properties) |
| `structure_projects(...)` | **Main entry point** — returns `StructuredOutput` |

`structure_projects` signature:
```python
def structure_projects(
    city: str,
    state: str,
    population_lakh: float,
    project_codes: List[str],
    has_bond_history: bool = False,
    osr_ratio: Optional[float] = None,   # 0.0–1.0
    has_credit_rating: bool = False,
) -> StructuredOutput
```

Raises `ValueError` for unknown project codes. All codes are
case-insensitively normalised inside the function.

**Cost scaling logic** (`_cost_midpoint`):

| Tier | Cost used |
|---|---|
| Tier 1 (>40 lakh pop.) | 80% of `cost_band_high` |
| Tier 2 (10–40 lakh) | midpoint of band |
| Tier 3 (<10 lakh) | 120% of `cost_band_low` |

### 2.3 `ucf_advisor.py`

CLI and rendering layer. Key functions:

| Function | Purpose |
|---|---|
| `render_catalog()` | ASCII project menu |
| `render_full_report(out)` | Combines all five sections into printable report |
| `render_summary_table(out)` | Section 1 — cost table |
| `render_finance_stacks(out)` | Section 2 — instrument mapping |
| `render_reform_checklist(out)` | Section 3 — reform checklist |
| `render_kpis(out)` | Section 4 — KPI table |
| `render_risk_flags(out)` | Section 5 — risk flags |
| `run_interactive(out_path)` | Guided CLI session |
| `run_from_json(json_path, out_path)` | Batch / headless mode |
| `main()` | argparse entry point |

---

## 3. Data model — The 31 projects

### Theme A — Green & Blue Infrastructure
| Code | Name |
|---|---|
| A1 | Footpaths & Non-Motorized Transport (NMT) |
| A2 | Public Parks & Urban Green Spaces |
| A3 | Urban Wetland & Waterbody Restoration |
| A4 | Urban Forestry & Tree Planting |
| A5 | Riverfront Development |

### Theme B — Water & Sanitation
| Code | Name |
|---|---|
| B1 | Piped Water Supply (24×7) |
| B2 | Sewerage & Wastewater Treatment |
| B3 | Stormwater Drainage & Flood Management |
| B4 | Rainwater Harvesting & Groundwater Recharge |
| B5 | Solid Waste Management |

### Theme C — Clean Energy & Energy Efficiency
| Code | Name |
|---|---|
| C1 | Rooftop Solar on Municipal Buildings |
| C2 | Solar-Powered Street Lighting |
| C3 | Energy Efficiency in Water & Sewage Pumping |
| C4 | Waste-to-Energy |
| C5 | EV Charging Infrastructure (Public) |

### Theme D — Climate Adaptation & Resilience
| Code | Name |
|---|---|
| D1 | Urban Heat Island Mitigation |
| D2 | Climate-Resilient Infrastructure Design |
| D3 | Disaster Risk Reduction (DRR) |
| D4 | Air Quality Improvement |
| D5 | Urban Agriculture & Food Systems |

### Theme E — Sustainable Mobility
| Code | Name |
|---|---|
| E1 | Bus Rapid Transit (BRT) & Public Transport |
| E2 | Transit-Oriented Development (TOD) |
| E3 | Parking Management & Demand Reduction |
| E4 | Waterways & Non-Motorized Freight |

### Theme F — Heritage & Place-Making
| Code | Name |
|---|---|
| F1 | Heritage Core Restoration |
| F2 | Public Plazas & People-First Streets |
| F3 | Creative Districts & Mixed-Use Redevelopment |

### Theme G — Inclusive & Social Infrastructure
| Code | Name |
|---|---|
| G1 | Affordable Housing near Transit & Jobs |
| G2 | Public Toilets & Sanitation Facilities |
| G3 | Urban Health Centres & Public Wellness |
| G4 | Digital & Smart City Infrastructure |

---

## 4. Finance instruments — reference definitions

| Instrument | When to recommend |
|---|---|
| **Revenue bond** | Project has a reliable user-fee stream (water tariffs, parking fees, market rents). Bond serviced from project revenues. |
| **General obligation bond** | Public good with no direct revenue (footpaths, parks, drainage). Serviced from ULB's tax base. |
| **Green bond / Climate bond** | Project is `green_eligible=True` and can be third-party verified against GBP/CBI taxonomy. |
| **PPP – BOT** | Private party builds, operates, transfers; takes revenue risk. Suited to parking, markets, EV charging. |
| **PPP – DBFOT** | Private party designs, builds, finances, operates, transfers. Suited to large infra (BRT, STP). |
| **Term loan (HUDCO/NaBFID)** | Long-tenor project finance for capital-heavy projects with tariff backstop (WTP, STP). |
| **UCF grant** | 25% first-loss grant from UCF; always part of the stack; not a standalone instrument. |
| **Hybrid: grant + bond + PPP** | Three-layer stack used for large, complex projects needing blended finance. |

**Rule:** A project should appear in at most two recommended instruments in
the primary position. The UCF grant is implicit in all stacks and listed
separately.

---

## 5. UCF funding mechanics

UCF = Urban Climate Finance programme (GoI / multilateral backed).

Standard stack:
```
Total project cost  =  25% UCF grant
                     + 50% market finance (bond / loan / PPP)
                     + 25% state / ULB contribution
```

Credit guarantee: Projects with `revenue_generating=True` and at least one
bond or term-loan instrument may be eligible for a credit guarantee from UCF
or a DFI (Development Finance Institution). The tool marks these with ✓ in
the cost table.

---

## 6. Reform prerequisites — master list

These are the seven standard reforms UCF requires. The tool surfaces only
those relevant to the selected projects plus always appends any missing items
from this list:

1. Property tax coverage & collection efficiency target
2. Own Source Revenue (OSR) improvement plan filed
3. SEBI-registered credit rating obtained
4. Annual audited accounts up to date (last 3 years)
5. Master Plan / GIS-based property mapping complete
6. User charge policy adopted (especially for water/SWM)
7. Environmental clearances initiated

Do not remove or rename these strings — they are matched by equality in tests.

---

## 7. Risk assessment rules

`assess_risks()` in `finance.py` generates up to 5 flags (capped for
readability). Current rules:

| Condition | Severity |
|---|---|
| `osr_ratio < 0.30` | HIGH |
| `has_bond_history == False` | HIGH |
| `has_credit_rating == False` | HIGH |
| Any selected project has `requires_env_clearance=True` | MEDIUM |
| `population_lakh > 40` (large city, jurisdiction overlap) | MEDIUM |
| `population_lakh < 5` (small ULB, capacity gap) | MEDIUM |

When adding new risk rules, follow the same pattern: check a condition,
append a `RiskFlag(severity, description, mitigation)`, cap the list at 5.

---

## 8. JSON input format

For non-interactive / API-driven use:

```json
{
  "city": "Nagpur",
  "state": "Maharashtra",
  "population_lakh": 24.0,
  "project_codes": ["B1", "C1", "C2", "A2"],
  "has_bond_history": true,
  "has_credit_rating": true,
  "osr_ratio": 0.42
}
```

Required keys: `city`, `state`, `population_lakh`, `project_codes`
Optional keys: `has_bond_history` (default `false`), `has_credit_rating`
(default `false`), `osr_ratio` (default `null`)

---

## 9. Development conventions

### Style
- Python 3.10+. Standard library only (no pip dependencies).
- All new data lives in `catalog.py`. Never hardcode project data
  in `finance.py` or `ucf_advisor.py`.
- Functions in `finance.py` must be pure (no I/O, no global mutation).
- Use `@dataclass` for structured data. Avoid raw dicts for domain objects.
- Keep rendering logic in `ucf_advisor.py`, not in `finance.py`.

### Adding a project
1. Append a new `Project(...)` to `CATALOG` in `catalog.py`.
2. Choose the correct `theme_code` (`A`–`G`). If creating a new theme,
   add a heading comment, update the theme table in this CLAUDE.md.
3. Set `cost_band_low` and `cost_band_high` in ₹ crore (not lakhs, not millions).
4. Set `green_eligible=True` if the project qualifies under ICMA Green Bond
   Principles (climate mitigation / adaptation / natural resources /
   biodiversity categories).
5. Set `revenue_generating=True` only if there is a direct, enforceable
   user-fee stream (not just indirect savings).
6. List `finance_instruments` in preference order (most appropriate first).
7. Run the smoke test below to verify nothing breaks.

### Changing cost band or split ratios
- Cost bands: update the `Project(...)` in `catalog.py`.
- UCF / market / state ratios: update the three constants at the top of
  `finance.py` (`UCF_GRANT_RATIO`, `MARKET_FINANCE_RATIO`, `STATE_ULB_RATIO`).
  These must always sum to 1.0.

### Running the smoke test
```bash
python -c "
from finance import structure_projects
out = structure_projects('TestCity', 'TestState', 15.0, ['A1','B1','C1'])
assert out.total_cost > 0
assert abs(out.total_ucf + out.total_market + out.total_state_ulb - out.total_cost) < 0.5
print('Smoke test passed. Total cost: ₹', out.total_cost, 'crore')
"
```

Expected output: `Smoke test passed. Total cost: ₹ <number> crore`

---

## 10. AI assistant behaviour guidelines

When a ULB begins a session with this tool (or with an AI assistant backed
by this codebase), the assistant should:

### 10.1 Session opening
- Ask for city name, state, and population.
- Ask whether they want to browse the full catalog or jump directly to
  specific themes.
- Never pre-select projects on behalf of the user.

### 10.2 Project selection
- Present projects theme by theme (A → G).
- For each project, briefly explain what it covers before the user commits.
- Allow multi-select within and across themes.
- After selection, confirm the list and allow corrections.

### 10.3 Financial structuring output
After project selection, always produce all five sections **in order**:
1. Project Summary Table (with total cost and UCF/market/state split)
2. Recommended Finance Instruments per Project
3. Reform Prerequisites Checklist
4. Key Impact KPIs for Bond Prospectus / UCF Application
5. Risk Flag Summary

Do not skip any section. If a section has no content (e.g. no risk flags),
state that explicitly rather than omitting the section header.

### 10.4 KPI guidance
When presenting KPIs, include:
- The KPI name exactly as it appears in `catalog.py`
- A blank "Baseline:" field for the ULB to fill in
- A blank "Target:" field
- A note on measurement method or data source

Do not invent KPIs not listed in the catalog. If a ULB asks for a KPI
not in the catalog, note that it is a custom addition and flag it clearly.

### 10.5 Finance instrument guidance
- Always explain why each instrument is recommended for each project.
- If the ULB has `has_bond_history=False`, highlight this as a risk and
  suggest HUDCO term loans as a safer first step.
- If `has_credit_rating=False`, emphasize this must be resolved before
  any market instrument can be used.

### 10.6 Reform checklist guidance
- Present the checklist as checkboxes the ULB can work through.
- Explain what each reform involves in 1–2 sentences if the user asks.
- Prioritise: credit rating → audited accounts → user charge policy.

### 10.7 What the assistant must NOT do
- Do not provide legal, accounting, or regulatory advice.
- Do not guarantee that a city will receive UCF funding.
- Do not alter cost estimates beyond the ranges in `catalog.py`.
- Do not recommend a project the user has not selected.
- Do not invent finance instruments not in the reference list (Section 4).

---

## 11. Glossary

| Term | Meaning |
|---|---|
| ULB | Urban Local Body (municipal corporation, council, or nagar panchayat) |
| UCF | Urban Climate Finance — GoI programme for climate-resilient city infra |
| DFI | Development Finance Institution (HUDCO, NaBFID, etc.) |
| OSR | Own Source Revenue (property tax, fees, rentals) |
| NRW | Non-Revenue Water — water lost before billing |
| FSI | Floor Space Index — plot coverage multiplier in land use policy |
| BOT | Build-Operate-Transfer PPP model |
| DBFOT | Design-Build-Finance-Operate-Transfer PPP model |
| DPR | Detailed Project Report |
| EIA | Environmental Impact Assessment |
| SEBI | Securities and Exchange Board of India |
| GBP | Green Bond Principles (ICMA) |
| CBI | Climate Bonds Initiative taxonomy |
| MRF | Material Recovery Facility (dry waste recycling plant) |
| STP | Sewage Treatment Plant |
| WTP | Water Treatment Plant |
| AQMS | Air Quality Monitoring Station |
| CPWD | Central Public Works Department (sets accessibility standards) |
| ICCC | Integrated Command and Control Centre (Smart City ops room) |
| NMT | Non-Motorized Transport (cycling, walking) |
| TOD | Transit-Oriented Development |
| BRT | Bus Rapid Transit |

---

## 12. Extending the system

### Adding a new theme (H, I, …)
1. Choose a single-letter code not already in use.
2. Add projects in `catalog.py` with `theme_code="H"`.
3. Update the theme table in Section 3 of this CLAUDE.md.
4. No changes required in `finance.py` or `ucf_advisor.py` — they are
   theme-agnostic.

### Internationalisation
All cost figures are in Indian Rupees (₹ crore). If adapting for another
country:
- Change currency symbol and unit in `ucf_advisor.py` (search for `₹`).
- Update `cost_band_low` / `cost_band_high` in all `Project` entries.
- Update the UCF split ratios in `finance.py` to match local programme rules.

### API / programmatic embedding
Import and call directly:
```python
from finance import structure_projects
from ucf_advisor import render_full_report

out = structure_projects(
    city="Indore",
    state="Madhya Pradesh",
    population_lakh=33.0,
    project_codes=["B1", "B2", "C1", "A2", "E1"],
    has_bond_history=True,
    has_credit_rating=True,
    osr_ratio=0.45,
)
print(render_full_report(out))
```

`StructuredOutput` exposes `.total_cost`, `.total_ucf`, `.total_market`,
`.total_state_ulb` as computed properties. Individual `CostEstimate` objects
are in `out.cost_estimates`. Risk flags are in `out.risk_flags`.
