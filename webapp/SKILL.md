---
name: bazos-webapp
description: >
  Skill for developing the Flask web application — routes, API endpoints, Jinja2 templates,
  and frontend (Bootstrap + vanilla JS). Use this skill whenever working on webapp/ directory,
  adding new pages or API endpoints, modifying templates, fixing frontend issues, changing
  Flask configuration, or working with Flask-Limiter. Also trigger when the user mentions
  dashboard, car comparison page, API responses, or any webapp-related task.
---

# Flask Webapp Skill

## Purpose

Web interface for browsing and analyzing scraped car data from bazos.cz. Provides a
dashboard with market statistics and a car comparison tool. All data is served via
JSON API endpoints consumed by frontend JavaScript.

## Architecture

```
webapp/
├── app.py          # Flask app, all routes and API endpoints
├── config.py       # App configuration (loads from .env)
├── static/         # CSS, JS, images (Bootstrap-based)
└── templates/      # Jinja2 HTML templates
```

## Pages

- **`/`** — Landing page (`index.html`)
- **`/dashboard`** — Analytics dashboard with overview stats, brand/model breakdowns,
  year/fuel/price distributions (`dashboard.html`)
- **`/car-compare`** — Compare a specific offer against market data (`car-compare.html`)

## API Endpoints

All API endpoints return JSON. Rate limited via Flask-Limiter.

### Dropdown APIs
- **`GET /api/brands`** — List all brands with at least one offer (60/min)
- **`GET /api/models/<brand>`** — List all models for a brand (60/min)

### Analytics APIs (Module 1: Overview)
- **`GET /api/stats/overview`** — High-level summary: total cars, brands, models, averages, data completeness, last scrape time (60/min)
- **`GET /api/stats/brands`** — Per-brand stats: count, avg price/mileage/year. Params: `limit` (default 24, max 50) (60/min)
- **`GET /api/stats/models`** — Per-model stats for a brand. Params: `brand` (required), `limit` (default 20) (60/min)
- **`GET /api/stats/year-distribution`** — Car count by year of manufacture. Params: `brand`, `model` (optional) (30/min)
- **`GET /api/stats/fuel-distribution`** — Car count by fuel type. Params: `brand` (optional) (30/min)
- **`GET /api/stats/price-distribution`** — Price histogram. Params: `brand`, `model`, `bucket` (default 50000 CZK, clamped 10k–500k) (30/min)

### Data Model

All API queries use the `Car` view model (flattened `car_view` joining brands + models + offers).
This provides a simple flat structure with: brand, model, year_manufacture, mileage, power,
fuel, price, url, scraped_at, years_in_usage, price_per_km, mileage_per_year.

## Frontend Stack

- **Bootstrap** for layout and components
- **Vanilla JavaScript** for API calls and dynamic content
- **CSS** for custom styling
- No frontend framework (React, Vue, etc.) — keep it simple

## Key Patterns

### Database Access

All routes use `get_db_session()` context manager — never create sessions manually:

```python
with get_db_session() as session:
    rows = session.query(Car).filter(...).all()
    return jsonify([...])
```

Every DB query is wrapped in `try/except SQLAlchemyError` with logging and a
generic error response `{"error": "Database error"}` with status 500.

### Adding a New API Endpoint

1. Add route in `app.py` with `@limiter.limit()` decorator
2. Use `get_db_session()` context manager
3. Query against `Car` view model (not raw Offer/Brand/Model unless necessary)
4. Wrap in try/except SQLAlchemyError
5. Return JSON with `jsonify()`
6. Write tests for the new endpoint
7. Document query params and response shape in the docstring

### Adding a New Page

1. Create template in `webapp/templates/`
2. Add route in `app.py` returning `render_template()`
3. Frontend JS calls API endpoints for data
4. Use Bootstrap for layout consistency

### Rate Limiting

Flask-Limiter is configured for API endpoints. Current limits:
- Standard endpoints: 60 requests/minute
- Heavier analytics endpoints: 30 requests/minute

Note: The limiter is also used during scraping operations, not just for webapp traffic.

## Configuration

- `webapp/config.py` loads settings from `.env` file
- Database credentials, Flask secret key, and other sensitive config via environment variables
- Never hardcode credentials or secrets

## Common Pitfalls

- **Always use `Car` view model for reads** — it provides the flattened structure the API
  expects. Using raw `Offer` model requires manual joins with Brand/Model.
- **Null handling**: Many fields can be None (mileage, year, power, fuel). Always check
  for None before arithmetic operations (round, float conversion).
- **Price outliers**: Price distribution endpoint filters out prices > 5M CZK and <= 0.
  Apply similar guards in new analytics endpoints.
- **Pagination**: Current endpoints use `limit` param but no offset/cursor. For large
  result sets, consider adding pagination.
