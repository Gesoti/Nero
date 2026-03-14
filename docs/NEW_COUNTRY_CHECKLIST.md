# New Country Addition Checklist

Step-by-step process for adding a new country to Nero. Each step references
the exact files to create/modify, following the established pattern from
Cyprus, Greece, and Spain integrations.

Replace `{cc}` with the 2-letter country code (e.g., `pt`, `it`, `fr`).
Replace `{Country}` with the country name (e.g., `Portugal`, `Italy`).

---

## Phase 1: Research (before writing code)

- [ ] **Find a public data source** for reservoir/dam water levels
  - Prefer: JSON REST API > structured HTML scraping > CSV/file download
  - Required fields: reservoir name, current volume or percentage
  - Desired fields: capacity, coordinates, river, dam type, year built
  - Check update frequency: real-time/daily/weekly acceptable
  - Verify no auth required and no aggressive rate limiting
  - Document: URL pattern, data format, number parsing quirks

- [ ] **Identify top 15-20 reservoirs** by capacity
  - Cross-reference multiple sources for accuracy
  - Record: name (English + local), capacity (hm³/MCM), coordinates (lat/lng)
  - Record: river name, dam type, height, year built
  - Identify the correct embalses.net/equivalent URL pattern per reservoir

- [ ] **Verify coordinates** using a mapping API or known positions
  - All dams should fall within the country's lat/lng bounding box
  - MITECO-style OGC APIs are useful for coordinates when scraping sites lack them

---

## Phase 2: Provider Implementation (TDD)

### 2.1 Create test file

- [ ] Create `tests/test_{cc}_provider.py`
  - Copy structure from `tests/test_spain_provider.py` or `tests/test_greece_provider.py`
  - Tests to include:
    - `test_{cc}_provider_importable`
    - `test_{cc}_provider_implements_protocol` (assert `isinstance(provider, DataProvider)`)
    - `test_fetch_dams_returns_N_reservoirs` (N = your dam count)
    - `test_fetch_dams_largest_capacity` (verify largest dam's capacity_mcm)
    - `test_fetch_dams_all_have_coordinates`
    - `test_fetch_dams_all_have_capacity`
    - `test_fetch_dams_all_in_{country}_latitude_range`
    - Parser tests for any custom number/date format functions
    - `test_fetch_percentages_returns_snapshot` (with mocked HTTP response)
    - `test_fetch_percentages_raises_on_http_error`
    - `test_fetch_date_statistics_returns_stats`
    - `test_fetch_monthly_inflows_returns_empty`
    - `test_fetch_events_returns_empty`
    - `test_fetch_timeseries_returns_empty` (if no historical API)
  - Run tests — confirm they FAIL (RED step)

### 2.2 Create provider

- [ ] Create `app/providers/{cc}.py`
  - Copy structure from `app/providers/spain.py` (scraping) or `app/providers/greece.py` (API)
  - Hardcode `_{COUNTRY}_DAMS: list[DamInfo]` with metadata for all tracked reservoirs
  - Use `DamInfo` fields: `name_en` (ASCII-safe), `name_el` (local script), `capacity_m3`, `capacity_mcm`, `lat`, `lng`, `height`, `year_built`, `river_name_el`, `type_el`, `image_url`, `wikipedia_url`
  - `name_en` should be ASCII-safe (no diacritics) — used in URLs
  - `name_el` can have local characters — used for display
  - Implement required protocol methods:
    - `fetch_dams()` → return hardcoded list
    - `fetch_percentages(target_date)` → fetch from upstream, return `PercentageSnapshot`
    - `fetch_date_statistics(target_date)` → fetch from upstream, return `DateStatistics`
    - `fetch_timeseries()` → return `[]` if no historical API
    - `fetch_monthly_inflows()` → return `[]`
    - `fetch_events()` → return `[]`
    - `close()` → close the httpx client
  - Add per-sync-cycle cache if fetching individual pages (see Spain pattern)
  - Number parsing: handle European format (dot=thousands, comma=decimal) if applicable
  - Run tests — confirm they PASS (GREEN step)

---

## Phase 3: Country Configuration

### 3.1 Update country_config.py

- [ ] Edit `app/country_config.py` — add `{cc}` to ALL 4 dicts:
  ```python
  COUNTRY_LOCALE_MAP["{cc}"] = "en"
  COUNTRY_DB_PATHS["{cc}"] = "data/{cc}/water.db"
  COUNTRY_LABELS["{cc}"] = "{Country}"
  COUNTRY_MAP_CENTRES["{cc}"] = (lat, lng)  # centre of the country
  ```

### 3.2 Wire provider into registry

- [ ] Edit `app/main.py`:
  - Add import: `from app.providers.{cc} import {Country}Provider`
  - Add `elif cc == "{cc}":` branch in `_build_provider_registry()`
  - Set appropriate `base_url` for the httpx client

### 3.3 Create layout template

- [ ] Create `app/templates/{cc}/layout.html`:
  ```html
  {% extends "base.html" %}
  {% block footer_data_source %}Data: <a href="..." ...>Source Name</a>{% endblock %}
  ```

### 3.4 Create dam descriptions

- [ ] Create `app/{cc}_dam_descriptions.py`:
  - Dict mapping `name_en` → prose description (200-400 words each)
  - Export function: `get_{cc}_dam_description(name_en: str) -> str`

### 3.5 Wire into routes

- [ ] Edit `app/routes/pages.py`:
  - Add import: `from app.{cc}_dam_descriptions import get_{cc}_dam_description`
  - Add `if country == "{cc}":` branch in `_get_dam_description_for_country()`
  - Add map zoom level: `map_zoom["{cc}"] = N` (6 for large countries, 7-8 for medium, 9 for small)
  - Add sitemap block: `elif country == "{cc}":` with static dam list import

---

## Phase 4: Testing

### 4.1 Route smoke tests

- [ ] Create `tests/test_routes_{cc}.py`
  - Copy from `tests/test_routes_es.py`
  - Fixture: `{cc}_client` with `patch.object(settings, "enabled_countries", "cy,...,{cc}")`
  - Tests: dashboard, map, blog, dam detail, about, privacy, health, robots.txt, ads.txt, sitemap
  - Tests: SEO meta/OG tags, security headers, footer attribution
  - Tests: dam detail 200/404, sitemap includes `/{cc}/dam/` URLs
  - Tests: Cyprus routes still work, country nav includes {Country}

### 4.2 SEO multi-country tests

- [ ] Update `tests/test_seo_multi_country.py`:
  - Add fixture with new country enabled
  - Add hreflang cross-link tests
  - Add sitemap inclusion tests

### 4.3 Full test suite

- [ ] Run `uv run pytest tests/ -v` — ALL tests must pass

---

## Phase 5: Deployment

### 5.1 Enable in Docker

- [ ] Edit `Dockerfile`: add `{cc}` to `WL_ENABLED_COUNTRIES`
- [ ] Edit `deploy/env.example`: add `{cc}` to `WL_ENABLED_COUNTRIES`

### 5.2 Rebuild CSS

- [ ] Run: `./tailwindcss -c tailwind.config.js -i app/static/css/input.css -o app/static/css/tailwind.min.css --minify`

### 5.3 Runtime smoke test

- [ ] Run:
  ```bash
  lsof -ti :8000 | xargs -r kill -9 2>/dev/null || true
  WL_ENABLED_COUNTRIES=cy,...,{cc} timeout 30 uv run python main.py &
  sleep 8
  curl -sf http://localhost:8000/health
  curl -sf http://localhost:8000/{cc}/ -o /dev/null -w "%{http_code}"
  kill %1 2>/dev/null || true
  ```

### 5.4 Update documentation

- [ ] Edit `CLAUDE.md`:
  - Update architecture description (add `/{cc}/` mention)
  - Add provider to module table
  - Add dam descriptions to module table
  - Update test count
  - Add data source quirks to domain details section
  - Update data flow diagram
  - Update `WL_ENABLED_COUNTRIES` examples

### 5.5 Commit and push

- [ ] Commit each phase separately (provider, config, tests, deploy)
- [ ] Push to remote

---

## Common Pitfalls

1. **Number format**: European sites use dots for thousands, commas for decimals. Always verify.
2. **HTML scraping regex**: ALWAYS test against real HTML, not assumed structure. Use `curl` to fetch a sample page first.
3. **name_en must be ASCII-safe**: Used in URL paths. Remove diacritics (Évora → Evora, Châtelot → Chatelot).
4. **DamInfo fields are legacy-named**: `name_el`, `river_name_el`, `type_el` are used for ALL countries despite the `_el` suffix (historical artifact from Cyprus/Greek origin).
5. **Per-sync-cycle cache**: If your provider makes N HTTP requests for N dams, add a cache dict to avoid double-fetching when `fetch_date_statistics` and `fetch_percentages` are called back-to-back during `initial_seed`.
6. **Timeseries**: If no historical API exists, return `[]` — data builds up over time via the scheduler.
7. **Map zoom**: Small countries (Cyprus) → 9, medium (Greece) → 7, large (Spain) → 6, very large (France) → 5-6.
8. **The `_()` i18n wrapper**: Still present in templates as NullTranslations passthrough. Don't remove it.
