/* TBRGS -- Testing Page */

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('run-tests-btn').addEventListener('click', runTests);
});

async function runTests() {
    const btn = document.getElementById('run-tests-btn');
    const status = document.getElementById('test-status');
    const output = document.getElementById('test-output');
    const tbody = document.getElementById('test-body');

    btn.disabled = true;
    setStatus(status, 'Running pytest...', 'loading');
    output.textContent = 'Running tests...\n';
    tbody.innerHTML = '';

    try {
        const data = await fetchJSON('/api/testing/run');
        output.textContent = data.output;

        // Parse test results
        if (data.results) {
            data.results.forEach(t => {
                const tr = document.createElement('tr');
                const passed = t.status === 'passed';
                tr.innerHTML = `
                    <td>${t.name}</td>
                    <td><span class="badge ${passed ? 'badge-pass' : 'badge-fail'}">${t.status}</span></td>
                    <td>${t.duration || '--'}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        const passCount = data.results?.filter(t => t.status === 'passed').length || 0;
        const total = data.results?.length || 0;
        setStatus(status, `${passCount}/${total} tests passed`, passCount === total ? 'success' : 'error');
    } catch (e) {
        setStatus(status, e.message, 'error');
        output.textContent = 'Error running tests: ' + e.message;
    }
    btn.disabled = false;
}
