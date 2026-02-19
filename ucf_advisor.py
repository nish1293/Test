#!/usr/bin/env python3
"""
UCF Advisor — Urban Climate Finance Project Structuring CLI

Usage
-----
Interactive mode (guided prompts):
    python ucf_advisor.py

Non-interactive / JSON input:
    python ucf_advisor.py --json input.json

Output to file:
    python ucf_advisor.py --out report.txt

Help:
    python ucf_advisor.py --help
"""

from __future__ import annotations
import argparse
import json
import sys
import textwrap
from typing import List, Optional

from catalog import CATALOG, CATALOG_BY_CODE, THEMES, get_projects_by_theme
from finance import StructuredOutput, structure_projects

# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

SEP = "─" * 72
THICK = "═" * 72


def _h1(text: str) -> str:
    return f"\n{THICK}\n  {text}\n{THICK}"


def _h2(text: str) -> str:
    return f"\n{SEP}\n  {text}\n{SEP}"


def render_catalog() -> str:
    lines = [_h1("UCF PROJECT CATALOG — URBAN SUSTAINABILITY MENU")]
    lines.append(
        "  Select one or more projects. You will be prompted for each theme.\n"
    )
    prev_theme = None
    for p in CATALOG:
        if p.theme != prev_theme:
            lines.append(f"\n  {'▶':>2}  {p.theme_code}. {p.theme}")
            prev_theme = p.theme
        desc_preview = p.description[0] if p.description else ""
        lines.append(f"       [{p.code:>2}]  {p.name}")
        lines.append(f"              {desc_preview}")
    return "\n".join(lines)


def render_summary_table(out: StructuredOutput) -> str:
    rows = [
        ("City & State", f"{out.city}, {out.state}"),
        ("Population Tier", out.population_tier),
        ("Selected Projects", ", ".join(p.code for p in out.selected_projects)),
        ("Total Estimated Cost", f"₹ {out.total_cost:,.1f} crore"),
        ("UCF Eligible (25%)", f"₹ {out.total_ucf:,.1f} crore"),
        ("Market Finance Required (50%)", f"₹ {out.total_market:,.1f} crore"),
        ("State / ULB Share (25%)", f"₹ {out.total_state_ulb:,.1f} crore"),
        (
            "Credit Guarantee Eligible",
            "Yes" if any(c.credit_guarantee_eligible for c in out.cost_estimates) else "No",
        ),
    ]
    lines = [_h2("1. PROJECT SUMMARY TABLE")]
    col_w = max(len(r[0]) for r in rows) + 2
    for label, value in rows:
        lines.append(f"  {label:<{col_w}} {value}")
    lines.append("")

    # Per-project cost breakdown
    lines.append("  Per-Project Cost Breakdown:")
    lines.append(f"  {'Code':<5} {'Project':<45} {'Total ₹Cr':>9} {'UCF':>7} {'Mkt':>7} {'S/ULB':>7}")
    lines.append("  " + "-" * 78)
    for c in out.cost_estimates:
        name = c.project_name[:43]
        cg = " ✓" if c.credit_guarantee_eligible else ""
        lines.append(
            f"  {c.project_code:<5} {name:<45} "
            f"{c.estimated_cost_crore:>8.1f} "
            f"{c.ucf_grant:>7.1f} "
            f"{c.market_finance:>7.1f} "
            f"{c.state_ulb_share:>7.1f}{cg}"
        )
    lines.append("  (✓ = Credit Guarantee Eligible)")
    return "\n".join(lines)


def render_finance_stacks(out: StructuredOutput) -> str:
    lines = [_h2("2. RECOMMENDED FINANCE INSTRUMENTS PER PROJECT")]
    for fs in out.finance_stacks:
        lines.append(f"\n  [{fs.project_code}] {fs.project_name}")
        for inst in fs.instruments:
            lines.append(f"       • {inst}")
        if fs.green_bond_eligible:
            lines.append("       ★ Green / Climate Bond eligible")
    return "\n".join(lines)


def render_reform_checklist(out: StructuredOutput) -> str:
    lines = [_h2("3. REFORM PREREQUISITES CHECKLIST")]
    lines.append(
        "  All items below must be completed (or substantially advanced)\n"
        "  before UCF funds are released.\n"
    )
    for item in out.reform_checklist:
        lines.append(f"  [ ] {item}")
    return "\n".join(lines)


def render_kpis(out: StructuredOutput) -> str:
    lines = [_h2("4. KEY IMPACT KPIs — INVESTOR / UCF APPLICATION")]
    for code, kpi_list in out.kpis.items():
        p = CATALOG_BY_CODE[code]
        lines.append(f"\n  [{code}] {p.name}")
        for kpi in kpi_list:
            lines.append(f"       • {kpi}")
            lines.append(f"         Baseline: [ULB to populate]  |  Target: [ULB to set]  |  "
                         f"Method: [ULB to define]")
    return "\n".join(lines)


def render_risk_flags(out: StructuredOutput) -> str:
    lines = [_h2("5. RISK FLAG SUMMARY")]
    if not out.risk_flags:
        lines.append("  No significant risk flags identified for this profile.")
        return "\n".join(lines)
    for i, rf in enumerate(out.risk_flags, 1):
        lines.append(f"\n  Risk {i} [{rf.severity}]")
        lines.append(f"  Issue      : {textwrap.fill(rf.description, 65, subsequent_indent=' ' * 15)}")
        lines.append(f"  Mitigation : {textwrap.fill(rf.mitigation, 65, subsequent_indent=' ' * 15)}")
    return "\n".join(lines)


def render_full_report(out: StructuredOutput) -> str:
    sections = [
        _h1(f"UCF FINANCIAL STRUCTURING REPORT — {out.city.upper()}, {out.state.upper()}"),
        render_summary_table(out),
        render_finance_stacks(out),
        render_reform_checklist(out),
        render_kpis(out),
        render_risk_flags(out),
        f"\n{THICK}\n  END OF REPORT\n{THICK}\n",
    ]
    return "\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive input helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val if val else default


def _prompt_float(msg: str, default: float) -> float:
    while True:
        raw = _prompt(msg, str(default))
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a numeric value.")


def _prompt_bool(msg: str, default: bool = False) -> bool:
    d = "y" if default else "n"
    raw = _prompt(f"{msg} (y/n)", d).lower()
    return raw.startswith("y")


def interactive_project_selection() -> List[str]:
    """Walk through each theme and ask the user which projects to include."""
    print(render_catalog())
    print()
    print("  Enter project codes separated by spaces (e.g. A1 B1 C2),")
    print("  or press Enter to skip a theme.\n")

    selected: List[str] = []
    themes_displayed = []
    for p in CATALOG:
        if p.theme not in themes_displayed:
            themes_displayed.append(p.theme)

    for theme in themes_displayed:
        theme_projects = [p for p in CATALOG if p.theme == theme]
        codes_in_theme = [p.code for p in theme_projects]
        raw = _prompt(f"  Projects from {theme} {codes_in_theme}").upper()
        for token in raw.split():
            if token in CATALOG_BY_CODE:
                if token not in selected:
                    selected.append(token)
            else:
                print(f"  Warning: {token!r} is not a valid code — skipped.")

    return selected


def gather_city_profile() -> dict:
    print(_h2("CITY PROFILE"))
    city = _prompt("  City name")
    state = _prompt("  State")
    pop = _prompt_float("  Population (in lakh, e.g. 12.5)", 10.0)
    bond_history = _prompt_bool("  Does the ULB have prior bond issuance history?")
    rating = _prompt_bool("  Does the ULB hold a current SEBI credit rating?")
    raw_osr = _prompt("  Own-source revenue as % of total expenditure (leave blank if unknown)")
    osr: Optional[float] = float(raw_osr) / 100 if raw_osr else None
    return dict(city=city, state=state, population_lakh=pop,
                has_bond_history=bond_history, has_credit_rating=rating,
                osr_ratio=osr)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run_interactive(out_path: Optional[str]) -> None:
    print(_h1("UCF ADVISOR — URBAN CLIMATE FINANCE PROJECT STRUCTURING"))
    print("  This tool helps Urban Local Bodies (ULBs) structure sustainability")
    print("  projects for UCF funding, market finance, and challenge applications.\n")

    profile = gather_city_profile()
    codes = interactive_project_selection()

    if not codes:
        print("\n  No projects selected. Exiting.")
        sys.exit(0)

    print(f"\n  Selected {len(codes)} project(s): {', '.join(codes)}")
    print("  Generating financial structuring report …\n")

    out = structure_projects(project_codes=codes, **profile)
    report = render_full_report(out)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  Report written to: {out_path}")
    else:
        print(report)


def run_from_json(json_path: str, out_path: Optional[str]) -> None:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    required = {"city", "state", "population_lakh", "project_codes"}
    missing = required - data.keys()
    if missing:
        print(f"Error: JSON missing required keys: {missing}", file=sys.stderr)
        sys.exit(1)

    out = structure_projects(
        city=data["city"],
        state=data["state"],
        population_lakh=float(data["population_lakh"]),
        project_codes=data["project_codes"],
        has_bond_history=data.get("has_bond_history", False),
        osr_ratio=data.get("osr_ratio"),
        has_credit_rating=data.get("has_credit_rating", False),
    )
    report = render_full_report(out)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to: {out_path}")
    else:
        print(report)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UCF Advisor — Urban Climate Finance Project Structuring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python ucf_advisor.py                          # guided interactive mode
              python ucf_advisor.py --json input.json        # from JSON file
              python ucf_advisor.py --json input.json --out report.txt
        """),
    )
    parser.add_argument("--json", metavar="FILE", help="Path to JSON input file")
    parser.add_argument("--out", metavar="FILE", help="Write report to file instead of stdout")
    args = parser.parse_args()

    if args.json:
        run_from_json(args.json, args.out)
    else:
        run_interactive(args.out)


if __name__ == "__main__":
    main()
