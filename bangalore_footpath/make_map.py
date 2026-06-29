"""Generate a standalone Leaflet web map from the pipeline's GeoJSON.

Green = footpath present (1), red = absent (0). Click a road for its length
and source. Produces a single self-contained index.html that loads Leaflet
from a CDN and inlines the GeoJSON, so it works by just opening the file.

    python make_map.py --geojson out/roads_footpath.geojson --out out/index.html
"""

from __future__ import annotations

import argparse
import json
import os

HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Bangalore Roads &amp; Footpaths</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body,#map{{height:100%;margin:0}}
  .legend{{background:#fff;padding:8px 10px;font:13px/1.4 sans-serif;
           box-shadow:0 1px 4px rgba(0,0,0,.3);border-radius:4px}}
  .legend i{{display:inline-block;width:14px;height:4px;margin-right:6px;
             vertical-align:middle}}
</style></head>
<body><div id="map"></div>
<script>
var data = {geojson};
var map = L.map('map');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{maxZoom:19, attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);
function style(f){{
  return {{color: f.properties.footpath_present==1 ? '#1a9850' : '#d73027',
           weight:3, opacity:0.85}};
}}
var layer = L.geoJSON(data, {{
  style: style,
  onEachFeature: function(f,l){{
    var p=f.properties;
    l.bindPopup('<b>'+(p.name||p.road_id||'road')+'</b><br>'+
      'Length: '+Number(p.length_m).toFixed(1)+' m<br>'+
      'Footpath: '+(p.footpath_present==1?'present':'absent')+
      ' ('+(p.footpath_source||'n/a')+')');
  }}
}}).addTo(map);
map.fitBounds(layer.getBounds());
var legend = L.control({{position:'bottomright'}});
legend.onAdd = function(){{
  var d=L.DomUtil.create('div','legend');
  d.innerHTML='<i style="background:#1a9850"></i> footpath present<br>'+
              '<i style="background:#d73027"></i> footpath absent';
  return d;
}};
legend.addTo(map);
</script></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geojson", required=True, help="Pipeline GeoJSON output")
    ap.add_argument("--out", help="Output HTML (default alongside geojson)")
    args = ap.parse_args()

    with open(args.geojson, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    out = args.out or os.path.join(os.path.dirname(args.geojson) or ".", "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(HTML.format(geojson=json.dumps(data)))
    print(f"Wrote {out} — open it in a browser.")


if __name__ == "__main__":
    main()
