/* TBRGS -- Route Finding Page */

let map, sensorData = [], routeLayers = [], polylineLayers = [];
let originMarker, destMarker;
/** 'sensor' = use dropdown; 'map' = use dragged pin position */
let originMode = 'sensor';
let destMode = 'sensor';

function makeEndpointIcon(label, color) {
    return L.divIcon({
        className: 'map-endpoint-icon',
        html: `<div class="map-endpoint-pin" style="--pin-color:${color}"><span>${label}</span></div>`,
        iconSize: [32, 40],
        iconAnchor: [16, 36],
        popupAnchor: [0, -32],
    });
}

function getSensorPos(sensorId) {
    const s = sensorData.find((x) => x.id === String(sensorId));
    return s ? [s.lat, s.lon] : [37.345, -121.94];
}

function syncOriginMarkerFromSelect() {
    const id = document.getElementById('origin').value;
    originMarker.setLatLng(getSensorPos(id));
}

function syncDestMarkerFromSelect() {
    const id = document.getElementById('destination').value;
    destMarker.setLatLng(getSensorPos(id));
}

function updateMapModeHint() {
    const el = document.getElementById('map-mode-hint');
    const parts = [];
    if (originMode === 'map') {
        parts.push(
            '<strong>Start</strong> uses the <strong>green (A)</strong> pin. The origin menu does not apply until you pick a sensor again.',
        );
    }
    if (destMode === 'map') {
        parts.push(
            '<strong>End</strong> uses the <strong>red (B)</strong> pin. The destination menu does not apply until you pick a sensor again.',
        );
    }
    el.innerHTML = parts.join('<br>');
}

document.addEventListener('DOMContentLoaded', async () => {
    map = L.map('map').setView([37.345, -121.94], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18,
    }).addTo(map);

    const sensors = await populateSensorDropdowns('origin', 'destination');
    sensorData = sensors;
    await populateAlgorithmDropdown('algorithm');

    document.getElementById('origin').value = '402365';
    document.getElementById('destination').value = '401129';

    sensors.forEach((s) => {
        L.circleMarker([s.lat, s.lon], {
            radius: 3,
            color: '#94a3b8',
            weight: 1,
            fillOpacity: 0.6,
        })
            .bindTooltip(s.id)
            .addTo(map);
    });

    originMarker = L.marker(getSensorPos('402365'), {
        draggable: true,
        autoPan: true,
        zIndexOffset: 2000,
        icon: makeEndpointIcon('A', '#059669'),
    })
        .addTo(map)
        .bindTooltip('Start — drag to place', { direction: 'top' });

    destMarker = L.marker(getSensorPos('401129'), {
        draggable: true,
        autoPan: true,
        zIndexOffset: 2000,
        icon: makeEndpointIcon('B', '#dc2626'),
    })
        .addTo(map)
        .bindTooltip('End — drag to place', { direction: 'top' });

    document.getElementById('origin').addEventListener('change', () => {
        originMode = 'sensor';
        syncOriginMarkerFromSelect();
        updateMapModeHint();
    });
    document.getElementById('destination').addEventListener('change', () => {
        destMode = 'sensor';
        syncDestMarkerFromSelect();
        updateMapModeHint();
    });

    originMarker.on('dragstart', () => {
        originMode = 'map';
        updateMapModeHint();
    });
    destMarker.on('dragstart', () => {
        destMode = 'map';
        updateMapModeHint();
    });
    originMarker.on('dragend', updateMapModeHint);
    destMarker.on('dragend', updateMapModeHint);

    const slider = document.getElementById('k');
    const display = document.getElementById('k-display');
    slider.addEventListener('input', () => (display.textContent = slider.value));

    document.getElementById('find-btn').addEventListener('click', findRoutes);
});

/** Build POST body: map pins override dropdowns when that end is in map mode. */
function buildRouteFindBody() {
    const body = {
        model: document.getElementById('model').value,
        algorithm: document.getElementById('algorithm').value,
        k: parseInt(document.getElementById('k').value, 10),
    };

    if (originMode === 'map') {
        const ll = originMarker.getLatLng();
        body.origin_lat = ll.lat;
        body.origin_lon = ll.lng;
        body.origin = '';
    } else {
        body.origin = document.getElementById('origin').value;
    }

    if (destMode === 'map') {
        const ll = destMarker.getLatLng();
        body.dest_lat = ll.lat;
        body.dest_lon = ll.lng;
        body.destination = '';
    } else {
        body.destination = document.getElementById('destination').value;
    }

    return { body };
}

/**
 * Fetch road-following geometry from OSRM for a list of waypoints.
 * Falls back to straight lines if the request fails.
 */
async function getOSRMRoute(waypoints) {
    if (waypoints.length < 2) return waypoints;

    const coords = waypoints.map(([lat, lon]) => `${lon},${lat}`).join(';');

    try {
        const res = await fetch(`/api/osrm?coords=${encodeURIComponent(coords)}`);
        if (!res.ok) return waypoints;
        const data = await res.json();
        if (data.code !== 'Ok' || !data.routes?.[0]) return waypoints;
        return data.routes[0].geometry.coordinates.map(([lon, lat]) => [lat, lon]);
    } catch {
        return waypoints;
    }
}

/** Minimum gap (meters) before prepending A / appending B so OSRM draws to the pins. */
const PIN_GAP_MIN_M = 5;

/**
 * OSRM is called with sensor centers along the graph path; the user's pins can sit
 * away from those snaps (or off the road polyline end). Extend waypoints so the
 * driving line reaches A and B.
 */
function buildRoadWaypointsFromPath(route) {
    const sensorMap = {};
    sensorData.forEach((s) => (sensorMap[s.id] = [s.lat, s.lon]));

    let pts = route.path.map((sid) => sensorMap[sid]).filter(Boolean);
    if (pts.length < 2) return pts;

    const o = originMarker.getLatLng();
    const d = destMarker.getLatLng();
    const firstSensor = pts[0];
    const lastSensor = pts[pts.length - 1];

    if (o.distanceTo(L.latLng(firstSensor[0], firstSensor[1])) >= PIN_GAP_MIN_M) {
        pts = [[o.lat, o.lng], ...pts];
    }
    if (d.distanceTo(L.latLng(lastSensor[0], lastSensor[1])) >= PIN_GAP_MIN_M) {
        pts = [...pts, [d.lat, d.lng]];
    }
    return pts;
}

async function findRoutes() {
    const btn = document.getElementById('find-btn');
    const status = document.getElementById('status');
    btn.disabled = true;
    setStatus(status, 'Finding routes...', 'loading');

    routeLayers.forEach((l) => map.removeLayer(l));
    routeLayers = [];
    polylineLayers = [];

    const built = buildRouteFindBody();

    try {
        const data = await fetchJSON('/api/routes/find', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(built.body),
        });

        if (data.error) {
            setStatus(status, data.error, 'error');
            btn.disabled = false;
            return;
        }

        setStatus(status, 'Snapping routes to roads...', 'loading');
        await renderRoutes(data.routes, data.endpoints);
        let msg = `Found ${data.count} route(s)`;
        if (data.endpoints) {
            const eo = data.endpoints.origin;
            const ed = data.endpoints.destination;
            if (eo.source === 'coordinates') {
                msg += ` · Start → nearest sensor ${eo.sensor_id}`;
            }
            if (ed.source === 'coordinates') {
                msg += ` · End → nearest sensor ${ed.sensor_id}`;
            }
        }
        setStatus(status, msg, 'success');
    } catch (e) {
        setStatus(status, e.message, 'error');
    }
    btn.disabled = false;
}

async function renderRoutes(routes) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';

    const sensorMap = {};
    sensorData.forEach((s) => (sensorMap[s.id] = [s.lat, s.lon]));

    const roadGeometries = await Promise.all(
        routes.map((route) => getOSRMRoute(buildRoadWaypointsFromPath(route))),
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

        route.path.forEach((sid, j) => {
            const pos = sensorMap[sid];
            if (!pos) return;
            const isEndpoint = j === 0 || j === route.path.length - 1;
            if (!isEndpoint) {
                const dot = L.circleMarker(pos, {
                    radius: 5,
                    color: ROUTE_COLORS[i % ROUTE_COLORS.length],
                    fillColor: '#fff',
                    fillOpacity: 1,
                    weight: 2,
                })
                    .bindTooltip(`Sensor ${sid}`)
                    .addTo(map);
                routeLayers.push(dot);
            }
        });
    });

    if (routeLayers.length > 0) {
        const group = L.featureGroup([...routeLayers, originMarker, destMarker]);
        map.fitBounds(group.getBounds().pad(0.1));
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
