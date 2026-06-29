"""Core geometry logic for the Bangalore road / footpath tool.

Pure functions only — no network, no I/O. Everything here is unit-testable
offline (see selftest.py). The network/download orchestration lives in
pipeline.py so that this module stays deterministic and fast to test.

The two questions this module answers, per road segment:
    1. How long is the road?        -> compute_lengths()
    2. Is a footpath present? (0/1)  -> assign_footpath_presence()
"""

from __future__ import annotations

from typing import Iterable, Optional

import geopandas as gpd
import pandas as pd

# Bangalore sits in UTM Zone 43N. EPSG:32643 is a metre-based projected CRS,
# so geometry.length comes out in metres directly (WGS84 degrees are useless
# for measuring length).
METRIC_CRS = "EPSG:32643"
WGS84 = "EPSG:4326"

# OSM `sidewalk=*` values that mean "a footpath exists alongside this road".
# 'no' / 'none' / 'separate' are handled explicitly below.
SIDEWALK_PRESENT_VALUES = {"both", "left", "right", "yes"}
SIDEWALK_ABSENT_VALUES = {"no", "none"}


def to_metric(gdf: gpd.GeoDataFrame, crs: str = METRIC_CRS) -> gpd.GeoDataFrame:
    """Reproject to a metre-based CRS so lengths/distances are in metres."""
    if gdf.crs is None:
        # Assume WGS84 lat/lon if the source forgot to declare a CRS.
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(crs)


def compute_lengths(
    roads: gpd.GeoDataFrame, crs: str = METRIC_CRS, col: str = "length_m"
) -> gpd.GeoDataFrame:
    """Add a per-segment length column (metres) computed in a metric CRS.

    Returns a copy reprojected to ``crs`` with ``col`` populated.
    """
    roads = to_metric(roads, crs).copy()
    roads[col] = roads.geometry.length
    return roads


def _sidewalk_tag_flag(value) -> Optional[bool]:
    """Map an OSM sidewalk tag value to True/False, or None if unknown.

    OSM occasionally stores list values (e.g. ['left', 'no']); any
    present-ish token wins.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    tokens = value if isinstance(value, (list, tuple)) else [value]
    tokens = [str(t).strip().lower() for t in tokens]
    if any(t in SIDEWALK_PRESENT_VALUES for t in tokens):
        return True
    if tokens and all(t in SIDEWALK_ABSENT_VALUES for t in tokens):
        return False
    # 'separate' or anything unrecognised -> let proximity decide.
    return None


def assign_footpath_presence(
    roads: gpd.GeoDataFrame,
    footways: Optional[gpd.GeoDataFrame] = None,
    buffer_m: float = 12.0,
    sidewalk_col: str = "sidewalk",
    crs: str = METRIC_CRS,
) -> gpd.GeoDataFrame:
    """Assign a binary ``footpath_present`` (0/1) to each road segment.

    A footpath is considered present if EITHER:
      * the road carries a positive OSM ``sidewalk`` tag, OR
      * a separately-mapped footway geometry runs within ``buffer_m`` metres
        of the road (sidewalks are very often mapped as their own lines).

    Adds two columns:
      * ``footpath_present`` : 0 or 1
      * ``footpath_source``  : one of tag / proximity / both / none
    """
    roads = to_metric(roads, crs).copy()

    # --- 1. Tag-based signal -------------------------------------------------
    if sidewalk_col in roads.columns:
        tag_flag = roads[sidewalk_col].map(_sidewalk_tag_flag)
    else:
        tag_flag = pd.Series([None] * len(roads), index=roads.index)
    tag_present = tag_flag.fillna(False).astype(bool)

    # --- 2. Proximity signal from separately-mapped footways -----------------
    prox_present = pd.Series(False, index=roads.index)
    if footways is not None and len(footways) > 0:
        fw = to_metric(footways, crs)
        fw = fw[fw.geometry.notna() & ~fw.geometry.is_empty]
        if len(fw) > 0:
            footprint = fw.geometry.buffer(buffer_m).union_all()
            prox_present = roads.geometry.intersects(footprint)

    present = tag_present | prox_present
    roads["footpath_present"] = present.astype(int)

    def _source(t, p):
        if t and p:
            return "both"
        if t:
            return "tag"
        if p:
            return "proximity"
        return "none"

    roads["footpath_source"] = [
        _source(t, p) for t, p in zip(tag_present, prox_present)
    ]
    return roads


def merge_footways(*gdfs: Optional[gpd.GeoDataFrame], crs: str = WGS84) -> gpd.GeoDataFrame:
    """Concatenate footway layers (OSM, detected, local) into one GeoDataFrame.

    Empty/None layers are skipped; all are aligned to ``crs``. Keeps only the
    geometry plus a ``footway_source`` column if present.
    """
    frames = []
    for g in gdfs:
        if g is None or len(g) == 0:
            continue
        g = g.copy()
        if g.crs is None:
            g = g.set_crs(WGS84)
        g = g.to_crs(crs)
        keep = ["geometry"] + (["footway_source"] if "footway_source" in g.columns else [])
        frames.append(g[keep])
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=crs)


def assign_footpath_presence_multi(
    roads: gpd.GeoDataFrame,
    osm_footways: Optional[gpd.GeoDataFrame] = None,
    detected_footways: Optional[gpd.GeoDataFrame] = None,
    buffer_m: float = 12.0,
    sidewalk_col: str = "sidewalk",
    detected_source: str = "tile2net",
    crs: str = METRIC_CRS,
) -> gpd.GeoDataFrame:
    """Layered presence: OSM (tag + proximity) first, then fill gaps with detection.

    A road that OSM already covers keeps its OSM ``footpath_source``
    (tag / proximity / both). A road OSM left ``none`` but that a *detected*
    footway (e.g. Tile2Net output) runs near is upgraded to present with
    ``footpath_source = detected_source``. This makes the Phase 2 contribution
    explicit and measurable (how many km detection added on top of OSM).
    """
    base = assign_footpath_presence(roads, osm_footways, buffer_m, sidewalk_col, crs)
    if detected_footways is None or len(detected_footways) == 0:
        return base

    # Proximity-only pass against detections (ignore any sidewalk tag by
    # pointing at a column that doesn't exist).
    det = assign_footpath_presence(
        base, detected_footways, buffer_m, sidewalk_col="__no_tag__", crs=crs
    )
    base_present = base["footpath_present"].astype(bool).to_numpy()
    det_present = det["footpath_present"].astype(bool).to_numpy()
    filled = det_present & ~base_present

    base.loc[filled, "footpath_present"] = 1
    base.loc[filled, "footpath_source"] = detected_source
    return base


def summarize(
    roads: gpd.GeoDataFrame,
    length_col: str = "length_m",
    present_col: str = "footpath_present",
    group_col: Optional[str] = None,
) -> pd.DataFrame:
    """Roll up total km and footpath coverage, optionally grouped (e.g. ward).

    Coverage % is by length, not by segment count — the policy-relevant metric
    ("what fraction of street-kilometres have a footpath?").
    """
    df = roads.copy()
    df["_with_fp"] = df[length_col] * (df[present_col] == 1)

    def _agg(frame: pd.DataFrame) -> pd.Series:
        total_km = frame[length_col].sum() / 1000.0
        fp_km = frame["_with_fp"].sum() / 1000.0
        return pd.Series(
            {
                "segments": len(frame),
                "total_km": round(total_km, 3),
                "footpath_km": round(fp_km, 3),
                "coverage_pct": round(100.0 * fp_km / total_km, 1)
                if total_km
                else 0.0,
            }
        )

    if group_col and group_col in df.columns:
        out = df.groupby(group_col).apply(_agg, include_groups=False)
        return out.reset_index()
    return _agg(df).to_frame().T
