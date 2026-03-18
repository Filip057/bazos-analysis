/**
 * Car Comparison Form Handler
 * Handles dependent brand→model dropdowns and comparison results
 */

document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("carComparisonForm");
    const brandSelect = document.getElementById("brand");
    const modelSelect = document.getElementById("model");
    const submitBtn = form.querySelector('button[type="submit"]');
    const submitText = document.getElementById("submitText");
    const loading = document.getElementById("loading");
    const resultsCard = document.getElementById("resultsCard");
    const resultsContent = document.getElementById("resultsContent");

    // ── Load brands on page load ──
    async function loadBrands() {
        try {
            const resp = await fetch("/api/brands");
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const brands = await resp.json();

            brands.forEach(b => {
                const opt = document.createElement("option");
                opt.value = b;
                opt.textContent = b.charAt(0).toUpperCase() + b.slice(1);
                brandSelect.appendChild(opt);
            });
        } catch (e) {
            console.error("Failed to load brands:", e);
        }
    }

    // ── Load models when brand changes ──
    brandSelect.addEventListener("change", async function() {
        const brand = this.value;

        // Reset model dropdown
        modelSelect.innerHTML = '<option value="">— vyber model —</option>';

        if (!brand) {
            modelSelect.disabled = true;
            return;
        }

        try {
            const resp = await fetch(`/api/models/${encodeURIComponent(brand)}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const models = await resp.json();

            models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m;
                opt.textContent = m;
                modelSelect.appendChild(opt);
            });

            modelSelect.disabled = false;
        } catch (e) {
            console.error("Failed to load models:", e);
            modelSelect.innerHTML = '<option value="">Chyba při načítání</option>';
        }
    });

    // ── Form submission ──
    form.addEventListener("submit", async function(e) {
        e.preventDefault();

        const brand = brandSelect.value;
        const model = modelSelect.value;
        const price = document.getElementById("price").value;
        const year = document.getElementById("year").value;
        const y_plusminus = document.getElementById("y_plusminus").value;
        const mileage = document.getElementById("mileage").value;
        const m_pct_plusminus = document.getElementById("m_pct_plusminus").value;

        if (!brand || !model || !price) {
            showError("Vyplň značku, model a cenu");
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        loading.style.display = 'inline-block';
        submitText.textContent = 'Porovnávám...';
        resultsCard.style.display = 'none';

        try {
            let apiUrl = `/api/car-compare/${encodeURIComponent(brand)}/${encodeURIComponent(model)}/${price}`;

            const params = new URLSearchParams();
            if (year) params.append('year', year);
            if (y_plusminus) params.append('y_plusminus', y_plusminus);
            if (mileage) params.append('mileage', mileage);
            if (m_pct_plusminus) params.append('m_pct_plusminus', m_pct_plusminus);

            if (params.toString()) {
                apiUrl += '?' + params.toString();
            }

            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 404) {
                    showError(data.error || data.message || 'Nenalezena žádná podobná auta');
                } else if (response.status === 400) {
                    showError(data.error || 'Neplatný vstup. Zkontroluj hodnoty.');
                } else {
                    showError(data.error || 'Chyba při načítání dat');
                }
            } else {
                displayResults(data, brand, model, price);
            }

        } catch (error) {
            console.error('Error:', error);
            showError('Chyba sítě: nepodařilo se připojit k serveru.');
        } finally {
            submitBtn.disabled = false;
            loading.style.display = 'none';
            submitText.textContent = 'Porovnat cenu';
        }
    });

    function displayResults(data, brand, model, price) {
        const percentile = data.percentile.toFixed(2);
        const totalCars = data.total_similar_cars;
        const cheaper = data.cars_cheaper;
        const moreExpensive = data.cars_more_expensive;
        const filters = data.filters_applied;

        let html = `
            <div class="text-center mb-4">
                <div class="percentile-display">${percentile}%</div>
                <p class="lead">${data.message}</p>
            </div>

            <div class="row text-center mb-4">
                <div class="col-md-4">
                    <div class="stats-item">
                        <h3 class="text-primary">${totalCars}</h3>
                        <p class="text-muted mb-0">Podobných aut</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stats-item">
                        <h3 class="text-success">${cheaper}</h3>
                        <p class="text-muted mb-0">Levnějších</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stats-item">
                        <h3 class="text-danger">${moreExpensive}</h3>
                        <p class="text-muted mb-0">Dražších</p>
                    </div>
                </div>
            </div>

            <div class="alert alert-info">
                <h5>Tvoje auto:</h5>
                <ul class="mb-0">
                    <li><strong>Značka:</strong> ${brand}</li>
                    <li><strong>Model:</strong> ${model}</li>
                    <li><strong>Cena:</strong> ${Number(price).toLocaleString('cs-CZ')} CZK</li>
                    ${filters.year_range ? `<li><strong>Roky:</strong> ${filters.year_range}</li>` : ''}
                    ${filters.mileage_range ? `<li><strong>Nájezd:</strong> ${filters.mileage_range} km</li>` : ''}
                </ul>
            </div>

            <div class="mt-4">
                <h5>Co to znamená?</h5>
                <p class="text-muted">
                    ${percentile < 50
                        ? "Super deal! Tvoje auto je levnější než většina podobných nabídek."
                        : percentile < 75
                        ? "Férová cena. Tvoje auto je konkurenceschopné."
                        : "Vyšší než průměr. Možná zvážit snížení ceny."}
                </p>
            </div>
        `;

        resultsContent.innerHTML = html;
        resultsCard.style.display = 'block';
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showError(message) {
        resultsContent.innerHTML = `
            <div class="error-message">
                <h5>Chyba</h5>
                <p class="mb-0">${message}</p>
            </div>
        `;
        resultsCard.style.display = 'block';
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Init
    loadBrands();
});
