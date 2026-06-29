# Bangalore Road & Footpath Tool — Phase 1

Measure the **length of every road** and flag **footpath present / absent (0/1)**
across Bangalore streets, then view it on a web map.

This is **Phase 1** of the roadmap: a road base layer with per-segment length
plus a first-pass binary footpath layer derived from OpenStreetMap. Later
phases add automated detection (Tile2Net), validation, and crowdsourcing.

## What it produces

For a chosen area (a ward, a bounding box, or the whole city):

| Output | Description |
|---|---|
| `out/roads_footpath.geojson` | Road segments with `length_m`, `footpath_present` (0/1), `footpath_source` |
| `out/roads_footpath.csv` | Same attributes as a flat table (no geometry) |
| `out/summary.csv` | Total km, footpath-km, and **% coverage by length** (optionally per ward) |
| `out/index.html` | Standalone Leaflet map — green = footpath, red = none, click for details |

## How it works

1. **Road length** — road centerlines are reprojected to **EPSG:32643**
   (UTM 43N, metres) and `geometry.length` is taken per segment. This is the
   reliable way to measure length; raw lat/lon degrees are not metric.
2. **Footpath presence (0/1)** — a segment is `1` if **either**:
   - it carries a positive OSM `sidewalk` tag (`both/left/right/yes`), **or**
   - a separately-mapped footway runs within ~12 m of it (sidewalks are very
     often mapped as their own lines in OSM).
   `footpath_source` records which signal fired (`tag` / `proximity` / `both` / `none`).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
# Recommended first run — one ward from OpenStreetMap (open & reproducible):
python pipeline.py --place "Shanthala Nagar, Bengaluru" --out out/

# Interactive map dashboard (hover to highlight, click for details, live stats):
python dashboard.py --geojson out/roads_footpath.geojson   # -> out/dashboard.html

# Statistics dashboard (KPIs + charts: coverage by source, gaps, by ward):
python stats_dashboard.py --input out/roads_footpath.csv --ward-col ward  # -> out/stats.html

# ...or the minimal click-only map:
python make_map.py --geojson out/roads_footpath.geojson    # -> out/index.html

# A bounding box instead (south west north east, in lat/lon):
python pipeline.py --bbox 12.96 77.59 12.99 77.62 --out out/

# Whole city, grouped by an attribute column for per-area coverage:
python pipeline.py --place "Bengaluru" --ward-col ward --out out/
```

### Phase 2 — fill OSM gaps with Tile2Net detection

OSM only covers streets someone has tagged. [Tile2Net](https://github.com/VIDA-NYU/tile2net)
detects sidewalks from aerial imagery; feeding that in upgrades streets OSM
left as *absent* to *present*, attributed as `footpath_source = tile2net`, so
you can see exactly how much coverage detection added.

```bash
# If you already ran Tile2Net and have its project output dir:
python pipeline.py --place "Shanthala Nagar, Bengaluru" \
    --tile2net-dir tile2net_out/ --out out/

# Or any detected-footpath file (GeoJSON/shapefile), optionally with a class column:
python pipeline.py --place "Shanthala Nagar, Bengaluru" \
    --detections-file detections.geojson --detection-class-col f_type --out out/
```

Running Tile2Net itself needs `pip install tile2net`, torch (GPU for any
volume), and an **aerial-imagery source for Bangalore** — Tile2Net ships only
US city sources, so supply local orthoimagery GeoTIFFs or register a custom
high-res XYZ basemap you're licensed to use. `tile2net_adapter.run_tile2net()`
wraps the run; `normalize_detections()` / `load_tile2net_dir()` convert its
output into the footways layer the pipeline consumes (both are offline-tested).

### Phase 3 — validate the footpath layer

Numbers are only credible once you've measured them against ground truth.
Phase 3 draws a random (optionally stratified) sample to label by foot or
Street View, then scores predictions.

```bash
# 1. Draw 60 segments, evenly split predicted-present / predicted-absent:
python validate.py sample --geojson out/roads_footpath.geojson \
    --n 60 --stratify --seed 42 --out validation_sample.csv

# 2. Fill the 'truth' column (0/1) in validation_sample.csv on the ground.

# 3. Score it:
python validate.py evaluate --predictions out/roads_footpath.csv \
    --truth validation_sample.csv
```

Reports a confusion matrix plus **precision, recall, specificity, accuracy,
F1, and Cohen's kappa**, computed two ways:

* **count-weighted** — per segment;
* **length-weighted** — per metre (the policy-relevant view: a wrong call on a
  2 km arterial matters more than on a 30 m lane).

Stratified sampling matters: labelling only predicted-present roads measures
*precision* but tells you nothing about *recall* (footpaths the tool missed) —
`--stratify` covers both classes.

### Using BBMP centerlines instead of OSM roads

The user-facing BBMP roads centerline layer lives on the OpenCity portal:
<https://data.opencity.in/dataset/bbmp-roads-centerline-map>. Download the
shapefile/GeoJSON and point the pipeline at it (footpaths still come from OSM
unless you also pass `--footways-file`):

```bash
python pipeline.py --roads-file bbmp_roads.shp --place "Bengaluru" --out out/
```

## Files

| File | Role |
|---|---|
| `core.py` | Pure geometry logic: length, footpath 0/1, layered (OSM+detection) presence, summary. **No network.** |
| `pipeline.py` | Download (OSM/osmnx or local files) + Phase 2 detection merge + CLI. |
| `tile2net_adapter.py` | Phase 2: run Tile2Net / load its output into a footways layer. |
| `dashboard.py` | Interactive map dashboard: hover-highlight, click-for-details side panel, live coverage stats, present/absent filter. Self-contained (Leaflet vendored in `assets/`). |
| `stats_dashboard.py` | Statistics dashboard: KPIs + charts (coverage by evidence source, present/absent, length histogram, coverage by ward, longest streets with no footpath). Pure HTML, no chart-library deps. |
| `make_map.py` | Minimal click-only Leaflet `index.html`. |
| `validate.py` | Phase 3: sample segments to label + score predictions (precision/recall/F1/kappa). |
| `selftest.py` | Offline correctness test of core + adapter + validation. |

```bash
python selftest.py   # verifies length + 0/1 logic with no network
```

## Network note

`core.py` and `selftest.py` need **no network**. `pipeline.py` downloads from
the OSM Overpass API (via osmnx) and, optionally, BBMP data from OpenCity.
Some managed/CI/sandbox environments block these hosts by egress policy — run
the download where they are reachable (e.g. a local machine), or supply local
files via `--roads-file` / `--footways-file`.

## Roadmap (where this fits)

- **Phase 1:** road length + OSM-derived footpath 0/1 + map ✅
- **Phase 2 (this update):** Tile2Net detection fills streets OSM hasn't
  tagged; added coverage is attributed `tile2net` in `footpath_source` ✅
- **Phase 3 (this update):** ground-truth validation harness — stratified
  sampling + precision/recall/F1/kappa, count- and length-weighted ✅
- **Phase 4:** richer quality score (continuity, width, obstructions, lighting).
- **Phase 5:** citizen corrections fed back to OpenStreetMap.
