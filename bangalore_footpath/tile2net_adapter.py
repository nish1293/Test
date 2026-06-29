"""Phase 2 — Tile2Net footpath detection adapter.

Tile2Net (https://github.com/VIDA-NYU/tile2net) extracts sidewalk, crosswalk,
and footpath geometry from orthorectified aerial imagery using semantic
segmentation. Phase 1 covers streets OSM has tagged; Phase 2 uses Tile2Net to
*fill the gaps* — streets with no OSM footpath info get a detected footpath
layer, which feeds the proximity signal in core.assign_footpath_presence_multi.

This module has two halves:

  * normalize_detections() / load_detections()  -- pure, offline-testable.
    Turn whatever Tile2Net (or any detector) emits into a footways
    GeoDataFrame the rest of the pipeline understands.

  * run_tile2net()  -- thin wrapper over the tile2net package. Requires torch,
    a GPU for any real volume, and an aerial-imagery tile source. It is lazily
    imported and guarded, so importing this module never pulls in torch.

Bangalore imagery note
----------------------
Tile2Net ships built-in sources for a few US cities only. For Bangalore you
must supply an aerial-imagery source — either:
  * a local directory of orthorectified GeoTIFF tiles (--input to tile2net), or
  * a custom XYZ tile endpoint (high-res satellite/aerial basemap you are
    licensed to use), registered as a tile2net source.
See the project docs for registering a custom source. Detection quality
depends entirely on imagery resolution (~0.15-0.30 m/px works well).
"""

from __future__ import annotations

import glob
import os
from typing import Optional

import geopandas as gpd

from core import WGS84

# Class labels Tile2Net uses for walkable surfaces. Crosswalks are walkable but
# not "a footpath alongside a road", so default to sidewalk + footpath only.
WALKABLE_CLASSES = {"sidewalk", "footpath", "footway"}


def normalize_detections(
    gdf: gpd.GeoDataFrame,
    class_col: Optional[str] = None,
    keep_classes=WALKABLE_CLASSES,
    source: str = "tile2net",
) -> gpd.GeoDataFrame:
    """Normalise a detector's output into a footways GeoDataFrame.

    * keeps Line and Polygon geometry (a sidewalk polygon still works for the
      proximity test — it is buffered and intersected like a line),
    * if ``class_col`` is given, filters to ``keep_classes``,
    * adds a ``footway_source`` column.
    """
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf = gdf[gdf.geometry.type.isin(
        ["LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    )]
    if class_col and class_col in gdf.columns:
        norm = gdf[class_col].astype(str).str.strip().str.lower()
        gdf = gdf[norm.isin({c.lower() for c in keep_classes})]
    gdf = gdf.reset_index(drop=True)
    gdf["footway_source"] = source
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf[["geometry", "footway_source"]]


def load_detections(
    path: str,
    class_col: Optional[str] = None,
    keep_classes=WALKABLE_CLASSES,
    source: str = "tile2net",
) -> gpd.GeoDataFrame:
    """Load a detection file (GeoJSON/shapefile) and normalise it."""
    return normalize_detections(gpd.read_file(path), class_col, keep_classes, source)


def load_tile2net_dir(
    project_dir: str,
    class_col: str = "f_type",
    source: str = "tile2net",
) -> gpd.GeoDataFrame:
    """Find and load Tile2Net's polygon/network output from a project dir.

    Tile2Net writes its vector results under the project directory (file names
    vary by version, e.g. ``*-Polygons.geojson`` / ``*-Network.geojson``). We
    pick up any GeoJSON under ``polygons``/``network`` subtrees and merge them.
    """
    patterns = [
        os.path.join(project_dir, "**", "*olygon*.geojson"),
        os.path.join(project_dir, "**", "*etwork*.geojson"),
        os.path.join(project_dir, "**", "*idewalk*.geojson"),
    ]
    files = sorted({f for p in patterns for f in glob.glob(p, recursive=True)})
    if not files:
        raise FileNotFoundError(
            f"No Tile2Net vector outputs (*.geojson) found under {project_dir!r}."
        )
    parts = []
    for f in files:
        g = gpd.read_file(f)
        col = class_col if class_col in g.columns else None
        parts.append(normalize_detections(g, col, source=source))
    import pandas as pd

    merged = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=WGS84)
    return merged


def run_tile2net(
    region_name: str,
    bbox,
    out_dir: str,
    input_imagery: Optional[str] = None,
    source: Optional[str] = None,
    zoom: int = 19,
):
    """Run Tile2Net end-to-end for an area; return the project output dir.

    Parameters
    ----------
    region_name : str   Project name Tile2Net uses for outputs.
    bbox        : (south, west, north, east) in lat/lon.
    out_dir     : str   Where Tile2Net writes tiles + vectors.
    input_imagery : str optional path/glob of local orthoimagery GeoTIFFs.
    source      : str   optional name of a registered tile2net imagery source.
    zoom        : int   imagery zoom level (higher = finer; needs the imagery).

    Requires `pip install tile2net` plus a working torch/CUDA install and an
    imagery source for the region. Raises a clear error if unavailable.
    """
    try:
        from tile2net import Raster  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "tile2net is not installed. Install it (pip install tile2net) in an "
            "environment with torch/GPU, and provide aerial imagery for Bangalore "
            "via input_imagery= or a registered source=. See module docstring."
        ) from exc

    if not input_imagery and not source:
        raise ValueError(
            "Bangalore has no built-in Tile2Net imagery source. Pass "
            "input_imagery=<geotiff dir> or source=<registered tile source>."
        )

    os.makedirs(out_dir, exist_ok=True)
    south, west, north, east = bbox
    raster = Raster(
        location=[south, west, north, east],
        name=region_name,
        input_dir=input_imagery,
        source=source,
        zoom=zoom,
        output_dir=out_dir,
    )
    raster.generate(zoom)          # build the tile grid
    raster.inference()             # run segmentation -> polygons + network
    return out_dir


def detected_footways(
    *,
    tile2net_dir: Optional[str] = None,
    detections_file: Optional[str] = None,
    class_col: Optional[str] = None,
) -> Optional[gpd.GeoDataFrame]:
    """Convenience loader used by the pipeline: return a footways GDF or None."""
    if tile2net_dir:
        return load_tile2net_dir(tile2net_dir)
    if detections_file:
        return load_detections(detections_file, class_col=class_col)
    return None
