// Week 4 - IoT
// Leaflet example

// Set the desired coordinates (here it is the ECE department)
const eceCoords = [38.287979, 21.788922];
const zoomLevel = 13;

// add an OpenStreetMap tile layer
var map = L.map('map').setView(eceCoords, zoomLevel);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

// add a marker
var marker = L.marker(eceCoords).addTo(map);

// add a red circle
var circle = L.circle([eceCoords[0]+0.01, eceCoords[1]+0.01], {
    color: 'red',
    fillColor: '#f03',
    fillOpacity: 0.5,
    radius: 500
    }).addTo(map);
    
// add a polygon
var polygon = L.polygon([
    [eceCoords[0]+0.02, eceCoords[1]-0.004],
    [eceCoords[0], eceCoords[1]-0.008],
    [eceCoords[0]-0.01, eceCoords[1]-0.001]
]).addTo(map);

// add a popup
var popup = L.popup()
    .setLatLng([eceCoords[0]+0.01, eceCoords[1]+0.01])
    .setContent("You are here!")
    .openOn(map);