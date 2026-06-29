"""Phase 1 pipeline: Bangalore road length + footpath presence (0/1).

Fetches road centerlines and footpaths, computes per-segment length in metres,
assigns a binary footpath flag, and writes GeoJSON + CSV + a summary.

Data sources
------------
* OSM (default): roads (network_type='drive') and footways are pulled with
  osmnx in one pass — fully open and reproducible.
* BBMP (optional): pass --roads-file to use the BBMP roads centerline
  shapefile from OpenCity (https://data.opencity.in/dataset/bbmp-roads-centerline-map).
  Footways still come from OSM unless --footways-file is given.

Examples
--------
    # Whole-ward MVP from OSM (recommended first run):
    python pipeline.py --place "Shanthala Nagar, Bengaluru" --out out/

    # A bounding box (S,W,N,E) instead of a named place:
    python pipeline.py --bbox 12.96 77.59 12.99 77.62 --out out/

    # Use BBMP centerlines for roads, OSM for footpaths:
    python pipeline.py --place "Bengaluru" --roads-file bbmp_roads.shp --out out/

Note: in some managed/CI environments the OSM Overpass API and OpenCity may be
blocked by network policy. Run where those hosts are reachable, or supply
local files via --roads-file / --footways-file. core.py has no network deps
and is covered by selftest.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Tuple

import geopandas as gpd

from core import (
    WGS84,
    assign_footpath_presence_multi,
    compute_lengths,
    summarize,
)
from tile2net_adapter import detected_footways


def _lazy_osmnx():
    try:
        import osmnx as ox  # noqa: WPS433
    except ImportError:  # pragma: no cover
        sys.exit("osmnx is required for OSM downloads: pip install osmnx")
    return ox


def get_boundary(place: Optional[str], bbox: Optional[Tuple[float, float, float, float]]):
    """Return a single WGS84 polygon for the study area."""
    ox = _lazy_osmnx()
    if place:
        gdf = ox.geocode_to_gdf(place)
        return gdf.geometry.iloc[0]
    if bbox:
        from shapely.geometry import box

        south, west, north, east = bbox
        return box(west, south, east, north)
    sys.exit("Provide either --place or --bbox.")


def download_roads_osm(polygon) -> gpd.GeoDataFrame:
    ox = _lazy_osmnx()
    G = ox.graph_from_polygon(polygon, network_type="drive", retain_all=True)
    edges = ox.graph_to_gdfs(G, nodes=False)
    keep = [c for c in ["name", "highway", "sidewalk", "geometry"] if c in edges.columns]
    edges = edges[keep].reset_index(drop=True)
    edges["road_id"] = ["R%05d" % i for i in range(len(edges))]
    return edges


def download_footways_osm(polygon) -> gpd.GeoDataFrame:
    ox = _lazy_osmnx()
    tags = {"highway": ["footway", "path", "pedestrian", "steps"]}
    try:
        fw = ox.features_from_polygon(polygon, tags)
    except Exception:  # noqa: BLE001 - empty result raises in some versions
        return gpd.GeoDataFrame(geometry=[], crs=WGS84)
    fw = fw[fw.geometry.type.isin(["LineString", "MultiLineString"])]
    return fw.reset_index(drop=True)


def load_roads_file(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if "road_id" not in gdf.columns:
        gdf["road_id"] = ["R%05d" % i for i in range(len(gdf))]
    return gdf


def export_webmap_geojson(roads: gpd.GeoDataFrame, path: str) -> None:
    """Write a slim WGS84 GeoJSON suitable for the Leaflet viewer."""
    cols = [c for c in ["road_id", "name", "length_m", "footpath_present",
                        "footpath_source", "geometry"] if c in roads.columns]
    roads[cols].to_crs(WGS84).to_file(path, driver="GeoJSON")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place", help='Named area, e.g. "Shanthala Nagar, Bengaluru"')
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"),
                    help="Bounding box: south west north east (lat lon)")
    ap.add_argument("--roads-file", help="Local roads shapefile/GeoJSON (e.g. BBMP centerlines)")
    ap.add_argument("--footways-file", help="Local footways shapefile/GeoJSON")
    ap.add_argument("--tile2net-dir",
                    help="Phase 2: Tile2Net project output dir (detected sidewalks fill OSM gaps)")
    ap.add_argument("--detections-file",
                    help="Phase 2: a detected-footpath GeoJSON/shapefile (alternative to --tile2net-dir)")
    ap.add_argument("--detection-class-col",
                    help="Column in the detections file holding the class label (e.g. f_type)")
    ap.add_argument("--ward-col", help="Column in roads to group the summary by (e.g. ward name)")
    ap.add_argument("--buffer", type=float, default=12.0,
                    help="Footway proximity buffer in metres (default 12)")
    ap.add_argument("--out", default="out", help="Output directory (default ./out)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    polygon = None
    if not args.roads_file or not args.footways_file:
        polygon = get_boundary(args.place, tuple(args.bbox) if args.bbox else None)

    # --- Roads ---------------------------------------------------------------
    if args.roads_file:
        print(f"Loading roads from {args.roads_file} ...")
        roads = load_roads_file(args.roads_file)
    else:
        print("Downloading road network from OSM ...")
        roads = download_roads_osm(polygon)
    print(f"  {len(roads)} road segments")

    # --- Footways ------------------------------------------------------------
    if args.footways_file:
        print(f"Loading footways from {args.footways_file} ...")
        footways = gpd.read_file(args.footways_file)
    else:
        print("Downloading footways from OSM ...")
        footways = download_footways_osm(polygon)
    print(f"  {len(footways)} footway features")

    # --- Phase 2: detected footpaths (Tile2Net) to fill OSM gaps -------------
    detected = detected_footways(
        tile2net_dir=args.tile2net_dir,
        detections_file=args.detections_file,
        class_col=args.detection_class_col,
    )
    if detected is not None:
        print(f"  {len(detected)} detected footpath features (Phase 2)")

    # --- Compute -------------------------------------------------------------
    roads = compute_lengths(roads)
    roads = assign_footpath_presence_multi(
        roads, footways, detected, buffer_m=args.buffer
    )

    # --- Export --------------------------------------------------------------
    gj = os.path.join(args.out, "roads_footpath.geojson")
    csv = os.path.join(args.out, "roads_footpath.csv")
    summ = os.path.join(args.out, "summary.csv")

    export_webmap_geojson(roads, gj)
    drop_geom = roads.drop(columns="geometry")
    drop_geom.to_csv(csv, index=False)
    summary = summarize(roads, group_col=args.ward_col)
    summary.to_csv(summ, index=False)

    print("\n--- Summary ---")
    print(summary.to_string(index=False))
    print(f"\nWrote:\n  {gj}\n  {csv}\n  {summ}")
    print("Open the map with:  python make_map.py --geojson %s" % gj)


if __name__ == "__main__":
    main()
