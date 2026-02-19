"""
UCF Financial Structuring Engine

Computes cost bands, UCF/market/state splits, maps projects to finance
instruments, generates reform checklists, and flags risk factors for a
given city profile and project selection.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from catalog import Project, CATALOG_BY_CODE

# ---------------------------------------------------------------------------
# UCF split ratios (standard structure)
# ---------------------------------------------------------------------------
UCF_GRANT_RATIO = 0.25          # 25% from UCF
MARKET_FINANCE_RATIO = 0.50     # 50% market instruments
STATE_ULB_RATIO = 0.25          # 25% state / ULB own funds

# ---------------------------------------------------------------------------
# Population tier thresholds (lakhs)
# ---------------------------------------------------------------------------
TIER_BANDS = {
    "Tier 1 (>40 lakh)": (40, float("inf")),
    "Tier 2 (10–40 lakh)": (10, 40),
    "Tier 3 (<10 lakh)": (0, 10),
}

# ---------------------------------------------------------------------------
# Data classes for outputs
# ---------------------------------------------------------------------------

@dataclass
class CostEstimate:
    project_code: str
    project_name: str
    estimated_cost_crore: float      # midpoint of cost band for tier
    ucf_grant: float
    market_finance: float
    state_ulb_share: float
    credit_guarantee_eligible: bool


@dataclass
class FinanceStack:
    project_code: str
    project_name: str
    instruments: List[str]
    green_bond_eligible: bool


@dataclass
class RiskFlag:
    severity: str          # HIGH / MEDIUM / LOW
    description: str
    mitigation: str


@dataclass
class StructuredOutput:
    city: str
    state: str
    population_tier: str
    selected_projects: List[Project]
    cost_estimates: List[CostEstimate]
    finance_stacks: List[FinanceStack]
    reform_checklist: List[str]
    kpis: Dict[str, List[str]]
    risk_flags: List[RiskFlag]

    # Aggregated totals
    @property
    def total_cost(self) -> float:
        return sum(c.estimated_cost_crore for c in self.cost_estimates)

    @property
    def total_ucf(self) -> float:
        return sum(c.ucf_grant for c in self.cost_estimates)

    @property
    def total_market(self) -> float:
        return sum(c.market_finance for c in self.cost_estimates)

    @property
    def total_state_ulb(self) -> float:
        return sum(c.state_ulb_share for c in self.cost_estimates)


# ---------------------------------------------------------------------------
# Core structuring logic
# ---------------------------------------------------------------------------

def classify_tier(population_lakh: float) -> str:
    for label, (lo, hi) in TIER_BANDS.items():
        if lo <= population_lakh < hi:
            return label
    return "Tier 3 (<10 lakh)"


def _cost_midpoint(project: Project, tier: str) -> float:
    """Scale cost midpoint based on population tier."""
    if "Tier 1" in tier:
        return project.cost_band_high * 0.80
    elif "Tier 2" in tier:
        return (project.cost_band_low + project.cost_band_high) / 2
    else:
        return project.cost_band_low * 1.20


def _credit_guarantee_eligible(project: Project) -> bool:
    """Eligible if revenue-generating and uses a bond or term loan."""
    bond_instruments = {"Revenue bond", "General obligation bond", "Green bond",
                        "Climate bond", "Term loan (HUDCO/NaBFID)"}
    return project.revenue_generating and bool(
        bond_instruments.intersection(project.finance_instruments)
    )


def compute_cost_estimates(projects: List[Project], tier: str) -> List[CostEstimate]:
    estimates = []
    for p in projects:
        cost = round(_cost_midpoint(p, tier), 1)
        estimates.append(CostEstimate(
            project_code=p.code,
            project_name=p.name,
            estimated_cost_crore=cost,
            ucf_grant=round(cost * UCF_GRANT_RATIO, 1),
            market_finance=round(cost * MARKET_FINANCE_RATIO, 1),
            state_ulb_share=round(cost * STATE_ULB_RATIO, 1),
            credit_guarantee_eligible=_credit_guarantee_eligible(p),
        ))
    return estimates


def compute_finance_stacks(projects: List[Project]) -> List[FinanceStack]:
    return [
        FinanceStack(
            project_code=p.code,
            project_name=p.name,
            instruments=p.finance_instruments,
            green_bond_eligible=p.green_eligible,
        )
        for p in projects
    ]


def compile_reform_checklist(projects: List[Project]) -> List[str]:
    """Deduplicated, ordered reform prerequisites across all selected projects."""
    seen = set()
    checklist = []
    for p in projects:
        for req in p.reform_prerequisites:
            if req not in seen:
                seen.add(req)
                checklist.append(req)
    # Always include the baseline items
    baseline = [
        "Property tax coverage & collection efficiency target",
        "Own Source Revenue (OSR) improvement plan filed",
        "SEBI-registered credit rating obtained",
        "Annual audited accounts up to date (last 3 years)",
        "Master Plan / GIS-based property mapping complete",
        "User charge policy adopted (especially for water/SWM)",
        "Environmental clearances initiated",
    ]
    for item in baseline:
        if item not in seen:
            seen.add(item)
            checklist.append(item)
    return checklist


def compile_kpis(projects: List[Project]) -> Dict[str, List[str]]:
    return {p.code: p.kpis for p in projects}


def assess_risks(
    projects: List[Project],
    population_lakh: float,
    has_bond_history: bool,
    osr_ratio: Optional[float],   # own-source revenue / total expenditure
    has_credit_rating: bool,
) -> List[RiskFlag]:
    """
    Generate top risk flags for this city profile.

    Parameters
    ----------
    osr_ratio : float or None
        Share of expenditure covered by own-source revenue (0–1).
        None = unknown.
    """
    flags: List[RiskFlag] = []

    # Risk 1 — Low own-source revenue
    if osr_ratio is not None and osr_ratio < 0.30:
        flags.append(RiskFlag(
            severity="HIGH",
            description="Low Own Source Revenue (OSR < 30% of expenditure) limits debt "
                        "service capacity and UCF eligibility.",
            mitigation="File a time-bound OSR improvement plan; adopt user charges for "
                       "water, SWM, and parking before UCF application.",
        ))

    # Risk 2 — No bond history
    if not has_bond_history:
        flags.append(RiskFlag(
            severity="HIGH",
            description="No municipal bond issuance history. Lenders will price in higher "
                        "risk premium or decline.",
            mitigation="Obtain SEBI credit rating first; consider a smaller debut bond or "
                       "HUDCO term loan to establish track record.",
        ))

    # Risk 3 — No credit rating
    if not has_credit_rating:
        flags.append(RiskFlag(
            severity="HIGH",
            description="No SEBI-registered credit rating. Mandatory for revenue bonds and "
                        "market finance instruments.",
            mitigation="Commission a rating agency (CRISIL, ICRA, CARE, India Ratings) "
                       "at least 12 months before bond issuance.",
        ))

    # Risk 4 — Environmental clearances missing for high-impact projects
    needs_ec = [p for p in projects if p.requires_env_clearance]
    if needs_ec:
        codes = ", ".join(p.code for p in needs_ec)
        flags.append(RiskFlag(
            severity="MEDIUM",
            description=f"Projects {codes} require Environmental Clearance (EC). "
                        "Delays in EC can stall construction and debt drawdown.",
            mitigation="Initiate EIA studies and file for EC in parallel with DPR "
                       "preparation. Build 12-month EC buffer into project timeline.",
        ))

    # Risk 5 — Overlapping jurisdiction / large Tier-1 city
    if population_lakh > 40:
        flags.append(RiskFlag(
            severity="MEDIUM",
            description="Large city: risk of overlapping jurisdiction with Development "
                        "Authority or Parastatal, creating implementation bottlenecks.",
            mitigation="Define clear project boundaries in MoU; include nodal agency "
                       "coordination clause in financial agreements.",
        ))

    # Risk 6 — Very small ULB, large capital programme
    if population_lakh < 5:
        flags.append(RiskFlag(
            severity="MEDIUM",
            description="Small ULB with limited institutional capacity to manage large "
                        "multi-project capital programme.",
            mitigation="Engage PMC (Project Management Consultant) early; consider "
                       "state-level pooled financing vehicle.",
        ))

    # Cap at top 5 for readability
    return flags[:5]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def structure_projects(
    city: str,
    state: str,
    population_lakh: float,
    project_codes: List[str],
    has_bond_history: bool = False,
    osr_ratio: Optional[float] = None,
    has_credit_rating: bool = False,
) -> StructuredOutput:
    """
    Full financial structuring for a ULB and selected project codes.

    Returns a StructuredOutput with cost table, finance stacks, reform
    checklist, KPIs, and risk flags.
    """
    projects = []
    for code in project_codes:
        p = CATALOG_BY_CODE.get(code.upper())
        if p is None:
            raise ValueError(f"Unknown project code: {code!r}")
        projects.append(p)

    tier = classify_tier(population_lakh)

    return StructuredOutput(
        city=city,
        state=state,
        population_tier=tier,
        selected_projects=projects,
        cost_estimates=compute_cost_estimates(projects, tier),
        finance_stacks=compute_finance_stacks(projects),
        reform_checklist=compile_reform_checklist(projects),
        kpis=compile_kpis(projects),
        risk_flags=assess_risks(
            projects, population_lakh, has_bond_history, osr_ratio, has_credit_rating
        ),
    )
