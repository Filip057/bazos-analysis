/*
 * Scraping control panel — start/stop/monitor scraping jobs.
 *
 * Uses authFetch() from auth.js for JWT-authenticated API calls.
 * Polls /api/admin/scrape/status every 3 seconds while a job is running.
 */

let currentJobId = null;
let pollInterval = null;

// ================================================================
// DB Stats
// ================================================================

async function loadDbStats() {
    try {
        const resp = await window.adminAuth.authFetch('/api/admin/scrape/db-stats');
        if (!resp.ok) return;
        const data = await resp.json();

        document.getElementById('stat-total').textContent =
            data.total_offers.toLocaleString('cs-CZ');
        document.getElementById('stat-brands').textContent =
            data.brands.length;
        document.getElementById('stat-last-scrape').textContent =
            data.latest_scrape ? formatDate(data.latest_scrape) : 'nikdy';

        // Brand breakdown cards
        const container = document.getElementById('brand-cards');
        container.innerHTML = '';
        if (data.brands.length > 0) {
            document.getElementById('brand-breakdown').style.display = '';
            data.brands.forEach(b => {
                container.innerHTML += `
                    <div class="col-md-2 col-sm-4 mb-2">
                        <div class="stat-card" style="padding:0.6rem 0.8rem;">
                            <div class="label">${escapeHtml(b.name)}</div>
                            <div class="value" style="font-size:1.2rem;">${b.count.toLocaleString('cs-CZ')}</div>
                        </div>
                    </div>`;
            });
        }

        // Populate brand dropdown
        const select = document.getElementById('scrape-brand');
        // Keep "all" option, remove old brand options
        while (select.options.length > 1) select.remove(1);
        data.brands.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.name;
            opt.textContent = `${b.name} (${b.count})`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Failed to load DB stats:', err);
    }
}

// ================================================================
// Start Scrape
// ================================================================

async function startScrape() {
    const brandSelect = document.getElementById('scrape-brand');
    const value = brandSelect.value;

    const body = value === 'all' ? {} : { brands: [value] };

    const btn = document.getElementById('btn-start');
    btn.disabled = true;
    btn.textContent = 'Spouštím...';

    try {
        const resp = await window.adminAuth.authFetch('/api/admin/scrape/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await resp.json();

        if (resp.status === 202) {
            currentJobId = data.job_id;
            showProgress();
            startPolling();
            showToast('Scraping spuštěn', 'success');
        } else if (resp.status === 409) {
            showToast('Scraping již běží', 'warning');
        } else {
            showToast(data.error || 'Chyba při spuštění', 'danger');
        }
    } catch (err) {
        showToast('Chyba sítě: ' + err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Spustit scraping';
    }
}

// ================================================================
// Cancel Scrape
// ================================================================

async function cancelScrape() {
    if (!currentJobId) return;
    const btn = document.getElementById('btn-cancel');
    btn.disabled = true;

    try {
        await window.adminAuth.authFetch('/api/admin/scrape/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: currentJobId }),
        });
        showToast('Scraping zrušen', 'info');
    } catch (err) {
        showToast('Chyba při rušení: ' + err.message, 'danger');
    } finally {
        btn.disabled = false;
    }
}

// ================================================================
// Polling
// ================================================================

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollStatus, 3000);
    pollStatus(); // immediate first poll
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

async function pollStatus() {
    try {
        const url = currentJobId
            ? `/api/admin/scrape/status?job_id=${currentJobId}`
            : '/api/admin/scrape/status';
        const resp = await window.adminAuth.authFetch(url);
        if (!resp.ok) return;

        const data = await resp.json();
        const job = data.job;

        if (!job) {
            stopPolling();
            hideProgress();
            return;
        }

        updateProgressUI(job);

        if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
            stopPolling();
            onJobFinished(job);
        }
    } catch (err) {
        console.error('Poll error:', err);
    }
}

// ================================================================
// Progress UI
// ================================================================

function showProgress() {
    document.getElementById('progress-section').style.display = '';
    document.getElementById('completed-banner').style.display = 'none';
    document.getElementById('control-section').querySelector('#btn-start').disabled = true;
}

function hideProgress() {
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('control-section').querySelector('#btn-start').disabled = false;
}

function updateProgressUI(job) {
    document.getElementById('progress-brand').textContent = job.current_brand || '—';

    const total = job.saved_count + job.filtered_count + job.failed_count;
    document.getElementById('p-saved').textContent = job.saved_count;
    document.getElementById('p-filtered').textContent = job.filtered_count;
    document.getElementById('p-failed').textContent = job.failed_count;
    document.getElementById('p-processed').textContent = job.processed_urls || total;

    // Progress bar — we don't know total URLs upfront, so show indeterminate
    // or use brands_done ratio if available
    const bar = document.getElementById('progress-bar');
    if (job.brands && job.brands_done) {
        const brandTotal = Array.isArray(job.brands) ? job.brands.length : 24;
        const done = job.brands_done.length;
        const pct = brandTotal > 0 ? Math.round((done / brandTotal) * 100) : 0;
        bar.style.width = pct + '%';
        bar.textContent = pct + '%';
    }

    // Brands done
    if (job.brands_done && job.brands_done.length > 0) {
        document.getElementById('brands-done-section').style.display = '';
        document.getElementById('brands-done-list').innerHTML =
            job.brands_done.map(b =>
                `<span class="badge bg-success brand-badge">${escapeHtml(b)}</span>`
            ).join(' ');
    }

    // Spinner visibility
    const spinner = document.getElementById('progress-spinner');
    spinner.style.display = (job.status === 'running' || job.status === 'queued') ? '' : 'none';
}

function onJobFinished(job) {
    hideProgress();

    if (job.status === 'completed') {
        const banner = document.getElementById('completed-banner');
        banner.style.display = '';
        banner.className = 'alert alert-success';
        document.getElementById('completed-summary').textContent =
            ` Uloženo ${job.saved_count} nabídek, filtrováno ${job.filtered_count}, chyb ${job.failed_count}.`;
    } else if (job.status === 'failed') {
        showToast('Scraping selhal: ' + (job.error_message || 'neznámá chyba'), 'danger');
    } else if (job.status === 'cancelled') {
        showToast('Scraping byl zrušen', 'info');
    }

    currentJobId = null;
    loadDbStats();
    loadHistory();
}

// ================================================================
// Job History
// ================================================================

async function loadHistory() {
    try {
        const resp = await window.adminAuth.authFetch('/api/admin/scrape/history');
        if (!resp.ok) return;
        const data = await resp.json();

        const tbody = document.getElementById('history-body');
        if (!data.jobs || data.jobs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-muted text-center">Zatím žádné joby</td></tr>';
            return;
        }

        tbody.innerHTML = data.jobs.map(job => {
            const brands = Array.isArray(job.brands) ? job.brands.join(', ') : 'všechny';
            const duration = job.started_at && job.completed_at
                ? formatDuration(new Date(job.completed_at) - new Date(job.started_at))
                : (job.status === 'running' ? 'běží...' : '—');

            return `<tr>
                <td><code>${escapeHtml(job.job_id)}</code></td>
                <td>${statusBadge(job.status)}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">${escapeHtml(brands)}</td>
                <td>${job.saved_count}</td>
                <td>${job.filtered_count}</td>
                <td>${job.failed_count}</td>
                <td>${job.started_at ? formatDate(job.started_at) : '—'}</td>
                <td>${duration}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.error('Failed to load history:', err);
    }
}

// ================================================================
// Helpers
// ================================================================

function statusBadge(status) {
    const map = {
        queued: 'bg-secondary',
        running: 'bg-primary',
        completed: 'bg-success',
        failed: 'bg-danger',
        cancelled: 'bg-warning text-dark',
    };
    const cls = map[status] || 'bg-secondary';
    return `<span class="badge status-badge ${cls}">${status}</span>`;
}

function formatDate(isoStr) {
    try {
        const d = new Date(isoStr);
        return d.toLocaleString('cs-CZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoStr;
    }
}

function formatDuration(ms) {
    const sec = Math.floor(ms / 1000);
    if (sec < 60) return sec + 's';
    const min = Math.floor(sec / 60);
    const rem = sec % 60;
    if (min < 60) return `${min}m ${rem}s`;
    const hr = Math.floor(min / 60);
    return `${hr}h ${min % 60}m`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showToast(message, type) {
    const container = document.getElementById('toast-container');
    const id = 'toast-' + Date.now();
    container.innerHTML += `
        <div id="${id}" class="toast align-items-center text-bg-${type} border-0 show" role="alert">
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`;
    setTimeout(() => {
        const el = document.getElementById(id);
        if (el) el.remove();
    }, 5000);
}

// ================================================================
// Init — check for active job on page load
// ================================================================

async function init() {
    await loadDbStats();
    await loadHistory();

    // Check if there's already an active job
    try {
        const resp = await window.adminAuth.authFetch('/api/admin/scrape/status');
        if (resp.ok) {
            const data = await resp.json();
            if (data.job && (data.job.status === 'running' || data.job.status === 'queued')) {
                currentJobId = data.job.job_id;
                showProgress();
                updateProgressUI(data.job);
                startPolling();
            }
        }
    } catch (err) {
        console.error('Failed to check active job:', err);
    }
}

init();
