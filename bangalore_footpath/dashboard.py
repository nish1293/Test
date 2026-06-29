"""Generate an interactive dashboard from the pipeline's GeoJSON.

A single self-contained HTML page (Leaflet from CDN, GeoJSON inlined):
  * hover a street  -> it highlights and shows a quick tooltip,
  * click a street  -> its details fill the side panel (name, length, footpath
    present/absent, how it was determined),
  * a summary header -> total streets, total km, % footpath coverage,
  * a legend + a present/absent filter.

    python dashboard.py --geojson out/roads_footpath.geojson
    # -> out/dashboard.html

Open the file in any browser. No server needed.
"""

from __future__ import annotations

import argparse
import json
import os

TEMPLATE = r"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>__TITLE__</title>
__LEAFLET_HEAD__
<style>
  :root{ --green:#1a9850; --red:#d73027; --ink:#1f2d3d; }
  html,body{height:100%;margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;color:var(--ink)}
  #app{display:flex;height:100%}
  #side{width:340px;flex:0 0 340px;overflow-y:auto;background:#f7f9fb;
        border-right:1px solid #dde3e8;padding:16px 18px;box-sizing:border-box}
  #map{flex:1}
  h1{font-size:18px;margin:0 0 4px}
  .sub{color:#6b7a88;font-size:12px;margin-bottom:14px}
  .stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
  .stat{background:#fff;border:1px solid #e3e9ee;border-radius:8px;padding:10px}
  .stat .v{font-size:20px;font-weight:700}
  .stat .l{font-size:11px;color:#6b7a88;text-transform:uppercase;letter-spacing:.04em}
  .bar{height:8px;border-radius:4px;background:#e3e9ee;overflow:hidden;margin:6px 0 16px}
  .bar > i{display:block;height:100%;background:var(--green)}
  .panel{background:#fff;border:1px solid #e3e9ee;border-radius:8px;padding:14px;min-height:90px}
  .panel h2{font-size:14px;margin:0 0 8px}
  .row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0;border-bottom:1px dashed #eef2f5}
  .row b{font-weight:600}
  .pill{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:12px;font-weight:600}
  .pill.y{background:var(--green)} .pill.n{background:var(--red)}
  .hint{color:#9aa7b2;font-size:12px}
  .legend,.filter{font-size:13px;margin-top:14px}
  .legend i{display:inline-block;width:14px;height:4px;margin-right:6px;vertical-align:middle}
  .filter label{display:block;margin:4px 0;cursor:pointer}
</style></head>
<body><div id="app">
  <div id="side">
    <h1>Bangalore Footpaths</h1>
    <div class="sub">Hover to highlight · click a street for details</div>
    <div class="stats">
      <div class="stat"><div class="v" id="s-streets">–</div><div class="l">Streets</div></div>
      <div class="stat"><div class="v" id="s-km">–</div><div class="l">Total km</div></div>
      <div class="stat"><div class="v" id="s-cov">–</div><div class="l">Footpath coverage</div></div>
      <div class="stat"><div class="v" id="s-fpkm">–</div><div class="l">Footpath km</div></div>
    </div>
    <div class="bar"><i id="s-barfill" style="width:0%"></i></div>

    <div class="panel" id="panel">
      <h2>Selected street</h2>
      <div class="hint">Click a street on the map to see its length and footpath status.</div>
    </div>

    <div class="legend">
      <i style="background:var(--green)"></i> footpath present<br>
      <i style="background:var(--red)"></i> footpath absent
    </div>
    <div class="filter">
      <label><input type="checkbox" id="f-present" checked> show present</label>
      <label><input type="checkbox" id="f-absent" checked> show absent</label>
    </div>
  </div>
  <div id="map"></div>
</div>
<script>
var data = __GEOJSON__;

var map = L.map('map');
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom:19, attribution:'&copy; OpenStreetMap contributors'}).addTo(map);

function present(f){ return Number(f.properties.footpath_present) === 1; }
function baseStyle(f){
  return {color: present(f) ? '#1a9850' : '#d73027', weight:3, opacity:0.85};
}
var hiStyle = {weight:8, opacity:1, color:'#2b6cb0'};

var selected = null;
function showDetails(f){
  var p = f.properties;
  var yes = present(f);
  document.getElementById('panel').innerHTML =
    '<h2>'+(p.name || p.road_id || 'Unnamed road')+'</h2>'+
    '<div class="row"><span>Footpath</span>'+
      '<span class="pill '+(yes?'y':'n')+'">'+(yes?'PRESENT':'ABSENT')+'</span></div>'+
    '<div class="row"><span>Length</span><b>'+Number(p.length_m).toFixed(0)+' m</b></div>'+
    '<div class="row"><span>Determined by</span><b>'+(p.footpath_source||'n/a')+'</b></div>'+
    (p.road_id?'<div class="row"><span>ID</span><b>'+p.road_id+'</b></div>':'');
}

var layer = L.geoJSON(data, {
  filter: function(f){
    var ok = present(f) ? document.getElementById('f-present').checked
                        : document.getElementById('f-absent').checked;
    return ok;
  },
  style: baseStyle,
  onEachFeature: function(f, l){
    l.bindTooltip(
      (f.properties.name||f.properties.road_id||'road')+' · '+
      Number(f.properties.length_m).toFixed(0)+' m · '+
      (present(f)?'footpath':'no footpath'), {sticky:true});
    l.on('mouseover', function(){ if(l!==selected) l.setStyle(hiStyle); });
    l.on('mouseout',  function(){ if(l!==selected) layer.resetStyle(l); });
    l.on('click', function(){
      if(selected) layer.resetStyle(selected);
      selected = l; l.setStyle(hiStyle); showDetails(f);
    });
  }
}).addTo(map);
map.fitBounds(layer.getBounds());

// ---- summary stats (computed from the data) ----
var totM=0, fpM=0, n=0;
L.geoJSON(data).eachLayer(function(){});
data.features.forEach(function(f){
  var len = Number(f.properties.length_m)||0;
  totM += len; if(present(f)) fpM += len; n++;
});
var cov = totM ? (100*fpM/totM) : 0;
document.getElementById('s-streets').textContent = n;
document.getElementById('s-km').textContent = (totM/1000).toFixed(2);
document.getElementById('s-fpkm').textContent = (fpM/1000).toFixed(2);
document.getElementById('s-cov').textContent = cov.toFixed(1)+'%';
document.getElementById('s-barfill').style.width = cov.toFixed(1)+'%';

// ---- filters redraw ----
function redraw(){
  layer.clearLayers();
  layer.addData(data);
}
document.getElementById('f-present').addEventListener('change', redraw);
document.getElementById('f-absent').addEventListener('change', redraw);
</script></body></html>
"""


CDN_HEAD = (
    '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>\n'
    '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
)


def _leaflet_head() -> str:
    """Inline vendored Leaflet (assets/) for a self-contained, offline file;
    fall back to the CDN if the vendored copy isn't present."""
    here = os.path.dirname(os.path.abspath(__file__))
    css = os.path.join(here, "assets", "leaflet.css")
    js = os.path.join(here, "assets", "leaflet.js")
    if os.path.exists(css) and os.path.exists(js):
        with open(css, encoding="utf-8") as fh:
            css_txt = fh.read()
        with open(js, encoding="utf-8") as fh:
            js_txt = fh.read()
        return f"<style>{css_txt}</style>\n<script>{js_txt}</script>"
    return CDN_HEAD


def render(geojson: dict, title: str = "Bangalore Footpaths") -> str:
    return (TEMPLATE
            .replace("__LEAFLET_HEAD__", _leaflet_head())
            .replace("__GEOJSON__", json.dumps(geojson))
            .replace("__TITLE__", title))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geojson", required=True, help="Pipeline GeoJSON output")
    ap.add_argument("--out", help="Output HTML (default <geojson dir>/dashboard.html)")
    ap.add_argument("--title", default="Bangalore Footpaths")
    args = ap.parse_args()

    with open(args.geojson, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = args.out or os.path.join(os.path.dirname(args.geojson) or ".", "dashboard.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(data, args.title))
    print(f"Wrote {out} — open it in a browser.")


if __name__ == "__main__":
    main()
