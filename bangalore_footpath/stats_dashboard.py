"""Statistics dashboard for the footpath layer.

Turns the pipeline output (CSV or GeoJSON) into an analytics page: headline
KPIs, footpath coverage by how it was determined, present-vs-absent split,
a segment-length histogram, optional coverage-by-ward, and an actionable
"longest streets with no footpath" list.

Stats are computed in Python (compute_stats() is pure and offline-tested) and
baked into a static, dependency-free HTML page — no JS chart library, no CDN.

    python stats_dashboard.py --input out/roads_footpath.csv
    python stats_dashboard.py --input out/roads_footpath.geojson --ward-col ward
    # -> out/stats.html
"""

from __future__ import annotations

import argparse
import html
import os
from typing import Dict, List, Optional

import pandas as pd

PRED_COL = "footpath_present"
LEN_COL = "length_m"
SRC_COL = "footpath_source"


# --------------------------------------------------------------------------- #
# Pure stats
# --------------------------------------------------------------------------- #
def compute_stats(
    df: pd.DataFrame,
    length_col: str = LEN_COL,
    present_col: str = PRED_COL,
    source_col: str = SRC_COL,
    ward_col: Optional[str] = None,
    n_gaps: int = 10,
    n_bins: int = 6,
) -> Dict:
    """Compute every figure the dashboard shows. Returns a plain dict."""
    df = df.copy()
    df[length_col] = pd.to_numeric(df[length_col], errors="coerce").fillna(0.0)
    df[present_col] = pd.to_numeric(df[present_col], errors="coerce").fillna(0).astype(int)

    total_m = float(df[length_col].sum())
    fp_m = float(df.loc[df[present_col] == 1, length_col].sum())
    stats: Dict = {
        "n_streets": int(len(df)),
        "total_km": round(total_m / 1000, 3),
        "footpath_km": round(fp_m / 1000, 3),
        "gap_km": round((total_m - fp_m) / 1000, 3),
        "coverage_pct": round(100 * fp_m / total_m, 1) if total_m else 0.0,
        "present_count": int((df[present_col] == 1).sum()),
        "absent_count": int((df[present_col] == 0).sum()),
    }

    # km by source of evidence
    by_source: List[Dict] = []
    if source_col in df.columns:
        g = df.groupby(source_col)[length_col].agg(["sum", "count"])
        for src, row in g.sort_values("sum", ascending=False).iterrows():
            by_source.append({
                "source": str(src),
                "km": round(row["sum"] / 1000, 3),
                "count": int(row["count"]),
            })
    stats["by_source"] = by_source

    # length histogram (metres)
    lengths = df[length_col]
    hist: List[Dict] = []
    if len(lengths) and lengths.max() > 0:
        cats = pd.cut(lengths, bins=n_bins)
        vc = cats.value_counts().sort_index()
        for interval, cnt in vc.items():
            hist.append({
                "label": f"{int(interval.left)}–{int(interval.right)} m",
                "count": int(cnt),
            })
    stats["length_hist"] = hist

    # coverage by ward (optional)
    by_ward: List[Dict] = []
    if ward_col and ward_col in df.columns:
        for ward, frame in df.groupby(ward_col):
            t = float(frame[length_col].sum())
            f = float(frame.loc[frame[present_col] == 1, length_col].sum())
            by_ward.append({
                "ward": str(ward),
                "total_km": round(t / 1000, 3),
                "coverage_pct": round(100 * f / t, 1) if t else 0.0,
            })
        by_ward.sort(key=lambda r: r["coverage_pct"])
    stats["by_ward"] = by_ward

    # longest streets with NO footpath — the actionable to-fix list
    gaps = df[df[present_col] == 0].sort_values(length_col, ascending=False)
    name_col = "name" if "name" in df.columns else None
    id_col = "road_id" if "road_id" in df.columns else None
    top_gaps: List[Dict] = []
    for _, row in gaps.head(n_gaps).iterrows():
        top_gaps.append({
            "name": str(row[name_col]) if name_col else (str(row[id_col]) if id_col else "—"),
            "length_m": int(round(row[length_col])),
        })
    stats["top_gaps"] = top_gaps
    return stats


# --------------------------------------------------------------------------- #
# Rendering (static HTML, no JS deps)
# --------------------------------------------------------------------------- #
def _bar_rows(items, label_key, value_key, suffix="", color="#1a9850") -> str:
    if not items:
        return '<div class="hint">No data.</div>'
    vmax = max(i[value_key] for i in items) or 1
    rows = []
    for it in items:
        w = 100 * it[value_key] / vmax
        rows.append(
            f'<div class="brow"><div class="blabel">{html.escape(str(it[label_key]))}</div>'
            f'<div class="btrack"><i style="width:{w:.1f}%;background:{color}"></i></div>'
            f'<div class="bval">{it[value_key]}{suffix}</div></div>'
        )
    return "\n".join(rows)


def _kpi(value, label, accent="#1f2d3d") -> str:
    return (f'<div class="kpi"><div class="kv" style="color:{accent}">{value}</div>'
            f'<div class="kl">{html.escape(label)}</div></div>')


def render(stats: Dict, title: str = "Bangalore Footpaths — Statistics") -> str:
    kpis = "".join([
        _kpi(stats["n_streets"], "Streets"),
        _kpi(stats["total_km"], "Total km"),
        _kpi(f'{stats["coverage_pct"]}%', "Footpath coverage", "#1a9850"),
        _kpi(stats["footpath_km"], "Footpath km", "#1a9850"),
        _kpi(stats["gap_km"], "Gap km (no footpath)", "#d73027"),
        _kpi(stats["absent_count"], "Streets w/o footpath", "#d73027"),
    ])

    presence = _bar_rows(
        [{"l": "Present", "v": stats["present_count"]},
         {"l": "Absent", "v": stats["absent_count"]}],
        "l", "v", color="#3a6ea5",
    )
    by_source = _bar_rows(stats["by_source"], "source", "km", " km")
    hist = _bar_rows(stats["length_hist"], "label", "count", color="#5b8def")

    ward_html = ""
    if stats["by_ward"]:
        ward_html = (
            '<div class="card"><h2>Coverage by ward (lowest first)</h2>'
            + _bar_rows([{"l": w["ward"], "v": w["coverage_pct"]} for w in stats["by_ward"]],
                        "l", "v", "%", color="#1a9850")
            + "</div>"
        )

    gap_rows = "".join(
        f'<tr><td>{html.escape(g["name"])}</td><td class="num">{g["length_m"]} m</td></tr>'
        for g in stats["top_gaps"]
    ) or '<tr><td colspan="2" class="hint">No gaps — full coverage.</td></tr>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{html.escape(title)}</title>
<style>
  body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;color:#1f2d3d;
       background:#eef2f5;margin:0;padding:24px}}
  h1{{font-size:22px;margin:0 0 2px}}
  .sub{{color:#6b7a88;font-size:13px;margin-bottom:18px}}
  .kpis{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:18px}}
  .kpi{{background:#fff;border:1px solid #e3e9ee;border-radius:10px;padding:14px}}
  .kv{{font-size:24px;font-weight:700}} .kl{{font-size:11px;color:#6b7a88;
       text-transform:uppercase;letter-spacing:.04em;margin-top:2px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .card{{background:#fff;border:1px solid #e3e9ee;border-radius:10px;padding:16px 18px}}
  .card.wide{{grid-column:1 / -1}}
  h2{{font-size:15px;margin:0 0 12px}}
  .brow{{display:flex;align-items:center;gap:10px;margin:7px 0;font-size:13px}}
  .blabel{{width:130px;flex:0 0 130px;color:#41515f;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .btrack{{flex:1;background:#eef2f5;border-radius:5px;height:14px;overflow:hidden}}
  .btrack > i{{display:block;height:100%}}
  .bval{{width:78px;flex:0 0 78px;text-align:right;font-weight:600}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  td{{padding:6px 4px;border-bottom:1px solid #eef2f5}}
  td.num{{text-align:right;font-weight:600}}
  .hint{{color:#9aa7b2;font-size:12px}}
  @media(max-width:900px){{.kpis{{grid-template-columns:repeat(2,1fr)}} .grid{{grid-template-columns:1fr}}}}
</style></head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="sub">Footpath presence/absence statistics across the analysed street network.</div>
  <div class="kpis">{kpis}</div>
  <div class="grid">
    <div class="card"><h2>Footpath coverage by evidence source (km)</h2>{by_source}</div>
    <div class="card"><h2>Streets: present vs absent (count)</h2>{presence}</div>
    <div class="card"><h2>Street length distribution (count)</h2>{hist}</div>
    <div class="card"><h2>Longest streets with no footpath</h2>
      <table><tbody>{gap_rows}</tbody></table></div>
    {ward_html}
  </div>
</body></html>
"""


def _read_any(path: str) -> pd.DataFrame:
    if path.lower().endswith((".geojson", ".json", ".shp", ".gpkg")):
        import geopandas as gpd

        return pd.DataFrame(gpd.read_file(path).drop(columns="geometry"))
    return pd.read_csv(path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="pipeline output (CSV or GeoJSON)")
    ap.add_argument("--ward-col", help="column to break coverage down by (e.g. ward)")
    ap.add_argument("--out", help="output HTML (default <input dir>/stats.html)")
    ap.add_argument("--title", default="Bangalore Footpaths — Statistics")
    args = ap.parse_args()

    df = _read_any(args.input)
    stats = compute_stats(df, ward_col=args.ward_col)
    out = args.out or os.path.join(os.path.dirname(args.input) or ".", "stats.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(stats, args.title))
    print(f"Wrote {out} — open it in a browser.")
    print(f"  {stats['n_streets']} streets · {stats['total_km']} km · "
          f"{stats['coverage_pct']}% coverage · {stats['absent_count']} without footpath")


if __name__ == "__main__":
    main()
