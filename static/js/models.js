/* TBRGS -- Model Comparison Page */

document.addEventListener('DOMContentLoaded', async () => {
    await populateSensorDropdowns('cmp-origin', 'cmp-destination');
    await populateAlgorithmDropdown('cmp-algorithm');

    document.getElementById('cmp-origin').value = '402365';
    document.getElementById('cmp-destination').value = '401129';

    // Load available models and create checkboxes
    const modelData = await fetchJSON('/api/models/available');
    const container = document.getElementById('model-checkboxes');
    modelData.models.forEach(m => {
        const label = document.createElement('label');
        const avail = m.available;
        label.innerHTML = `
            <input type="checkbox" value="${m.name}" ${avail ? 'checked' : 'disabled'}>
            ${m.name.toUpperCase()}
            ${!avail ? '<span class="badge badge-unavailable">unavailable</span>' : ''}
        `;
        container.appendChild(label);
    });

    document.getElementById('compare-btn').addEventListener('click', compare);
});

async function compare() {
    const btn = document.getElementById('compare-btn');
    const status = document.getElementById('cmp-status');
    btn.disabled = true;
    setStatus(status, 'Comparing models...', 'loading');

    const checked = [...document.querySelectorAll('#model-checkboxes input:checked')];
    const models = checked.map(c => c.value);

    if (models.length === 0) {
        setStatus(status, 'Select at least one model', 'error');
        btn.disabled = false;
        return;
    }

    const body = {
        origin: document.getElementById('cmp-origin').value,
        destination: document.getElementById('cmp-destination').value,
        algorithm: document.getElementById('cmp-algorithm').value,
        models: models,
        k: 5,
    };

    try {
        const data = await fetchJSON('/api/models/compare', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body),
        });

        renderComparison(data.comparisons);
        setStatus(status, 'Comparison complete', 'success');
    } catch (e) {
        setStatus(status, e.message, 'error');
    }
    btn.disabled = false;
}

function renderComparison(comparisons) {
    const container = document.getElementById('comparison-results');
    container.innerHTML = '';

    for (const [model, result] of Object.entries(comparisons)) {
        const card = document.createElement('div');
        card.className = 'comparison-card';

        if (result.error) {
            card.innerHTML = `
                <h3>${model.toUpperCase()}</h3>
                <p class="status error">${result.error}</p>
            `;
        } else {
            const routes = result.routes;
            const best = routes[0];
            const bestMins = best ? (best.travel_time_seconds / 60).toFixed(1) : '--';

            let tableRows = routes.map((r, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td>${(r.travel_time_seconds / 60).toFixed(1)} min</td>
                    <td>${r.distance_km} km</td>
                    <td>${r.num_sensors}</td>
                </tr>
            `).join('');

            card.innerHTML = `
                <h3>${model.toUpperCase()}</h3>
                <div style="margin-bottom:0.75rem">
                    <span class="metric">${bestMins}</span>
                    <span class="metric-label"> min (best route)</span>
                </div>
                <table class="table">
                    <thead><tr><th>#</th><th>Time</th><th>Distance</th><th>Sensors</th></tr></thead>
                    <tbody>${tableRows}</tbody>
                </table>
            `;
        }
        container.appendChild(card);
    }
}
