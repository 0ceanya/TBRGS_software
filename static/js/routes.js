/* TBRGS -- Route Finding Page */

let map,
    sensorData = [],
    routeLayers = [],
    polylineLayers = [];
/** Incremented on each new search so in-flight path animations cancel */
let routeAnimationGeneration = 0;
let originMarker, destMarker;
/** 'sensor' = use dropdown; 'map' = use dragged pin position */
let originMode = 'sensor';
let destMode = 'sensor';

const geocodeCache = new Map();

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

async function reverseLabel(lat, lon) {
    const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;
    if (geocodeCache.has(key)) return geocodeCache.get(key);
    try {
        const res = await fetch(
            `/api/geocode/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`,
        );
        if (!res.ok) throw new Error('geocode failed');
        const data = await res.json();
        const out = {
            display_name: data.display_name || '',
            short_label: data.short_label || data.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
        };
        geocodeCache.set(key, out);
        return out;
    } catch {
        const fallback = { display_name: '', short_label: `${lat.toFixed(4)}, ${lon.toFixed(4)}` };
        geocodeCache.set(key, fallback);
        return fallback;
    }
}

async function refreshOriginTooltip() {
    const ll = originMarker.getLatLng();
    const geo = await reverseLabel(ll.lat, ll.lng);
    originMarker.setTooltipContent(`A — ${geo.short_label}`);
}

async function refreshDestTooltip() {
    const ll = destMarker.getLatLng();
    const geo = await reverseLabel(ll.lat, ll.lng);
    destMarker.setTooltipContent(`B — ${geo.short_label}`);
}

function syncOriginMarkerFromSelect() {
    const id = document.getElementById('origin').value;
    originMarker.setLatLng(getSensorPos(id));
    refreshOriginTooltip();
}

function syncDestMarkerFromSelect() {
    const id = document.getElementById('destination').value;
    destMarker.setLatLng(getSensorPos(id));
    refreshDestTooltip();
}

function setOriginFromSensor(s) {
    if (!s) return;
    originMode = 'sensor';
    const sel = document.getElementById('origin');
    sel.value = s.id;
    originMarker.setLatLng([s.lat, s.lon]);
    updateMapModeHint();
    refreshOriginTooltip();
}

function setDestFromSensor(s) {
    if (!s) return;
    destMode = 'sensor';
    const sel = document.getElementById('destination');
    sel.value = s.id;
    destMarker.setLatLng([s.lat, s.lon]);
    updateMapModeHint();
    refreshDestTooltip();
}

function updateMapModeHint() {
    const el = document.getElementById('map-mode-hint');
    const parts = [];
    if (originMode === 'map') {
        parts.push(
            '<strong>Start (A)</strong> follows the green pin (advanced sensor list does not apply until you pick a sensor again).',
        );
    }
    if (destMode === 'map') {
        parts.push(
            '<strong>End (B)</strong> follows the red pin (destination list does not apply until you pick a sensor again).',
        );
    }
    el.innerHTML = parts.join('<br>');
}

function wireSensorFilter(searchId, selectId) {
    const search = document.getElementById(searchId);
    const sel = document.getElementById(selectId);
    search.addEventListener('input', () => {
        const q = search.value.trim().toLowerCase();
        const prev = sel.value;
        const match = q
            ? sensorData.filter((s) => s.id.toLowerCase().includes(q))
            : sensorData;
        sel.innerHTML = match.map((s) => `<option value="${s.id}">${s.id}</option>`).join('');
        if (match.some((s) => s.id === prev)) sel.value = prev;
    });
}

function selectedMilestoneSteps() {
    const boxes = document.querySelectorAll('.milestone-checks input[name="ms"]:checked');
    const steps = [...boxes].map((b) => parseInt(b.value, 10)).sort((a, b) => a - b);
    return steps.length ? steps : [1];
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
        .bindTooltip('A — …', { direction: 'top' });

    destMarker = L.marker(getSensorPos('401129'), {
        draggable: true,
        autoPan: true,
        zIndexOffset: 2000,
        icon: makeEndpointIcon('B', '#dc2626'),
    })
        .addTo(map)
        .bindTooltip('B — …', { direction: 'top' });

    refreshOriginTooltip();
    refreshDestTooltip();

    const tcSel = document.getElementById('test-case-pems');
    try {
        const tcData = await fetchJSON('/api/test-cases');
        for (const tc of tcData.test_cases || []) {
            const o = document.createElement('option');
            o.value = tc.id;
            o.textContent = tc.label;
            o.dataset.origin = tc.default_origin;
            o.dataset.dest = tc.default_destination;
            o.dataset.time = tc.time_context || '';
            tcSel.appendChild(o);
        }
    } catch {
        /* keep "None" only */
    }

    tcSel.addEventListener('change', () => {
        const opt = tcSel.selectedOptions[0];
        if (!opt || !opt.value) return;
        const o = opt.dataset.origin;
        const d = opt.dataset.dest;
        const t = opt.dataset.time;
        if (o) {
            const sens = sensorData.find((x) => x.id === o);
            if (sens) setOriginFromSensor(sens);
        }
        if (d) {
            const sens = sensorData.find((x) => x.id === d);
            if (sens) setDestFromSensor(sens);
        }
        if (t && /^\d{1,2}:\d{2}$/.test(t)) {
            const parts = t.split(':');
            const hh = parts[0].padStart(2, '0').slice(-2);
            const mm = parts[1].padStart(2, '0').slice(-2);
            document.getElementById('departure-time').value = `${hh}:${mm}`;
        }
        document.getElementById('scenario').value = 'custom';
    });

    const scenarioSel = document.getElementById('scenario');
    try {
        const scData = await fetchJSON('/api/scenarios');
        scData.scenarios.forEach((s) => {
            const o = document.createElement('option');
            o.value = s.id;
            o.textContent = s.label;
            o.dataset.origin = s.default_origin || '';
            o.dataset.dest = s.default_destination || '';
            o.dataset.time = s.time_context || '';
            scenarioSel.appendChild(o);
        });
    } catch {
        scenarioSel.innerHTML = '<option value="custom">Custom</option>';
    }

    scenarioSel.addEventListener('change', () => {
        const opt = scenarioSel.selectedOptions[0];
        if (!opt || opt.dataset.origin === undefined) return;
        if (opt.value === 'custom') return;
        tcSel.value = '';
        const o = opt.dataset.origin;
        const d = opt.dataset.dest;
        const t = opt.dataset.time;
        if (o) {
            const sens = sensorData.find((x) => x.id === o);
            if (sens) setOriginFromSensor(sens);
        }
        if (d) {
            const sens = sensorData.find((x) => x.id === d);
            if (sens) setDestFromSensor(sens);
        }
        if (t && /^\d{1,2}:\d{2}$/.test(t)) {
            document.getElementById('departure-time').value =
                t.length === 5 ? t : `0${t}`.slice(-5);
        }
    });

    document.getElementById('sensor-advanced-toggle').addEventListener('click', () => {
        const body = document.getElementById('sensor-advanced-body');
        const btn = document.getElementById('sensor-advanced-toggle');
        const open = body.hidden;
        body.hidden = !open;
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    wireSensorFilter('origin-search', 'origin');
    wireSensorFilter('destination-search', 'destination');

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
    originMarker.on('dragend', () => {
        updateMapModeHint();
        refreshOriginTooltip();
    });
    destMarker.on('dragend', () => {
        updateMapModeHint();
        refreshDestTooltip();
    });

    const slider = document.getElementById('k');
    const display = document.getElementById('k-display');
    slider.addEventListener('input', () => (display.textContent = slider.value));

    document.getElementById('find-btn').addEventListener('click', findRoutes);
});

/** Build POST body: map pins override dropdowns when that end is in map mode. */
function buildRouteFindBody() {
    const depEl = document.getElementById('departure-time');
    const depVal = depEl?.value || '';
    const body = {
        model: document.getElementById('model').value,
        algorithm: document.getElementById('algorithm').value,
        k: parseInt(document.getElementById('k').value, 10),
        departure_time: depVal || null,
        milestone_steps: selectedMilestoneSteps(),
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
 * Map lines: OSRM “best” driving path(s) between the A and B pins only.
 * Travel time / distance in the table still come from the sensor graph + model.
 */
async function fetchPinToPinDrivingGeometries(numRoutes) {
    const o = originMarker.getLatLng();
    const d = destMarker.getLatLng();
    const coords = `${o.lng},${o.lat};${d.lng},${d.lat}`;
    const pinA = [o.lat, o.lng];
    const pinB = [d.lat, d.lng];
    const straight = [pinA, pinB];

    let url = `/api/osrm?coords=${encodeURIComponent(coords)}`;
    if (numRoutes > 1) {
        url += '&alternatives=true';
    }

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('osrm http');
        const data = await res.json();
        if (data.code !== 'Ok' || !data.routes?.length) throw new Error('osrm response');

        const geoms = data.routes.map((r) =>
            r.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
        );
        const out = [];
        for (let i = 0; i < numRoutes; i++) {
            const g = geoms[Math.min(i, geoms.length - 1)];
            out.push(g.length >= 2 ? g : straight);
        }
        return out;
    } catch {
        return Array.from({ length: numRoutes }, () => straight);
    }
}

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

/** Precompute segment lengths (meters) for progressive polyline drawing */
function buildPolylineSampler(latlngs, mapInstance) {
    if (!latlngs || latlngs.length < 2) {
        return { latlngs: latlngs || [], segLens: [], total: 0 };
    }
    const segLens = [];
    let total = 0;
    for (let i = 1; i < latlngs.length; i++) {
        const d = mapInstance.distance(L.latLng(latlngs[i - 1]), L.latLng(latlngs[i]));
        segLens.push(d);
        total += d;
    }
    return { latlngs, segLens, total };
}

/** Points along the polyline from the start up to targetDist meters */
function latlngsAtDistance(sampler, targetDist) {
    const { latlngs, segLens, total } = sampler;
    if (latlngs.length < 2) return latlngs.length ? [latlngs[0], latlngs[0]] : [];
    const clamped = Math.max(0, Math.min(targetDist, total));
    if (clamped <= 0) {
        const p = latlngs[0];
        return [p, p];
    }
    if (clamped >= total) return latlngs;

    const out = [latlngs[0]];
    let acc = 0;
    for (let i = 0; i < segLens.length; i++) {
        const seg = segLens[i];
        if (acc + seg >= clamped) {
            const t = (clamped - acc) / seg;
            const a = L.latLng(latlngs[i]);
            const b = L.latLng(latlngs[i + 1]);
            out.push([a.lat + t * (b.lat - a.lat), a.lng + t * (b.lng - a.lng)]);
            return out;
        }
        acc += seg;
        out.push(latlngs[i + 1]);
    }
    return out;
}

/**
 * Reveal the route along the road geometry, with a moving "front" marker.
 * @returns {Promise<L.Polyline|null>} the polyline, or null if cancelled
 */
function animateRoutePolyline(mapInstance, latlngs, lineStyle, durationMs, isAlive) {
    const sampler = buildPolylineSampler(latlngs, mapInstance);
    if (sampler.total <= 0 || latlngs.length < 2) {
        const line = L.polyline(latlngs, lineStyle).addTo(mapInstance);
        return Promise.resolve(line);
    }

    const startPt = latlngs[0];
    const poly = L.polyline([startPt, startPt], lineStyle).addTo(mapInstance);
    const head = L.circleMarker(L.latLng(startPt), {
        radius: 7,
        color: lineStyle.color || '#2563eb',
        fillColor: '#ffffff',
        fillOpacity: 0.95,
        weight: 3,
        className: 'route-search-head',
    }).addTo(mapInstance);

    const start = performance.now();

    return new Promise((resolve) => {
        function frame(now) {
            if (!isAlive()) {
                mapInstance.removeLayer(poly);
                mapInstance.removeLayer(head);
                resolve(null);
                return;
            }
            const raw = Math.min(1, (now - start) / durationMs);
            const eased = easeOutCubic(raw);
            const dist = eased * sampler.total;
            const pts = latlngsAtDistance(sampler, dist);
            poly.setLatLngs(pts.length >= 2 ? pts : [startPt, startPt]);
            head.setLatLng(pts[pts.length - 1]);
            if (raw < 1) {
                requestAnimationFrame(frame);
            } else {
                poly.setLatLngs(latlngs);
                mapInstance.removeLayer(head);
                resolve(poly);
            }
        }
        requestAnimationFrame(frame);
    });
}

function renderForecastSection(data) {
    const intro = document.getElementById('forecast-intro');
    const section = document.getElementById('forecast-section');
    const noteEl = document.getElementById('forecast-note');
    const tables = document.getElementById('forecast-tables');

    const dep = data.departure_time || document.getElementById('departure-time')?.value;
    if (dep) {
        intro.hidden = false;
        intro.textContent = `Assuming departure at ${dep}. ${data.forecast_note || ''}`;
    } else {
        intro.hidden = true;
        intro.textContent = '';
    }

    noteEl.textContent = data.forecast_note || '';

    const milestones = data.horizon_milestones || [];
    const extras = milestones.slice(1);
    if (extras.length === 0) {
        section.hidden = true;
        tables.innerHTML = '';
        return;
    }

    section.hidden = false;
    tables.innerHTML = '';

    extras.forEach((m) => {
        const wrap = document.createElement('div');
        wrap.className = 'forecast-block';
        wrap.innerHTML = `<h4 class="forecast-block-title">Traffic at ${m.label} (step ${m.step})</h4>`;
        const table = document.createElement('table');
        table.className = 'table';
        table.innerHTML =
            '<thead><tr><th>#</th><th>Travel time</th><th>Distance</th><th>Sensors</th></tr></thead><tbody></tbody>';
        const tb = table.querySelector('tbody');
        (m.routes || []).forEach((route, i) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${i + 1}</td>
                <td>${route.travel_time_display}</td>
                <td>${route.distance_km} km</td>
                <td>${route.num_sensors}</td>
            `;
            tb.appendChild(tr);
        });
        wrap.appendChild(table);
        tables.appendChild(wrap);
    });
}

async function findRoutes() {
    const btn = document.getElementById('find-btn');
    const status = document.getElementById('status');
    btn.disabled = true;
    setStatus(status, 'Finding routes...', 'loading');

    routeAnimationGeneration += 1;
    const animGen = routeAnimationGeneration;

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
            document.getElementById('forecast-section').hidden = true;
            btn.disabled = false;
            return;
        }

        renderForecastSection(data);

        setStatus(status, 'Snapping routes to roads...', 'loading');
        await renderRoutes(data.routes, animGen, status);
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

async function renderRoutes(routes, animGen, statusEl) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';

    const roadGeometries = await fetchPinToPinDrivingGeometries(routes.length);

    if (animGen !== routeAnimationGeneration) return;

    let bounds = L.latLngBounds([]);
    roadGeometries.forEach((latlngs) => {
        latlngs.forEach((p) => bounds.extend(p));
    });
    if (bounds.isValid()) {
        bounds.extend(originMarker.getLatLng());
        bounds.extend(destMarker.getLatLng());
        map.fitBounds(bounds.pad(0.1));
    }

    routes.forEach((route, i) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span style="color:${ROUTE_COLORS[i % ROUTE_COLORS.length]}; font-weight:700">${i + 1}</span></td>
            <td>${route.travel_time_display}</td>
            <td>${route.distance_km} km</td>
            <td>${route.num_sensors}</td>
        `;
        tr.addEventListener('click', () => highlightRoute(i));
        tbody.appendChild(tr);
    });

    if (statusEl && animGen === routeAnimationGeneration) {
        setStatus(statusEl, 'Tracing routes on the map...', 'loading');
    }

    for (let i = 0; i < routes.length; i++) {
        if (animGen !== routeAnimationGeneration) return;

        if (i > 0) {
            await new Promise((r) => setTimeout(r, 180));
            if (animGen !== routeAnimationGeneration) return;
        }

        const latlngs = roadGeometries[i];
        if (latlngs.length < 2) continue;

        const lineStyle = {
            color: ROUTE_COLORS[i % ROUTE_COLORS.length],
            weight: i === 0 ? 5 : 4,
            opacity: i === 0 ? 0.92 : 0.52,
            lineCap: 'round',
            lineJoin: 'round',
        };
        if (i > 0) {
            lineStyle.dashArray = '12, 10';
        }

        const sampler = buildPolylineSampler(latlngs, map);
        const duration = Math.min(2600, Math.max(750, sampler.total / 2.8));

        const polyline = await animateRoutePolyline(
            map,
            latlngs,
            lineStyle,
            duration,
            () => animGen === routeAnimationGeneration,
        );

        if (polyline == null) return;

        routeLayers.push(polyline);
        polylineLayers.push(polyline);
    }
}

function highlightRoute(index) {
    document.querySelectorAll('#results-body tr').forEach((tr, i) => {
        tr.classList.toggle('active', i === index);
    });
    polylineLayers.forEach((layer, i) => {
        const isAlt = i > 0;
        layer.setStyle({
            weight: i === index ? 6 : isAlt ? 4 : 5,
            opacity: i === index ? 1.0 : 0.35,
            dashArray: isAlt ? '12, 10' : undefined,
        });
        if (i === index) layer.bringToFront();
    });
}
