# Map framworks pros/cons
(based on: https://www.geoapify.com/map-libraries-comparison-leaflet-vs-maplibre-gl-vs-openlayers-trends-and-statistics/)
## Quick summary
For the current project (prototype) Leaflet remains the most practical choice for rapid development. However in the future we would migrate to MapLibre GL, which is more professional and represent the modern standard vector-bassed visualization. OpenLayers is unnecessary complex and heavy.
## Detailed Analysis
### Leaflet
Pros:
- Complexity: easy to learn and implement
- Lightweight: smallest file size
- Ecosystem: extensive library of plugins
Cons:
- 3D support: not supported
- Map style: raster tiles only
- Rendering engine: DOM (HTML elements + SVG)
## MapLibre GL
Pros:
- 3D support: supported
- Map style: vector and raster tiles
- Rendering engine: WebGL (smooth zooming)
Cons:
- Complexity: moderate
- Ecosystem: moderate but growing
## OpenLayers
Unnecessarily complex