/**
 * Car Comparison Form Handler
 * Handles form submission and displays comparison results
 */

document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("carComparisonForm");
    const submitBtn = form.querySelector('button[type="submit"]');
    const submitText = document.getElementById("submitText");
    const loading = document.getElementById("loading");
    const resultsCard = document.getElementById("resultsCard");
    const resultsContent = document.getElementById("resultsContent");

    form.addEventListener("submit", async function(e) {
        e.preventDefault();

        // Get form data
        const formData = new FormData(form);
        const brand = formData.get('brand');
        const model = formData.get('model');
        const price = formData.get('price');
        const year = formData.get('year');
        const y_plusminus = formData.get('y_plusminus');
        const mileage = formData.get('mileage');
        const m_pct_plusminus = formData.get('m_pct_plusminus');

        // Validate required fields
        if (!brand || !model || !price) {
            showError("Please fill in Brand, Model, and Price fields");
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        loading.style.display = 'inline-block';
        submitText.textContent = 'Comparing...';
        resultsCard.style.display = 'none';

        try {
            // Build API URL with path parameters
            let apiUrl = `/api/car-compare/${encodeURIComponent(brand)}/${encodeURIComponent(model)}/${price}`;

            // Add query parameters for optional filters
            const params = new URLSearchParams();
            if (year) params.append('year', year);
            if (y_plusminus) params.append('y_plusminus', y_plusminus);
            if (mileage) params.append('mileage', mileage);
            if (m_pct_plusminus) params.append('m_pct_plusminus', m_pct_plusminus);

            if (params.toString()) {
                apiUrl += '?' + params.toString();
            }

            // Make API request
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();

            if (!response.ok) {
                // Handle error response
                if (response.status === 404) {
                    showError(data.error || data.message || 'No similar cars found for comparison');
                } else if (response.status === 400) {
                    showError(data.error || 'Invalid input. Please check your values.');
                } else {
                    showError(data.error || 'An error occurred while fetching data');
                }
            } else {
                // Display success results
                displayResults(data, brand, model, price);
            }

        } catch (error) {
            console.error('Error:', error);
            showError('Network error: Could not connect to server. Please try again.');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            loading.style.display = 'none';
            submitText.textContent = 'Compare Price';
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
                        <p class="text-muted mb-0">Similar Cars Found</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stats-item">
                        <h3 class="text-success">${cheaper}</h3>
                        <p class="text-muted mb-0">Cars Cheaper</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stats-item">
                        <h3 class="text-danger">${moreExpensive}</h3>
                        <p class="text-muted mb-0">Cars More Expensive</p>
                    </div>
                </div>
            </div>

            <div class="alert alert-info">
                <h5>Your Car Details:</h5>
                <ul class="mb-0">
                    <li><strong>Brand:</strong> ${brand}</li>
                    <li><strong>Model:</strong> ${model}</li>
                    <li><strong>Price:</strong> ${price.toLocaleString()} CZK</li>
                    ${filters.year_range ? `<li><strong>Year Range:</strong> ${filters.year_range}</li>` : ''}
                    ${filters.mileage_range ? `<li><strong>Mileage Range:</strong> ${filters.mileage_range} km</li>` : ''}
                </ul>
            </div>

            <div class="mt-4">
                <h5>What does this mean?</h5>
                <p class="text-muted">
                    ${percentile < 50
                        ? "✅ Great deal! Your car is priced lower than most similar offers."
                        : percentile < 75
                        ? "👍 Fair price. Your car is competitively priced."
                        : "⚠️ Higher than average. You might want to reconsider the price."}
                </p>
            </div>
        `;

        resultsContent.innerHTML = html;
        resultsCard.style.display = 'block';

        // Smooth scroll to results
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showError(message) {
        const errorHtml = `
            <div class="error-message">
                <h5>❌ Error</h5>
                <p class="mb-0">${message}</p>
            </div>
        `;

        resultsContent.innerHTML = errorHtml;
        resultsCard.style.display = 'block';
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});
