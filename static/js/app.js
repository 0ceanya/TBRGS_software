/* TBRGS -- Shared utilities */

async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

function setStatus(el, msg, type) {
    el.textContent = msg;
    el.className = 'status ' + (type || '');
}

/* Populate a <select> with sensor options */
async function populateSensorDropdowns(...selectIds) {
    const data = await fetchJSON('/api/graph/sensors');
    const options = data.sensors.map(s =>
        `<option value="${s.id}">${s.id}</option>`
    ).join('');
    for (const id of selectIds) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = options;
    }
    return data.sensors;
}

/* Populate a <select> with algorithm options */
async function populateAlgorithmDropdown(...selectIds) {
    const data = await fetchJSON('/api/graph/algorithms');
    const options = data.algorithms.map(a =>
        `<option value="${a}" ${a === 'AS' ? 'selected' : ''}>${a}</option>`
    ).join('');
    for (const id of selectIds) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = options;
    }
}

/* Route colors for map overlays */
const ROUTE_COLORS = ['#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626',
                       '#0891b2', '#4f46e5', '#15803d', '#b45309', '#9f1239'];
