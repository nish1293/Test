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
    assign_footpath_presence_multi,
    compute_lengths,
    merge_footways,
    summarize,
    WGS84,
)
from tile2net_adapter import normalize_detections

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

    test_phase2_detection()
    test_phase3_validation()
    print("\nALL SELF-TESTS PASSED")


def test_phase2_detection() -> None:
    """Phase 2: a detected footpath fills R3 (the OSM-absent street).

    Also exercises normalize_detections() on a polygon (Tile2Net emits sidewalk
    polygons, not just lines) and confirms OSM-covered roads keep their source.
    """
    roads, footways = build_synthetic()
    roads = compute_lengths(roads)

    # A detected sidewalk POLYGON straddling R3 (which OSM marks sidewalk=no).
    dx = 0.00006  # ~6 m
    r3 = roads.set_index("road_id").loc["R3", "geometry"]
    # build a thin polygon around R3 in lat/lon by buffering in WGS84 degrees
    detected_raw = gpd.GeoDataFrame(
        {"f_type": ["sidewalk"]},
        geometry=[
            _line(
                (LON + 0.05 + dx, LAT),
                (LON + 0.05 + dx, LAT + 0.0030),
            ).buffer(0.00002)
        ],
        crs=WGS84,
    )
    detected = normalize_detections(detected_raw, class_col="f_type")
    assert detected.iloc[0].footway_source == "tile2net"
    assert "Polygon" in detected.geometry.type.iloc[0]

    out = assign_footpath_presence_multi(roads, footways, detected, buffer_m=12.0)
    by_id = out.set_index("road_id")
    # OSM-covered roads keep their original source...
    assert by_id.loc["R1", "footpath_source"] == "tag"
    assert by_id.loc["R2", "footpath_source"] == "proximity"
    # ...and R3, previously absent, is now filled by detection.
    assert by_id.loc["R3", "footpath_present"] == 1, "detection should fill R3"
    assert by_id.loc["R3", "footpath_source"] == "tile2net"

    # Coverage rises to 100% once the gap is filled.
    cov = summarize(out).iloc[0]["coverage_pct"]
    assert cov == 100.0, cov

    # merge_footways sanity: OSM + detected combine into one layer.
    merged = merge_footways(footways, detected)
    assert len(merged) == len(footways) + len(detected)
    print(f"[ok] Phase 2: detection filled R3, coverage 83.2% -> {cov}%")


def test_phase3_validation() -> None:
    """Phase 3: confusion matrix, metrics, evaluate join, and sampling."""
    import pandas as pd

    from validate import (
        confusion,
        evaluate,
        metrics_from_confusion,
        sample_segments,
    )

    # Hand-built case: 2 TP, 1 FP, 1 FN, 1 TN.
    pred = pd.Series([1, 1, 1, 0, 0])
    truth = pd.Series([1, 1, 0, 1, 0])
    c = confusion(pred, truth)
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (2, 1, 1, 1), c
    m = metrics_from_confusion(c)
    assert m["precision"] == round(2 / 3, 4), m
    assert m["recall"] == round(2 / 3, 4), m
    assert m["accuracy"] == 0.6, m
    print(f"[ok] Phase 3 metrics: P={m['precision']} R={m['recall']} "
          f"acc={m['accuracy']} kappa={m['kappa']}")

    # Length-weighted differs from count-weighted: weight the FP heavily.
    weight = pd.Series([10, 10, 1000, 10, 10])
    cw = confusion(pred, truth, weight)
    assert cw["fp"] == 1000, cw
    mw = metrics_from_confusion(cw)
    assert mw["precision"] < m["precision"], "big FP should hurt length precision"

    # evaluate(): join predictions to a partially-labelled truth file.
    preds = pd.DataFrame({
        "road_id": ["R1", "R2", "R3", "R4", "R5"],
        "footpath_present": [1, 1, 1, 0, 0],
        "length_m": [10, 10, 1000, 10, 10],
    })
    truth_df = pd.DataFrame({
        "road_id": ["R1", "R2", "R3", "R4", "R5"],
        "truth": [1, 1, 0, 1, ""],  # R5 left unlabelled
    })
    rep = evaluate(preds, truth_df)
    assert rep["n_unlabelled"] == 1 and rep["n_scored"] == 4, rep
    assert "length" in rep and rep["count"]["n"] == 4
    print(f"[ok] Phase 3 evaluate: scored {rep['n_scored']}, "
          f"{rep['n_unlabelled']} unlabelled, count-acc={rep['count']['accuracy']}")

    # Sampling is deterministic and stratified across both predicted classes.
    samp = sample_segments(preds, n=4, stratify=True, seed=7)
    samp2 = sample_segments(preds, n=4, stratify=True, seed=7)
    assert list(samp.road_id) == list(samp2.road_id), "seed must be deterministic"
    assert samp["footpath_present"].nunique() == 2, "stratify should cover 0 and 1"
    print(f"[ok] Phase 3 sampling: deterministic, stratified ({len(samp)} rows)")


if __name__ == "__main__":
    main()
