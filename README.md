# UCF Advisor — Urban Climate Finance Project Structuring

A Python CLI tool that helps Indian Urban Local Bodies (ULBs) structure
sustainability projects for the Urban Climate Finance (UCF) programme.

## Quick start

**Requirements:** Python 3.10+. No third-party packages needed.

### Interactive mode
```bash
python ucf_advisor.py
```
You will be guided through city profile entry and project selection.

### JSON / batch mode
```bash
python ucf_advisor.py --json input.json
python ucf_advisor.py --json input.json --out report.txt
```

**`input.json` format:**
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

### Programmatic use
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

## Project catalog

31 project types across 7 themes:

| Theme | Codes |
|---|---|
| A. Green & Blue Infrastructure | A1–A5 |
| B. Water & Sanitation | B1–B5 |
| C. Clean Energy & Energy Efficiency | C1–C5 |
| D. Climate Adaptation & Resilience | D1–D5 |
| E. Sustainable Mobility | E1–E4 |
| F. Heritage & Place-Making | F1–F3 |
| G. Inclusive & Social Infrastructure | G1–G4 |

Run `python ucf_advisor.py` and browse the full menu to see all 28 projects
with descriptions.

## Output sections

For each run the tool produces five sections:

1. **Project Summary Table** — cost estimates, UCF/market/state split
2. **Finance Instruments** — recommended instruments per project
3. **Reform Prerequisites Checklist** — what the city must complete first
4. **Key Impact KPIs** — investor-facing commitments with baseline/target fields
5. **Risk Flag Summary** — top risks and mitigations

## Smoke test
```bash
python -c "
from finance import structure_projects
out = structure_projects('TestCity', 'TestState', 15.0, ['A1','B1','C1'])
assert out.total_cost > 0
assert abs(out.total_ucf + out.total_market + out.total_state_ulb - out.total_cost) < 0.5
print('OK — Total cost: ₹', out.total_cost, 'crore')
"
```

## For AI assistants

See `CLAUDE.md` for the complete guide on codebase conventions, data model
documentation, and behavioural guidelines for AI assistants.
