"""Offline self-test for core.py using synthetic geometry.

No network required. Proves that:
  * length is computed correctly in metres (EPSG:32643),
  * the footpath 0/1 flag fires from BOTH the sidewalk tag and from a
    nearby separately-mapped footway, and stays 0 when neither applies,
  * the summary rollup aggregates km and coverage correctly.

Run:  python selftest.py
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import LineString

from core import (
    assign_footpath_presence,
    compute_lengths,
    summarize,
    WGS84,
)

# A handy spot in central Bengaluru (~MG Road area) to build realistic
# lat/lon geometry. 0.001 deg longitude ~= 101 m at this latitude; we don't
# rely on that approximation — lengths are checked after metric reprojection.
LAT = 12.9750
LON = 77.6050


def _line(*lonlat_pairs) -> LineString:
    return LineString(lonlat_pairs)


def build_synthetic():
    # Three roads:
    #  R1: has sidewalk=both  (tag-present)
    #  R2: no tag, but a footway runs ~5 m alongside (proximity-present)
    #  R3: sidewalk=no and no footway nearby (absent)
    roads = gpd.GeoDataFrame(
        {
            "road_id": ["R1", "R2", "R3"],
            "sidewalk": ["both", None, "no"],
        },
        geometry=[
            _line((LON, LAT), (LON + 0.0100, LAT)),            # ~1.08 km E-W
            _line((LON, LAT + 0.02), (LON, LAT + 0.02 + 0.0050)),  # ~0.55 km N-S
            _line((LON + 0.05, LAT), (LON + 0.05, LAT + 0.0030)),  # ~0.33 km N-S
        ],
        crs=WGS84,
    )

    # One footway, offset ~5 m north of R2, running parallel to it.
    dy = 0.000045  # ~5 m in latitude
    footways = gpd.GeoDataFrame(
        {"fw_id": ["F1"]},
        geometry=[
            _line((LON, LAT + 0.02 + dy), (LON, LAT + 0.02 + 0.0050 + dy)),
        ],
        crs=WGS84,
    )
    return roads, footways


def main() -> None:
    roads, footways = build_synthetic()

    roads = compute_lengths(roads)
    # R1 should be ~1080 m; sanity bounds rather than exact (datum maths).
    r1 = roads.loc[roads.road_id == "R1", "length_m"].iloc[0]
    assert 1000 < r1 < 1150, f"R1 length off: {r1:.1f} m"
    print(f"[ok] length computed in metres (R1 = {r1:.1f} m)")

    roads = assign_footpath_presence(roads, footways, buffer_m=12.0)
    by_id = roads.set_index("road_id")

    assert by_id.loc["R1", "footpath_present"] == 1, "R1 tag should be present"
    assert by_id.loc["R1", "footpath_source"] == "tag"
    assert by_id.loc["R2", "footpath_present"] == 1, "R2 proximity should fire"
    assert by_id.loc["R2", "footpath_source"] == "proximity"
    assert by_id.loc["R3", "footpath_present"] == 0, "R3 should be absent"
    assert by_id.loc["R3", "footpath_source"] == "none"
    print("[ok] footpath 0/1 from tag, proximity, and absence all correct")

    summary = summarize(roads)
    row = summary.iloc[0]
    total_km = round((r1 + by_id.loc["R2", "length_m"] + by_id.loc["R3", "length_m"]) / 1000, 3)
    assert abs(row["total_km"] - total_km) < 0.01, row["total_km"]
    # R1 + R2 have footpaths, R3 doesn't.
    assert 0 < row["coverage_pct"] < 100, row["coverage_pct"]
    print(
        f"[ok] summary: {int(row['segments'])} segs, "
        f"{row['total_km']} km total, {row['coverage_pct']}% with footpath"
    )

    print("\nALL SELF-TESTS PASSED")


if __name__ == "__main__":
    main()
