# Issue 14 — Research Map Visualization + Routing for Driver App

## Google Maps
- Not free to use.

## Leaflet

### Pros
- Free
- Pretty lightweight
- Many plugins:
  - Heatmaps
  - Routing
- No API key needed

### Cons
- No vector maps
- Visual style looks a bit older

**Available for both SvelteKit and React.**


## MapLibre GL JS

### Pros
- Open source
- Supports vector maps
- Good performance on mobile PWAs
- Compatible with OpenStreetMap

### Cons
- A bit more complex than Leaflet
- For offline usage, you need your own tile server?

**Available for both SvelteKit and React.**


## OpenLayers

### Pros
- Very feature-rich
- Supports vector and grid maps
- Heatmaps supported
- Open source
- Stable and mature

### Cons
- More complex again

**Available for both SvelteKit and React.**


## Conclusion
We should consider whether we want:
- A simple solution → **Leaflet**, easiest and fully sufficient for our needs  
- A more advanced but more complex solution → **MapLibre** or **OpenLayers**

➡️ **Leaflet is probably enough for us and would be the easiest choice.**

---

## Useful Links (not looked much into it, just collected)

### React with Leaflet
https://react-leaflet.js.org/  
https://github.com/PaulLeCam/react-leaflet  

### React with MapLibre
https://visgl.github.io/react-maplibre/docs/get-started  
https://maplibre.org/maplibre-react-native/  

---

### SvelteKit with Leaflet  
*(Potential issues with the `window` object in SSR environments)*  
https://svelte.dev/playground/62271e8fda854e828f26d75625286bc3?version=5.43.14  
https://www.youtube.com/watch?v=JFctWXEzFZw  

### SvelteKit with MapLibre
https://docs.maptiler.com/svelte/maplibre-gl-js/how-to-use-maplibre-gl-js/  
https://github.com/watergis/sveltekit-maplibre-boilerplate  
https://dev.to/mierune/a-guide-to-building-a-map-application-with-svelte-58je  



# Routing:

## Leaflet Routing Machine (LRM):

- easy to use
- can do waypoints
- can cooperate with OpenStreetMap

https://github.com/perliedman/leaflet-routing-machine

## GraphHopper:

- can do Routing for Car,Bikes,Trucks etc.
- routing seems to be pretty good
- has leaflet integration
- free

https://www.graphhopper.com/


## alternatively host a own routing server (probably too complicated):

- OSRM

- Valhalla 

- GraphHopper

# Conclusion:

- LRM for easy to use
- GraphHopper for a better look
- not sure with memory usuage so LRM might also be better there
