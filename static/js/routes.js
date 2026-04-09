/* TBRGS -- Route Finding Page */

let map, sensorData = [], routeLayers = [], polylineLayers = [];

document.addEventListener('DOMContentLoaded', async () => {
    map = L.map('map').setView([37.345, -121.94], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);

    const sensors = await populateSensorDropdowns('origin', 'destination');
    sensorData = sensors;
    await populateAlgorithmDropdown('algorithm');

    document.getElementById('origin').value = '402365';
    document.getElementById('destination').value = '401129';

    sensors.forEach(s => {
        L.circleMarker([s.lat, s.lon], {
            radius: 3, color: '#94a3b8', weight: 1, fillOpacity: 0.6
        }).bindTooltip(s.id).addTo(map);
    });

    const slider = document.getElementById('k');
    const display = document.getElementById('k-display');
    slider.addEventListener('input', () => display.textContent = slider.value);

    document.getElementById('find-btn').addEventListener('click', findRoutes);
});

/**
 * Fetch road-following geometry from OSRM for a list of waypoints.
 * Falls back to straight lines if the request fails.
 */
async function getOSRMRoute(waypoints) {
    if (waypoints.length < 2) return waypoints;

    // Route through our backend proxy to avoid CORS issues
    const coords = waypoints.map(([lat, lon]) => `${lon},${lat}`).join(';');

    try {
        const res = await fetch(`/api/osrm?coords=${encodeURIComponent(coords)}`);
        if (!res.ok) return waypoints;
        const data = await res.json();
        if (data.code !== 'Ok' || !data.routes?.[0]) return waypoints;
        // GeoJSON [lon, lat] -> Leaflet [lat, lon]
        return data.routes[0].geometry.coordinates.map(([lon, lat]) => [lat, lon]);
    } catch {
        return waypoints;
    }
}

async function findRoutes() {
    const btn = document.getElementById('find-btn');
    const status = document.getElementById('status');
    btn.disabled = true;
    setStatus(status, 'Finding routes...', 'loading');

    routeLayers.forEach(l => map.removeLayer(l));
    routeLayers = [];
    polylineLayers = [];

    const body = {
        origin: document.getElementById('origin').value,
        destination: document.getElementById('destination').value,
        model: document.getElementById('model').value,
        algorithm: document.getElementById('algorithm').value,
        k: parseInt(document.getElementById('k').value),
    };

    try {
        const data = await fetchJSON('/api/routes/find', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });

        if (data.error) {
            setStatus(status, data.error, 'error');
            btn.disabled = false;
            return;
        }

        setStatus(status, 'Snapping routes to roads...', 'loading');
        await renderRoutes(data.routes);
        setStatus(status, `Found ${data.count} route(s)`, 'success');
    } catch (e) {
        setStatus(status, e.message, 'error');
    }
    btn.disabled = false;
}

async function renderRoutes(routes) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';

    const sensorMap = {};
    sensorData.forEach(s => sensorMap[s.id] = [s.lat, s.lon]);

    // Fetch OSRM road geometries for all routes in parallel
    const roadGeometries = await Promise.all(
        routes.map(route => {
            const waypoints = route.path.map(sid => sensorMap[sid]).filter(Boolean);
            return getOSRMRoute(waypoints);
        })
    );

    routes.forEach((route, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span style="color:${ROUTE_COLORS[i]}; font-weight:700">${i + 1}</span></td>
            <td>${route.travel_time_display}</td>
            <td>${route.distance_km} km</td>
            <td>${route.num_sensors}</td>
        `;
        tr.addEventListener('click', () => highlightRoute(i));
        tbody.appendChild(tr);

        // Draw road-snapped polyline
        const latlngs = roadGeometries[i];
        if (latlngs.length > 1) {
            const polyline = L.polyline(latlngs, {
                color: ROUTE_COLORS[i % ROUTE_COLORS.length],
                weight: i === 0 ? 5 : 3,
                opacity: i === 0 ? 0.9 : 0.6,
            }).addTo(map);
            routeLayers.push(polyline);
            polylineLayers.push(polyline);
        }

        // Sensor dots along the route
        route.path.forEach((sid, j) => {
            const pos = sensorMap[sid];
            if (!pos) return;
            const isEndpoint = j === 0 || j === route.path.length - 1;
            if (!isEndpoint) {
                const dot = L.circleMarker(pos, {
                    radius: 5,
                    color: ROUTE_COLORS[i % ROUTE_COLORS.length],
                    fillColor: '#fff', fillOpacity: 1, weight: 2,
                }).bindTooltip(`Sensor ${sid}`).addTo(map);
                routeLayers.push(dot);
            }
        });
    });

    if (routeLayers.length > 0) {
        const group = L.featureGroup(routeLayers);
        map.fitBounds(group.getBounds().pad(0.1));
    }

    // Origin / destination markers
    if (routes.length > 0) {
        const oPos = sensorMap[routes[0].path[0]];
        const dPos = sensorMap[routes[0].path[routes[0].path.length - 1]];
        if (oPos) {
            const m = L.marker(oPos).bindPopup(`<b>Origin</b><br>Sensor ${routes[0].path[0]}`).addTo(map);
            routeLayers.push(m);
        }
        if (dPos) {
            const m = L.marker(dPos).bindPopup(`<b>Destination</b><br>Sensor ${routes[0].path[routes[0].path.length - 1]}`).addTo(map);
            routeLayers.push(m);
        }
    }
}

function highlightRoute(index) {
    document.querySelectorAll('#results-body tr').forEach((tr, i) => {
        tr.classList.toggle('active', i === index);
    });
    polylineLayers.forEach((layer, i) => {
        layer.setStyle({
            weight: i === index ? 6 : 3,
            opacity: i === index ? 1.0 : 0.4,
        });
        if (i === index) layer.bringToFront();
    });
}
